-- dds_core: compara cada amostra de saída com um modelo de referência do DDS, clock a clock:
--   fase(k) = fase(k-1) + M,  endereço(k) = fase(k)(31..22),
--   amostra(k) = tabela_sel[endereço(k-3)]   (2 clocks das memórias + 1 do registrador)
-- Cobre reset (saída em 0x80), as quatro formas, trocas de frequência e de forma com o DDS
-- rodando e a escrita na RAM arbitrária enquanto outra forma está na saída.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_dds_core is
end entity;

architecture sim of tb_dds_core is
	signal clk			: std_logic := '0';
	signal rst			: std_logic := '1';
	signal frequency	: unsigned (FREQ_WIDTH - 1 downto 0) := (others => '0');
	signal sel			: std_logic_vector (1 downto 0) := SEL_SINE;
	signal lut_we		: std_logic := '0';
	signal lut_waddr	: unsigned (ADDR_WIDTH - 1 downto 0) := (others => '0');
	signal lut_wdata	: std_logic_vector (DATA_WIDTH - 1 downto 0) := (others => '0');
	signal sample		: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal running		: boolean := true;

	-- padrão escrito na RAM: dente de serra (uma rampa por período)
	function pattern (a : natural) return natural is
	begin
		return a / 4;
	end function;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.dds_core
		port map (clk => clk, rst => rst, frequency => frequency, sel => sel, lut_we => lut_we,
					 lut_waddr => lut_waddr, lut_wdata => lut_wdata, sample => sample);

	stimulus : process
		type tables_t is array (0 to 3) of mem_t;
		variable tables	: tables_t := (read_mif("lut/sine_1024x8.mif"), read_mif("lut/triangle_1024x8.mif"),
												  read_mif("lut/sinc_1024x8.mif"), read_mif("lut/ecg_1024x8.mif"));
		type hist_t is array (0 to 2) of natural;
		variable hist		: hist_t := (others => 0);			-- endereços dos 3 últimos clocks
		variable phase		: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
		variable m			: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
		variable errors	: natural := 0;
		variable checked	: natural := 0;

		-- um clock: atualiza o modelo e confere a amostra
		procedure tick (name : string) is
			variable expected	: natural;
		begin
			wait until rising_edge(clk);
			expected := tables(to_integer(unsigned(sel)))(hist(2));	-- sel já atualizado na borda
			if lut_we = '1' then
				tables(3)(to_integer(lut_waddr)) := to_integer(unsigned(lut_wdata));
			end if;
			if rst = '0' then
				phase := phase + m;
			end if;
			hist := to_integer(phase(ACC_WIDTH - 1 downto ACC_WIDTH - ADDR_WIDTH)) & hist(0 to 1);
			wait for 1 ns;
			if rst = '1' then
				check(sample = DAC_MIDSCALE, "reset: amostra " & to_hstring(sample) & ", esperado 80", errors);
			else
				check(to_integer(unsigned(sample)) = expected, name & ": amostra " &
						integer'image(to_integer(unsigned(sample))) & ", esperado " & integer'image(expected) &
						" (endereço " & integer'image(hist(2)) & ")", errors);
				checked := checked + 1;
			end if;
		end procedure;

		procedure run (n : natural; name : string) is
		begin
			for i in 1 to n loop
				tick(name);
			end loop;
		end procedure;

		procedure set_frequency (f : natural) is
		begin
			frequency <= to_unsigned(f, FREQ_WIDTH);
			m := ftw_of(f);
		end procedure;
	begin
		set_frequency(100_000);
		run(5, "reset");
		rst <= '0';
		run(3_000, "seno 100 kHz");

		-- frequência e forma mudam com o DDS rodando: fase contínua
		set_frequency(262_143);
		run(1_000, "seno 262 kHz");
		set_frequency(7_919);
		sel <= SEL_SAW;
		run(2_000, "rampa");
		sel <= SEL_SINC;
		run(2_000, "sinc");
		set_frequency(100_000);
		sel <= SEL_ARB;
		run(2_000, "arbitrária (ECG inicial)");

		-- escreve a RAM arbitrária inteira enquanto o seno está na saída
		sel <= SEL_SINE;
		for a in 0 to 2 ** ADDR_WIDTH - 1 loop
			lut_we <= '1';
			lut_waddr <= to_unsigned(a, ADDR_WIDTH);
			lut_wdata <= std_logic_vector(to_unsigned(pattern(a), DATA_WIDTH));
			tick("seno durante a escrita");
		end loop;
		lut_we <= '0';
		run(10, "seno");
		sel <= SEL_ARB;
		run(2_000, "arbitrária (padrão escrito)");

		-- reset no meio: saída volta ao zero do sinal e a fase recomeça
		rst <= '1';
		phase := (others => '0');
		run(5, "reset");
		rst <= '0';
		sel <= SEL_SINE;
		set_frequency(1_000);
		run(1_000, "seno 1 kHz depois do reset");

		report integer'image(checked) & " amostras conferidas com o modelo";
		running <= false;
		finish("tb_dds_core", errors);
	end process;

end architecture;

-- LUT: as três ROMs e a RAM arbitrária, endereço por endereço.
--   1. sel = 00, 01, 10: varre os 1024 endereços e compara com os .mif (latência de 2 clocks);
--   2. sel = 11: a RAM começa com o ECG (lut/ecg_1024x8.mif);
--   3. escreve um padrão nos 1024 endereços pela porta de escrita enquanto o seno é lido,
--      e confere que a leitura do seno não foi afetada;
--   4. sel = 11 de novo: a RAM devolve o padrão escrito.
-- Rodar a partir de fpga/ (os .mif são lidos de ./lut/); o run_all.sh já faz isso.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_LUT is
end entity;

architecture sim of tb_LUT is
	signal clk			: std_logic := '0';
	signal addr			: unsigned (ADDR_WIDTH - 1 downto 0) := (others => '0');
	signal sel			: std_logic_vector (1 downto 0) := SEL_SINE;
	signal lut_we		: std_logic := '0';
	signal lut_waddr	: unsigned (ADDR_WIDTH - 1 downto 0) := (others => '0');
	signal lut_wdata	: std_logic_vector (DATA_WIDTH - 1 downto 0) := (others => '0');
	signal q				: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal running		: boolean := true;

	-- padrão escrito na RAM: 3 períodos de seno (vizinhos têm valores diferentes, o que
	-- denuncia escrita no endereço errado, e a forma é fácil de reconhecer na figura)
	function pattern (a : natural) return natural is
	begin
		return integer(round(128.0 + 120.0 * sin(2.0 * MATH_PI * 3.0 * real(a) / 1024.0)));
	end function;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.LUT
		port map (clk => clk, addr => addr, sel => sel, lut_we => lut_we, lut_waddr => lut_waddr,
					 lut_wdata => lut_wdata, qOut => q);

	stimulus : process
		constant SINE		: mem_t := read_mif("lut/sine_1024x8.mif");
		constant TRIANGLE	: mem_t := read_mif("lut/triangle_1024x8.mif");
		constant SINC		: mem_t := read_mif("lut/sinc_1024x8.mif");
		constant ECG		: mem_t := read_mif("lut/ecg_1024x8.mif");
		variable written	: mem_t;
		variable errors	: natural := 0;

		-- varre os endereços em ordem embaralhada; o endereço posto antes da borda k é
		-- registrado nela, e a leitura aparece em q depois da borda k+1 (2 clocks).
		-- Com write = true, escreve o padrão ao mesmo tempo.
		procedure sweep (s : std_logic_vector; mem : mem_t; name : string; write : boolean := false) is
			type hist_t is array (0 to 1) of natural;
			variable hist	: hist_t := (others => 0);
			variable a		: natural;
			variable bad	: natural := 0;
		begin
			sel <= s;
			for k in 0 to 2 ** ADDR_WIDTH loop
				a := (k * 389) mod 2 ** ADDR_WIDTH;		-- 389 é primo: passa por todos
				addr <= to_unsigned(a, ADDR_WIDTH);
				if write and k < 2 ** ADDR_WIDTH then
					lut_we <= '1';
					lut_waddr <= to_unsigned(1023 - a, ADDR_WIDTH);
					lut_wdata <= std_logic_vector(to_unsigned(pattern(1023 - a), DATA_WIDTH));
				else
					lut_we <= '0';
				end if;
				hist := a & hist(0 to 0);
				wait until rising_edge(clk);
				wait for 1 ns;
				if k >= 1 then
					if to_integer(unsigned(q)) /= mem(hist(1)) then
						bad := bad + 1;
					end if;
					check(to_integer(unsigned(q)) = mem(hist(1)), name & ": endereço " &
							integer'image(hist(1)) & " leu " & integer'image(to_integer(unsigned(q))) &
							", esperado " & integer'image(mem(hist(1))), errors);
				end if;
			end loop;
			lut_we <= '0';
			report name & ": 1024 endereços lidos, " & integer'image(bad) & " diferenças";
		end procedure;
	begin
		for a in written'range loop
			written(a) := pattern(a);
		end loop;
		wait until falling_edge(clk);

		sweep(SEL_SINE, SINE, "seno");
		sweep(SEL_SAW, TRIANGLE, "rampa");
		sweep(SEL_SINC, SINC, "sinc");
		sweep(SEL_ARB, ECG, "arbitrária (ECG inicial)");
		sweep(SEL_SINE, SINE, "seno durante a escrita na RAM", write => true);
		sweep(SEL_ARB, written, "arbitrária (depois da escrita)");

		running <= false;
		finish("tb_LUT", errors);
	end process;

end architecture;

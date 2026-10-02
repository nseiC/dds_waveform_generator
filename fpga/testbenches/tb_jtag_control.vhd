-- jtag_control: do JTAG (tck de ~6 MHz) até os registradores de 10 MHz, com o testbench no
-- papel da IP do Virtual JTAG e do quartus_stp:
--   1. IR 01 e IR 10 mudam frequência e forma de onda;
--   2. 64 escritas na LUT (IR 11) viram 64 pulsos de lut_we, na ordem, com endereço e dado;
--   3. DR em bypass (IR 00) não muda nada.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_jtag_control is
end entity;

architecture sim of tb_jtag_control is
	constant N_WRITES	: positive := 64;
	type word_array is array (0 to N_WRITES - 1) of natural;

	signal tck, tdi, tdo					: std_logic := '0';
	signal ir_in, ir_out					: std_logic_vector (IR_WIDTH - 1 downto 0) := IR_NOP;
	signal vs_cdr, vs_sdr, vs_udr		: std_logic := '0';
	signal clk								: std_logic := '0';
	signal rst								: std_logic := '1';
	signal frequency						: unsigned (FREQ_WIDTH - 1 downto 0);
	signal sel								: std_logic_vector (1 downto 0);
	signal lut_we							: std_logic;
	signal lut_waddr						: unsigned (ADDR_WIDTH - 1 downto 0);
	signal lut_wdata						: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal activity						: std_logic;
	signal running							: boolean := true;
	signal writes							: word_array := (others => 0);
	signal write_count						: natural := 0;

	function word (i : natural) return natural is
	begin
		return ((i * 13) mod 1024) * 256 + (i * 29 + 7) mod 256;	-- endereço & dado
	end function;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.jtag_control
		port map (tck => tck, tdi => tdi, tdo => tdo, ir_in => ir_in, ir_out => ir_out,
					 vs_cdr => vs_cdr, vs_sdr => vs_sdr, vs_udr => vs_udr, clk => clk, rst => rst,
					 frequency => frequency, sel => sel, lut_we => lut_we, lut_waddr => lut_waddr,
					 lut_wdata => lut_wdata, activity => activity);

	-- registra cada escrita na LUT vista no domínio de 10 MHz
	monitor : process(clk)
	begin
		if rising_edge(clk) and lut_we = '1' then
			if write_count < N_WRITES then
				writes(write_count) <= to_integer(lut_waddr) * 256 + to_integer(unsigned(lut_wdata));
			end if;
			write_count <= write_count + 1;
		end if;
	end process;

	stimulus : process
		variable errors	: natural := 0;
		variable cap		: std_logic_vector (DR_WIDTH - 1 downto 0);

		procedure dr (value : natural) is
		begin
			vjtag_dr(tck, tdi, vs_cdr, vs_sdr, vs_udr, tdo, std_logic_vector(to_unsigned(value, DR_WIDTH)), cap);
		end procedure;
	begin
		wait for 5 * T_CLK10;
		rst <= '0';
		wait for 5 * T_CLK10;
		check(frequency = 1000 and sel = SEL_SINE, "valores depois do reset", errors);

		-- 1. frequência e forma de onda
		vjtag_ir(tck, ir_in, IR_FREQ);
		dr(440);
		wait for 10 * T_CLK10;
		check(frequency = 440, "IR 01: frequência = " & integer'image(to_integer(frequency)), errors);
		dr(262_143);
		wait for 10 * T_CLK10;
		check(frequency = 262_143, "IR 01: frequência = " & integer'image(to_integer(frequency)), errors);
		vjtag_ir(tck, ir_in, IR_SEL);
		dr(2);
		wait for 10 * T_CLK10;
		check(sel = SEL_SINC, "IR 10: sel = " & to_string(sel), errors);

		-- 2. escritas na LUT, uma atrás da outra como o quartus_stp faz
		vjtag_ir(tck, ir_in, IR_LUT);
		for i in 0 to N_WRITES - 1 loop
			dr(word(i));
		end loop;
		wait for 10 * T_CLK10;
		check(write_count = N_WRITES, integer'image(write_count) & " escritas na LUT, esperado " &
				integer'image(N_WRITES), errors);
		for i in 0 to N_WRITES - 1 loop
			check(writes(i) = word(i), "escrita " & integer'image(i) & ": " & integer'image(writes(i)) &
					", esperado " & integer'image(word(i)), errors);
		end loop;

		-- 3. bypass não muda nada
		vjtag_ir(tck, ir_in, IR_NOP);
		dr(12_345);
		wait for 10 * T_CLK10;
		check(frequency = 262_143 and sel = SEL_SINC and write_count = N_WRITES, "bypass mudou a configuração", errors);

		running <= false;
		finish("tb_jtag_control", errors);
	end process;

end architecture;

-- control_registers: valores depois do reset (1 kHz, seno), decodificação de cada instrução,
-- pulso de 1 clock em lut_we, IR 00 ignorado e activity trocando a cada comando aceito.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_control_registers is
end entity;

architecture sim of tb_control_registers is
	signal clk			: std_logic := '0';
	signal rst			: std_logic := '1';
	signal cmd_valid	: std_logic := '0';
	signal cmd_ir		: std_logic_vector (IR_WIDTH - 1 downto 0) := IR_NOP;
	signal cmd_data	: std_logic_vector (DR_WIDTH - 1 downto 0) := (others => '0');
	signal frequency	: unsigned (FREQ_WIDTH - 1 downto 0);
	signal sel			: std_logic_vector (1 downto 0);
	signal lut_we		: std_logic;
	signal lut_waddr	: unsigned (ADDR_WIDTH - 1 downto 0);
	signal lut_wdata	: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal activity	: std_logic;
	signal running		: boolean := true;
	signal we_pulses	: natural := 0;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.control_registers
		generic map (DEFAULT_FREQUENCY => 1000, DEFAULT_SEL => SEL_SINE)
		port map (clk => clk, rst => rst, cmd_valid => cmd_valid, cmd_ir => cmd_ir, cmd_data => cmd_data,
					 frequency => frequency, sel => sel, lut_we => lut_we, lut_waddr => lut_waddr,
					 lut_wdata => lut_wdata, activity => activity);

	count_we : process(clk)
	begin
		if rising_edge(clk) and lut_we = '1' then
			we_pulses <= we_pulses + 1;
		end if;
	end process;

	stimulus : process
		variable errors	: natural := 0;
		variable act		: std_logic;

		procedure send (ir : std_logic_vector; value : natural) is
		begin
			wait until falling_edge(clk);
			cmd_ir <= ir;
			cmd_data <= std_logic_vector(to_unsigned(value, DR_WIDTH));
			cmd_valid <= '1';
			wait until falling_edge(clk);
			cmd_valid <= '0';
		end procedure;
	begin
		wait for 3 * T_CLK10;
		wait until falling_edge(clk);
		rst <= '0';
		wait until falling_edge(clk);
		check(frequency = 1000, "frequência depois do reset: " & integer'image(to_integer(frequency)), errors);
		check(sel = SEL_SINE, "sel depois do reset: " & to_string(sel), errors);
		check(lut_we = '0', "lut_we ativo depois do reset", errors);
		act := activity;

		send(IR_FREQ, 262_143);
		check(frequency = 262_143, "IR 01: frequência = " & integer'image(to_integer(frequency)), errors);
		check(activity /= act, "activity não trocou", errors);
		act := activity;

		send(IR_SEL, 16#3FFFE#);											-- só os 2 bits de baixo contam
		check(sel = "10", "IR 10: sel = " & to_string(sel), errors);
		check(frequency = 262_143, "IR 10 mexeu na frequência", errors);

		-- IR 11: um pulso de lut_we por comando, com endereço e dado do DR
		for a in 0 to 31 loop
			send(IR_LUT, (1023 - a) * 256 + a * 3);
			check(lut_waddr = to_unsigned(1023 - a, ADDR_WIDTH), "IR 11: endereço " &
					integer'image(to_integer(lut_waddr)), errors);
			check(lut_wdata = std_logic_vector(to_unsigned(a * 3, DATA_WIDTH)), "IR 11: dado " &
					to_hstring(lut_wdata), errors);
		end loop;
		wait until falling_edge(clk);
		check(we_pulses = 32, integer'image(we_pulses) & " pulsos de lut_we, esperado 32", errors);
		check(sel = "10" and frequency = 262_143, "IR 11 mexeu na configuração", errors);

		-- IR 00 não faz nada
		act := activity;
		send(IR_NOP, 12_345);
		check(frequency = 262_143 and sel = "10", "IR 00 mexeu na configuração", errors);
		check(activity = act, "IR 00 trocou activity", errors);
		check(we_pulses = 32, "IR 00 gerou escrita na LUT", errors);

		-- reset volta aos valores padrão
		rst <= '1';
		wait until falling_edge(clk);
		wait until falling_edge(clk);
		check(frequency = 1000 and sel = SEL_SINE, "reset não voltou aos valores padrão", errors);

		running <= false;
		finish("tb_control_registers", errors);
	end process;

end architecture;

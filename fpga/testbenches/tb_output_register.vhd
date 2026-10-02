-- output_register: zero do sinal (0x80) durante o reset, carrega na borda de subida.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_output_register is
end entity;

architecture sim of tb_output_register is
	signal clk		: std_logic := '0';
	signal rst		: std_logic := '1';
	signal d, q		: std_logic_vector (DATA_WIDTH - 1 downto 0) := (others => '0');
	signal running	: boolean := true;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.output_register
		port map (clk => clk, rst => rst, d => d, q => q);

	stimulus : process
		variable errors : natural := 0;
	begin
		d <= x"FF";
		wait for 3 * T_CLK10;
		check(q = DAC_MIDSCALE, "reset: saída " & to_hstring(q) & ", esperado 80", errors);
		wait until falling_edge(clk);
		rst <= '0';

		for i in 0 to 255 loop
			d <= std_logic_vector(to_unsigned(i, DATA_WIDTH));
			wait until rising_edge(clk);
			wait for 1 ns;
			check(q = std_logic_vector(to_unsigned(i, DATA_WIDTH)), "não carregou " & integer'image(i), errors);
			wait until falling_edge(clk);
		end loop;

		rst <= '1';
		wait for 1 ns;
		check(q = DAC_MIDSCALE, "reset assíncrono não voltou para 80", errors);

		running <= false;
		finish("tb_output_register", errors);
	end process;

end architecture;

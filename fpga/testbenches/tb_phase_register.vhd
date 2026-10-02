-- phase_register: carrega só na borda de subida, segura o valor entre bordas e zera na hora
-- com o reset assíncrono.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_phase_register is
end entity;

architecture sim of tb_phase_register is
	signal clk			: std_logic := '0';
	signal rst			: std_logic := '1';
	signal word, q		: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
	signal running		: boolean := true;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.phase_register
		port map (clk => clk, rst => rst, word => word, wOut => q);

	stimulus : process
		variable errors : natural := 0;

		-- valores de 32 bits diferentes a cada ciclo, com todos os bits mudando
		function value (i : natural) return unsigned is
		begin
			return rotate_left(unsigned'(x"9E3779B9"), i) xor to_unsigned(i, ACC_WIDTH);
		end function;
	begin
		wait for 3 * T_CLK10;
		check(q = 0, "reset: saída deveria ser 0", errors);
		rst <= '0';

		for i in 1 to 100 loop
			wait until falling_edge(clk);
			word <= value(i);
			wait for 1 ns;
			check(q = value(i - 1) or i = 1,
					"mudou fora da borda de subida no ciclo " & integer'image(i), errors);
			wait until rising_edge(clk);
			wait for 1 ns;
			check(q = value(i),
					"não carregou na borda de subida no ciclo " & integer'image(i), errors);
		end loop;

		-- reset assíncrono no meio do ciclo
		wait for T_CLK10 / 4;
		rst <= '1';
		wait for 1 ns;
		check(q = 0, "reset assíncrono não zerou na hora", errors);
		wait until rising_edge(clk);
		wait for 1 ns;
		check(q = 0, "carregou com o reset ativo", errors);

		running <= false;
		finish("tb_phase_register", errors);
	end process;

end architecture;

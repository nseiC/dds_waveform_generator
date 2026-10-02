-- reset_sync: entra em reset na hora em que rst_in sobe (em qualquer ponto do ciclo) e sai
-- exatamente na 3ª borda de subida depois de rst_in cair.

library ieee;
use ieee.std_logic_1164.all;
use work.tb_utils_pkg.all;

entity tb_reset_sync is
end entity;

architecture sim of tb_reset_sync is
	constant STAGES	: positive := 3;
	signal clk			: std_logic := '0';
	signal rst_in		: std_logic := '1';
	signal rst_out		: std_logic;
	signal running		: boolean := true;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.reset_sync
		generic map (STAGES => STAGES)
		port map (clk => clk, rst_in => rst_in, rst_out => rst_out);

	stimulus : process
		variable errors : natural := 0;
	begin
		wait for 1 ns;
		check(rst_out = '1', "começa fora do reset", errors);

		for trial in 1 to 5 loop
			-- solta rst_in num ponto qualquer do ciclo
			wait for T_CLK10 * 3 + trial * 17 ns;
			rst_in <= '0';
			for edge in 1 to STAGES loop
				wait until rising_edge(clk);
				wait for 1 ns;
				if edge < STAGES then
					check(rst_out = '1', "saiu do reset cedo, na borda " & integer'image(edge), errors);
				else
					check(rst_out = '0', "não saiu do reset na borda " & integer'image(STAGES), errors);
				end if;
			end loop;
			wait for 5 * T_CLK10;
			check(rst_out = '0', "voltou para reset sozinho", errors);

			-- entra em reset no meio do ciclo, sem esperar o clock
			wait for trial * 13 ns;
			rst_in <= '1';
			wait for 1 ns;
			check(rst_out = '1', "não entrou em reset na hora", errors);
		end loop;

		running <= false;
		finish("tb_reset_sync", errors);
	end process;

end architecture;

-- cmd_sync: comandos saem de um domínio de ~6 MHz (como o tck) e chegam no de 10 MHz.
--   1. 300 comandos com dados aleatórios e intervalos aleatórios (no mínimo um DR de 18 bits):
--      cada um chega uma única vez, na ordem, com o dado certo;
--   2. um reset no destino não repete o último comando.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.tb_utils_pkg.all;

entity tb_cmd_sync is
end entity;

architecture sim of tb_cmd_sync is
	constant WIDTH		: positive := 20;
	constant N_CMDS	: positive := 300;

	type data_array is array (1 to N_CMDS) of std_logic_vector (WIDTH - 1 downto 0);

	signal clk, src_clk	: std_logic := '0';
	signal rst				: std_logic := '1';
	signal src_toggle		: std_logic := '0';
	signal src_data		: std_logic_vector (WIDTH - 1 downto 0) := (others => '0');
	signal dst_valid		: std_logic;
	signal dst_data		: std_logic_vector (WIDTH - 1 downto 0);
	signal running			: boolean := true;
	signal sent_data		: data_array;
	signal sent				: natural := 0;
	signal received		: natural := 0;
	signal errors_rx		: natural := 0;
begin

	clk <= not clk after T_CLK10 / 2 when running;
	src_clk <= not src_clk after T_TCK / 2 when running;	-- sem relação de fase com clk

	dut : entity work.cmd_sync
		generic map (WIDTH => WIDTH)
		port map (clk => clk, rst => rst, src_toggle => src_toggle, src_data => src_data,
					 dst_valid => dst_valid, dst_data => dst_data);

	-- origem: muda o dado e troca o toggle na mesma borda, como o vjtag_dr no Update-DR
	source : process
		variable seed1, seed2	: positive := 3;
		variable r					: real;
		variable gap				: natural;
	begin
		wait for 1 us;
		for i in 1 to N_CMDS loop
			uniform(seed1, seed2, r);
			gap := 22 + integer(floor(r * 40.0));
			for k in 1 to gap loop
				wait until rising_edge(src_clk);
			end loop;
			uniform(seed1, seed2, r);
			src_data <= std_logic_vector(to_unsigned(integer(floor(r * 2.0 ** WIDTH)), WIDTH));
			src_toggle <= not src_toggle;
			wait for 0 ns;
			sent_data(i) <= src_data;
			sent <= i;
		end loop;
		wait;
	end process;

	-- destino: confere cada pulso de dst_valid
	sink : process(clk)
		variable n, e : natural := 0;
	begin
		if rising_edge(clk) and dst_valid = '1' then
			n := n + 1;
			if n > N_CMDS or n > sent then
				e := e + 1;
				report "comando a mais (nº " & integer'image(n) & ")" severity error;
			elsif dst_data /= sent_data(n) then
				e := e + 1;
				if e <= MAX_REPORTS then
					report "comando " & integer'image(n) & ": dado " & to_hstring(dst_data) &
							 ", esperado " & to_hstring(sent_data(n)) severity error;
				end if;
			end if;
			received <= n;
			errors_rx <= e;
		end if;
	end process;

	control : process
		variable errors : natural := 0;
	begin
		wait for 5 * T_CLK10;
		rst <= '0';
		wait until sent = N_CMDS;
		wait for 20 * T_CLK10;
		check(received = N_CMDS, integer'image(received) & " comandos recebidos, esperado " &
				integer'image(N_CMDS), errors);

		-- reset no destino depois do último comando: nada pode ser repetido
		wait until rising_edge(clk);
		rst <= '1';
		wait for 5 * T_CLK10;
		rst <= '0';
		wait for 20 * T_CLK10;
		check(received = N_CMDS, "o reset repetiu um comando", errors);

		report integer'image(received) & " comandos atravessaram o domínio de clock";
		running <= false;
		finish("tb_cmd_sync", errors + errors_rx);
	end process;

end architecture;

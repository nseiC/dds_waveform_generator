-- Registrador de fase do acumulador, com reset assíncrono. Atualiza na borda de subida,
-- como o resto do caminho de dados.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity phase_register is
	port(
		clk, rst		: in std_logic;
		word			: in unsigned (ACC_WIDTH - 1 downto 0);
		wOut			: out unsigned (ACC_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of phase_register is
begin

	sequential : process(clk, rst)
	begin
		if rst = '1' then
			wOut <= (others => '0');
		elsif rising_edge(clk) then
			wOut <= word;
		end if;
	end process;

end architecture;

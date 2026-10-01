library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity phase_register is
	port(
		clk,rst		: in std_logic;
		word			: in unsigned (31 downto 0);
		wOut			: out unsigned (31 downto 0)
	);
end entity;

architecture behavior of phase_register is

	begin
	
	sequential : process(clk, rst) 
		begin
			if rst = '1' then
				wOut <= (others => '0');
			elsif clk'EVENT and clk = '0' then
				wOut <= word;
			end if;
	end process;

end architecture;
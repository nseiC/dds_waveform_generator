library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity truncator is
	port(
		wIn	: in unsigned (31 downto 0);
		bOUt	: out unsigned (9 downto 0)
	);
end entity;

architecture behavior of truncator is
	
	begin
	
	combinacional: process(wIn)
		begin
			bOut <= wIn (31 downto 22);
		end process;
	
end architecture;
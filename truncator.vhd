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
			bOut (0) <= wIn (0);
			bOut (1) <= wIn (1);
			bOut (2) <= wIn (2);
			bOut (3) <= wIn (3);
			bOut (4) <= wIn (4);
			bOut (5) <= wIn (5);
			bOut (6) <= wIn (6);
			bOut (7) <= wIn (7);
			bOut (8) <= wIn (8);
			bOut (9) <= wIn (9);
		end process;
	
end architecture;
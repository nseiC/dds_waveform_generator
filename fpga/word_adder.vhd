library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity word_adder is
	port(
		ftw		: in unsigned (31 downto 0);
		feedback	: in unsigned (31 downto 0);
		wOut		: out unsigned(31 downto 0)
	);
end entity;

architecture behavior of word_adder is
	begin
		wOUt <= ftw + feedback;
end architecture;
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity frequency_translator is
	port(
		frequency	: in unsigned (17 downto 0);
		FTW			: out unsigned (31 downto 0)
	);
end entity;

architecture behavior of frequency_translator is
	constant S : natural := 24;
	constant K : unsigned(32 downto 0) := "1" & x"AD7F29AC";   -- round(2^56 / 10 MHz)
	signal   P : unsigned(50 downto 0);                       -- 18 + 33 bits
begin
	P   <= frequency * K;
	FTW <= resize(P(P'high downto S), FTW'length);
end architecture;
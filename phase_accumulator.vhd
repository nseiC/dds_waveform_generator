library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity phase_accumulator is
	port(
		frequency	: in unsigned (17 downto 0);
		clk,rst 		: in std_logic;
		bOut			: out unsigned (9 downto 0)
		);
end entity;

architecture behavior of phase_accumulator is

	component word_adder is
		port(
			ftw		: in unsigned (31 downto 0);
			feedback	: in unsigned (31 downto 0);
			wOut		: out unsigned(31 downto 0)
		);
	end component;
	
	component phase_register is
		port(
			clk,rst		: in std_logic;
			word			: in unsigned (31 downto 0);
			wOut			: out unsigned (31 downto 0)
		);
	end component;
	
	component truncator is
		port(
			wIn	: in unsigned (31 downto 0);
			bOUt	: out unsigned (9 downto 0)
		);
	end component;

	component frequency_translator is
		port(
			frequency	: in unsigned (17 downto 0);
			FTW			: out unsigned (31 downto 0)
		);
	end component;	
	
	signal ftw,fbw,my_word,my_word_out : unsigned ( 31 downto 0);
	
	begin

	ft1	:	frequency_translator port map(frequency, ftw);
	wa1	:	word_adder				port map(ftw, fbw, my_word);
	pr1	:	phase_register			port map(clk, rst,my_word,my_word_out);
	tr1	:	truncator				port map(my_word_out,bOut);
	
end architecture;
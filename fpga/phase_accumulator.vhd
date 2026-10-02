-- Acumulador de fase: converte a frequência em FTW, soma a FTW à fase a cada clock e
-- entrega os bits altos da fase como endereço da LUT.
--
--   frequency -> frequency_translator -> word_adder -> phase_register -+-> truncator -> bOut
--                                            ^                         |
--                                            +------- realimentação ---+

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity phase_accumulator is
	port(
		frequency	: in unsigned (FREQ_WIDTH - 1 downto 0);
		clk, rst		: in std_logic;
		bOut			: out unsigned (ADDR_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of phase_accumulator is
	signal ftw, my_word, my_word_out : unsigned (ACC_WIDTH - 1 downto 0);
begin

	ft1 : entity work.frequency_translator
		port map (frequency => frequency, FTW => ftw);

	wa1 : entity work.word_adder
		port map (ftw => ftw, feedback => my_word_out, wOut => my_word);

	pr1 : entity work.phase_register
		port map (clk => clk, rst => rst, word => my_word, wOut => my_word_out);

	tr1 : entity work.truncator
		port map (wIn => my_word_out, bOut => bOut);

end architecture;

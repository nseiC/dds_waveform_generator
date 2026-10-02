-- Converte a frequência pedida (Hz) na palavra de sintonia (FTW) do acumulador de fase.
-- M = f * 2^32 / f_clk sem divisor: multiplicação por FTW_K = round(2^56 / f_clk) em ponto
-- fixo Q24. Para f de 0 a 262 143 Hz o erro de M é menor que 1 LSB.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity frequency_translator is
	port(
		frequency	: in unsigned (FREQ_WIDTH - 1 downto 0);
		FTW			: out unsigned (ACC_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of frequency_translator is
	signal P : unsigned (FREQ_WIDTH + FTW_K'length - 1 downto 0);	-- 18 + 33 bits
begin
	P   <= frequency * FTW_K;
	FTW <= resize(P(P'high downto FTW_SHIFT), FTW'length);
end architecture;

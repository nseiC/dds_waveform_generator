-- Somador do acumulador de fase: FTW + fase atual. O estouro natural do resultado de
-- 32 bits é a volta de 2*pi.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity word_adder is
	port(
		ftw		: in unsigned (ACC_WIDTH - 1 downto 0);
		feedback	: in unsigned (ACC_WIDTH - 1 downto 0);
		wOut		: out unsigned (ACC_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of word_adder is
begin
	wOut <= ftw + feedback;
end architecture;

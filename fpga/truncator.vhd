-- Truncamento de fase: os ADDR_WIDTH bits mais significativos da fase endereçam a LUT
-- (fase(31..22) para 1024 amostras por período).

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity truncator is
	port(
		wIn	: in unsigned (ACC_WIDTH - 1 downto 0);
		bOut	: out unsigned (ADDR_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of truncator is
begin
	bOut <= wIn(ACC_WIDTH - 1 downto ACC_WIDTH - ADDR_WIDTH);
end architecture;

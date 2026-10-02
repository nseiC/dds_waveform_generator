-- Registrador da amostra que vai para o DAC. Os 8 bits mudam juntos na mesma borda (no
-- top-level ele vira registrador de I/O, ver FAST_OUTPUT_REGISTER no DDS.qsf), o que
-- evita glitches no DAC0800, que não tem latch. No reset a saída fica no zero do sinal.

library ieee;
use ieee.std_logic_1164.all;
use work.dds_pkg.all;

entity output_register is
	port(
		clk, rst	: in std_logic;
		d			: in std_logic_vector (DATA_WIDTH - 1 downto 0);
		q			: out std_logic_vector (DATA_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of output_register is
begin

	sequential : process(clk, rst)
	begin
		if rst = '1' then
			q <= DAC_MIDSCALE;
		elsif rising_edge(clk) then
			q <= d;
		end if;
	end process;

end architecture;

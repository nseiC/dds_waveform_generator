-- Núcleo do DDS: acumulador de fase, LUT e registrador de saída, tudo no clock de 10 MHz.
-- Recebe a configuração já no domínio do clock (frequência, forma de onda e escrita na
-- LUT arbitrária) e entrega uma amostra por clock para o DAC.
--
-- Latência: a amostra registrada em sample corresponde à fase de 3 clocks antes
-- (2 das memórias + 1 do registrador de saída).

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity dds_core is
	port(
		clk, rst		: in std_logic;
		frequency	: in unsigned (FREQ_WIDTH - 1 downto 0);
		sel			: in std_logic_vector (1 downto 0);
		lut_we		: in std_logic;
		lut_waddr	: in unsigned (ADDR_WIDTH - 1 downto 0);
		lut_wdata	: in std_logic_vector (DATA_WIDTH - 1 downto 0);
		sample		: out std_logic_vector (DATA_WIDTH - 1 downto 0)
	);
end entity;

architecture structure of dds_core is
	signal addr		: unsigned (ADDR_WIDTH - 1 downto 0);
	signal q_lut	: std_logic_vector (DATA_WIDTH - 1 downto 0);
begin

	pha : entity work.phase_accumulator
		port map (frequency => frequency, clk => clk, rst => rst, bOut => addr);

	lut1 : entity work.LUT
		port map (clk => clk, addr => addr, sel => sel, lut_we => lut_we, lut_waddr => lut_waddr,
					 lut_wdata => lut_wdata, qOut => q_lut);

	outreg : entity work.output_register
		port map (clk => clk, rst => rst, d => q_lut, q => sample);

end architecture;

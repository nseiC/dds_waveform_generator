-- Clock do DAC no pino, como no código legado (GPIO[1]): cópia do clock de 10 MHz com a borda
-- de subida no meio de cada amostra, 50 ns depois de os bits mudarem.
-- Usa um registrador DDR de saída (altddio_out): '0' depois da borda de subida de clk e '1'
-- depois da de descida. É o jeito recomendado de levar um clock a um pino, sem passar o
-- clock pela lógica.
-- O DAC0800 não usa clock; o pino fica disponível para um DAC com registrador de entrada.

library ieee;
use ieee.std_logic_1164.all;

library altera_mf;
use altera_mf.altera_mf_components.all;

entity dac_clock is
	port(
		clk		: in std_logic;
		dac_clk	: out std_logic
	);
end entity;

architecture structure of dac_clock is
	constant LOW	: std_logic_vector (0 downto 0) := "0";
	constant HIGH	: std_logic_vector (0 downto 0) := "1";
	signal q			: std_logic_vector (0 downto 0);
begin

	ddio : altddio_out
		generic map (
			extend_oe_disable => "OFF",
			intended_device_family => "Cyclone IV E",
			invert_output => "OFF",
			lpm_type => "altddio_out",
			oe_reg => "UNREGISTERED",
			power_up_high => "OFF",
			width => 1
		)
		port map (
			datain_h => LOW,		-- vale depois da borda de subida de clk
			datain_l => HIGH,		-- vale depois da borda de descida
			outclock => clk,
			dataout => q
		);

	dac_clk <= q(0);

end architecture;

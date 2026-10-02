-- Conversão fase -> amplitude: três ROMs (seno, rampa, sinc), a RAM da forma arbitrária e o
-- multiplexador de saída. Todas as memórias registram endereço e saída, então qOut
-- corresponde ao endereço de 2 clocks antes.
-- A RAM arbitrária é lida no endereço da fase e escrita no endereço que vem do PC
-- (lut_waddr), sem interromper a leitura.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity LUT is
	port(
		clk			: in std_logic;
		addr			: in unsigned (ADDR_WIDTH - 1 downto 0);
		sel			: in std_logic_vector (1 downto 0);
		lut_we		: in std_logic;
		lut_waddr	: in unsigned (ADDR_WIDTH - 1 downto 0);
		lut_wdata	: in std_logic_vector (DATA_WIDTH - 1 downto 0);
		qOut			: out std_logic_vector (DATA_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of LUT is
	signal qsine, qsaw, qsinc, qarb	: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal raddr, waddr					: std_logic_vector (ADDR_WIDTH - 1 downto 0);
begin
	raddr <= std_logic_vector(addr);
	waddr <= std_logic_vector(lut_waddr);

	sine : entity work.sine_LUT
		port map (address => raddr, clock => clk, q => qsine);

	saw : entity work.saw_LUT
		port map (address => raddr, clock => clk, q => qsaw);

	sinc : entity work.sinc_LUT
		port map (address => raddr, clock => clk, q => qsinc);

	arb : entity work.arbitrary_LUT
		port map (clock => clk, data => lut_wdata, rdaddress => raddr, wraddress => waddr,
					 wren => lut_we, q => qarb);

	mux : entity work.out_mux
		port map (sel => sel, q_sine => qsine, q_saw => qsaw, q_sinc => qsinc, q_arb => qarb,
					 qout => qOut);

end architecture;

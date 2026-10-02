-- Top-level do gerador DDS na DE2-115: só liga os blocos aos pinos da placa.
--
--   clk_50 -> PLL -> clk10 (10 MHz) ------------------------------+
--   rst_n + locked -> reset_sync -> rst                            |
--   PC -> jtag_interface -> frequência, sel, escrita na LUT -> dds_core -> dac (8 bits)
--
-- Pinos (DDS.qsf): clk_50 = CLOCK_50, rst_n = KEY[0], dac = GPIO[9..2] (dac(0) é o LSB),
-- dac_gnd = GPIO[0], led_locked = LEDG[0], led_cmd = LEDG[1].

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity DDS is
	generic(
		DEFAULT_FREQUENCY	: natural := 1000;							-- Hz, até o PC mandar outra
		DEFAULT_SEL			: std_logic_vector (1 downto 0) := SEL_SINE
	);
	port(
		clk_50		: in std_logic;											-- 50 MHz da placa
		rst_n			: in std_logic;											-- KEY[0], ativo em '0'
		dac			: out std_logic_vector (DATA_WIDTH - 1 downto 0);	-- barramento do DAC0800
		dac_gnd		: out std_logic;											-- referência de terra no cabo
		led_locked	: out std_logic;											-- PLL travado
		led_cmd		: out std_logic											-- muda a cada comando do PC
	);
end entity;

architecture structure of DDS is
	signal clk10, locked			: std_logic;
	signal pll_rst, rst_async	: std_logic;
	signal rst						: std_logic;
	signal frequency				: unsigned (FREQ_WIDTH - 1 downto 0);
	signal sel						: std_logic_vector (1 downto 0);
	signal lut_we					: std_logic;
	signal lut_waddr				: unsigned (ADDR_WIDTH - 1 downto 0);
	signal lut_wdata				: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal activity				: std_logic;
begin

	pll_rst <= not rst_n;
	rst_async <= pll_rst or not locked;

	pll1 : entity work.PLL
		port map (areset => pll_rst, inclk0 => clk_50, c0 => clk10, locked => locked);

	rsync : entity work.reset_sync
		port map (clk => clk10, rst_in => rst_async, rst_out => rst);

	pc : entity work.jtag_interface
		generic map (DEFAULT_FREQUENCY => DEFAULT_FREQUENCY, DEFAULT_SEL => DEFAULT_SEL)
		port map (clk => clk10, rst => rst, frequency => frequency, sel => sel, lut_we => lut_we,
					 lut_waddr => lut_waddr, lut_wdata => lut_wdata, activity => activity);

	core : entity work.dds_core
		port map (clk => clk10, rst => rst, frequency => frequency, sel => sel, lut_we => lut_we,
					 lut_waddr => lut_waddr, lut_wdata => lut_wdata, sample => dac);

	dac_gnd <= '0';
	led_locked <= locked;
	led_cmd <= activity;

end architecture;

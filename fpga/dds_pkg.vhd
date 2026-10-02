-- Constantes compartilhadas pelo DDS: larguras do caminho de dados, conversão Hz -> FTW,
-- protocolo do Virtual JTAG e códigos das formas de onda.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package dds_pkg is

	-- caminho de dados
	constant ACC_WIDTH	: natural := 32;		-- acumulador de fase (N)
	constant ADDR_WIDTH	: natural := 10;		-- endereço da LUT (P): 1024 amostras por período
	constant DATA_WIDTH	: natural := 8;		-- amostra e DAC (D), offset binary
	constant FREQ_WIDTH	: natural := 18;		-- frequência pedida pelo PC, inteiro em Hz

	-- Hz -> FTW: M = (f * FTW_K) >> FTW_SHIFT, com FTW_K = round(2^56 / f_clk) e f_clk = 10 MHz
	constant FTW_SHIFT	: natural := 24;
	constant FTW_K			: unsigned (32 downto 0) := "1" & x"AD7F29AC";	-- 7 205 759 404

	-- Virtual JTAG: IR de 2 bits, DR de 18 bits
	constant IR_WIDTH		: natural := 2;
	constant DR_WIDTH		: natural := 18;
	constant IR_NOP		: std_logic_vector (IR_WIDTH - 1 downto 0) := "00";	-- bypass
	constant IR_FREQ		: std_logic_vector (IR_WIDTH - 1 downto 0) := "01";	-- frequência em Hz
	constant IR_SEL		: std_logic_vector (IR_WIDTH - 1 downto 0) := "10";	-- forma de onda
	constant IR_LUT		: std_logic_vector (IR_WIDTH - 1 downto 0) := "11";	-- endereço(17..8) & dado(7..0)

	-- formas de onda (sel)
	constant SEL_SINE		: std_logic_vector (1 downto 0) := "00";
	constant SEL_SAW		: std_logic_vector (1 downto 0) := "01";
	constant SEL_SINC		: std_logic_vector (1 downto 0) := "10";
	constant SEL_ARB		: std_logic_vector (1 downto 0) := "11";

	-- zero do sinal em offset binary: saída do DAC durante o reset
	constant DAC_MIDSCALE	: std_logic_vector (DATA_WIDTH - 1 downto 0) := x"80";

end package;

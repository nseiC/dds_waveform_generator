library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity DDS is	
	port(
		frequency	: in unsigned (17 downto 0);
		clk, rst 	: in std_logic;
		qOut			: out std_logic_vector (7 downto 0);
		qIn			: in std_logic_vector (7 downto 0)
	);
end entity;

architecture behavior of DDS is 
	component PLL IS
		PORT
		(
			areset		: IN STD_LOGIC  := '0';
			inclk0		: IN STD_LOGIC  := '0';
			c0		: OUT STD_LOGIC ;
			locked		: OUT STD_LOGIC 
		);
	end component;
	
	component phase_accumulator is
		port(
			frequency	: in unsigned (17 downto 0);
			clk,rst 		: in std_logic;
			bOut			: out unsigned (9 downto 0)
			);
	end component;
	
	component LUT is
		port(
			qOut 				: out std_logic_vector (7 downto 0);
			qIn				: in std_logic_vector (7 downto 0);
			clk, rst, wren	: in std_logic;
			addr 				: in unsigned (9 downto 0);
			sel				: in std_logic_vector (1 downto 0)
		);
	end component;
	
	signal clk50Mhz, clk10MHz 	: std_logic;
	signal bOut					  	: unsigned (9 downto 0);
	signal wren						: std_logic;  	
	signal sel1						: std_logic_vector ( 1 downto 0);
	begin
	pll1	:	PLL 						port map (rst,clk50Mhz,clk10Mhz);
	pha 	:  phase_accumulator 	port map (frequency,clk,rst,bOut);
	lut1  :	LUT						port map (qOut,qIn,clk10Mhz,rst,wren,bOut,sel1);

end architecture;
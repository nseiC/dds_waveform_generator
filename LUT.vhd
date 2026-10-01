library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity LUT is
	port(
		addr 				: in unsigned (9 downto 0);
		qOut 				: out std_logic_vector (7 downto 0);
		qIn				: in std_logic_vector (7 downto 0);
		clk, rst, wren	: in std_logic;
		sel				: in std_logic_vector (1 downto 0)
	);
end entity;

architecture behavior of LUT is
	component sine_LUT IS
		PORT
		(
			address		: IN STD_LOGIC_VECTOR (9 DOWNTO 0);
			clock		: IN STD_LOGIC  := '1';
			q		: OUT STD_LOGIC_VECTOR (7 DOWNTO 0)
		);
	end component;
	
	component sinc_LUT IS
		PORT
		(
			address		: IN STD_LOGIC_VECTOR (9 DOWNTO 0);
			clock		: IN STD_LOGIC  := '1';
			q		: OUT STD_LOGIC_VECTOR (7 DOWNTO 0)
		);
	end component;
	
	component saw_LUT IS
		PORT
		(
			address		: IN STD_LOGIC_VECTOR (9 DOWNTO 0);
			clock		: IN STD_LOGIC  := '1';
			q		: OUT STD_LOGIC_VECTOR (7 DOWNTO 0)
		);
	end component;
	
	component arbitrary_LUT IS
		PORT
		(
			address		: IN STD_LOGIC_VECTOR (9 DOWNTO 0);
			clock		: IN STD_LOGIC  := '1';
			data		: IN STD_LOGIC_VECTOR (7 DOWNTO 0);
			wren		: IN STD_LOGIC ;
			q		: OUT STD_LOGIC_VECTOR (7 DOWNTO 0)
		);
	end component;
	
	component out_mux IS
		PORT(
			sel								: in std_logic_vector (1 downto 0); 
			wren, rst						: in std_logic;
			q_sine,q_saw,q_sinc,q_arb	: in std_logic_vector ( 7 downto 0);
			qout								: out std_logic_vector ( 7 downto 0)
		);
	end component;
	
	signal qsine,qsaw,qsinc,qarb,qmux	: std_logic_vector (7 downto 0);
	signal addr_casted						: std_logic_vector (9 downto 0);
	begin
	addr_casted <= std_logic_vector (addr);
	sine	: sine_LUT port map (addr_casted,clk,qsine);
	saw	: saw_LUT  port map (addr_casted,clk,qsaw);
	sinc	: sinc_LUT port map (addr_casted,clk,qsaw);
	arb  : arbitrary_LUT port map (addr_casted,clk,qIn,wren,qarb);
	mux	: out_mux  port map (sel,wren,rst,qsine,qsaw,qarb,qmux);
	qOut <= qmux;
end architecture; 
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
	
	
	component jtag is
		port (
			tdi                : out std_logic;                                       -- jtag.tdi
			tdo                : in  std_logic                    := '0';             --     .tdo
			ir_in              : out std_logic_vector(1 downto 0);                    --     .ir_in
			ir_out             : in  std_logic_vector(1 downto 0) := (others => '0'); --     .ir_out
			virtual_state_cdr  : out std_logic;                                       --     .virtual_state_cdr
			virtual_state_sdr  : out std_logic;                                       --     .virtual_state_sdr
			virtual_state_e1dr : out std_logic;                                       --     .virtual_state_e1dr
			virtual_state_pdr  : out std_logic;                                       --     .virtual_state_pdr
			virtual_state_e2dr : out std_logic;                                       --     .virtual_state_e2dr
			virtual_state_udr  : out std_logic;                                       --     .virtual_state_udr
			virtual_state_cir  : out std_logic;                                       --     .virtual_state_cir
			virtual_state_uir  : out std_logic;                                       --     .virtual_state_uir
			tck                : out std_logic                                        --  tck.clk
		);
	end component;
	
	signal clk50Mhz, clk10MHz 		: std_logic;
	signal bOut					  		: unsigned (9 downto 0);
	signal wren							: std_logic;  	
	signal sel1							: std_logic_vector ( 1 downto 0);
	signal tck, tdi, tdo         	: std_logic;
	signal ir_in, ir_out          : std_logic_vector(1 downto 0);
	signal vs_cdr, vs_sdr, vs_udr : std_logic;
	begin
	pll1	:	PLL 						port map (rst,clk50Mhz,clk10Mhz);
	pha 	:  phase_accumulator 	port map (frequency,clk,rst,bOut);
	lut1  :	LUT						port map (qOut,qIn,clk10Mhz,rst,wren,bOut,sel1);
	myjtag : jtag 						port map (
															tck               => tck,
															tdi               => tdi,
															tdo               => tdo,
															ir_in             => ir_in,
															ir_out            => ir_out,
															virtual_state_cdr => vs_cdr,
															virtual_state_sdr => vs_sdr,
															virtual_state_udr => vs_udr,
															virtual_state_e1dr => open,
															virtual_state_pdr  => open,
															virtual_state_e2dr => open,
															virtual_state_cir  => open,
															virtual_state_uir  => open
										);
end architecture;
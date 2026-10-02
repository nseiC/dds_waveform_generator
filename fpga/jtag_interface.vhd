-- Controle pelo PC: a IP do Virtual JTAG (jtag, gerada no Platform Designer) e a lógica que
-- transforma os comandos em configuração do DDS (jtag_control). O PC fala com ela pelo
-- quartus_stp através do USB-Blaster; ver GUI/README.md.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity jtag_interface is
	generic(
		DEFAULT_FREQUENCY	: natural := 1000;
		DEFAULT_SEL			: std_logic_vector (1 downto 0) := SEL_SINE
	);
	port(
		clk, rst		: in std_logic;
		frequency	: out unsigned (FREQ_WIDTH - 1 downto 0);
		sel			: out std_logic_vector (1 downto 0);
		lut_we		: out std_logic;
		lut_waddr	: out unsigned (ADDR_WIDTH - 1 downto 0);
		lut_wdata	: out std_logic_vector (DATA_WIDTH - 1 downto 0);
		activity		: out std_logic
	);
end entity;

architecture structure of jtag_interface is
	-- a IP gerada pelo Platform Designer fica na biblioteca "jtag", não em "work":
	-- por isso é instanciada como componente
	component jtag is
		port (
			tdi                : out std_logic;
			tdo                : in  std_logic                    := '0';
			ir_in              : out std_logic_vector(1 downto 0);
			ir_out             : in  std_logic_vector(1 downto 0) := (others => '0');
			virtual_state_cdr  : out std_logic;
			virtual_state_sdr  : out std_logic;
			virtual_state_e1dr : out std_logic;
			virtual_state_pdr  : out std_logic;
			virtual_state_e2dr : out std_logic;
			virtual_state_udr  : out std_logic;
			virtual_state_cir  : out std_logic;
			virtual_state_uir  : out std_logic;
			tck                : out std_logic
		);
	end component;

	signal tck, tdi, tdo				: std_logic;
	signal ir_in, ir_out				: std_logic_vector (IR_WIDTH - 1 downto 0);
	signal vs_cdr, vs_sdr, vs_udr	: std_logic;
begin

	vjtag : jtag
		port map (
			tck                => tck,
			tdi                => tdi,
			tdo                => tdo,
			ir_in              => ir_in,
			ir_out             => ir_out,
			virtual_state_cdr  => vs_cdr,
			virtual_state_sdr  => vs_sdr,
			virtual_state_udr  => vs_udr,
			virtual_state_e1dr => open,
			virtual_state_pdr  => open,
			virtual_state_e2dr => open,
			virtual_state_cir  => open,
			virtual_state_uir  => open
		);

	ctrl : entity work.jtag_control
		generic map (DEFAULT_FREQUENCY => DEFAULT_FREQUENCY, DEFAULT_SEL => DEFAULT_SEL)
		port map (tck => tck, tdi => tdi, tdo => tdo, ir_in => ir_in, ir_out => ir_out,
					 vs_cdr => vs_cdr, vs_sdr => vs_sdr, vs_udr => vs_udr,
					 clk => clk, rst => rst, frequency => frequency, sel => sel, lut_we => lut_we,
					 lut_waddr => lut_waddr, lut_wdata => lut_wdata, activity => activity);

end architecture;

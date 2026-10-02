-- Toda a lógica do controle pelo PC, sem a IP do Virtual JTAG: recebe os sinais da IP
-- (domínio do tck) e entrega a configuração do DDS no domínio de 10 MHz.
--
--   sinais da IP -> vjtag_dr (tck) -> cmd_sync (tck -> 10 MHz) -> control_registers (10 MHz)
--
-- Separado de jtag_interface para poder ser simulado: o testbench faz o papel da IP.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity jtag_control is
	generic(
		DEFAULT_FREQUENCY	: natural := 1000;
		DEFAULT_SEL			: std_logic_vector (1 downto 0) := SEL_SINE
	);
	port(
		-- lado da IP (domínio do tck)
		tck, tdi		: in std_logic;
		tdo			: out std_logic;
		ir_in			: in std_logic_vector (IR_WIDTH - 1 downto 0);
		ir_out		: out std_logic_vector (IR_WIDTH - 1 downto 0);
		vs_cdr		: in std_logic;
		vs_sdr		: in std_logic;
		vs_udr		: in std_logic;
		-- lado do DDS (domínio de clk)
		clk, rst		: in std_logic;
		frequency	: out unsigned (FREQ_WIDTH - 1 downto 0);
		sel			: out std_logic_vector (1 downto 0);
		lut_we		: out std_logic;
		lut_waddr	: out unsigned (ADDR_WIDTH - 1 downto 0);
		lut_wdata	: out std_logic_vector (DATA_WIDTH - 1 downto 0);
		activity		: out std_logic
	);
end entity;

architecture structure of jtag_control is
	signal tck_ir		: std_logic_vector (IR_WIDTH - 1 downto 0);
	signal tck_data	: std_logic_vector (DR_WIDTH - 1 downto 0);
	signal tck_toggle	: std_logic;
	signal tck_cmd		: std_logic_vector (IR_WIDTH + DR_WIDTH - 1 downto 0);
	signal cmd_valid	: std_logic;
	signal cmd			: std_logic_vector (IR_WIDTH + DR_WIDTH - 1 downto 0);
begin

	dr : entity work.vjtag_dr
		port map (tck => tck, tdi => tdi, tdo => tdo, ir_in => ir_in, ir_out => ir_out,
					 vs_cdr => vs_cdr, vs_sdr => vs_sdr, vs_udr => vs_udr,
					 cmd_ir => tck_ir, cmd_data => tck_data, cmd_toggle => tck_toggle);

	tck_cmd <= tck_ir & tck_data;

	sync : entity work.cmd_sync
		generic map (WIDTH => IR_WIDTH + DR_WIDTH)
		port map (clk => clk, rst => rst, src_toggle => tck_toggle, src_data => tck_cmd,
					 dst_valid => cmd_valid, dst_data => cmd);

	regs : entity work.control_registers
		generic map (DEFAULT_FREQUENCY => DEFAULT_FREQUENCY, DEFAULT_SEL => DEFAULT_SEL)
		port map (clk => clk, rst => rst, cmd_valid => cmd_valid,
					 cmd_ir => cmd(IR_WIDTH + DR_WIDTH - 1 downto DR_WIDTH),
					 cmd_data => cmd(DR_WIDTH - 1 downto 0),
					 frequency => frequency, sel => sel, lut_we => lut_we, lut_waddr => lut_waddr,
					 lut_wdata => lut_wdata, activity => activity);

end architecture;

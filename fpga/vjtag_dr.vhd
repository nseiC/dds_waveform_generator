-- Registrador de dados (DR) do Virtual JTAG, no domínio do tck.
--
-- O PC escolhe a instrução no IR (ir_in) e desloca 18 bits no DR, LSB primeiro. No
-- Update-DR o valor deslocado vira um comando (cmd_ir, cmd_data) e cmd_toggle troca de
-- nível: é o aviso para o domínio de 10 MHz (ver cmd_sync). cmd_ir e cmd_data ficam parados
-- até o próximo Update-DR.
--
--   IR 00  bypass de 1 bit, sem comando
--   IR 01  frequência em Hz          IR 10  forma de onda (bits 1..0)
--   IR 11  escrita na LUT: endereço(17..8) & dado(7..0)
--
-- No Capture-DR o DR recebe o último valor escrito com a mesma instrução, então um
-- device_virtual_dr_shift que leia o DR devolve o valor anterior (útil para depurar).

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity vjtag_dr is
	port(
		tck, tdi		: in std_logic;
		tdo			: out std_logic;
		ir_in			: in std_logic_vector (IR_WIDTH - 1 downto 0);
		ir_out		: out std_logic_vector (IR_WIDTH - 1 downto 0);
		vs_cdr		: in std_logic;		-- Capture-DR
		vs_sdr		: in std_logic;		-- Shift-DR
		vs_udr		: in std_logic;		-- Update-DR
		cmd_ir		: out std_logic_vector (IR_WIDTH - 1 downto 0);
		cmd_data		: out std_logic_vector (DR_WIDTH - 1 downto 0);
		cmd_toggle	: out std_logic
	);
end entity;

architecture behavior of vjtag_dr is
	type shadow_t is array (0 to 2 ** IR_WIDTH - 1) of std_logic_vector (DR_WIDTH - 1 downto 0);

	-- o domínio do tck não tem reset: valores iniciais de configuração
	signal dr			: std_logic_vector (DR_WIDTH - 1 downto 0) := (others => '0');
	signal bypass		: std_logic := '0';
	signal shadow		: shadow_t := (others => (others => '0'));
	signal ir_reg		: std_logic_vector (IR_WIDTH - 1 downto 0) := IR_NOP;
	signal data_reg	: std_logic_vector (DR_WIDTH - 1 downto 0) := (others => '0');
	signal toggle		: std_logic := '0';
begin

	shift : process(tck)
	begin
		if rising_edge(tck) then
			if vs_cdr = '1' then
				dr <= shadow(to_integer(unsigned(ir_in)));
				bypass <= '0';
			elsif vs_sdr = '1' then
				dr <= tdi & dr(DR_WIDTH - 1 downto 1);
				bypass <= tdi;
			end if;
		end if;
	end process;

	update : process(tck)
	begin
		if rising_edge(tck) then
			if vs_udr = '1' and ir_in /= IR_NOP then
				ir_reg <= ir_in;
				data_reg <= dr;
				toggle <= not toggle;
				shadow(to_integer(unsigned(ir_in))) <= dr;
			end if;
		end if;
	end process;

	tdo <= bypass when ir_in = IR_NOP else dr(0);
	ir_out <= ir_in;		-- o Capture-IR devolve a instrução atual

	cmd_ir <= ir_reg;
	cmd_data <= data_reg;
	cmd_toggle <= toggle;

end architecture;

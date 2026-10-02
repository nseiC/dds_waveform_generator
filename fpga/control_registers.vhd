-- Registradores de configuração do DDS, no domínio de 10 MHz. Cada comando que chega do PC
-- (cmd_valid por 1 clock) é decodificado pela instrução:
--
--   IR 01  frequency <= dado(17..0)
--   IR 10  sel       <= dado(1..0)
--   IR 11  um pulso em lut_we, com lut_waddr = dado(17..8) e lut_wdata = dado(7..0)
--
-- activity troca de nível a cada comando aceito (LED de atividade na placa).
-- Depois do reset o DDS gera DEFAULT_FREQUENCY Hz na forma DEFAULT_SEL, sem precisar do PC.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;

entity control_registers is
	generic(
		DEFAULT_FREQUENCY	: natural := 1000;
		DEFAULT_SEL			: std_logic_vector (1 downto 0) := SEL_SINE
	);
	port(
		clk, rst		: in std_logic;		-- rst síncrono
		cmd_valid	: in std_logic;
		cmd_ir		: in std_logic_vector (IR_WIDTH - 1 downto 0);
		cmd_data		: in std_logic_vector (DR_WIDTH - 1 downto 0);
		frequency	: out unsigned (FREQ_WIDTH - 1 downto 0);
		sel			: out std_logic_vector (1 downto 0);
		lut_we		: out std_logic;
		lut_waddr	: out unsigned (ADDR_WIDTH - 1 downto 0);
		lut_wdata	: out std_logic_vector (DATA_WIDTH - 1 downto 0);
		activity		: out std_logic
	);
end entity;

architecture behavior of control_registers is
	signal act : std_logic := '0';
begin

	decode : process(clk)
	begin
		if rising_edge(clk) then
			lut_we <= '0';
			if rst = '1' then
				frequency <= to_unsigned(DEFAULT_FREQUENCY, FREQ_WIDTH);
				sel <= DEFAULT_SEL;
				lut_waddr <= (others => '0');
				lut_wdata <= (others => '0');
				act <= '0';
			elsif cmd_valid = '1' then
				case cmd_ir is
					when IR_FREQ =>
						frequency <= unsigned(cmd_data(FREQ_WIDTH - 1 downto 0));
						act <= not act;
					when IR_SEL =>
						sel <= cmd_data(1 downto 0);
						act <= not act;
					when IR_LUT =>
						lut_waddr <= unsigned(cmd_data(DR_WIDTH - 1 downto DATA_WIDTH));
						lut_wdata <= cmd_data(DATA_WIDTH - 1 downto 0);
						lut_we <= '1';
						act <= not act;
					when others =>
						null;
				end case;
			end if;
		end if;
	end process;

	activity <= act;

end architecture;

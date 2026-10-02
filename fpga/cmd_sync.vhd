-- Passa um comando de um domínio de clock para outro (aqui, do tck do JTAG para os 10 MHz).
--
-- A origem troca src_toggle a cada comando novo e mantém src_data parado até o próximo.
-- O destino sincroniza o toggle em STAGES flip-flops; quando o nível sincronizado muda,
-- src_data já está estável há pelo menos STAGES - 1 clocks e é copiado para dst_data, com
-- um pulso de 1 clock em dst_valid.
--
-- Requisito: dois comandos seguidos precisam estar separados por mais de STAGES + 1 clocks
-- do destino. Um DR de 18 bits leva mais de 22 ciclos de tck (3,7 us a 6 MHz), e 4 clocks
-- de 10 MHz são 0,4 us.

library ieee;
use ieee.std_logic_1164.all;

entity cmd_sync is
	generic(
		WIDTH		: positive;
		STAGES	: positive := 3		-- pelo menos 2
	);
	port(
		clk, rst		: in std_logic;		-- domínio de destino; rst síncrono
		src_toggle	: in std_logic;
		src_data		: in std_logic_vector (WIDTH - 1 downto 0);
		dst_valid	: out std_logic;
		dst_data		: out std_logic_vector (WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of cmd_sync is
	signal sync		: std_logic_vector (STAGES - 1 downto 0) := (others => '0');
	signal last		: std_logic := '0';
	signal data		: std_logic_vector (WIDTH - 1 downto 0) := (others => '0');
	signal valid	: std_logic := '0';

	-- identifica a cadeia como sincronizador para o TimeQuest (MTBF)
	attribute altera_attribute : string;
	attribute altera_attribute of sync : signal is
		"-name SYNCHRONIZER_IDENTIFICATION ""FORCED IF ASYNCHRONOUS""";
begin

	synchronizer : process(clk)
	begin
		if rising_edge(clk) then
			sync <= sync(STAGES - 2 downto 0) & src_toggle;
		end if;
	end process;

	capture : process(clk)
	begin
		if rising_edge(clk) then
			valid <= '0';
			if rst = '1' then
				-- acompanha o toggle durante o reset: nenhum comando antigo é repetido
				last <= sync(STAGES - 1);
			elsif sync(STAGES - 1) /= last then
				last <= sync(STAGES - 1);
				data <= src_data;
				valid <= '1';
			end if;
		end if;
	end process;

	dst_valid <= valid;
	dst_data <= data;

end architecture;

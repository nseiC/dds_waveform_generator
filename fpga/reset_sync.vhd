-- Sincronizador de reset: entra em reset na hora (assíncrono) e sai sincronizado com o
-- clock, STAGES bordas depois de rst_in cair. Evita que os registradores saiam do reset em
-- bordas diferentes.

library ieee;
use ieee.std_logic_1164.all;

entity reset_sync is
	generic(
		STAGES	: positive := 3
	);
	port(
		clk		: in std_logic;
		rst_in	: in std_logic;		-- ativo em '1', assíncrono
		rst_out	: out std_logic		-- ativo em '1', liberado em sincronia com clk
	);
end entity;

architecture behavior of reset_sync is
	signal chain : std_logic_vector (STAGES - 1 downto 0) := (others => '1');
begin

	sequential : process(clk, rst_in)
	begin
		if rst_in = '1' then
			chain <= (others => '1');
		elsif rising_edge(clk) then
			chain <= chain(STAGES - 2 downto 0) & '0';
		end if;
	end process;

	rst_out <= chain(STAGES - 1);

end architecture;

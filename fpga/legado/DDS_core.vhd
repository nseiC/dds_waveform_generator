library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- NCO (Numerically Controlled Oscillator) baseado em MT-085 Fig. 2
-- Blocos: Delta Phase Register -> Phase Accumulator -> Phase Truncation
--         -> Sine Lookup Table -> Output Register
--
-- Equacao de sintonia (MT-085 Eq.1):  f_out = M * f_c / 2^n
--   f_c = 10 MHz (clk_en a cada 5 ciclos do clock de 50 MHz)
--   n   = 32 bits
--   Resolucao de frequencia = 10e6 / 2^32 ~ 0.00233 Hz por passo
entity DDS_core is
    port (
        clk      : in  std_logic;           -- 50 MHz sistema
        clk_en   : in  std_logic;           -- habilita em 10 MHz (1 pulso a cada 5 clocks)
        rst      : in  std_logic;
        m        : in  std_logic_vector(31 downto 0); -- Delta Phase Register (FTW = tuning word M)
        sine_out : out std_logic_vector(7 downto 0)  -- amplitude DAC (offset binary)
    );
end entity;

architecture rtl of DDS_core is

    -- Phase accumulator (32 bits -> 2^32 possiveis pontos de fase, MT-085 Fig. 3)
    signal phase_acc : unsigned(31 downto 0) := (others => '0');

    -- Phase truncation: apenas os 8 MSBs enderecam a ROM de 256 entradas
    -- (MT-085 p.3: truncacao de fase adiciona ruido de fase aceito em troca de ROM menor)
    signal rom_addr  : std_logic_vector(7 downto 0);

    component DDS_sine_rom is
        port (
            clk  : in  std_logic;
            addr : in  std_logic_vector(7 downto 0);
            data : out std_logic_vector(7 downto 0)
        );
    end component;

begin

    -- Phase Accumulator: incrementado por M a cada ciclo de 10 MHz
    -- Overflow natural de 32 bits fecha o ciclo de fase (MT-085 p.2)
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                phase_acc <= (others => '0');
            elsif clk_en = '1' then
                phase_acc <= phase_acc + unsigned(m);
            end if;
        end if;
    end process;

    -- Phase Truncation: bits [31:24] -> 8 bits -> 256 entradas na ROM
    rom_addr <= std_logic_vector(phase_acc(31 downto 24));

    -- Sine Lookup Table com saida registrada (pipeline: 1 ciclo de latencia)
    -- Latencia total: 1 ciclo clk_en para acc + 1 ciclo clk para ROM = ~200 ns
    u_rom : DDS_sine_rom
        port map (
            clk  => clk,
            addr => rom_addr,
            data => sine_out
        );

end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Gerador de funcoes DDS - arquitetura baseada em Analog Devices MT-085
-- (Figura 2: NCO com Delta Phase Register + Phase Accumulator + Sine ROM)
--
-- Pinagem GPIO (10 pinos total):
--   GPIO[0]    : GND de referencia (logico '0' permanente)
--   GPIO[1]    : CLK_OUT - clock de 1 MHz para DAC externo (~40% duty cycle)
--   GPIO[9:2]  : DAC_OUT[7:0] - barramento paralelo de 8 bits (offset binary)
--                0x80 = zero / midscale | 0xFF = +pico | 0x00 = -pico
--
-- Selecao de frequencia (1 switch por vez):
--   SW[0] = 100 Hz  | SW[1] = 1 kHz  | SW[2] = 10 kHz
--   SW[3] = 100 kHz | SW[4] = 300 kHz
--
-- Equacao (MT-085 Eq.1): f_out = M * f_c / 2^32
--   f_c = 1 MHz  (clock de atualizacao DDS = 50 MHz / 50)
--   n   = 32 bits
--
-- Tabela de FTW (M = round(f_out * 2^32 / 1e6)):
--   100 Hz  : M = 0x00068DB9  (f_real = 100.000 Hz)
--   1 kHz   : M = 0x00418937  (f_real = 1000.000 Hz)
--   10 kHz  : M = 0x028F5C29  (f_real = 10000.000 Hz)
--   100 kHz : M = 0x1999999A  (f_real = 100000.000 Hz)
--   300 kHz : M = 0x4CCCCCCD  (f_real = 300000.000 Hz)
--
-- AVISO: limite pratico f_out < f_c/3 = 333 kHz (MT-085).
--   300 kHz esta no limite -> filtro LPF externo apos o DAC e obrigatorio.
entity DDS is
    port (
        clk     : in  std_logic;                    -- 50 MHz oscilador da placa
        rst_n   : in  std_logic;                    -- KEY0, reset ativo em nivel baixo
        sw      : in  std_logic_vector(4 downto 0); -- SW[4:0] selecao de frequencia
        clk_out : out std_logic;                    -- GPIO: clock 1 MHz para DAC externo
        dac_out : out std_logic_vector(7 downto 0); -- GPIO: barramento DAC 8 bits
        gnd_out : out std_logic                     -- GPIO: referencia GND (sempre '0')
    );
end entity;

architecture rtl of DDS is

    signal rst     : std_logic;

    -- Divisor de clock: 50 MHz -> 1 MHz
    -- Contador 0..49 (50 estados = periodo de 1000 ns = 1 MHz)
    signal div_cnt : integer range 0 to 49 := 0;
    signal en_1m   : std_logic := '0'; -- pulso de habilitacao em 1 MHz

    -- FTW (Delta Phase Register / tuning word M) selecionado pelos switches
    signal ftw     : std_logic_vector(31 downto 0);

    -- Saida do NCO
    signal sine_val : std_logic_vector(7 downto 0);

    component DDS_core is
        port (
            clk      : in  std_logic;
            clk_en   : in  std_logic;
            rst      : in  std_logic;
            m        : in  std_logic_vector(31 downto 0);
            sine_out : out std_logic_vector(7 downto 0)
        );
    end component;

begin

    rst     <= not rst_n;
    gnd_out <= '0';

    ---------------------------------------------------------------------------
    -- Divisor de clock: 50 MHz -> 1 MHz
    -- en_1m = '1' durante 1 ciclo de 50 MHz a cada 50 ciclos (periodo 1000 ns)
    -- clk_out sobe 1 ciclo apos en_1m para garantir setup do DAC externo:
    --   cnt: 0   1   2  ...  21  22  ...  49   0   1 ...
    --   en : 1   0   0  ...   0   0  ...   0   1   0 ...  <- DDS atualiza
    --   dat: D1  D1  D1 ...  D1  D1  ...  D1  D2  D2 ...  <- dado estavel
    --   clk: 0   0   1  ...   1   0  ...   0   0   0 ...  <- 40% duty cycle
    ---------------------------------------------------------------------------
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                div_cnt <= 0;
                en_1m   <= '0';
            else
                if div_cnt = 49 then
                    div_cnt <= 0;
                    en_1m   <= '1';
                else
                    div_cnt <= div_cnt + 1;
                    en_1m   <= '0';
                end if;
            end if;
        end if;
    end process;

    -- Clock GPIO: alto de cnt=2 a cnt=21 (20 ciclos = 400 ns = 40% duty cycle, 1 MHz)
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                clk_out <= '0';
            else
                if div_cnt = 1 then
                    clk_out <= '1';   -- sobe: dado ja esta estavel ha 1 ciclo (20 ns)
                elsif div_cnt = 21 then
                    clk_out <= '0';
                end if;
            end if;
        end if;
    end process;

    ---------------------------------------------------------------------------
    -- Selecao de FTW via switches (Delta Phase Register - MT-085 Fig. 2)
    -- Prioridade: frequencia mais alta ganha se mais de 1 switch ativo
    -- FTW = round(f_out * 2^32 / 1e6)
    ---------------------------------------------------------------------------
    process(sw)
    begin
        if    sw(4) = '1' then ftw <= x"4CCCCCCD"; -- 300 kHz
        elsif sw(3) = '1' then ftw <= x"1999999A"; -- 100 kHz
        elsif sw(2) = '1' then ftw <= x"028F5C29"; -- 10 kHz
        elsif sw(1) = '1' then ftw <= x"00418937"; -- 1 kHz
        elsif sw(0) = '1' then ftw <= x"00068DB9"; -- 100 Hz
        else                   ftw <= (others => '0'); -- sem sinal (DC midscale 0x80)
        end if;
    end process;

    ---------------------------------------------------------------------------
    -- NCO: Phase Accumulator + Sine ROM (MT-085 Fig. 2)
    ---------------------------------------------------------------------------
    u_nco : DDS_core
        port map (
            clk      => clk,
            clk_en   => en_1m,
            rst      => rst,
            m        => ftw,
            sine_out => sine_val
        );

    -- Registrar saida DAC para evitar glitches na transicao de FTW
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                dac_out <= x"80"; -- midscale (0V)
            else
                dac_out <= sine_val;
            end if;
        end if;
    end process;

end architecture;

-- Top-level DDS com o PLL e as memórias pelos modelos altera_mf do Quartus.
--   1. com KEY[0] apertado (rst_n = '0'): DAC no zero do sinal (0x80) e PLL destravado;
--   2. o PLL trava, acende led_locked e gera 10 MHz a partir dos 50 MHz;
--   3. sem PC, a saída é o seno de 1 kHz: cada amostra dos pinos do DAC segue a tabela e a
--      frequência medida bate com 1 kHz; dac_gnd fica em '0';
--   4. apertar KEY[0] de novo volta a saída para 0x80 e recomeça a fase.
-- O modelo da IP do Virtual JTAG não gera tck na simulação; o caminho do PC até o DAC é
-- testado no tb_system.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_DDS is
end entity;

architecture sim of tb_DDS is
	constant T_CLK50		: time := 20 ns;
	signal clk_50			: std_logic := '0';
	signal rst_n			: std_logic := '0';
	signal dac				: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal dac_gnd			: std_logic;
	signal led_locked		: std_logic;
	signal led_cmd			: std_logic;
	signal running			: boolean := true;
begin

	clk_50 <= not clk_50 after T_CLK50 / 2 when running;

	dut : entity work.DDS
		port map (clk_50 => clk_50, rst_n => rst_n, dac => dac, dac_gnd => dac_gnd,
					 led_locked => led_locked, led_cmd => led_cmd);

	-- bloco depois do dut: os nomes externos só existem depois que ele é elaborado
	check_block : block
		alias clk10	is << signal .tb_DDS.dut.clk10 : std_logic >>;
		alias addr	is << signal .tb_DDS.dut.core.addr : unsigned (ADDR_WIDTH - 1 downto 0) >>;
	begin

		stimulus : process
			constant SINE		: mem_t := read_mif("lut/sine_1024x8.mif");
			type hist_t is array (0 to 2) of natural;
			variable hist		: hist_t;
			variable errors	: natural := 0;
			variable t0, t1	: time;
			variable a, d		: natural;
			variable wraps		: natural := 0;
			variable led		: std_logic;
			variable f_meas	: real;
		begin
			-- 1. KEY[0] apertado
			wait for 2 us;
			check(dac = DAC_MIDSCALE, "reset: DAC = " & to_hstring(dac) & ", esperado 80", errors);
			check(led_locked = '0', "PLL travado com areset ativo", errors);

			-- 2. solta o reset e espera o PLL
			rst_n <= '1';
			wait until led_locked = '1' for 100 us;
			check(led_locked = '1', "PLL não travou em 100 us", errors);
			wait until rising_edge(clk10);
			t0 := now;
			for i in 1 to 10 loop
				wait until rising_edge(clk10);
			end loop;
			report "período de clk10 = " & time'image((now - t0) / 10);
			check((now - t0) / 10 = 100 ns, "PLL não está gerando 10 MHz", errors);

			-- 3. seno de 1 kHz no DAC, amostra(k) = seno[endereço(k-3)]
			led := led_cmd;
			for i in 0 to 2 loop
				wait until rising_edge(clk10);
				wait for 1 ns;
				hist := to_integer(addr) & hist(0 to 1);
			end loop;
			wait until rising_edge(clk10);
			for i in 1 to 22_000 loop
				wait for 1 ns;
				check(to_integer(unsigned(dac)) = SINE(hist(2)), "DAC = " & integer'image(to_integer(unsigned(dac))) &
						", esperado " & integer'image(SINE(hist(2))), errors);
				a := to_integer(addr);
				d := (a - hist(0)) mod 1024;
				check(d <= 1, "passo do endereço " & integer'image(d) & " a 1 kHz", errors);
				if a < hist(0) then
					if wraps = 0 then
						t0 := now;
					end if;
					t1 := now;
					wraps := wraps + 1;
				end if;
				hist := a & hist(0 to 1);
				wait until rising_edge(clk10);
			end loop;
			check(wraps >= 2, "o endereço deu " & integer'image(wraps) & " volta(s) em 2,2 ms", errors);
			if wraps >= 2 then
				f_meas := real(wraps - 1) / (real((t1 - t0) / 1 ns) * 1.0e-9);
				report "frequência no DAC = " & real'image(f_meas) & " Hz";
				check(abs(f_meas - 1000.0) < 1.0, "frequência padrão fora de 1 kHz", errors);
			end if;
			check(dac_gnd = '0', "dac_gnd deveria ficar em 0", errors);
			check(led_cmd = led, "led_cmd mudou sem comando do PC", errors);

			-- 4. KEY[0] de novo
			rst_n <= '0';
			wait for 1 us;
			check(dac = DAC_MIDSCALE, "reset no meio: DAC = " & to_hstring(dac), errors);
			check(addr = 0, "reset no meio: a fase não voltou a zero", errors);

			running <= false;
			finish("tb_DDS", errors);
		end process;

	end block;

end architecture;

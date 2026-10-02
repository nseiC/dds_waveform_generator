-- Testbench do top-level DDS (VHDL-2008, auto-verificável).
--
-- Verifica:
--   1. o PLL gera 10 MHz a partir do clk de 50 MHz;
--   2. o endereço da LUT (DDS.bOut) avança f*1024/f_clk posições por clock e
--      dá a volta na frequência pedida;
--   3. qOut segue a forma de onda escolhida por sel (comparada aos .mif), e a
--      LUT arbitrária guarda o que foi escrito com wren.
--
-- Rodar a partir da raiz do projeto (os .mif são lidos de ./lut/).

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use std.textio.all;

entity tb_DDS is
end entity;

architecture sim of tb_DDS is

	constant T_CLK		: time := 20 ns;		-- 50 MHz da placa
	constant F_CLK		: real := 10.0e6;		-- clock do DDS (saída do PLL)

	type mem_t is array (0 to 1023) of natural;

	impure function read_mif (name : string) return mem_t is
		file f			: text open read_mode is name;
		variable l		: line;
		variable a, v	: integer;
		variable c		: character;
		variable ok		: boolean;
		variable m		: mem_t := (others => 0);
	begin
		while not endfile(f) loop
			readline(f, l);
			read(l, a, ok);						-- linhas "k : valor;"; o resto falha aqui
			if ok then
				loop
					read(l, c);
					exit when c = ':';
				end loop;
				read(l, v);
				m(a) := v;
			end if;
		end loop;
		return m;
	end function;

	-- conteúdo escrito na LUT arbitrária durante o teste
	function arb_pattern (a : natural) return natural is
	begin
		return (a * 7 + 3) mod 256;
	end function;

	signal clk			: std_logic := '0';
	signal rst			: std_logic := '1';
	signal frequency	: unsigned (17 downto 0) := (others => '0');
	signal qOut			: std_logic_vector (7 downto 0);
	signal qIn			: std_logic_vector (7 downto 0);
	signal sel			: std_logic_vector (1 downto 0) := "00";
	signal wren			: std_logic := '0';

	begin

	clk <= not clk after T_CLK / 2;

	dut : entity work.DDS port map (frequency => frequency, clk => clk, rst => rst,
											  qOut => qOut, qIn => qIn, sel => sel, wren => wren);

	watchdog : process
		begin
			wait for 20 ms;
			report "timeout: simulação não terminou" severity failure;
	end process;

	-- bloco depois do dut: os nomes externos só existem depois que o dut é elaborado
	check : block
		alias addr	is << signal .tb_DDS.dut.bOut : unsigned (9 downto 0) >>;
		alias clk10	is << signal .tb_DDS.dut.clk10MHz : std_logic >>;
	begin

		-- dado escrito na RAM arbitrária: função do endereço atual
		qIn <= std_logic_vector(to_unsigned(arb_pattern(to_integer(addr)), 8));

		stimulus : process
			constant SINE		: mem_t := read_mif("lut/sine_1024x8.mif");
			constant TRIANGLE	: mem_t := read_mif("lut/triangle_1024x8.mif");
			constant SINC		: mem_t := read_mif("lut/sinc_1024x8.mif");
			variable arb		: mem_t;
			variable errors	: natural := 0;
			variable t0			: time;

			procedure fail (msg : string) is
			begin
				errors := errors + 1;
				if errors <= 10 then
					report msg severity error;
				end if;
			end procedure;

			procedure wait_clk10 (n : natural) is
			begin
				for i in 1 to n loop
					wait until rising_edge(clk10);
				end loop;
			end procedure;

			-- endereço: passo por clock e frequência das voltas (endereço diminui = volta de 2pi)
			procedure check_frequency (f_hz : natural; periods : positive) is
				variable step				: real := real(f_hz) * 1024.0 / F_CLK;
				variable limit				: natural := integer(real(periods + 2) * F_CLK / real(f_hz));
				variable a, a_prev, d	: integer;
				variable wraps				: natural := 0;
				variable t_first, t_last: time;
				variable f_meas			: real;
			begin
				frequency <= to_unsigned(f_hz, 18);
				wait_clk10(4);
				a_prev := to_integer(addr);
				while wraps <= periods loop
					if limit = 0 then
						fail("f = " & integer'image(f_hz) & " Hz: endereço deu " & integer'image(wraps) &
							  " volta(s), esperado " & integer'image(periods + 1));
						return;
					end if;
					limit := limit - 1;
					wait until rising_edge(clk10);
					a := to_integer(addr);
					d := (a - a_prev) mod 1024;
					if d /= integer(floor(step)) and d /= integer(ceil(step)) then
						fail("f = " & integer'image(f_hz) & " Hz: endereço " & integer'image(a_prev) &
							  " -> " & integer'image(a) & ", passo esperado " & real'image(step));
					end if;
					if a < a_prev then
						if wraps = 0 then
							t_first := now;
						end if;
						t_last := now;
						wraps := wraps + 1;
					end if;
					a_prev := a;
				end loop;
				f_meas := real(periods) / (real((t_last - t_first) / 1 ns) * 1.0e-9);
				report "f pedida = " & integer'image(f_hz) & " Hz, medida no endereço = " &
						 real'image(f_meas) & " Hz";
				if abs(f_meas - real(f_hz)) > 1.0e-3 * real(f_hz) then
					fail("frequência medida fora da tolerância de 0,1%");
				end if;
			end procedure;

			-- saída: ROMs/RAM têm endereço e saída registrados, então qOut após a borda n
			-- corresponde ao endereço amostrado na borda n-1
			procedure check_wave (s : std_logic_vector (1 downto 0); mem : mem_t;
										 name : string; cycles : positive) is
				variable a_prev, a	: natural;
				variable bad			: natural := 0;
			begin
				sel <= s;
				wait_clk10(3);
				a_prev := to_integer(addr);
				for i in 1 to cycles loop
					wait until rising_edge(clk10);
					a := to_integer(addr);
					wait for 1 ns;
					if to_integer(unsigned(qOut)) /= mem(a_prev) then
						bad := bad + 1;
						fail("sel = " & to_string(s) & " (" & name & "): addr " & integer'image(a_prev) &
							  ", qOut = " & integer'image(to_integer(unsigned(qOut))) &
							  ", esperado " & integer'image(mem(a_prev)));
					end if;
					a_prev := a;
				end loop;
				report "sel = " & to_string(s) & " (" & name & "): " & integer'image(cycles) &
						 " amostras comparadas, " & integer'image(bad) & " diferenças";
			end procedure;

		begin
			for i in arb'range loop
				arb(i) := arb_pattern(i);
			end loop;

			wait for 1 us;
			rst <= '0';
			wait for 20 us;						-- trava do PLL

			-- 1. clock do DDS
			wait until rising_edge(clk10);
			t0 := now;
			wait_clk10(10);
			report "período de clk10MHz = " & time'image((now - t0) / 10);
			if (now - t0) / 10 /= 100 ns then
				fail("PLL não está gerando 10 MHz");
			end if;

			-- 2. endereço da LUT
			check_frequency(1_000, 3);
			check_frequency(100_000, 50);
			check_frequency(262_143, 100);	-- máximo de 18 bits

			-- 3. formas de onda
			frequency <= to_unsigned(100_000, 18);
			check_wave("00", SINE, "seno", 2000);
			check_wave("01", TRIANGLE, "rampa", 2000);
			check_wave("10", SINC, "sinc", 2000);

			-- LUT arbitrária: a 1 kHz o passo é < 1, então um período escreve os 1024 endereços
			frequency <= to_unsigned(1_000, 18);
			wait_clk10(4);
			wren <= '1';
			wait_clk10(10_100);
			wren <= '0';
			frequency <= to_unsigned(100_000, 18);
			check_wave("11", arb, "arbitrária", 2000);

			-- troca de sel com o DDS rodando, sem reset
			check_wave("00", SINE, "seno", 500);

			if errors = 0 then
				report "tb_DDS: OK";
			else
				report "tb_DDS: " & integer'image(errors) & " erro(s)" severity failure;
			end if;
			std.env.finish;
		end process;

	end block;

end architecture;

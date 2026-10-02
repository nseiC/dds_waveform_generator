-- phase_accumulator: o endereço da LUT segue, clock a clock, o modelo
--   fase(k) = fase(k-1) + M,  endereço = fase(31..22)
-- para várias frequências, inclusive trocas com o acumulador rodando (a fase continua de
-- onde estava, sem salto). Mede também a frequência pelas voltas do endereço.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_phase_accumulator is
end entity;

architecture sim of tb_phase_accumulator is
	signal clk			: std_logic := '0';
	signal rst			: std_logic := '1';
	signal frequency	: unsigned (FREQ_WIDTH - 1 downto 0) := (others => '0');
	signal addr			: unsigned (ADDR_WIDTH - 1 downto 0);
	signal running		: boolean := true;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	dut : entity work.phase_accumulator
		port map (frequency => frequency, clk => clk, rst => rst, bOut => addr);

	stimulus : process
		variable errors	: natural := 0;
		variable phase		: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
		variable m			: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');

		-- n clocks conferindo o endereço; devolve quantas voltas a fase deu
		procedure run (n : natural; laps : out natural) is
			variable prev : unsigned (ACC_WIDTH - 1 downto 0);
		begin
			laps := 0;
			for i in 1 to n loop
				wait until rising_edge(clk);
				prev := phase;
				phase := phase + m;
				if phase < prev then
					laps := laps + 1;
				end if;
				wait for 1 ns;
				check(addr = phase(ACC_WIDTH - 1 downto ACC_WIDTH - ADDR_WIDTH),
						"f = " & integer'image(to_integer(frequency)) & " Hz: endereço " &
						integer'image(to_integer(addr)) & ", esperado " &
						integer'image(to_integer(phase(ACC_WIDTH - 1 downto ACC_WIDTH - ADDR_WIDTH))), errors);
			end loop;
		end procedure;

		procedure set_frequency (f : natural) is
		begin
			frequency <= to_unsigned(f, FREQ_WIDTH);
			m := ftw_of(f);
		end procedure;

		variable laps : natural;
	begin
		-- durante o reset a fase fica em zero
		set_frequency(1_000);
		wait for 3 * T_CLK10 + 10 ns;
		check(addr = 0, "endereço deveria ser 0 no reset", errors);
		wait until falling_edge(clk);
		rst <= '0';

		-- 1 kHz: M = 429 496 (999,9983 Hz), então 3 voltas fecham em 30 001 clocks
		run(30_001, laps);
		check(laps = 3, "1 kHz: " & integer'image(laps) & " voltas em 3 ms, esperado 3", errors);

		-- trocas sem reset: a fase continua de onde estava
		set_frequency(100_000);
		run(1_000, laps);
		check(laps = 10, "100 kHz: " & integer'image(laps) & " voltas em 0,1 ms, esperado 10", errors);
		set_frequency(262_143);
		run(5_000, laps);
		set_frequency(1);
		run(100, laps);
		set_frequency(0);
		run(100, laps);
		check(laps = 0, "f = 0 Hz: a fase não deveria andar", errors);
		set_frequency(123_457);
		run(5_000, laps);

		-- reset no meio: volta para a fase zero
		rst <= '1';
		wait for 1 ns;
		check(addr = 0, "reset não zerou a fase", errors);
		phase := (others => '0');
		wait until falling_edge(clk);
		rst <= '0';
		run(1_000, laps);

		running <= false;
		finish("tb_phase_accumulator", errors);
	end process;

end architecture;

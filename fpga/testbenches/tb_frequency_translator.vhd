-- frequency_translator: varre as 2^18 frequências de entrada e confere a FTW
--   1. contra a especificação M = (f * FTW_K) >> 24;
--   2. contra o valor exato f * 2^32 / 10 MHz: o erro precisa ser menor que 1 LSB.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_frequency_translator is
end entity;

architecture sim of tb_frequency_translator is
	signal frequency	: unsigned (FREQ_WIDTH - 1 downto 0) := (others => '0');
	signal ftw			: unsigned (ACC_WIDTH - 1 downto 0);
begin

	dut : entity work.frequency_translator
		port map (frequency => frequency, FTW => ftw);

	stimulus : process
		variable errors		: natural := 0;
		variable exact, err	: real;
		variable worst			: real := 0.0;
	begin
		for f in 0 to 2 ** FREQ_WIDTH - 1 loop
			frequency <= to_unsigned(f, FREQ_WIDTH);
			wait for 1 ns;
			check(ftw = ftw_of(f), "f = " & integer'image(f) & " Hz: FTW = " & to_hstring(ftw) &
					", esperado " & to_hstring(ftw_of(f)), errors);
			exact := real(f) * 2.0 ** ACC_WIDTH / 10.0e6;
			err := exact - real(to_integer(ftw));
			check(abs(err) < 1.0, "f = " & integer'image(f) & " Hz: erro de " & real'image(err) &
					" LSB na FTW", errors);
			if abs(err) > worst then
				worst := abs(err);
			end if;
		end loop;
		report "2^18 frequências conferidas; maior erro da FTW = " & real'image(worst) & " LSB = " &
				 real'image(worst * 10.0e6 / 2.0 ** ACC_WIDTH * 1.0e3) & " mHz";
		finish("tb_frequency_translator", errors);
	end process;

end architecture;

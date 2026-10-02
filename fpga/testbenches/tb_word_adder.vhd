-- word_adder: soma de 32 bits com estouro (módulo 2^32), em casos de borda e 10 000 pares
-- aleatórios.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_word_adder is
end entity;

architecture sim of tb_word_adder is
	signal a, b, s : unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
begin

	dut : entity work.word_adder
		port map (ftw => a, feedback => b, wOut => s);

	stimulus : process
		variable errors			: natural := 0;
		variable seed1, seed2	: positive := 7;
		variable expected			: unsigned (ACC_WIDTH downto 0);

		impure function random32 return unsigned is
			variable r1, r2 : real;
		begin
			uniform(seed1, seed2, r1);
			uniform(seed1, seed2, r2);
			return to_unsigned(integer(floor(r1 * 65536.0)), 16) & to_unsigned(integer(floor(r2 * 65536.0)), 16);
		end function;

		procedure test (x, y : unsigned) is
		begin
			a <= x;
			b <= y;
			wait for 1 ns;
			expected := resize(x, ACC_WIDTH + 1) + resize(y, ACC_WIDTH + 1);
			check(s = expected(ACC_WIDTH - 1 downto 0), to_hstring(x) & " + " & to_hstring(y) &
					" = " & to_hstring(s) & ", esperado " & to_hstring(expected(ACC_WIDTH - 1 downto 0)), errors);
		end procedure;

		constant ZERO	: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
		constant ONES	: unsigned (ACC_WIDTH - 1 downto 0) := (others => '1');
	begin
		test(ZERO, ZERO);
		test(ONES, to_unsigned(1, ACC_WIDTH));		-- estouro: volta a zero
		test(ONES, ONES);
		test(x"80000000", x"80000000");
		test(x"FFFFFFF0", x"00000020");
		for i in 1 to 10_000 loop
			test(random32, random32);
		end loop;
		finish("tb_word_adder", errors);
	end process;

end architecture;

-- truncator: o endereço da LUT são os 10 bits mais significativos da fase.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_truncator is
end entity;

architecture sim of tb_truncator is
	signal phase	: unsigned (ACC_WIDTH - 1 downto 0) := (others => '0');
	signal addr		: unsigned (ADDR_WIDTH - 1 downto 0);
begin

	dut : entity work.truncator
		port map (wIn => phase, bOut => addr);

	stimulus : process
		variable errors			: natural := 0;
		variable seed1, seed2	: positive := 11;
		variable r1, r2			: real;

		procedure test (value : unsigned) is
			constant p : unsigned (ACC_WIDTH - 1 downto 0) := value;	-- literais vêm com índice crescente
		begin
			phase <= p;
			wait for 1 ns;
			check(addr = p(ACC_WIDTH - 1 downto ACC_WIDTH - ADDR_WIDTH), "fase " & to_hstring(p) &
					": endereço " & to_hstring(addr), errors);
		end procedure;
	begin
		test(x"00000000");
		test(x"003FFFFF");		-- último valor do endereço 0
		test(x"00400000");		-- primeiro do endereço 1
		test(x"FFFFFFFF");
		test(x"80000000");
		for k in 0 to 2 ** ADDR_WIDTH - 1 loop
			test(to_unsigned(k, ADDR_WIDTH) & to_unsigned(k * 4093 mod 2 ** 22, 22));
		end loop;
		for i in 1 to 5_000 loop
			uniform(seed1, seed2, r1);
			uniform(seed1, seed2, r2);
			test(to_unsigned(integer(floor(r1 * 65536.0)), 16) & to_unsigned(integer(floor(r2 * 65536.0)), 16));
		end loop;
		finish("tb_truncator", errors);
	end process;

end architecture;

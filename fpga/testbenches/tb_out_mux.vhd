-- out_mux: cada código de sel escolhe a entrada certa.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_out_mux is
end entity;

architecture sim of tb_out_mux is
	signal sel								: std_logic_vector (1 downto 0) := SEL_SINE;
	signal q_sine, q_saw, q_sinc, q_arb	: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal qout								: std_logic_vector (DATA_WIDTH - 1 downto 0);
begin

	dut : entity work.out_mux
		port map (sel => sel, q_sine => q_sine, q_saw => q_saw, q_sinc => q_sinc, q_arb => q_arb,
					 qout => qout);

	stimulus : process
		variable errors : natural := 0;

		procedure test (s : std_logic_vector; expected : std_logic_vector; name : string) is
		begin
			sel <= s;
			wait for 1 ns;
			check(qout = expected, "sel = " & to_string(s) & ": saída " & to_hstring(qout) &
					", esperado " & name & " = " & to_hstring(expected), errors);
		end procedure;
	begin
		for i in 0 to 255 loop
			q_sine <= std_logic_vector(to_unsigned(i, DATA_WIDTH));
			q_saw  <= std_logic_vector(to_unsigned((i + 64) mod 256, DATA_WIDTH));
			q_sinc <= std_logic_vector(to_unsigned((i + 128) mod 256, DATA_WIDTH));
			q_arb  <= std_logic_vector(to_unsigned(255 - i, DATA_WIDTH));
			wait for 1 ns;
			test(SEL_SINE, q_sine, "q_sine");
			test(SEL_SAW, q_saw, "q_saw");
			test(SEL_SINC, q_sinc, "q_sinc");
			test(SEL_ARB, q_arb, "q_arb");
		end loop;
		finish("tb_out_mux", errors);
	end process;

end architecture;

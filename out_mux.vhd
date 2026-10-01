library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity out_mux IS
		PORT(
			sel								: in std_logic_vector ( 1 downto 0);
			wren, rst						: in std_logic;
			q_sine,q_saw,q_sinc,q_arb	: in std_logic_vector ( 7 downto 0);
			qout								: out std_logic_vector ( 7 downto 0)
		);
end entity;

architecture behavior of out_mux is
	begin
	with sel select
	qout <= q_sine when "00",
	        q_saw  when "01",
	        q_sinc when "10",
	        q_arb  when "11",
	        (others => '0') when others;
end architecture;
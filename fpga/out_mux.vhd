-- Seleciona a forma de onda que vai para o DAC: 00 seno, 01 rampa, 10 sinc, 11 arbitrária.

library ieee;
use ieee.std_logic_1164.all;
use work.dds_pkg.all;

entity out_mux is
	port(
		sel									: in std_logic_vector (1 downto 0);
		q_sine, q_saw, q_sinc, q_arb	: in std_logic_vector (DATA_WIDTH - 1 downto 0);
		qout									: out std_logic_vector (DATA_WIDTH - 1 downto 0)
	);
end entity;

architecture behavior of out_mux is
begin
	with sel select
	qout <= q_sine when SEL_SINE,
	        q_saw  when SEL_SAW,
	        q_sinc when SEL_SINC,
	        q_arb  when others;
end architecture;

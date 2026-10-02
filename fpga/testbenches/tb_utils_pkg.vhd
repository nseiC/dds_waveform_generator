-- Utilidades comuns aos testbenches (VHDL-2008):
--   - leitura das tabelas .mif;
--   - contagem de erros e encerramento com "<nome>: OK", que o run_all.sh procura;
--   - modelo de referência da conversão Hz -> FTW;
--   - BFM do Virtual JTAG: os procedimentos fazem o papel da IP sld_virtual_jtag, gerando
--     tck, tdi, ir_in e os estados Capture/Shift/Update-DR como a IP gera.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use work.dds_pkg.all;

package tb_utils_pkg is

	constant MAX_REPORTS	: natural := 10;		-- mensagens de erro mostradas por testbench
	constant T_CLK10		: time := 100 ns;		-- clock do DDS
	constant T_TCK			: time := 166 ns;		-- ~6 MHz, o tck do USB-Blaster

	type mem_t is array (0 to 2 ** ADDR_WIDTH - 1) of natural;

	impure function read_mif (name : string) return mem_t;

	procedure check (ok : boolean; msg : string; variable errors : inout natural);
	procedure finish (name : string; errors : natural);

	-- especificação do frequency_translator: M = (f * FTW_K) >> FTW_SHIFT
	function ftw_of (f : natural) return unsigned;

	-- Virtual JTAG: seleciona a instrução (equivale ao device_virtual_ir_shift)
	procedure vjtag_ir (
		signal tck		: out std_logic;
		signal ir_in	: out std_logic_vector;
		value				: std_logic_vector);

	-- Virtual JTAG: Capture-DR, Shift-DR (LSB primeiro), Exit1-DR e Update-DR
	-- (equivale ao device_virtual_dr_shift). captured recebe o que saiu em tdo.
	procedure vjtag_dr (
		signal tck, tdi					: out std_logic;
		signal vs_cdr, vs_sdr, vs_udr	: out std_logic;
		signal tdo							: in std_logic;
		value									: std_logic_vector;
		variable captured					: out std_logic_vector);

end package;

package body tb_utils_pkg is

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

	procedure check (ok : boolean; msg : string; variable errors : inout natural) is
	begin
		if not ok then
			errors := errors + 1;
			if errors <= MAX_REPORTS then
				report msg severity error;
			end if;
		end if;
	end procedure;

	procedure finish (name : string; errors : natural) is
	begin
		if errors = 0 then
			report name & ": OK";
		else
			report name & ": " & integer'image(errors) & " erro(s)" severity failure;
		end if;
		std.env.finish;
	end procedure;

	function ftw_of (f : natural) return unsigned is
		variable p : unsigned (FREQ_WIDTH + FTW_K'length - 1 downto 0);
	begin
		p := to_unsigned(f, FREQ_WIDTH) * FTW_K;
		return resize(p(p'high downto FTW_SHIFT), ACC_WIDTH);
	end function;

	-- um ciclo de tck: os sinais já estão no lugar; o DUT amostra na borda de subida
	procedure tck_cycle (signal tck : out std_logic) is
	begin
		wait for T_TCK / 2;
		tck <= '1';
		wait for T_TCK / 2;
		tck <= '0';
	end procedure;

	procedure vjtag_ir (
		signal tck		: out std_logic;
		signal ir_in	: out std_logic_vector;
		value				: std_logic_vector) is
	begin
		ir_in <= value;
		for i in 1 to 4 loop
			tck_cycle(tck);
		end loop;
	end procedure;

	procedure vjtag_dr (
		signal tck, tdi					: out std_logic;
		signal vs_cdr, vs_sdr, vs_udr	: out std_logic;
		signal tdo							: in std_logic;
		value									: std_logic_vector;
		variable captured					: out std_logic_vector) is
		variable v		: std_logic_vector (value'length - 1 downto 0) := value;
		variable cap	: std_logic_vector (value'length - 1 downto 0);
	begin
		vs_cdr <= '1';									-- Capture-DR
		tck_cycle(tck);
		vs_cdr <= '0';
		vs_sdr <= '1';									-- Shift-DR, LSB primeiro
		for i in 0 to v'high loop
			tdi <= v(i);
			wait for T_TCK / 4;
			cap(i) := tdo;								-- o PC lê tdo antes da borda que desloca
			wait for T_TCK / 4;
			tck <= '1';
			wait for T_TCK / 2;
			tck <= '0';
		end loop;
		vs_sdr <= '0';									-- Exit1-DR
		tck_cycle(tck);
		vs_udr <= '1';									-- Update-DR
		tck_cycle(tck);
		vs_udr <= '0';
		for i in 1 to 2 loop							-- Run-Test/Idle
			tck_cycle(tck);
		end loop;
		captured := cap;
	end procedure;

end package body;

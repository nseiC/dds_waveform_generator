-- vjtag_dr: o testbench faz o papel da IP do Virtual JTAG (BFM do tb_utils_pkg) e confere
--   1. o DR desloca LSB primeiro e o Update-DR vira comando (cmd_ir, cmd_data, cmd_toggle);
--   2. o Capture-DR devolve o último valor escrito com a mesma instrução;
--   3. IR 00 é bypass de 1 bit e não gera comando;
--   4. comandos de LUT e de forma de onda; ir_out repete ir_in.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_vjtag_dr is
end entity;

architecture sim of tb_vjtag_dr is
	signal tck, tdi, tdo					: std_logic := '0';
	signal ir_in, ir_out					: std_logic_vector (IR_WIDTH - 1 downto 0) := IR_NOP;
	signal vs_cdr, vs_sdr, vs_udr		: std_logic := '0';
	signal cmd_ir							: std_logic_vector (IR_WIDTH - 1 downto 0);
	signal cmd_data						: std_logic_vector (DR_WIDTH - 1 downto 0);
	signal cmd_toggle						: std_logic;
begin

	dut : entity work.vjtag_dr
		port map (tck => tck, tdi => tdi, tdo => tdo, ir_in => ir_in, ir_out => ir_out,
					 vs_cdr => vs_cdr, vs_sdr => vs_sdr, vs_udr => vs_udr,
					 cmd_ir => cmd_ir, cmd_data => cmd_data, cmd_toggle => cmd_toggle);

	stimulus : process
		variable errors	: natural := 0;
		variable cap		: std_logic_vector (DR_WIDTH - 1 downto 0);
		variable cap8		: std_logic_vector (7 downto 0);
		variable toggle	: std_logic;

		-- desloca value com a instrução ir e confere o comando gerado
		procedure command (ir : std_logic_vector; value : natural; name : string) is
			constant v : std_logic_vector (DR_WIDTH - 1 downto 0) := std_logic_vector(to_unsigned(value, DR_WIDTH));
		begin
			toggle := cmd_toggle;
			vjtag_dr(tck, tdi, vs_cdr, vs_sdr, vs_udr, tdo, v, cap);
			check(cmd_toggle /= toggle, name & ": cmd_toggle não trocou", errors);
			check(cmd_ir = ir, name & ": cmd_ir = " & to_string(cmd_ir), errors);
			check(cmd_data = v, name & ": cmd_data = " & to_hstring(cmd_data) & ", esperado " & to_hstring(v), errors);
		end procedure;
	begin
		wait for 100 ns;
		check(ir_out = ir_in, "ir_out deveria repetir ir_in", errors);

		-- 1. frequência
		vjtag_ir(tck, ir_in, IR_FREQ);
		check(ir_out = IR_FREQ, "ir_out deveria repetir ir_in", errors);
		command(IR_FREQ, 16#2A5A5#, "IR 01");
		check(cap = (cap'range => '0'), "primeiro Capture-DR deveria devolver zero", errors);

		-- 2. o Capture-DR devolve o valor anterior da mesma instrução
		command(IR_FREQ, 440, "IR 01 (2º)");
		check(cap = std_logic_vector(to_unsigned(16#2A5A5#, DR_WIDTH)),
				"Capture-DR devolveu " & to_hstring(cap) & ", esperado 2A5A5", errors);

		-- 3. bypass: tdo é tdi atrasado de 1 bit, sem comando
		vjtag_ir(tck, ir_in, IR_NOP);
		toggle := cmd_toggle;
		vjtag_dr(tck, tdi, vs_cdr, vs_sdr, vs_udr, tdo, std_logic_vector'(x"B5"), cap8);
		check(cap8 = x"6A", "bypass: tdo = " & to_hstring(cap8) & ", esperado 6A (B5 << 1)", errors);
		check(cmd_toggle = toggle, "bypass gerou um comando", errors);
		check(cmd_ir = IR_FREQ and cmd_data = std_logic_vector(to_unsigned(440, DR_WIDTH)),
				"bypass alterou o último comando", errors);

		-- 4. forma de onda e escrita na LUT
		vjtag_ir(tck, ir_in, IR_SEL);
		command(IR_SEL, 3, "IR 10");
		vjtag_ir(tck, ir_in, IR_LUT);
		for a in 0 to 15 loop
			command(IR_LUT, a * 256 + (a * 17) mod 256, "IR 11, endereço " & integer'image(a));
		end loop;
		check(ir_out = IR_LUT, "ir_out deveria repetir ir_in", errors);

		finish("tb_vjtag_dr", errors);
	end process;

end architecture;

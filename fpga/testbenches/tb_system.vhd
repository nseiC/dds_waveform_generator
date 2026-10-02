-- Sistema sem a IP e sem o PLL: jtag_control + dds_core, do comando do PC até a amostra do
-- DAC. O testbench faz o papel do quartus_stp e da IP do Virtual JTAG, como a GUI faria:
--   1. depois do reset, sem PC: seno de 1 kHz;
--   2. o PC pede 100 kHz e depois sinc: a saída segue a tabela, o passo do endereço é
--      f * 1024 / f_clk e a frequência medida bate com a pedida;
--   3. o PC envia uma LUT inteira (1024 escritas pelo JTAG) e escolhe a forma arbitrária:
--      a saída devolve a LUT enviada.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.dds_pkg.all;
use work.tb_utils_pkg.all;

entity tb_system is
end entity;

architecture sim of tb_system is
	signal tck, tdi, tdo					: std_logic := '0';
	signal ir_in, ir_out					: std_logic_vector (IR_WIDTH - 1 downto 0) := IR_NOP;
	signal vs_cdr, vs_sdr, vs_udr		: std_logic := '0';
	signal clk								: std_logic := '0';
	signal rst								: std_logic := '1';
	signal frequency						: unsigned (FREQ_WIDTH - 1 downto 0);
	signal sel								: std_logic_vector (1 downto 0);
	signal lut_we							: std_logic;
	signal lut_waddr						: unsigned (ADDR_WIDTH - 1 downto 0);
	signal lut_wdata						: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal activity						: std_logic;
	signal sample							: std_logic_vector (DATA_WIDTH - 1 downto 0);
	signal running							: boolean := true;

	-- forma enviada pelo PC: um seno com o 3º harmônico, como uma LUT gerada pela GUI
	function uploaded (a : natural) return natural is
		constant x : real := 2.0 * MATH_PI * real(a) / 1024.0;
	begin
		return integer(round(128.0 + 90.0 * sin(x) + 30.0 * sin(3.0 * x)));
	end function;
begin

	clk <= not clk after T_CLK10 / 2 when running;

	ctrl : entity work.jtag_control
		port map (tck => tck, tdi => tdi, tdo => tdo, ir_in => ir_in, ir_out => ir_out,
					 vs_cdr => vs_cdr, vs_sdr => vs_sdr, vs_udr => vs_udr, clk => clk, rst => rst,
					 frequency => frequency, sel => sel, lut_we => lut_we, lut_waddr => lut_waddr,
					 lut_wdata => lut_wdata, activity => activity);

	core : entity work.dds_core
		port map (clk => clk, rst => rst, frequency => frequency, sel => sel, lut_we => lut_we,
					 lut_waddr => lut_waddr, lut_wdata => lut_wdata, sample => sample);

	-- bloco depois do core: os nomes externos só existem depois que ele é elaborado
	check_block : block
		alias addr is << signal .tb_system.core.addr : unsigned (ADDR_WIDTH - 1 downto 0) >>;
	begin

		stimulus : process
			constant SINE	: mem_t := read_mif("lut/sine_1024x8.mif");
			constant SINC	: mem_t := read_mif("lut/sinc_1024x8.mif");
			variable upl	: mem_t;
			variable errors	: natural := 0;
			variable cap	: std_logic_vector (DR_WIDTH - 1 downto 0);

			procedure dr (value : natural) is
			begin
				vjtag_dr(tck, tdi, vs_cdr, vs_sdr, vs_udr, tdo, std_logic_vector(to_unsigned(value, DR_WIDTH)), cap);
			end procedure;

			-- n clocks: amostra(k) = tabela[endereço(k-3)] e passo do endereço = f*1024/f_clk;
			-- mede a frequência pelas voltas do endereço
			procedure observe (f_hz : natural; mem : mem_t; name : string; n : positive) is
				type hist_t is array (0 to 2) of natural;
				variable hist			: hist_t;
				variable step			: real := real(f_hz) * 1024.0 / 10.0e6;
				variable a, d, wraps	: natural := 0;
				variable t0, t1		: time;
				variable f_meas		: real;
			begin
				-- hist(0..2) = endereços depois das 3 bordas anteriores
				for i in 0 to 2 loop
					wait until rising_edge(clk);
					wait for 1 ns;
					hist := to_integer(addr) & hist(0 to 1);
				end loop;
				wait until rising_edge(clk);
				for i in 1 to n loop
					wait for 1 ns;
					check(to_integer(unsigned(sample)) = mem(hist(2)), name & ": amostra " &
							integer'image(to_integer(unsigned(sample))) & ", esperado " &
							integer'image(mem(hist(2))), errors);
					a := to_integer(addr);
					d := (a - hist(0)) mod 1024;
					check(d = integer(floor(step)) or d = integer(ceil(step)), name & ": passo do endereço " &
							integer'image(d) & ", esperado " & real'image(step), errors);
					if a < hist(0) then
						if wraps = 0 then
							t0 := now;
						end if;
						t1 := now;
						wraps := wraps + 1;
					end if;
					hist := a & hist(0 to 1);
					wait until rising_edge(clk);
				end loop;
				if wraps >= 3 then
					f_meas := real(wraps - 1) / (real((t1 - t0) / 1 ns) * 1.0e-9);
					report name & ": f medida = " & real'image(f_meas) & " Hz";
					check(abs(f_meas - real(f_hz)) < 1.0e-3 * real(f_hz), name & ": frequência fora de 0,1 %", errors);
				end if;
			end procedure;
		begin
			for a in upl'range loop
				upl(a) := uploaded(a);
			end loop;

			wait for 5 * T_CLK10;
			wait until falling_edge(clk);
			rst <= '0';

			-- 1. sem PC: o padrão é seno de 1 kHz
			observe(1_000, SINE, "padrão (1 kHz, seno)", 35_000);

			-- 2. o PC muda frequência e forma
			vjtag_ir(tck, ir_in, IR_FREQ);
			dr(100_000);
			vjtag_ir(tck, ir_in, IR_SEL);
			dr(0);
			wait for 1 us;
			observe(100_000, SINE, "100 kHz, seno", 5_000);
			dr(2);
			wait for 1 us;
			observe(100_000, SINC, "100 kHz, sinc", 5_000);

			-- 3. o PC envia a LUT inteira e escolhe a forma arbitrária
			vjtag_ir(tck, ir_in, IR_LUT);
			for a in 0 to 2 ** ADDR_WIDTH - 1 loop
				dr(a * 256 + upl(a));
			end loop;
			vjtag_ir(tck, ir_in, IR_SEL);
			dr(3);
			vjtag_ir(tck, ir_in, IR_FREQ);
			dr(50_000);
			wait for 1 us;
			observe(50_000, upl, "50 kHz, LUT enviada pelo JTAG", 5_000);

			running <= false;
			finish("tb_system", errors);
		end process;

	end block;

end architecture;

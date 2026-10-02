-- RAM 1024 x 8 da forma de onda arbitrária, em duas portas (altsyncram DUAL_PORT, um clock):
--   porta A: escrita, no endereço que o PC mandar pelo JTAG;
--   porta B: leitura, no endereço da fase.
-- Assim a escrita não interrompe a leitura. Endereço e saída da porta B são registrados,
-- como nas ROMs: q sai 2 clocks depois de rdaddress.
-- Começa com o ECG sintético de lut/ecg_1024x8.mif.
--
-- Escrito à mão, com os mesmos parâmetros que o assistente "RAM: 2-PORT" do Quartus 18.1
-- gera para esta configuração (o qmegawiz de linha de comando não gera altsyncram).

library ieee;
use ieee.std_logic_1164.all;

library altera_mf;
use altera_mf.altera_mf_components.all;

entity arbitrary_LUT is
	port
	(
		clock			: in std_logic := '1';
		data			: in std_logic_vector (7 downto 0);
		rdaddress	: in std_logic_vector (9 downto 0);
		wraddress	: in std_logic_vector (9 downto 0);
		wren			: in std_logic := '0';
		q				: out std_logic_vector (7 downto 0)
	);
end arbitrary_LUT;

architecture SYN of arbitrary_LUT is

	signal sub_wire0	: std_logic_vector (7 downto 0);

begin
	q <= sub_wire0(7 downto 0);

	altsyncram_component : altsyncram
	generic map (
		address_aclr_b => "NONE",
		address_reg_b => "CLOCK0",
		clock_enable_input_a => "BYPASS",
		clock_enable_input_b => "BYPASS",
		clock_enable_output_b => "BYPASS",
		init_file => "./lut/ecg_1024x8.mif",
		intended_device_family => "Cyclone IV E",
		lpm_type => "altsyncram",
		numwords_a => 1024,
		numwords_b => 1024,
		operation_mode => "DUAL_PORT",
		outdata_aclr_b => "NONE",
		outdata_reg_b => "CLOCK0",
		power_up_uninitialized => "FALSE",
		read_during_write_mode_mixed_ports => "DONT_CARE",
		widthad_a => 10,
		widthad_b => 10,
		width_a => 8,
		width_b => 8,
		width_byteena_a => 1
	)
	port map (
		address_a => wraddress,
		address_b => rdaddress,
		clock0 => clock,
		data_a => data,
		wren_a => wren,
		q_b => sub_wire0
	);

end SYN;

# Restrições de tempo do DDS (TimeQuest)

# 50 MHz da placa; o PLL deriva os 10 MHz do caminho de dados
create_clock -name clk_50 -period 20.000 [get_ports {clk_50}]
derive_pll_clocks
derive_clock_uncertainty

# JTAG (Virtual JTAG / hub SLD): o Quartus já cria o clock altera_reserved_tck. Aqui ele vira
# um grupo assíncrono, e os pinos do JTAG recebem os atrasos do modelo do Quartus.
if {[get_collection_size [get_clocks -nowarn {altera_reserved_tck}]] > 0} {
	set_clock_groups -asynchronous -group [get_clocks {altera_reserved_tck}]
	set_input_delay -clock altera_reserved_tck -clock_fall 3 [get_ports {altera_reserved_tdi altera_reserved_tms}]
	set_output_delay -clock altera_reserved_tck 3 [get_ports {altera_reserved_tdo}]
}

# Os comandos do tck chegam aos 10 MHz pelo cmd_sync (toggle sincronizado em 3 flip-flops):
# o grupo assíncrono acima já corta esses caminhos na análise.

# Entradas e saídas sem relação de tempo com o clock: o botão de reset passa pelo
# reset_sync; o DAC0800 não tem clock (os 8 bits saem juntos dos registradores de I/O); LEDs.
set_false_path -from [get_ports {rst_n}]
set_false_path -to [get_ports {dac[*] dac_gnd led_locked led_cmd}]

#!/usr/bin/env bash
# Roda os testbenches da parte digital no GHDL e mostra um resumo.
#
# Uso:  fpga/testbenches/run_all.sh [tb_nome ...]     (sem argumentos: todos, do menor ao top-level)
#       WAVES=1 fpga/testbenches/run_all.sh tb_dds_core   grava testbenches/waves/tb_dds_core.ghw (GTKWave)
#       VCD=1 ...   grava testbenches/work/<tb>.vcd com os sinais de work/<tb>.opt (gerar_figuras.py)
#
# Variáveis: GHDL (padrão: ghdl), QUARTUS_ROOTDIR (padrão: ~/intelFPGA_lite/18.1/quartus).
# Na primeira execução compila a biblioteca altera_mf do Quartus (modelos do PLL e das
# memórias) em testbenches/work/. Sai com código 1 se algum testbench falhar.
set -euo pipefail

TB_DIR="$(cd "$(dirname "$0")" && pwd)"
FPGA="$(cd "$TB_DIR/.." && pwd)"
GHDL="${GHDL:-ghdl}"
QUARTUS_ROOTDIR="${QUARTUS_ROOTDIR:-$HOME/intelFPGA_lite/18.1/quartus}"
SIM_LIB="$QUARTUS_ROOTDIR/eda/sim_lib"
WORK="$TB_DIR/work"
FLAGS=(--std=08 -fsynopsys -frelaxed --workdir="$WORK" -P"$WORK")

# fontes do FPGA em ordem de dependência
SOURCES=(
	dds_pkg.vhd
	PLL.vhd sine_LUT.vhd saw_LUT.vhd sinc_LUT.vhd arbitrary_LUT.vhd jtag/synthesis/jtag.vhd
	frequency_translator.vhd word_adder.vhd phase_register.vhd truncator.vhd phase_accumulator.vhd
	out_mux.vhd LUT.vhd output_register.vhd dds_core.vhd
	reset_sync.vhd vjtag_dr.vhd cmd_sync.vhd control_registers.vhd jtag_control.vhd jtag_interface.vhd
	DDS.vhd
)

# testbenches, dos blocos menores ao top-level
ALL_TBS=(
	tb_frequency_translator tb_word_adder tb_phase_register tb_truncator tb_phase_accumulator
	tb_out_mux tb_LUT tb_output_register tb_dds_core
	tb_reset_sync tb_vjtag_dr tb_cmd_sync tb_control_registers tb_jtag_control
	tb_system tb_DDS
)
TBS=("${@:-${ALL_TBS[@]}}")

mkdir -p "$WORK"
cd "$FPGA"	# os .mif são lidos de ./lut/

if [ ! -f "$WORK/altera_mf-obj08.cf" ]; then
	echo "Compilando altera_mf (avisos em testbenches/work/altera_mf.log)..."
	"$GHDL" -a "${FLAGS[@]}" --work=altera_mf \
		"$SIM_LIB/altera_mf_components.vhd" "$SIM_LIB/altera_mf.vhd" > "$WORK/altera_mf.log" 2>&1 \
		|| { echo "Falha ao compilar altera_mf, ver $WORK/altera_mf.log"; exit 1; }
fi

echo "Analisando os fontes e os testbenches..."
"$GHDL" -a "${FLAGS[@]}" "${SOURCES[@]}" "$TB_DIR/tb_utils_pkg.vhd"
for tb in "${ALL_TBS[@]}"; do
	"$GHDL" -a "${FLAGS[@]}" "$TB_DIR/$tb.vhd"
done

failed=0
printf '\n%-26s %-9s %s\n' "testbench" "resultado" "tempo"
for tb in "${TBS[@]}"; do
	log="$WORK/$tb.log"
	run_opts=(--ieee-asserts=disable-at-0)
	if [ "${WAVES:-0}" = "1" ]; then
		mkdir -p "$TB_DIR/waves"
		run_opts+=(--wave="$TB_DIR/waves/$tb.ghw")
	fi
	if [ "${VCD:-0}" = "1" ]; then		# usado pelo gerar_figuras.py
		run_opts+=(--vcd="$WORK/$tb.vcd" --vcd-4states --vcd-nodate)
		if [ -f "$WORK/$tb.opt" ]; then
			run_opts+=(--read-wave-opt="$WORK/$tb.opt")
		fi
	fi
	start=$(date +%s)
	if "$GHDL" -e "${FLAGS[@]}" -Wno-binding "$tb" > "$log" 2>&1 \
		&& "$GHDL" -r "${FLAGS[@]}" -Wno-binding "$tb" "${run_opts[@]}" >> "$log" 2>&1 \
		&& grep -q "$tb: OK" "$log"; then
		result="OK"
	else
		result="FALHOU"
		failed=1
	fi
	printf '%-26s %-9s %ss\n' "$tb" "$result" "$(( $(date +%s) - start ))"
	if [ "$result" = "FALHOU" ]; then
		grep -E "error|failure|erro" "$log" | head -5 | sed 's/^/    /'
	fi
done

echo
if [ "$failed" = "0" ]; then
	echo "Todos os testbenches passaram. Logs em testbenches/work/<tb>.log"
else
	echo "Há testbenches com falha. Logs em testbenches/work/<tb>.log"
	exit 1
fi

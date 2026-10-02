#!/usr/bin/env bash
# Simula o top-level DDS com o GHDL (sim/tb_DDS.vhd).
# Compila na primeira vez a biblioteca altera_mf do Quartus (modelos do PLL e das memórias).
#
# Uso: sim/run_ghdl.sh [--wave]     (--wave grava sim/work/tb_DDS.ghw para o GTKWave)
# Variáveis: GHDL (padrão: ghdl), QUARTUS_ROOTDIR (padrão: ~/intelFPGA_lite/18.1/quartus)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GHDL="${GHDL:-ghdl}"
QUARTUS_ROOTDIR="${QUARTUS_ROOTDIR:-$HOME/intelFPGA_lite/18.1/quartus}"
SIM_LIB="$QUARTUS_ROOTDIR/eda/sim_lib"
WORK="$ROOT/sim/work"
FLAGS=(--std=08 -fsynopsys -frelaxed --workdir="$WORK" -P"$WORK")

RUN_OPTS=(--ieee-asserts=disable-at-0)
if [ "${1:-}" = "--wave" ]; then
	RUN_OPTS+=(--wave="$WORK/tb_DDS.ghw")
fi

mkdir -p "$WORK"
cd "$ROOT"	# os .mif são lidos de ./lut/

if [ ! -f "$WORK/altera_mf-obj08.cf" ]; then
	echo "Compilando altera_mf (avisos em sim/work/altera_mf.log)..."
	"$GHDL" -a "${FLAGS[@]}" --work=altera_mf \
		"$SIM_LIB/altera_mf_components.vhd" "$SIM_LIB/altera_mf.vhd" > "$WORK/altera_mf.log" 2>&1 \
		|| { echo "Falha ao compilar altera_mf, ver $WORK/altera_mf.log"; exit 1; }
fi

"$GHDL" -a "${FLAGS[@]}" \
	PLL.vhd sine_LUT.vhd saw_LUT.vhd sinc_LUT.vhd arbitrary_LUT.vhd \
	jtag/synthesis/jtag.vhd \
	frequency_translator.vhd word_adder.vhd phase_register.vhd truncator.vhd phase_accumulator.vhd \
	out_mux.vhd LUT.vhd DDS.vhd \
	sim/tb_DDS.vhd
"$GHDL" -e "${FLAGS[@]}" -Wno-binding tb_DDS
"$GHDL" -r "${FLAGS[@]}" -Wno-binding tb_DDS "${RUN_OPTS[@]}"

#!/usr/bin/env bash
# Gera o executável da interface em GUI/dist/dds-waveform-generator: um arquivo único, com o
# Python, o Tkinter, o ícone e as tabelas .mif dentro. Não precisa do .venv para rodar, só do
# Quartus (para o quartus_stp).
#
# Uso: GUI/build_exe.sh        (precisa do uv; baixa o PyInstaller num ambiente em GUI/build/)
set -euo pipefail

cd "$(dirname "$0")"
UV="${UV:-$HOME/.local/bin/uv}"
ROOT="$(cd .. && pwd)"
VENV=build/venv

[ -x "$VENV/bin/python" ] || "$UV" venv -q --python 3.12 "$VENV"
"$UV" pip install -q --python "$VENV/bin/python" pyinstaller

"$VENV/bin/python" -m PyInstaller --noconfirm --clean --log-level WARN \
	--onefile --windowed --name dds-waveform-generator \
	--distpath dist --workpath build/pyinstaller --specpath build \
	--add-data "$ROOT/docs/logo/icon.png:." \
	--add-data "$ROOT/fpga/lut/*.mif:lut" \
	gui.py

echo "Executável: GUI/dist/dds-waveform-generator"

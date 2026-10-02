#!/usr/bin/env bash
# Cria o atalho "DDS Waveform Generator" no menu de aplicativos e na área de trabalho.
# Usa o executável de GUI/dist (gerado pelo build_exe.sh) ou, se ele não existir, o run.sh.
set -euo pipefail

GUI_DIR="$(cd "$(dirname "$0")" && pwd)"
ICON="$(cd "$GUI_DIR/../docs/logo" && pwd)/icon.png"
EXE="$GUI_DIR/dist/dds-waveform-generator"
[ -x "$EXE" ] || EXE="$GUI_DIR/run.sh"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
NAME=dds-waveform-generator.desktop

mkdir -p "$APPS"
cat > "$APPS/$NAME" <<DESKTOP
[Desktop Entry]
Type=Application
Name=DDS Waveform Generator
Comment=Controle do gerador DDS pelo Virtual JTAG
Exec="$EXE"
Icon=$ICON
Terminal=false
Categories=Development;Electronics;
DESKTOP
chmod +x "$APPS/$NAME"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" || true
echo "Menu de aplicativos: $APPS/$NAME"

if [ -d "$DESKTOP_DIR" ]; then
	cp "$APPS/$NAME" "$DESKTOP_DIR/$NAME"
	chmod +x "$DESKTOP_DIR/$NAME"
	# no GNOME, o atalho só abre com dois cliques depois de marcado como confiável
	command -v gio >/dev/null && gio set "$DESKTOP_DIR/$NAME" metadata::trusted true 2>/dev/null || true
	echo "Área de trabalho: $DESKTOP_DIR/$NAME"
fi
echo "Abre: $EXE"

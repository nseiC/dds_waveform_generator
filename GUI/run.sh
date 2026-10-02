#!/usr/bin/env bash
# Abre a interface do JTAG UART usando o Python do ambiente do projeto.
cd "$(dirname "$0")" && exec .venv/bin/python gui.py "$@"

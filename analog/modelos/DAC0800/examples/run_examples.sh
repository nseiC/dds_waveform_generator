#!/bin/bash
# Roda todos os exemplos no ngspice e confere o resultado.
# (Os .cir sao escritos para LTspice; a unica diferenca e a palavra PARAMS:
#  na linha .subckt, que ../tests/run_tests.sh gera em dac0800_ng.lib.)
set -e
cd "$(dirname "$0")"
command -v ngspice >/dev/null || { echo "ngspice nao encontrado"; exit 1; }
sed 's/^\.SUBCKT DAC0800 \(.*\)$/.SUBCKT DAC0800 \1 PARAMS:/' ../DAC0800.lib > ../tests/dac0800_ng.lib
mkdir -p .run
fail=0
for f in ${@:-*.cir}; do
  sed -e 's|\.include \.\./DAC0800\.lib|.include ../../tests/dac0800_ng.lib|' -e '/^\.end$/d' "$f" > ".run/$f"
  cat "checks/${f%.cir}.ctl" >> ".run/$f" 2>/dev/null || echo ".end" >> ".run/$f"
  out=$(cd .run && ngspice -b "$f" 2>&1 | tr '\r' '\n')
  echo "=== $f ==="
  echo "$out" | grep -aE '^(PASS|FAIL|RESULT)' || true
  if echo "$out" | grep -qai "timestep too small"; then
    echo "FAIL  simulacao abortou (timestep too small)"; fail=$((fail+1))
  fi
  fail=$((fail + $(echo "$out" | grep -ac '^FAIL' || true)))
  if ! echo "$out" | grep -aq '^PASS'; then
    echo "FAIL  $f nao produziu resultado"; fail=$((fail+1))
  fi
done
echo
[ "$fail" -eq 0 ] && echo "TODOS OS EXEMPLOS OK" || { echo "$fail FALHA(S)"; exit 1; }

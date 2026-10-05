.control
set noaskquit
run
let ok = 1
meas tran e0 FIND v(eo) AT=9.5e-05
echo "RESULT fundo positivo: EO $&e0 V (tabela 9.96)"
if abs(e0-(9.96)) > 0.039
  let ok = 0
end
meas tran e1 FIND v(eo) AT=0.000195
echo "RESULT fundo positivo - LSB: EO $&e1 V (tabela 9.88)"
if abs(e1-(9.88)) > 0.039
  let ok = 0
end
meas tran e2 FIND v(eo) AT=0.000295
echo "RESULT (+) zero: EO $&e2 V (tabela 0.04)"
if abs(e2-(0.04)) > 0.039
  let ok = 0
end
meas tran e3 FIND v(eo) AT=0.000395
echo "RESULT (-) zero: EO $&e3 V (tabela -0.04)"
if abs(e3-(-0.04)) > 0.039
  let ok = 0
end
meas tran e4 FIND v(eo) AT=0.000495
echo "RESULT fundo negativo + LSB: EO $&e4 V (tabela -9.88)"
if abs(e4-(-9.88)) > 0.039
  let ok = 0
end
meas tran e5 FIND v(eo) AT=0.000595
echo "RESULT fundo negativo: EO $&e5 V (tabela -9.96)"
if abs(e5-(-9.96)) > 0.039
  let ok = 0
end
if ok > 0
  echo "PASS  Tabela 3 reproduzida (dentro de 1/2 LSB = 39 mV)"
else
  echo "FAIL  Tabela 3"
end
quit
.endc
.end

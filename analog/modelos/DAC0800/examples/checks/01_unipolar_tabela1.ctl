.control
set noaskquit
run
let ok = 1
meas tran e0 FIND v(eo) AT=1.9e-05
meas tran eb0 FIND v(eob) AT=1.9e-05
echo "RESULT fundo de escala: EO $&e0 V, EOB $&eb0 V (tabela -9.96 / 0)"
if (abs(e0-(-9.96)) > 0.0195) | (abs(eb0-(0)) > 0.0195)
  let ok = 0
end
meas tran e1 FIND v(eo) AT=3.9e-05
meas tran eb1 FIND v(eob) AT=3.9e-05
echo "RESULT fundo de escala - LSB: EO $&e1 V, EOB $&eb1 V (tabela -9.92 / -0.04)"
if (abs(e1-(-9.92)) > 0.0195) | (abs(eb1-(-0.04)) > 0.0195)
  let ok = 0
end
meas tran e2 FIND v(eo) AT=5.9e-05
meas tran eb2 FIND v(eob) AT=5.9e-05
echo "RESULT meia escala + LSB: EO $&e2 V, EOB $&eb2 V (tabela -5.04 / -4.92)"
if (abs(e2-(-5.04)) > 0.0195) | (abs(eb2-(-4.92)) > 0.0195)
  let ok = 0
end
meas tran e3 FIND v(eo) AT=7.9e-05
meas tran eb3 FIND v(eob) AT=7.9e-05
echo "RESULT meia escala: EO $&e3 V, EOB $&eb3 V (tabela -5 / -4.96)"
if (abs(e3-(-5)) > 0.0195) | (abs(eb3-(-4.96)) > 0.0195)
  let ok = 0
end
meas tran e4 FIND v(eo) AT=9.9e-05
meas tran eb4 FIND v(eob) AT=9.9e-05
echo "RESULT meia escala - LSB: EO $&e4 V, EOB $&eb4 V (tabela -4.96 / -5)"
if (abs(e4-(-4.96)) > 0.0195) | (abs(eb4-(-5)) > 0.0195)
  let ok = 0
end
meas tran e5 FIND v(eo) AT=0.000119
meas tran eb5 FIND v(eob) AT=0.000119
echo "RESULT zero + LSB: EO $&e5 V, EOB $&eb5 V (tabela -0.04 / -9.92)"
if (abs(e5-(-0.04)) > 0.0195) | (abs(eb5-(-9.92)) > 0.0195)
  let ok = 0
end
meas tran e6 FIND v(eo) AT=0.000139
meas tran eb6 FIND v(eob) AT=0.000139
echo "RESULT zero: EO $&e6 V, EOB $&eb6 V (tabela 0 / -9.96)"
if (abs(e6-(0)) > 0.0195) | (abs(eb6-(-9.96)) > 0.0195)
  let ok = 0
end
if ok > 0
  echo "PASS  Tabela 1 reproduzida (todos os codigos dentro de 1/2 LSB = 19,5 mV)"
else
  echo "FAIL  Tabela 1"
end
quit
.endc
.end

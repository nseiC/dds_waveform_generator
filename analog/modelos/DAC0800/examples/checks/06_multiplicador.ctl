.control
set noaskquit
run
meas tran pp0 PP v(eo) from=0.001 to=0.002
meas tran pp1 PP v(eo) from=0.003 to=0.004
meas tran pp2 PP v(eo) from=0.005 to=0.006
meas tran pp3 PP v(eo) from=0.007 to=0.008
let r1 = pp1/pp0
let r2 = pp2/pp0
let r3 = pp3/pp0
echo "RESULT amplitude pp: codigo 255 $&pp0 V, 128 $&pp1 V, 64 $&pp2 V, 16 $&pp3 V"
echo "RESULT razoes: $&r1 , $&r2 , $&r3 (128/255 = 0,502, 64/255 = 0,251, 16/255 = 0,0627)"
if (abs(pp0-8*255/256) < 0.1) & (abs(r1-128/255) < 0.005) & (abs(r2-64/255) < 0.005) & (abs(r3-16/255) < 0.003)
  echo "PASS  a saida e codigo x referencia (multiplicador de 2 quadrantes)"
else
  echo "FAIL  multiplicador"
end
quit
.endc
.end

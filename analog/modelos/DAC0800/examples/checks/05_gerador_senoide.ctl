.control
set noaskquit
run
meas tran emax MAX v(eo) from=1m to=3m
meas tran emin MIN v(eo) from=1m to=3m
meas tran omax MAX v(out) from=1m to=3m
meas tran omin MIN v(out) from=1m to=3m
meas tran f1 TRIG v(out) VAL=0 RISE=1 TARG v(out) VAL=0 RISE=2
let fo = 1/f1
echo "RESULT escada de $&emin a $&emax V; filtrada de $&omin a $&omax V; frequencia $&fo Hz"
if (abs(emax-9.92) < 0.06) & (abs(emin+9.92) < 0.06) & (abs(fo-1k) < 10) & (omax > 9) & (omin < -9)
  echo "PASS  senoide de 1 kHz, +-9,96 V em 8 bits"
else
  echo "FAIL  gerador de senoide"
end
quit
.endc
.end

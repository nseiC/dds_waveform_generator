.control
set noaskquit
run
linearize v(eo)
let s = vector(256)
let k = 0
while k < 256
  let idx = floor((k*10u + 9u)/20n + 0.5)
  let s[k] = v(eo)[idx]
  let k = k + 1
end
let d = s[1,255] - s[0,254]
let dmin = minimum(d)
let dmax = maximum(d)
let e0 = s[0]
let e255 = s[255]
echo "RESULT codigo 0: $&e0 V, codigo 255: $&e255 V, degraus de $&dmin a $&dmax V (1 LSB = 39,1 mV)"
if (abs(e0) < 0.005) & (abs(e255-9.96) < 0.02) & (dmin > 0.0195) & (dmax < 0.0585)
  echo "PASS  256 degraus monotonicos de 0 a +9,96 V"
else
  echo "FAIL  rampa em escada"
end
quit
.endc
.end

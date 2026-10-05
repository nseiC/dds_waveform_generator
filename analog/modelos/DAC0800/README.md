> [!NOTE]
> **Origem:** esta pasta foi copiada do repositório
> [nseiC/LTSpice-behavioral-IC-lib](https://github.com/nseiC/LTSpice-behavioral-IC-lib/tree/main/DAC0800)
> (commit `5890672`, 1º de outubro de 2026), onde o modelo é mantido. Ela está aqui sem alterações
> (além desta nota), em domínio público (CC0), como no original. O `DAC0800.lib` é o mesmo arquivo usado na simulação
> da placa ([`../../simulation/DAC0800.lib`](../../simulation/DAC0800.lib)) e é descrito no
> Apêndice D do TCC. Atualizações do modelo devem ser feitas no repositório de origem.

# DAC0800 — behavioural SPICE model for LTspice

A functional (`.subckt`) macromodel of the **DAC0800 / DAC0802 8-bit
multiplying D/A converter** with complementary current outputs, built from the
Texas Instruments (National) datasheet *SNAS538C, June 1999 – revised
February 2013*.

It is not a transistor-level model. Every block of the Block Diagram
(Figure 4) — reference amplifier, reference current source, eight current
switches, complementary outputs, logic inputs with threshold control — is
reproduced by its **terminal behaviour**, with the numbers of the TYPICAL
column of the Electrical Characteristics and the typical curves. The point is
to use the DAC as part of a circuit: op-amp output stages, bipolar outputs,
waveform generators, A/D converters, a modulated (multiplying) reference.

## Files

| File | What it is |
|---|---|
| `DAC0800.lib` | the model — a single `.subckt DAC0800`, heavily commented |
| `DAC0800.asy` | LTspice symbol: B1…B8 and VLC on the left, supplies, reference and outputs on the right |
| `examples/` | netlists prontos: Tabelas 1, 2 e 3 do datasheet, rampa em escada com amp. op., gerador de senoide digital, multiplicador / atenuador digital |
| `tests/` | datasheet regression tests (see *Verification*) |

## Installing in LTspice

1. Copy `DAC0800.lib` and `DAC0800.asy` next to your schematic (or into
   `Documents\LTspiceXVII\lib\sub` and `...\lib\sym`).
2. Place the symbol with **F2 → (your directory) → DAC0800**.
3. The symbol already carries `SYMATTR ModelFile DAC0800.lib`. In a plain
   netlist (Figure 18 — basic positive reference):

```
.include DAC0800.lib
Vr  vr 0 10
R14 vr r14 5k            ; RREF: IREF = 10 V / 5k = 2 mA
R15 r15 0 5k             ; R15 ~ RREF
Cc  cc vm 10n            ; CC = 0.01 uF for a fixed reference
*  VLC IOUTB VM IOUT B1 B2 B3 B4 B5 B6 B7 B8 VP VREFP VREFN COMP
X1 0   iob   vm io   b1 b2 b3 b4 b5 b6 b7 b8 vp r14   r15   cc DAC0800
```

### What to put on the schematic

```
.tran 0 <stop> 0 <maxstep>        e.g.  .tran 0 2.6m 0 100n
```

The bits switch in ~70 ns; a `maxstep` of a few tens of ns shows the edges,
anything up to a fraction of the code period is fine for the levels. Pick
`CC` as the datasheet does: **0.01 µF for a fixed reference** (slow, quiet
reference loop), **15 pF or less when the reference carries a signal**
(multiplying, Figure 7), none for a pulsed reference into a low impedance
(Figure 26).

## Pinout

The port order is the 16-lead PDIP pin order (the SOIC numbers the same
signals differently):

| # | Name | | # | Name |
|---:|---|---|---:|---|
| 1 | `VLC` — threshold control | | 9 | `B5` |
| 2 | `IOUTB` — I<sub>OUT</sub> bar | | 10 | `B6` |
| 3 | `VM` — V− | | 11 | `B7` |
| 4 | `IOUT` | | 12 | `B8` — LSB |
| 5 | `B1` — MSB | | 13 | `VP` — V+ |
| 6 | `B2` | | 14 | `VREFP` — V<sub>REF</sub>(+) |
| 7 | `B3` | | 15 | `VREFN` — V<sub>REF</sub>(−) |
| 8 | `B4` | | 16 | `COMP` — compensation |

I<sub>FS</sub> = (V<sub>REF</sub>/R<sub>REF</sub>)·255/256,
I<sub>OUT</sub> = I<sub>REF</sub>·code/256, I<sub>OUT</sub> + I<sub>OUTB</sub> =
I<sub>FS</sub> for every code. Both outputs **sink** current (into the part).

## How each block is modelled

| Block | Model | From the datasheet |
|---|---|---|
| Reference amplifier | transconductance stage (0.4 mS, ±40 µA) into COMP (5 pF inside + your C<sub>C</sub> to V−); COMP sets the reference current sunk at pin 14, so the loop holds V<sub>14</sub> = V<sub>15</sub>; 1 µA bias out of pin 15 | I<sub>15</sub>; Figure 7 (≈3 MHz with C<sub>C</sub> = 15 pF), Figure 26 / dI/dt = 8 mA/µs with no C<sub>C</sub> |
| Reference range | soft limit at 2.1 mA (V− = −5 V) … 4.2 mA (V− ≤ −8 V); I<sub>REF</sub> collapses with pin 15 less than 4.5 V above V− | I<sub>FSR</sub>, Figures 5 and 8 |
| Current switches | B1…B8 steer I<sub>REF</sub>/2 … I<sub>REF</sub>/256 to IOUT (bit high) or IOUTB (bit low); the last 1/256 is the R-2R termination; ideal weights; 0.2 µA zero-scale current on each output | I<sub>ZS</sub>; Figures 4 and 17 |
| Logic inputs | threshold V<sub>LC</sub> + 1.4 V, each bit fully switched within ±0.1 V of it; 2 µA out of a low input, ~0 into a high one | Figures 9, 10, 13, 27; V<sub>IL</sub> 0.8 V / V<sub>IH</sub> 2.0 V with V<sub>LC</sub> = 0 |
| Switching | each bit ramps between the outputs in 70 ns: 35 ns to 50 %, within 1/2 LSB in ~93 ns | t<sub>PLH</sub> / t<sub>PHL</sub> 35 ns, t<sub>s</sub> 100 ns typ |
| Output compliance | the current holds down to V− + 4.5 V (−10.5 V at ±15 V) and up to any positive voltage | V<sub>OC</sub> −10 … +18 V; Figure 11 |
| Supplies | I+ = 2.2 mA + 10 µA/V·(V+ − V−); I− = I+ + I<sub>REF</sub> + I<sub>OUT</sub> + I<sub>OUTB</sub> (the reference and output currents return through V−) | power supply current table |

## Everything is a parameter

```
X1 … DAC0800 TSW=100 IZS=1u
```

| Parameter | Default | Meaning |
|---|---|---|
| `VTHO`, `VTHW` | 1.4 V, 0.1 V | logic threshold above V<sub>LC</sub>; half-width of a bit transition |
| `TSW` | 70 ns | bit switching ramp (t<sub>pd</sub> = `TSW`/2) |
| `IIL`, `CIN` | 2 µA, 2 pF | current out of a low input; input capacitance (assumed) |
| `IZS` | 0.2 µA | zero-scale current on each output |
| `COUT` | 5 pF | output capacitance (assumed, not in the datasheet) |
| `GM1`, `I1MAX`, `CINT` | 0.4 mS, 40 µA, 5 pF | reference amplifier: transconductance, current limit (sets the slew), internal compensation |
| `GM2` | 1 mA/V | reference current per volt on COMP |
| `VCMN` | 4.5 V | compliance and reference common-mode limit above V− |
| `IBREF` | 1 µA | reference bias current out of pin 15 |

## Verification

`tests/` holds a datasheet-driven regression suite, run under **ngspice**
(`run_tests.sh` adds the `PARAMS:` keyword — the only difference from the
LTspice file):

```
cd tests && ./run_tests.sh
```

All 34 checks pass (V<sub>S</sub> = ±15 V, V<sub>REF</sub> = 10 V,
R<sub>REF</sub> = R15 = 5 kΩ unless noted):

| Measured | Model | Datasheet |
|---|---|---|
| Table 1 (unipolar, Fig. 21), 7 codes | e.g. full scale −9.957 / 0.000 V, half scale −4.998 / −4.959 V | −9.960 / 0.000, −5.000 / −4.960 V — every code within 1/2 LSB |
| Table 2 (bipolar, Fig. 22), 7 codes | +9.998 / −9.914 V … −9.914 / +9.998 V | ±10.000 / ∓9.920 V — within 1/2 LSB |
| Table 3 (offset binary, Fig. 23) | +9.956 / +0.039 / −0.039 / −9.956 V | +9.960 / +0.040 / −0.040 / −9.960 V |
| All 256 codes | monotonic, every step 1.000 LSB, worst deviation 0.13 LSB, I<sub>OUT</sub> + I<sub>OUTB</sub> = I<sub>FS</sub> | 8-bit monotonic, nonlinearity ±0.19 % FS max |
| Logic threshold, V<sub>LC</sub> = 0 / 3.4 V | 1.40 / 4.80 V, 10–90 % within ±0.08 V | V<sub>LC</sub> + 1.4 V, fully switched within ±0.1 V (Fig. 13) |
| Logic input current, low | 2.0 µA out of the pin | I<sub>IL</sub> −2 µA typ |
| I<sub>FS</sub> for I<sub>REF</sub> = 0.2 / 1 / 2 / 4 mA | 255/256·I<sub>REF</sub> (+0.2 µA I<sub>ZS</sub>) | Figure 5 |
| Output current range | 2.10 mA at V− = −5 V, 4.18 mA at V− = −15 V | I<sub>FSR</sub> max 2.1 / 4.2 mA |
| Reference bias; negative reference (Fig. 20) | 1.0 µA out of pin 15; I<sub>FS</sub> = 1.991 mA | I<sub>15</sub> −1 µA typ |
| Output compliance, all bits on | constant within 1/2 LSB from −10 V to +18 V, ~0 at −11.5 V | V<sub>OC</sub> −10 … +18 V |
| t<sub>PLH</sub> / t<sub>PHL</sub>, all bits | 35.6 / 35.6 ns | 35 ns typ, 60 max |
| Settling to 1/2 LSB, all bits | 93 ns | 100 ns typ |
| Major carry 01111111 → 10000000 | within 1/2 LSB after 105 ns | — |
| Pulsed reference, no C<sub>C</sub> (Fig. 26) | dI/dt = 7.8 mA/µs | 8 mA/µs typ, 4 min |
| Reference small signal (Fig. 7), R14 = 1 kΩ | −3 dB at 3.3 MHz (C<sub>C</sub> = 15 pF), 6.4 kHz (C<sub>C</sub> = 10 nF) | MHz range with 15 pF |
| I+ / I− at ±5 V 1 mA, +5/−15 V 2 mA, ±15 V 2 mA | 2.31 / 4.30, 2.41 / 6.39, 2.51 / 6.49 mA; independent of the code | 2.3 / 4.3, 2.4 / 6.4, 2.5 / 6.5 mA typ |

## Exemplos

Cada exemplo em `examples/` é simulado e conferido por
`examples/run_examples.sh` (todos juntos, alguns segundos). Os que usam um
amp. op. trazem um modelo comportamental da classe do LM741 (100 dB, 1 MHz,
0,5 V/µs) no próprio arquivo.

| Exemplo | O que mostra | Resultado medido |
|---|---|---|
| `01_unipolar_tabela1.cir` | Figura 21: saídas em corrente em 5k para o terra | os 7 códigos da Tabela 1 dentro de 1/2 LSB |
| `02_bipolar_tabela2.cir` | Figura 22: 10k para +10 V, saída diferencial de ~20 Vpp sem amp. op. | os 7 códigos da Tabela 2 dentro de 1/2 LSB |
| `03_rampa_escada_ampop.cir` | Figura 24: contador de 8 bits + amp. op. de transimpedância | 256 degraus de 39,0 mV, de 0 a +9,957 V |
| `04_offset_binario.cir` | Figura 23: binário com offset simétrico | Tabela 3: +9,956 / +0,039 / −0,039 / −9,956 V |
| `05_gerador_senoide.cir` | tabela de seno de 8 bits a 100 kHz + DAC + filtro RC | senoide de 1 kHz, ±9,9 V |
| `06_multiplicador.cir` | referência modulada (5 V + 4 V de seno), código como "ganho" | amplitude ×1, ×0,502, ×0,251, ×0,0627 para os códigos 255, 128, 64, 16 |

```
cd examples && ./run_examples.sh                       # todos
cd examples && ./run_examples.sh 06_multiplicador.cir  # um so
```

Observações didáticas:

* **O "zero" do offset binário não existe** (exemplo 04): o passo na saída é
  de 2 LSB (78 mV) e o código 128 dá +40 mV, o 127 dá −40 mV.
* **A referência é unipolar** (exemplo 06): a corrente de referência só
  entra no pino 14, então o sinal na referência precisa de um offset que a
  mantenha positiva — é a "multiplicação de 2 quadrantes" do datasheet
  (Figura 28 mostra como acomodar referências bipolares).
* **C<sub>C</sub> decide o que a referência aguenta**: com os 10 nF da
  referência fixa a malha de referência corta em ~6 kHz; o multiplicador do
  exemplo 06 usa 15 pF (corte em ~3 MHz).

## LTspice .FRA

The DAC0800 is not inside a control loop in any of the examples and was not
put through the FRA robustness check. It is built the same way as the
drivers (no time-dependent sources, ramps written as *target − y*, no
saturating stage left without a slope), and `.ac` works on it: the
reference small-signal response of test 08 is an `.ac` analysis.

## What is *not* modelled

* **No temperature model** (full-scale tempco, threshold drift of
  Figure 10).
* **Ideal bit weights**: no nonlinearity, no full-scale or full-scale-symmetry
  error, and no switching glitch of its own — all bits move together (the
  only glitch is the one the input edges' own skew makes).
* The **extra compliance and reference range at low I<sub>REF</sub>**
  (Figures 8 and 11 give ~1–2 V more at 0.2 mA) — fixed at V− + 4.5 V.
* The **positive common-mode limit** of the reference amplifier (V+ − 1.5 V),
  the logic-input range (−10 … +18 V), the power supply sensitivity and the
  absolute maximum ratings are not policed. The reference current cannot go
  negative (as in the part).
* **Output resistance** (> 20 MΩ) and capacitance are not in the datasheet:
  1 GΩ leakage and 5 pF on each output.
* A **floating logic input reads high** (its 2 µA charges it up) — tie
  unused inputs.

## Licence

Public domain / CC0. No warranty.

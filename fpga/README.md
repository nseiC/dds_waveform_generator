# Parte digital: o DDS no FPGA

[← Voltar ao início](../README.md) · [Parte analógica](../analog/README.md) · [Interface (GUI)](../GUI/README.md) · [Roda de fase (jogo)](https://nseic.github.io/dds_waveform_generator/jogo/)

Núcleo do gerador, em VHDL: acumulador de fase de 32 bits, quatro memórias de forma de onda
e o Virtual JTAG para controle pelo PC. Roda na **Terasic DE2-115** (Intel Cyclone IV E
EP4CE115F29C7) e entrega a cada clock um código de 8 bits para o DAC da
[placa analógica](../analog/README.md).

Ferramentas: Quartus Prime 18.1 Lite (síntese) e GHDL (simulação).

## Arquitetura

```
                       ┌──────────────────────── phase_accumulator ────────────────────────┐
 frequência (Hz) ──18──▶ frequency_translator ──FTW 32──▶ word_adder ──▶ phase_register ──┬─▶ truncator ──10──┐
                       │   M = (f·K) >> 24                    ▲                           │                 │
                       │                                      └──── realimentação 32 ─────┘                 │
                       └────────────────────────────────────────────────────────────────────────────────────┘
                                                                                                             │ endereço
                       ┌──────────────────────────────── LUT ───────────────────────────────────┐            │
                       │  sine_LUT (ROM)  saw_LUT (ROM)  sinc_LUT (ROM)  arbitrary_LUT (RAM) ◀──┼────────────┘
                       │       └──────────────┴──────────────┴─────────────┘                    │
                       │                         out_mux ◀── sel (2 bits)                       │
                       └─────────────────────────────┬──────────────────────────────────────────┘
                                                     │ 8 bits
 CLOCK_50 ──▶ PLL (÷5) ──▶ 10 MHz (todos os blocos)  ▼
                                              DAC paralelo 8 bits ──▶ filtro de reconstrução ──▶ saída analógica

 PC (GUI Python) ──USB-Blaster──▶ Virtual JTAG ──▶ frequência, sel, escrita na LUT arbitrária
```

O acumulador de fase soma a palavra de sintonia (FTW, ou M) a cada clock. O estouro natural
do registrador de 32 bits é a volta de 2π. Os 10 bits mais significativos da fase endereçam
a LUT, que converte fase em amplitude.

> [!TIP]
> Para ver isso funcionando em câmera lenta, abra a **[roda de fase](https://nseic.github.io/dds_waveform_generator/jogo/)**:
> é o mesmo acumulador, reduzido a 8 bits, com a LUT ao lado e o desafio *descubra o M*.

## Parâmetros

| Grandeza | Valor |
|---|---|
| Clock do DDS (f<sub>clk</sub>) | 10 MHz (PLL a partir dos 50 MHz da placa) |
| Acumulador de fase (N) | 32 bits |
| Resolução de frequência Δf = f<sub>clk</sub> / 2³² | ≈ 2,33 mHz |
| Endereço da LUT (P) | 10 bits, 1024 amostras por período |
| Largura da amostra (D) | 8 bits, offset binary (zero do sinal = código 128) |
| Entrada de frequência | 18 bits, inteiro em Hz (0 a 262 143 Hz) |
| Conversão Hz → FTW | `M = (f × 7 205 759 404) >> 24` (ponto fixo Q24) |
| Limite de Nyquist | 5 MHz (na prática, bem abaixo, conforme o DAC e o filtro) |

Relações principais:

$$
f_{out} = \frac{M \cdot f_{clk}}{2^{N}} \qquad
\Delta f = \frac{f_{clk}}{2^{N}} \qquad
\text{SFDR}_{\text{truncamento de fase}} \approx 6{,}02 \cdot P \ \text{dB} \approx 60\ \text{dB}
$$

A quantização da amostra em 8 bits limita a relação sinal-ruído a cerca de
6,02 · 8 + 1,76 ≈ 50 dB.

## Arquivos

| Arquivo | Função |
|---|---|
| `DDS.qpf`, `DDS.qsf` | Projeto Quartus (Cyclone IV E EP4CE115F29C7, top-level `DDS`) |
| `DDS.vhd` | Top-level: PLL, acumulador de fase, LUT e Virtual JTAG. Portas: `clk`, `rst`, `frequency` (18), `sel` (2), `wren`, `qIn` (8), `qOut` (8) |
| `phase_accumulator.vhd` | Junta o conversor de frequência, o somador, o registrador de fase e o truncador |
| `frequency_translator.vhd` | Converte a frequência em Hz na FTW de 32 bits (multiplicação em ponto fixo) |
| `word_adder.vhd` | Somador de 32 bits: FTW + fase atual |
| `phase_register.vhd` | Registrador de fase de 32 bits, com reset assíncrono |
| `truncator.vhd` | Seleciona os 10 bits mais significativos da fase (31..22) para endereçar a LUT |
| `LUT.vhd` | Instancia as quatro memórias e o multiplexador de saída |
| `out_mux.vhd` | Seleciona a forma de onda: `00` seno, `01` rampa, `10` sinc, `11` arbitrária |
| `sine_LUT`, `saw_LUT`, `sinc_LUT` (`.vhd/.qip/.cmp`) | ROMs 1024 × 8 (`altsyncram`), inicializadas pelos `.mif` |
| `arbitrary_LUT` (`.vhd/.qip/.cmp`) | RAM 1024 × 8 para a forma de onda arbitrária |
| `PLL` (`.vhd/.qip/.cmp/.ppf`) | ALTPLL: 50 MHz → 10 MHz |
| `jtag.qsys`, `jtag/` | Virtual JTAG (Platform Designer), IR de 2 bits |
| `lut/` | Tabelas `.mif` das formas de onda ([abaixo](#formas-de-onda-lut)) |
| `sim/` | Testbench do top-level (`tb_DDS.vhd`, VHDL-2008) e script do GHDL ([Simulação](#simulação)) |

<details>
<summary><b>Como a frequência vira FTW sem divisor</b> (<code>frequency_translator</code>)</summary>

<br>

A palavra de sintonia exata seria `M = f · 2³² / f_clk`, o que pede uma divisão. Como f<sub>clk</sub>
é fixo, a divisão vira multiplicação por uma constante em ponto fixo com 24 bits fracionários:

```
K = round(2^56 / f_clk) = 7 205 759 404 = 0x1_AD7F_29AC   (33 bits)
P = f · K                                                  (18 + 33 = 51 bits)
M = P >> 24                                                (32 bits)
```

Para todas as entradas de 0 a 262 143 Hz o erro de `M` é menor que 1 LSB, ou seja, o erro de
frequência fica abaixo de Δf ≈ 2,33 mHz. A GUI usa a mesma conta para mostrar a FTW esperada.

</details>

<details>
<summary><b>Por que só 10 bits endereçam a LUT</b> (<code>truncator</code>)</summary>

<br>

Uma LUT com 2³² posições seria impossível. O truncador descarta os 22 bits de baixo da fase e
usa `fase(31..22)` como endereço: são 1024 amostras por período. O custo é um erro de fase
periódico, que aparece no espectro como espúrios a cerca de 6,02 · P ≈ 60 dB abaixo da
portadora. Na roda de fase dá para ver o efeito: o ponteiro anda, mas o endereço só muda
quando ele cruza a fronteira de um setor.

</details>

## Formas de onda (`lut/`)

Todas têm 1024 amostras de 8 bits em offset binary, com o zero do sinal no código 128.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../docs/img/luts-dark.svg">
  <img src="../docs/img/luts-light.svg" alt="Conteúdo das quatro tabelas: seno, triângulo, sinc e ECG sintético" width="100%">
</picture>

| Arquivo | Conteúdo | Uso |
|---|---|---|
| `sine_1024x8.mif` | `round(128 + 127·sin(2πk/1024))` | ROM `sine_LUT` |
| `triangle_1024x8.mif` | Rampa de subida e descida, em fase com o seno | ROM `saw_LUT` |
| `sinc_1024x8.mif` | `round(128 + 127·sinc((k−512)/64))`, janela x ∈ [−8, 8) | ROM `sinc_LUT` |
| `ecg_1024x8.mif` | ECG sintético estocástico (modelo ECGSYN) | Forma arbitrária, carregada pela GUI |

<details>
<summary><b>ECG sintético</b></summary>

<br>

Gerado com o modelo dinâmico **ECGSYN** (McSharry et al., 2003), distribuído pelo PhysioNet:
três EDOs acopladas com as ondas P, Q, R, S e T como gaussianas na fase, intervalos RR
estocásticos com espectro bimodal (ondas de Mayer a 0,1 Hz e arritmia sinusal respiratória
a 0,25 Hz, razão LF/HF = 0,5) e ruído de medida. Parâmetros: 120 bpm médios, desvio de
3 bpm, ruído de 0,015 mV, semente 2026.

A tabela contém **2 batimentos por período** (RR de 0,502 s e 0,496 s), recortados no segmento
TP para emendar sem descontinuidade. Assim, com **f = 1 Hz** no DDS, a saída é um ECG de
**120 bpm**. Escala: ≈ 8,8 µV por código (R ≈ 1,1 mV).

</details>

## Controle pelo PC (Virtual JTAG)

| IR | Instrução | DR (18 bits) |
|---|---|---|
| `00` | nenhuma | — |
| `01` | frequência | f em Hz |
| `10` | forma de onda | `sel` nos 2 bits de baixo |
| `11` | escrita na LUT arbitrária | `endereço(9..0) & dado(7..0)` |

O PC usa o `quartus_stp` (`device_virtual_ir_shift` / `device_virtual_dr_shift`). A
[GUI](../GUI/README.md) faz isso por trás e documenta o lado do PC.

> [!NOTE]
> O Virtual JTAG já está instanciado no top-level, mas o bloco de registradores que recebe
> o DR ainda não foi feito. Por enquanto, frequência, `sel` e escrita na LUT são portas do
> top-level (ver [Estado atual](#estado-atual)).

## Compilar e gravar

1. Abra `fpga/DDS.qpf` no Quartus 18.1 e compile (*Processing → Start Compilation*).
   Se a pasta `fpga/jtag/` for apagada, regenere o Virtual JTAG abrindo `fpga/jtag.qsys`
   no Platform Designer (*Generate HDL*, VHDL).
2. Grave o `.sof` (`fpga/output_files/DDS.sof`) pelo Programmer (USB-Blaster, chave
   RUN/PROG da placa em **RUN**).
3. Feche o Programmer antes de abrir a [GUI](../GUI/README.md): os dois disputam o cabo.

## Simulação

`sim/tb_DDS.vhd` simula o top-level completo, com o PLL e as memórias pelos modelos
`altera_mf` do Quartus, e confere o resultado sozinho:

- o PLL gera 10 MHz a partir do clock de 50 MHz;
- o endereço da LUT avança f·1024/f<sub>clk</sub> posições por clock e dá a volta na frequência
  pedida (1 kHz, 100 kHz e 262 143 Hz, tolerância de 0,1 %);
- `qOut` segue a forma de onda escolhida por `sel`, comparada amostra a amostra com os
  `.mif`, e a RAM arbitrária devolve o que foi escrito com `wren`.

```bash
sudo apt install ghdl     # uma vez
fpga/sim/run_ghdl.sh      # ~3,5 min; termina com "tb_DDS: OK"
```

Na primeira execução o script compila a biblioteca `altera_mf` em `fpga/sim/work/`
(o Quartus é procurado em `~/intelFPGA_lite/18.1/quartus` ou em `QUARTUS_ROOTDIR`).
O testbench usa nomes externos do VHDL-2008 para observar o endereço interno `bOut`.
O ModelSim-Altera 18.1 para Linux é 32-bit e precisa das bibliotecas i386 do sistema;
por isso a simulação foi montada no GHDL.

Os códigos de um seno de 1 kHz simulados aqui também alimentam a
[simulação analógica](../analog/README.md#simulação-no-ltspice): os PWL dos 8 bits em
`analog/simulation/pwl/` saíram desta simulação.

## Estado atual

- [x] Acumulador de fase de 32 bits com conversão Hz → FTW em ponto fixo
- [x] PLL de 10 MHz a partir do clock de 50 MHz, clock de todo o caminho de dados
- [x] ROMs de seno, rampa e sinc, RAM arbitrária e multiplexador de saída
- [x] Virtual JTAG instanciado no top-level
- [x] Testbench do top-level passando no GHDL
- [ ] Bloco de registradores do JTAG (deslocamento do DR em `tck`, atualização no Update-DR e
      sincronização para o domínio de 10 MHz)
- [ ] Ligar frequência, `sel` e escrita da LUT arbitrária ao JTAG; hoje são portas do top-level,
      e `tdo` e `ir_out` do Virtual JTAG ainda não têm fonte
- [ ] Endereço de escrita da LUT arbitrária: hoje a RAM é escrita no endereço da fase; a escrita
      pelo JTAG vai precisar de um multiplexador de endereço
- [ ] Pinagem do DAC, do clock e do reset (o `DDS.qsf` ainda não tem atribuições de pinos) e
      restrições de timing (`.sdc`)
- [ ] Validação na placa, com medidas de frequência e espectro

<details>
<summary><b>Correções de ligação (outubro de 2026)</b>, confirmadas na síntese e na simulação</summary>

<br>

- `truncator`: o endereço da LUT passou a ser `fase(31..22)`; antes eram os 10 bits menos
  significativos da fase.
- `phase_accumulator`: a realimentação do somador agora é a saída do `phase_register`; antes a
  entrada `feedback` não tinha fonte e o acumulador não acumulava.
- `LUT`: `sinc_LUT` ligada em `qsinc` (havia dois drivers em `qsaw`) e `out_mux` com mapeamento
  nomeado; antes `qsinc` ficava de fora e a saída `qout` sem conexão.
- `DDS`: o PLL recebe a porta `clk` (antes um sinal sem fonte); o acumulador de fase roda em
  `clk10MHz`, como a LUT e o cálculo da FTW; `sel` e `wren` viraram portas de entrada.
- Na síntese, o Quartus removia as memórias e o PLL (0 bits de memória). Agora ficam as
  4 memórias de 1024 × 8 e o PLL, e os avisos caíram de 90 para 10, todos do Virtual JTAG
  ainda não ligado.

</details>

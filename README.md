# Gerador de formas de onda DDS em FPGA

Trabalho de Conclusão de Curso: gerador de sinais por **Síntese Digital Direta (DDS)**
implementado em VHDL na placa **Terasic DE2-115** (Intel Cyclone IV E EP4CE115F29C7),
com saída por DAC paralelo de 8 bits e controle pelo PC via **Virtual JTAG**.

Ferramentas: Quartus Prime 18.1 Lite, ModelSim-Altera, Python 3.12 (interface).

> Projeto em desenvolvimento — ver [Estado atual](#estado-atual).

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

O acumulador de fase soma a palavra de sintonia (FTW, ou M) a cada clock; o estouro
natural do registrador de 32 bits é a volta de 2π. Os 10 bits mais significativos da
fase endereçam a LUT, que converte fase em amplitude.

## Parâmetros

| Grandeza | Valor |
|---|---|
| Clock do DDS (f_clk) | 10 MHz (PLL a partir dos 50 MHz da placa) |
| Acumulador de fase (N) | 32 bits |
| Resolução de frequência Δf = f_clk / 2³² | ≈ 2,33 mHz |
| Endereço da LUT (P) | 10 bits → 1024 amostras por período |
| Largura da amostra / DAC (D) | 8 bits, offset binary (0 V = código 128) |
| Entrada de frequência | 18 bits, inteiro em Hz (0 a 262 143 Hz) |
| Conversão Hz → FTW | `M = (f × 7 205 759 404) >> 24` (ponto fixo Q24, K = round(2⁵⁶ / f_clk)) |
| Limite de Nyquist | 5 MHz (uso prático bem abaixo, conforme DAC e filtro) |

Relações principais:

```
f_out = M · f_clk / 2^N          Δf = f_clk / 2^N          SFDR (truncamento de fase) ≈ 6,02 · P dB
```

## Estrutura do repositório

| Arquivo | Função |
|---|---|
| `DDS.vhd` | Top-level: PLL, acumulador de fase, LUT e Virtual JTAG |
| `phase_accumulator.vhd` | Junta conversor de frequência, somador, registrador de fase e truncador |
| `frequency_translator.vhd` | Converte frequência em Hz na FTW de 32 bits (multiplicação em ponto fixo) |
| `word_adder.vhd` | Somador de 32 bits: FTW + fase atual |
| `phase_register.vhd` | Registrador de fase de 32 bits, com reset assíncrono |
| `truncator.vhd` | Seleciona 10 bits da fase para endereçar a LUT |
| `LUT.vhd` | Instancia as quatro memórias e o multiplexador de saída |
| `out_mux.vhd` | Seleciona a forma de onda: `00` seno, `01` rampa, `10` sinc, `11` arbitrária |
| `sine_LUT`, `saw_LUT`, `sinc_LUT` (`.vhd/.qip/.cmp`) | ROMs 1024 × 8 (`altsyncram`), inicializadas pelos `.mif` |
| `arbitrary_LUT` (`.vhd/.qip/.cmp`) | RAM 1024 × 8 para a forma de onda arbitrária |
| `PLL` (`.vhd/.qip/.cmp/.ppf`) | ALTPLL: 50 MHz → 10 MHz |
| `jtag.qsys`, `jtag/` | Virtual JTAG (Platform Designer): IR de 2 bits |
| `lut/` | Tabelas `.mif` (abaixo) |
| `GUI/` | Interface em Python para controlar o DDS pelo PC ([GUI/README.md](GUI/README.md)) |
| `DDS.qpf`, `DDS.qsf` | Projeto Quartus |

## Formas de onda (`lut/`)

Todas com 1024 amostras de 8 bits em offset binary, zero do sinal no código 128.

| Arquivo | Conteúdo | Uso |
|---|---|---|
| `sine_1024x8.mif` | `round(128 + 127·sin(2πk/1024))` | ROM `sine_LUT` |
| `triangle_1024x8.mif` | Rampa de subida e descida, em fase com o seno | ROM `saw_LUT` |
| `sinc_1024x8.mif` | `round(128 + 127·sinc((k−512)/64))`, janela x ∈ [−8, 8) | ROM `sinc_LUT` |
| `ecg_1024x8.mif` | ECG sintético estocástico (modelo ECGSYN) | Forma arbitrária, carregada pela GUI |

### ECG sintético

Gerado com o modelo dinâmico **ECGSYN** (McSharry et al., 2003), distribuído pelo
PhysioNet: três EDOs acopladas com as ondas P, Q, R, S e T como gaussianas na fase,
intervalos RR estocásticos com espectro bimodal (ondas de Mayer a 0,1 Hz e arritmia
sinusal respiratória a 0,25 Hz, razão LF/HF = 0,5) e ruído de medida.
Parâmetros: 120 bpm médios, desvio de 3 bpm, ruído de 0,015 mV, semente 2026.

A tabela contém **2 batimentos por período** (RR de 0,502 s e 0,496 s), recortados
no segmento TP para emendar sem descontinuidade. Assim, com **f = 1 Hz** no DDS, a
saída é um ECG de **120 bpm**. Escala: ≈ 8,8 µV por código (R ≈ 1,1 mV).

## Controle pelo PC (Virtual JTAG)

| IR | Instrução | DR (18 bits) |
|---|---|---|
| `00` | nenhuma | — |
| `01` | frequência | f em Hz |
| `10` | forma de onda | `sel` nos 2 bits de baixo |
| `11` | escrita na LUT arbitrária | `endereço(9..0) & dado(7..0)` |

O PC usa o `quartus_stp` (`device_virtual_ir_shift` / `device_virtual_dr_shift`);
a GUI em `GUI/` faz isso por trás. Detalhes e instalação em [GUI/README.md](GUI/README.md).

## Como usar

1. Abra `DDS.qpf` no Quartus 18.1 e compile (*Processing → Start Compilation*).
   Se a pasta `jtag/` for apagada, regenere o Virtual JTAG abrindo `jtag.qsys` no
   Platform Designer (*Generate HDL*, VHDL).
2. Grave o `.sof` pelo Programmer (USB-Blaster, chave RUN/PROG da placa em **RUN**).
3. Feche o Programmer e rode a interface: `cd GUI && ./run.sh`.
4. Conecte, escolha a frequência e a forma de onda; para a arbitrária, abra
   `lut/ecg_1024x8.mif` (ou outro arquivo) e clique em *Enviar ao FPGA*.

## Estado atual

Implementado:

- Acumulador de fase de 32 bits com conversão Hz → FTW em ponto fixo
- PLL de 10 MHz
- ROMs de seno, rampa e sinc, RAM arbitrária e multiplexador de saída
- Virtual JTAG instanciado no top-level
- Interface gráfica em Python, com envio de frequência, forma de onda e LUT

Pendente:

- Bloco de registradores do JTAG (deslocamento do DR em `tck`, atualização no
  Update-DR e sincronização para o domínio de 10 MHz)
- Ligar frequência, `sel` e escrita da LUT arbitrária ao JTAG
- Pinagem do DAC, do clock e do reset; restrições de timing (`.sdc`)
- Validação em simulação (ModelSim) e na placa, com medidas de frequência e espectro

## Referências

- Analog Devices. *MT-085: Fundamentals of Direct Digital Synthesis (DDS)*.
- Analog Devices. *A Technical Tutorial on Digital Signal Synthesis*, 1999.
- J. Tierney, C. Rader, B. Gold. "A Digital Frequency Synthesizer". *IEEE Transactions
  on Audio and Electroacoustics*, 19(1), 1971.
- P. E. McSharry, G. D. Clifford, L. Tarassenko, L. A. Smith. "A dynamical model for
  generating synthetic electrocardiogram signals". *IEEE Transactions on Biomedical
  Engineering*, 50(3), 2003.
- A. L. Goldberger et al. "PhysioBank, PhysioToolkit, and PhysioNet". *Circulation*,
  101(23), 2000. ECGSYN: <https://physionet.org/content/ecgsyn/>
- Terasic. *DE2-115 User Manual*.

# Código legado: a versão de bancada

[← Parte digital](../README.md) · [← Início](../../README.md)

Versão anterior do gerador, usada na bancada até setembro de 2026, inclusive na
[medição de 3 de setembro](../../analog/README.md) (seno de 100 Hz com 5,08 V de pico a pico).
É o ponto de partida do projeto atual. A pinagem do DAC foi mantida, para que a placa analógica e
o cabo continuassem os mesmos.

**Origem:** repositório `DDS_Generator`, projeto `TCC/TCCV1` (Quartus 17.1), que compila os VHDL
de `TCC/claude/`. Os três arquivos desta pasta são exatamente os que geraram o `.sof` usado na
bancada, compilado em 28 de maio de 2026. Só os caminhos do `DDS.qsf` mudaram.

## Arquitetura

O circuito segue a arquitetura clássica de DDS, no esquema da nota MT-085 da Analog Devices:
acumulador de fase, truncamento e ROM de seno.

| Arquivo | Função |
|---|---|
| `DDS.vhd` | Top-level, todo em 50 MHz. Um contador gera um pulso de habilitação a cada 50 ciclos (1 MHz). As chaves SW[4..0] escolhem a FTW entre cinco constantes, e um registrador entrega a amostra aos pinos. Também gera o `clk_out` de 1 MHz (GPIO[1]) e o `gnd_out` (GPIO[0]). |
| `DDS_core.vhd` | Acumulador de fase de 32 bits, que avança a cada pulso de 1 MHz; o endereço da ROM é `fase(31..24)` |
| `DDS_sine_rom.vhd` | ROM de seno de 256 × 8 bits em offset binary, inferida numa M9K |

| Chave | Frequência | FTW (f<sub>c</sub> = 1 MHz) |
|---|---|---|
| SW0 | 100 Hz | `0x00068DB9` |
| SW1 | 1 kHz | `0x00418937` |
| SW2 | 10 kHz | `0x028F5C29` |
| SW3 | 100 kHz | `0x1999999A` |
| SW4 | 300 kHz | `0x4CCCCCCD` |

Com mais de uma chave ligada, vale a de maior frequência. Sem nenhuma, a saída fica parada no
código 128 (0 V).

**Pinos:** os mesmos da versão atual (`clk` em Y2, `rst_n` em M23, `dac_out[0..7]` em GPIO[2..9],
`clk_out` em GPIO[1] e `gnd_out` em GPIO[0]), mais as chaves SW0 a SW4 (AB28, AC28, AC27, AD27 e
AB27). Todos em 3,3-V LVTTL.

## Comparação com a versão atual

| | Legado | Atual |
|---|---|---|
| Taxa de amostras | 1 MHz (habilitação a cada 50 ciclos de 50 MHz) | 10 MHz (PLL) |
| Acumulador de fase | 32 bits | 32 bits |
| Tabelas | seno, 256 × 8 bits | seno, rampa, sinc e arbitrária regravável, 1024 × 8 bits |
| Frequência | cinco valores fixos, de 100 Hz a 300 kHz | qualquer inteiro de 0 a 262 143 Hz |
| FTW | constantes calculadas à mão | multiplicação em ponto fixo no FPGA |
| Controle | chaves da placa | PC, pelo Virtual JTAG e pela [GUI](../../GUI/README.md) |
| Organização | três entidades: topo (divisor, seleção da FTW e saída), núcleo e ROM | uma entidade por função, com o top-level só ligando os blocos |
| Verificação | simulação no ModelSim, inspecionada a olho | 16 testbenches auto-verificáveis no GHDL |
| Clock para o DAC | 1 MHz | 10 MHz, por registrador DDR |
| Recursos | 72 LEs, 48 registradores, 2 048 bits de memória | 378 LEs, 264 registradores, 32 768 bits de memória |

**Limitações:**
- Gerava só seno, em cinco frequências fixas. Qualquer outra exigia recalcular a constante e recompilar.
- A 300 kHz restavam 3,3 amostras por período.
- A tabela de 256 posições limita o maior espúrio de truncamento de fase a cerca de −48 dBc (6,02 · P, com P = 8).

## Compilar

Abra `fpga/legado/DDS.qpf` no Quartus (17.1 ou 18.1) e compile. A compilação leva cerca de 1 min,
fecha com Fmax de 242 MHz no clock de 50 MHz e grava como a versão atual. A frequência é escolhida
pelas chaves; a GUI não funciona com esta versão, porque ela não tem o Virtual JTAG.

No repositório antigo ficaram também outras tentativas, que não estão aqui:
- uma variante do `DDS.vhd` em `TCCV1/`, a 10 MHz, que não chegou a ser compilada;
- as versões `TCCV2` e `TCCV3`, com dois DACs MCP4921 por SPI e seleção de frequência pelas chaves ou pela UART.

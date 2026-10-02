<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/logo-dark.svg">
    <img src="docs/logo/logo-light.svg" alt="DDS Waveform Generator — Síntese Digital Direta em FPGA Cyclone IV" width="720">
  </picture>
</p>

# DDS Waveform Generator

Gerador de formas de onda por **Síntese Digital Direta (DDS)** descrito em VHDL para FPGA
Intel/Altera **Cyclone IV E** (`EP4CE115F29C7`), desenvolvido como Trabalho de Conclusão de Curso.

## Arquitetura

```
frequency ─► frequency_translator ─► word_adder ─► phase_register ─► truncator ─► LUT ─► qOut
 (18 bits)        (FTW 32 bits)            ▲               │          (10 bits)   (8 bits)
                                           └───────────────┘
                                        acumulador de fase 32 bits
```

| Bloco | Arquivo | Função |
|---|---|---|
| Topo | `DDS.vhd` | Entidade de topo: PLL, acumulador de fase e LUT |
| PLL | `PLL.vhd` | Gera o clock de 10 MHz |
| Acumulador de fase | `phase_accumulator.vhd`, `word_adder.vhd`, `phase_register.vhd` | Soma a FTW a cada ciclo de clock (32 bits) |
| Conversão de frequência | `frequency_translator.vhd` | Converte a frequência desejada (Hz) na palavra de sintonia (FTW) para clock de 10 MHz |
| Truncador | `truncator.vhd` | Reduz a fase de 32 para 10 bits de endereço |
| LUT | `LUT.vhd`, `out_mux.vhd` | ROMs de seno, triangular e sinc + RAM arbitrária, selecionadas por `sel` |

## Tabelas de forma de onda

Todas com 1024 amostras × 8 bits em *offset binary* (`lut/`):

| Arquivo | Forma de onda |
|---|---|
| `lut/sine_1024x8.mif` | Seno, 1 período |
| `lut/triangle_1024x8.mif` | Triangular, em fase com o seno |
| `lut/sinc_1024x8.mif` | Sinc, janela x ∈ [-8, 8) com pico no centro |
| `arbitrary_LUT.vhd` | RAM gravável para forma de onda arbitrária |

## Como abrir

Abra `DDS.qpf` no Quartus Prime. A entidade de topo é `DDS`.

## Logo

Os arquivos do logo ficam em [`docs/logo/`](docs/logo/), em SVG (vetorial) e PNG (2×):

| Versão | SVG | PNG |
|---|---|---|
| Fundo claro | [`logo-light.svg`](docs/logo/logo-light.svg) | [`logo-light.png`](docs/logo/logo-light.png) |
| Fundo escuro | [`logo-dark.svg`](docs/logo/logo-dark.svg) | [`logo-dark.png`](docs/logo/logo-dark.png) |
| Ícone | [`icon.svg`](docs/logo/icon.svg) | [`icon.png`](docs/logo/icon.png) |

O símbolo representa o próprio DDS: a roda de fase (acumulador) projeta seu ponto numa
senoide em degraus — a saída quantizada da LUT.

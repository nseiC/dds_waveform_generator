"""Gera as figuras do texto do TCC em overleaf/figuras/.

Desenha as figuras de fundamentação e de sistema (diagrama de blocos do DDS, roda de fase,
espectros, sistema completo, hierarquia do VHDL, LUTs e filtro) em PDF vetorial, no mesmo
estilo das figuras dos testbenches, e copia para lá as figuras dos testbenches e as fotos
da bancada.

Uso (precisa de numpy e matplotlib):  python3 docs/gerar_figuras_tcc.py
As figuras dos testbenches saem de fpga/testbenches/gerar_figuras.py; rode-o antes se mudarem.
"""

from __future__ import annotations

import gzip
import math
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import patches, ticker  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "overleaf" / "figuras"
SPICE = ROOT / "analog" / "simulation" / "resultados"  # exportações do LTspice (.txt.gz)

INK = "#12233A"
ACCENT = "#E8711A"
TEAL = "#12807A"
GRAY = "#8A96A6"
GRID = "#D5DDE5"
LIGHT = "#F3F6F9"
LARGURA = 6.3  # 16 cm

# figuras dos testbenches usadas no texto
TESTBENCHES = [
    "tb_frequency_translator", "tb_phase_accumulator", "tb_LUT_tabelas", "tb_LUT_latencia",
    "tb_dds_core_formas", "tb_dds_core_latencia", "tb_vjtag_dr", "tb_cmd_sync", "tb_jtag_control",
    "tb_system_visao_geral", "tb_system_detalhes", "tb_DDS_pll", "tb_DDS_saida",
    # blocos menores (Apêndice B)
    "tb_word_adder", "tb_phase_register", "tb_truncator", "tb_out_mux", "tb_output_register",
    "tb_reset_sync", "tb_control_registers",
]
# visões RTL do Quartus (prints em fpga/testbenches/rtl), uma por entidade
RTL = ["DDS", "dds_core", "phase_accumulator", "frequency_translator", "word_adder", "phase_register",
       "truncator", "LUT", "out_mux", "output_register", "reset_sync", "cmd_sync", "control_registers_1",
       "control_registers_2", "jtag_control", "vjtag_dr"]
# fotos da bancada (analog/figuras) -> nome no TCC
FOTOS = {"PCB.jpeg": "placa.jpeg", "Setup.jpeg": "bancada.jpeg", "Output .jpeg": "medicao.jpeg",
         "PCB_esquematico.png": "pcb_esquematico.png", "PCB_layout.png": "pcb_layout.png", "PCB_3D.png": "pcb_3d.png",
         "LTspice_esquematico.png": "ltspice_esquematico.png"}


def estilo() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.linewidth": 0.7,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "pdf.fonttype": 42,
    })


def num(v: float, _pos=None) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}"
    return f"{v:.6g}".replace(".", ",")


def virgula(ax, eixos: str = "xy") -> None:
    if "x" in eixos:
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(num))
    if "y" in eixos:
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(num))


def salvar(fig, nome: str) -> None:
    fig.savefig(OUT / f"{nome}.pdf", bbox_inches="tight", metadata={"CreationDate": None})
    plt.close(fig)
    print(f"  figuras/{nome}.pdf")


def caixa(ax, x, y, w, h, texto, cor=INK, fundo="white", fs=8.5, lw=1.0, estilo="round,pad=0.02,rounding_size=0.06"):
    ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle=estilo, facecolor=fundo, edgecolor=cor, lw=lw))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, color=INK, linespacing=1.25)


def seta(ax, x0, y0, x1, y1, texto=None, cor=INK, lw=1.0, dy=0.06, fs=7.5, ha="center"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops={"arrowstyle": "-|>", "color": cor, "lw": lw, "shrinkA": 0, "shrinkB": 0,
                            "mutation_scale": 9})
    if texto:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, texto, ha=ha, va="bottom", fontsize=fs, color=INK)


def eixo_vazio(fig_w, fig_h, xlim, ylim):
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


# ---------------------------------------------------------------------------
# fundamentação
# ---------------------------------------------------------------------------

def fig_dds_blocos():
    """Arquitetura clássica do DDS, com o sinal em cada ponto."""
    fig, ax = eixo_vazio(LARGURA, 2.55, (0, 16), (-0.2, 6.2))
    w, h, y = 2.3, 1.5, 3.4
    xs = [1.1, 3.95, 6.8, 9.65, 12.5]
    nomes = ["Acumulador\nde fase\n($N$ bits)", "Truncamento\n($P$ bits)", "LUT\n(fase →\namplitude)",
             "DAC\n($D$ bits)", "Filtro\npassa-baixas"]
    for x, n in zip(xs, nomes):
        caixa(ax, x, y, w, h, n, fs=8)
    seta(ax, 0.1, y + h / 2, xs[0], y + h / 2, "$M$", dy=0.08)
    rot = ["$N$", "$P$", "$D$", ""]
    for i in range(4):
        seta(ax, xs[i] + w, y + h / 2, xs[i + 1], y + h / 2, rot[i], dy=0.08)
    seta(ax, xs[4] + w, y + h / 2, 15.95, y + h / 2, "$s(t)$", dy=0.08)
    # clock
    ax.text(xs[0] + w / 2, y + h + 0.55, "$f_{clk}$", ha="center", va="bottom", fontsize=8)
    seta(ax, xs[0] + w / 2, y + h + 0.55, xs[0] + w / 2, y + h)
    # miniaturas do sinal em cada ponto
    k = np.arange(48)
    m = 2 ** 32 // 13
    fase = (k * m) % 2 ** 32
    end = fase >> 28                                   # P = 4 bits, para ser visível
    amostra = np.round(127 * np.sin(2 * np.pi * end / 16))
    t = np.linspace(0, 48, 600)
    suave = 127 * np.sin(2 * np.pi * (t * m / 2 ** 32) - np.pi / 16)
    mini = [(k, fase / 2 ** 32, "o"), (k, end / 16, "s"), (k, amostra / 127, "o"),
            (np.repeat(k, 2)[1:], np.repeat(amostra / 127, 2)[:-1], "-"), (t, suave / 127, "-")]
    for x, (xx, yy, tipo) in zip(xs, mini):
        a = fig.add_axes([0, 0, 0, 0])
        bb = ax.transData.transform([(x, 0.25), (x + w, 2.95)])
        inv = fig.transFigure.inverted().transform(bb)
        a.set_position([inv[0][0], inv[0][1], inv[1][0] - inv[0][0], inv[1][1] - inv[0][1]])
        if tipo == "o":
            a.plot(xx, yy, ".", color=ACCENT, ms=2.2)
        elif tipo == "s":
            a.step(xx, yy, where="post", color=ACCENT, lw=0.8)
        else:
            a.plot(xx, yy, color=ACCENT, lw=0.9)
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_color(GRID)
    legs = ["fase", "endereço", "amostras", "degraus", "sinal"]
    for x, l in zip(xs, legs):
        ax.text(x + w / 2, -0.15, l, ha="center", va="top", fontsize=7.5, color=GRAY)
    salvar(fig, "dds_blocos")


def fig_roda_fase():
    """Roda de fase de 8 bits com LUT de 16 posições, M = 40, e as amostras resultantes."""
    n_bits, p_bits, m = 8, 4, 40
    full, bins = 2 ** n_bits, 2 ** p_bits
    fig = plt.figure(figsize=(LARGURA, 2.7))
    a = fig.add_axes([0.0, 0.03, 0.36, 0.94])
    b = fig.add_axes([0.45, 0.2, 0.54, 0.72])
    a.set_aspect("equal")
    a.axis("off")
    r = 1.0
    a.add_patch(patches.Circle((0, 0), r, fill=False, color=GRAY, lw=0.8))
    for i in range(bins):
        ang = np.pi / 2 - 2 * np.pi * i / bins
        a.plot(r * np.cos(ang), r * np.sin(ang), ".", color=INK, ms=3)
        a.text(1.17 * r * np.cos(ang), 1.17 * r * np.sin(ang), str(i), ha="center", va="center", fontsize=6.5,
               color=GRAY)
    ph = [(k * m) % full for k in range(7)]
    for k, p in enumerate(ph):
        ang = np.pi / 2 - 2 * np.pi * p / full
        a.annotate("", xy=(0.86 * np.cos(ang), 0.86 * np.sin(ang)), xytext=(0, 0),
                   arrowprops={"arrowstyle": "-|>", "color": ACCENT if k else INK, "lw": 0.9,
                               "alpha": 0.35 + 0.65 * k / 6, "mutation_scale": 7})
        a.text(0.66 * np.cos(ang), 0.66 * np.sin(ang), f"{k}", fontsize=6.5, ha="center", va="center",
               color=INK, bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4})
    a.set_xlim(-1.35, 1.35)
    a.set_ylim(-1.35, 1.35)
    a.text(0, -1.33, f"$N={n_bits}$, $P={p_bits}$, $M={m}$", ha="center", va="top", fontsize=8)
    kk = np.arange(20)
    fase = (kk * m) % full
    end = fase >> (n_bits - p_bits)
    amostra = np.sin(2 * np.pi * end / bins)
    t = np.linspace(0, 19, 500)
    b.plot(t, np.sin(2 * np.pi * t * m / full), color=GRAY, lw=0.8, ls="--", label="seno ideal")
    b.step(kk, amostra, where="post", color=INK, lw=0.9, label="saída da LUT (retida)")
    b.plot(kk, amostra, "o", color=ACCENT, ms=3, label="amostras")
    b.set_xlabel("clock $k$")
    b.set_ylabel("amplitude")
    b.set_xlim(0, 19)
    b.set_ylim(-1.25, 1.25)
    b.grid(color=GRID, lw=0.4)
    b.legend(loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=3, frameon=False, fontsize=7.5)
    virgula(b)
    salvar(fig, "roda_fase")


def fig_espectros():
    """(a) espectro das amostras de um DDS de 32/10/8 bits; (b) imagens na saída do DAC (ZOH) e filtro."""
    f_clk, n_acc, p_bits, d_bits = 10e6, 32, 10, 8
    f_out = 1_234_567
    m = int(f_out * 2 ** n_acc // f_clk)
    n = 2 ** 16
    k = np.arange(n, dtype=np.int64)
    fase = (k * m) % 2 ** n_acc
    end = fase >> (n_acc - p_bits)
    lut = np.round(128 + 127 * np.sin(2 * np.pi * np.arange(2 ** p_bits) / 2 ** p_bits))
    x = lut[end] - 128
    win = np.blackman(n)
    spec = np.abs(np.fft.rfft(x * win))
    spec_db = 20 * np.log10(spec / spec.max() + 1e-12)
    f = np.fft.rfftfreq(n, 1 / f_clk)
    carrier = np.argmax(spec)
    mask = np.ones_like(spec, dtype=bool)
    mask[max(carrier - 12, 0):carrier + 13] = False
    mask[:8] = False
    sfdr = -spec_db[mask].max()

    fig, (a, b) = plt.subplots(2, 1, figsize=(LARGURA, 5.0), gridspec_kw={"hspace": 0.55})
    a.plot(f / 1e6, spec_db, color=INK, lw=0.5)
    a.axhline(-6.02 * p_bits, color=ACCENT, ls="--", lw=0.8)
    a.text(4.98, -6.02 * p_bits + 1.5, f"−6,02$P$ = −{num(round(6.02 * p_bits, 1))} dBc", color=ACCENT,
           ha="right", va="bottom", fontsize=7.5)
    a.axhline(-sfdr, color=TEAL, ls=":", lw=0.9)
    a.text(0.05, -sfdr + 1.5, f"maior espúrio: −{num(round(sfdr, 1))} dBc", color=TEAL, ha="left",
           va="bottom", fontsize=7.5)
    a.set_xlim(0, 5)
    a.set_ylim(-120, 5)
    a.set_xlabel("frequência (MHz)")
    a.set_ylabel("dBc")
    a.set_title(f"(a) amostras do DDS: $f_{{out}}$ = {f_out / 1e6:.3f} MHz, $N = 32$, $P = 10$, $D = 8$".replace(".", ","),
                fontsize=8.5, loc="left")
    a.grid(color=GRID, lw=0.4)
    virgula(a)

    # (b) DAC com retenção de ordem zero: imagens em k f_clk ± f_out com envoltória sinc
    fo = 1e6
    ff = np.linspace(1, 3.2 * f_clk, 4000)
    env = 20 * np.log10(np.abs(np.sinc(ff / f_clk)) + 1e-9)
    f0, q = 1 / (2 * math.pi * 48 * 3.3e-9), 0.5
    hfil = 20 * np.log10(np.abs(1 / ((1j * ff / f0) ** 2 + 1j * ff / (f0 * q) + 1)))
    b.plot(ff / 1e6, env, color=GRAY, ls="--", lw=0.8, label=r"envoltória $|\mathrm{sinc}(f/f_{clk})|$")
    b.plot(ff / 1e6, hfil, color=TEAL, lw=0.9, label="filtro de reconstrução")
    linhas = [fo] + [kk * f_clk + s * fo for kk in (1, 2, 3) for s in (-1, 1) if kk * f_clk + s * fo < 3.2 * f_clk]
    for fl in linhas:
        g = 20 * np.log10(abs(np.sinc(fl / f_clk)))
        gf = g + 20 * np.log10(abs(1 / ((1j * fl / f0) ** 2 + 1j * fl / (f0 * q) + 1)))
        b.vlines(fl / 1e6, -100, g, color=INK, lw=1.1)
        b.plot(fl / 1e6, g, "o", color=INK, ms=2.5)
        b.plot(fl / 1e6, gf, "v", color=ACCENT, ms=3.5)
    b.plot([], [], "o", color=INK, ms=2.5, label="saída do DAC")
    b.plot([], [], "v", color=ACCENT, ms=3.5, label="após o filtro")
    b.set_xlim(0, 32)
    b.set_ylim(-100, 5)
    b.set_xlabel("frequência (MHz)")
    b.set_ylabel("dB")
    b.set_title("(b) saída do DAC para $f_{out}$ = 1 MHz e $f_{clk}$ = 10 MHz: imagens e filtro", fontsize=8.5,
                loc="left")
    b.grid(color=GRID, lw=0.4)
    b.legend(loc="lower left", frameon=False, ncol=2, fontsize=7)
    virgula(b)
    salvar(fig, "espectros")
    return sfdr


# ---------------------------------------------------------------------------
# sistema
# ---------------------------------------------------------------------------

def fig_sistema():
    fig, ax = eixo_vazio(LARGURA, 3.3, (0, 16), (0, 8.4))
    grupos = [(0.1, 4.2, 3.3, 4.0, "PC"), (4.1, 0.4, 5.6, 7.8, "FPGA (DE2-115)"),
              (10.4, 0.4, 5.5, 7.8, "Placa analógica")]
    for x, y, w, h, t in grupos:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                            facecolor=LIGHT, edgecolor=GRID, lw=0.8))
        ax.text(x + 0.15, y + h - 0.12, t, ha="left", va="top", fontsize=8.5, fontweight="bold")
    caixa(ax, 0.4, 6.0, 2.9, 1.0, "interface gráfica\n(Python)", fs=8)
    caixa(ax, 0.4, 4.85, 2.9, 0.8, "quartus_stp", fs=8)
    seta(ax, 1.85, 6.0, 1.85, 5.65)
    ax.text(1.85, 4.75, "USB-Blaster", ha="center", va="top", fontsize=7, color=GRAY)
    caixa(ax, 4.4, 5.9, 2.75, 1.2, "Virtual JTAG\n(jtag_interface)", fs=7.5)
    caixa(ax, 4.4, 4.2, 2.75, 1.1, "PLL\n50 → 10 MHz", fs=7.5)
    caixa(ax, 4.4, 2.5, 2.75, 1.1, "reset_sync", fs=7.5)
    caixa(ax, 7.6, 2.5, 2.1, 4.6, "dds_core\n\nacumulador\nde fase\n\nLUT\n\nregistrador\nde saída", fs=7.5)
    seta(ax, 3.3, 5.25, 4.4, 6.5)
    seta(ax, 7.15, 6.5, 7.6, 6.5)
    seta(ax, 7.15, 4.75, 7.6, 4.75)
    seta(ax, 7.15, 3.05, 7.6, 3.05)
    ax.text(5.78, 1.35, "CLOCK_50, KEY[0]", fontsize=7, ha="center", color=GRAY)
    seta(ax, 5.78, 1.65, 5.78, 2.5)
    caixa(ax, 10.8, 5.6, 2.2, 1.5, "DAC0800", fs=7.5)
    caixa(ax, 13.45, 5.6, 2.2, 1.5, "conversor\ncorrente-\ntensão", fs=7.5)
    caixa(ax, 13.45, 3.2, 2.2, 1.5, "filtro de\nreconstrução", fs=7.5)
    caixa(ax, 10.8, 3.2, 2.2, 1.5, "ganho\najustável", fs=7.5)
    caixa(ax, 10.8, 0.9, 2.2, 1.5, "buffer\n(seguidor)", fs=7.5)
    seta(ax, 9.7, 6.35, 10.8, 6.35, "8 bits", dy=0.1, fs=7)
    seta(ax, 13.0, 6.35, 13.45, 6.35)
    seta(ax, 14.55, 5.6, 14.55, 4.7)
    seta(ax, 13.45, 3.95, 13.0, 3.95)
    seta(ax, 11.9, 3.2, 11.9, 2.4)
    seta(ax, 13.0, 1.65, 15.85, 1.65, "saída", dy=0.1, fs=7.5)
    salvar(fig, "sistema")


def fig_hierarquia():
    nos = [
        (0, "DDS", "top-level: pinos da DE2-115"),
        (1, "PLL", "50 MHz → 10 MHz (IP)"),
        (1, "reset_sync", "reset liberado em sincronia"),
        (1, "jtag_interface", "controle pelo PC"),
        (2, "jtag", "Virtual JTAG (IP)"),
        (2, "jtag_control", "lógica do controle"),
        (3, "vjtag_dr", "registrador DR (domínio do tck)"),
        (3, "cmd_sync", "travessia tck → 10 MHz"),
        (3, "control_registers", "frequência, forma, escrita na LUT"),
        (1, "dds_core", "núcleo do DDS (10 MHz)"),
        (2, "phase_accumulator", "acumulador de fase"),
        (3, "frequency_translator", "Hz → FTW"),
        (3, "word_adder", "FTW + fase"),
        (3, "phase_register", "registrador de 32 bits"),
        (3, "truncator", "fase(31..22)"),
        (2, "LUT", "fase → amplitude"),
        (3, "sine/saw/sinc_LUT", "ROMs 1024 × 8 (IP)"),
        (3, "arbitrary_LUT", "RAM de duas portas (IP)"),
        (3, "out_mux", "seleção da forma"),
        (2, "output_register", "amostra para o DAC"),
    ]
    dy, dx, h = 0.5, 1.25, 0.36
    n = len(nos)
    fig, ax = plt.subplots(figsize=(LARGURA, n * dy * 0.4 + 0.2))
    ax.set_xlim(0, 15)
    ax.set_ylim(-n * dy, 0.4)
    ax.axis("off")
    ultimo = {}
    for i, (d, nome, desc) in enumerate(nos):
        y = -i * dy
        x = d * dx
        w = 0.21 * len(nome) + 0.4
        ip = "(IP)" in desc
        ax.add_patch(patches.FancyBboxPatch((x, y - h / 2), w, h, boxstyle="round,pad=0.01,rounding_size=0.06",
                                            facecolor=LIGHT if ip else "white", edgecolor=INK, lw=0.8))
        ax.text(x + w / 2, y, nome, ha="center", va="center", fontsize=7, family="DejaVu Sans Mono")
        ax.text(x + w + 0.2, y, desc, ha="left", va="center", fontsize=7.5, color=GRAY)
        if d > 0:
            px, py = ultimo[d - 1]
            ax.plot([px + 0.25, px + 0.25, x], [py - h / 2, y, y], color=GRAY, lw=0.7)
        ultimo[d] = (x, y)
    salvar(fig, "hierarquia")


# ---------------------------------------------------------------------------
# tabelas e filtro
# ---------------------------------------------------------------------------

def read_mif(name: str) -> np.ndarray:
    text = (ROOT / "fpga" / "lut" / name).read_text(encoding="utf-8")
    return np.array([int(v) for v in re.findall(r"^\s*\d+\s*:\s*(\d+)\s*;", text, re.M)])


def fig_luts():
    tabs = [("(a) seno", "sine_1024x8.mif"), ("(b) rampa (triângulo)", "triangle_1024x8.mif"),
            ("(c) sinc", "sinc_1024x8.mif"), ("(d) ECG sintético", "ecg_1024x8.mif")]
    fig, axs = plt.subplots(2, 2, figsize=(LARGURA, 3.9), sharex=True, sharey=True,
                            gridspec_kw={"hspace": 0.4, "wspace": 0.08})
    for ax, (t, n) in zip(axs.flat, tabs):
        ax.plot(read_mif(n), color=ACCENT, lw=1.1)
        ax.set_title(t, fontsize=8.5, loc="left")
        ax.set_xlim(0, 1023)
        ax.set_ylim(-8, 263)
        ax.set_xticks([0, 256, 512, 768, 1023])
        ax.set_yticks([0, 64, 128, 192, 255])
        ax.grid(color=GRID, lw=0.4)
    for ax in axs[1]:
        ax.set_xlabel("endereço")
    for ax in axs[:, 0]:
        ax.set_ylabel("código")
    salvar(fig, "luts")


def fig_filtro():
    r, c = 48.0, 3.3e-9
    f0 = 1 / (2 * math.pi * r * c)
    f = np.logspace(3, 8, 600)
    s = 1j * f / f0
    db = 20 * np.log10(np.abs(1 / (s ** 2 + 2 * s + 1)))
    f3 = f0 * math.sqrt(math.sqrt(2) - 1)
    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    ax.semilogx(f, db, color=ACCENT, lw=1.4)
    for x, txt, cor in [(f3, f"$-3$ dB: {num(round(f3 / 1e3))} kHz", GRAY), (262143, "262 kHz", INK),
                        (10e6, "$f_{clk}$ = 10 MHz", TEAL)]:
        ax.axvline(x, color=cor, ls="--", lw=0.8)
        ax.text(x * 1.07, -66, txt, color=cor, fontsize=7.5, rotation=90, va="bottom")
    ax.set_xlim(1e3, 1e8)
    ax.set_ylim(-70, 5)
    ax.set_xlabel("frequência (Hz)")
    ax.set_ylabel("ganho (dB)")
    ax.grid(color=GRID, lw=0.4, which="both")
    salvar(fig, "filtro")


# ---------------------------------------------------------------------------
# simulação da placa analógica (LTspice)
# ---------------------------------------------------------------------------

def ler_spice():
    with gzip.open(SPICE / "WAVEFORMS.txt.gz", "rt") as fh:
        onda = np.loadtxt(fh, skiprows=1)
    f, dif, fil = [], [], []
    with gzip.open(SPICE / "WAVEFORMS_FFT.txt.gz", "rt", encoding="latin-1") as fh:
        next(fh)
        for linha in fh:
            v = re.findall(r"\(([-+0-9.e]+)dB", linha)
            if len(v) == 2:
                f.append(float(linha.split()[0]))
                dif.append(float(v[0]))
                fil.append(float(v[1]))
    return onda, np.array(f), np.array(dif), np.array(fil)


def fig_spice(onda, f, dif, fil):
    t, buf, vdif, vfil, vinv = onda[:, 0], onda[:, 1], onda[:, 2], onda[:, 3], onda[:, 4]
    fig, (a, b) = plt.subplots(2, 1, figsize=(LARGURA, 4.6), gridspec_kw={"hspace": 0.55})
    a.plot(t * 1e3, vdif, color=GRAY, lw=1.0, label="conversor corrente-tensão")
    a.plot(t * 1e3, buf, color=ACCENT, lw=1.2, label="saída (após ganho, filtro e buffer)")
    a.set_xlim(0, 5)
    a.set_ylim(-4.2, 3)
    a.set_xlabel("tempo (ms)")
    a.set_ylabel("tensão (V)")
    a.set_title("(a) seno de 1 kHz: cinco períodos", fontsize=8.5, loc="left")
    a.legend(loc="lower center", frameon=False, ncol=2)
    a.grid(color=GRID, lw=0.4)
    virgula(a)
    # zoom em uma subida da saída: degraus antes do filtro e sinal suavizado depois
    z = np.where((buf[:-1] < 0) & (buf[1:] >= 0))[0][0]
    t0 = t[z] - 6e-6
    m = (t >= t0) & (t <= t0 + 12e-6)
    b.plot((t[m] - t0) * 1e6, vinv[m] * 1e3, color=INK, lw=1.0, drawstyle="steps-post", label="antes do filtro")
    b.plot((t[m] - t0) * 1e6, vfil[m] * 1e3, color=ACCENT, lw=1.3, label="depois do filtro")
    b.set_xlim(0, 12)
    b.set_xlabel("tempo (µs)")
    b.set_ylabel("tensão (mV)")
    b.set_title("(b) detalhe de uma subida: degraus de um código e o sinal filtrado", fontsize=8.5, loc="left")
    b.legend(loc="upper left", frameon=False)
    b.grid(color=GRID, lw=0.4)
    virgula(b)
    salvar(fig, "spice_tempo")

    k1 = int(np.argmax(fil[1:200])) + 1
    fig, ax = plt.subplots(figsize=(LARGURA, 3.0))
    ax.semilogx(f[1:], dif[1:] - dif[k1], color=GRAY, lw=0.5, label="conversor corrente-tensão", rasterized=True)
    ax.semilogx(f[1:], fil[1:] - fil[k1], color=ACCENT, lw=0.5, label="saída do filtro", rasterized=True)
    for x, y, txt in [(6e3, -62, "harmônicas"), (1.024e6, -52, "1024$f$ ± $f$")]:
        ax.annotate(txt, xy=(x, y), ha="center", fontsize=7.5, color=INK)
    ax.set_xlim(200, f[-1])
    ax.set_ylim(-160, 10)
    ax.set_xlabel("frequência (Hz)")
    ax.set_ylabel("dBc")
    ax.grid(color=GRID, lw=0.4, which="major")
    ax.legend(loc="lower left", frameon=False)
    salvar(fig, "spice_fft")


def main() -> None:
    estilo()
    OUT.mkdir(exist_ok=True)
    print("Desenhando:")
    fig_dds_blocos()
    fig_roda_fase()
    sfdr = fig_espectros()
    fig_sistema()
    fig_hierarquia()
    fig_luts()
    fig_filtro()
    fig_spice(*ler_spice())
    print(f"  (SFDR da simulação numérica: {sfdr:.1f} dBc)")
    print("Copiando:")
    tb = ROOT / "fpga" / "testbenches" / "figuras"
    for nome in TESTBENCHES:
        shutil.copyfile(tb / f"{nome}.pdf", OUT / f"{nome}.pdf")
        print(f"  figuras/{nome}.pdf")
    for nome in RTL:
        shutil.copyfile(ROOT / "fpga" / "testbenches" / "rtl" / f"rtl_{nome}.png", OUT / f"rtl_{nome}.png")
        print(f"  figuras/rtl_{nome}.png")
    for orig, dest in FOTOS.items():
        shutil.copyfile(ROOT / "analog" / "figuras" / orig, OUT / dest)
        print(f"  figuras/{dest}")


if __name__ == "__main__":
    main()

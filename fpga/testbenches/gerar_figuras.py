"""Gera as figuras dos testbenches da parte digital, para o texto do TCC.

Roda os testbenches no GHDL gravando um VCD só com os sinais listados em SINAIS, lê os VCD e
desenha uma ou mais figuras por circuito em fpga/testbenches/figuras/, em PNG (300 dpi) e
PDF (vetorial, para o LaTeX). As figuras não têm título: a legenda fica no texto.

Uso (precisa de numpy e matplotlib; GHDL e Quartus como no run_all.sh):
    python3 fpga/testbenches/gerar_figuras.py                 # todos os testbenches
    python3 fpga/testbenches/gerar_figuras.py tb_dds_core     # só alguns
    python3 fpga/testbenches/gerar_figuras.py --sem-simular   # redesenha com os VCD que já existem
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import ticker  # noqa: E402

TB_DIR = Path(__file__).resolve().parent
FPGA = TB_DIR.parent
WORK = TB_DIR / "work"
OUT = TB_DIR / "figuras"

# cores do projeto (docs/logo)
INK = "#12233A"
ACCENT = "#E8711A"
TEAL = "#12807A"
GRAY = "#8A96A6"
LIGHT = "#F3F6F9"

LARGURA = 6.3  # polegadas: 16 cm, a largura útil de uma página A4 com margens da ABNT

FS = {"ns": 1e6, "µs": 1e9, "ms": 1e12}  # femtossegundos por unidade

# sinais gravados de cada testbench (nomes em minúsculas, como o GHDL grava)
SINAIS = {
    "tb_frequency_translator": ["frequency", "ftw"],
    "tb_word_adder": ["a", "b", "s"],
    "tb_phase_register": ["clk", "rst", "word", "q"],
    "tb_truncator": ["phase", "addr"],
    "tb_phase_accumulator": ["frequency", "addr"],
    "tb_out_mux": ["sel", "q_sine", "q_saw", "q_sinc", "q_arb", "qout"],
    "tb_lut": ["clk", "addr", "sel", "q", "lut_we", "lut_waddr", "lut_wdata"],
    "tb_output_register": ["clk", "rst", "d", "q"],
    "tb_dds_core": ["clk", "rst", "frequency", "sel", "lut_we", "sample", "dut/addr"],
    "tb_reset_sync": ["clk", "rst_in", "rst_out", "dut/chain"],
    "tb_vjtag_dr": ["tck", "tdi", "tdo", "ir_in", "vs_cdr", "vs_sdr", "vs_udr", "cmd_ir", "cmd_data",
                    "cmd_toggle", "dut/dr"],
    "tb_cmd_sync": ["src_clk", "src_toggle", "src_data", "clk", "rst", "dst_valid", "dst_data", "dut/sync"],
    "tb_control_registers": ["clk", "rst", "cmd_valid", "cmd_ir", "cmd_data", "frequency", "sel", "lut_we",
                             "lut_waddr", "lut_wdata", "activity"],
    "tb_jtag_control": ["tck", "tdi", "vs_cdr", "vs_sdr", "vs_udr", "clk", "frequency", "lut_we",
                        "dut/tck_toggle", "dut/sync/sync", "dut/cmd_valid"],
    "tb_system": ["sample", "frequency", "sel", "activity", "core/addr"],
    "tb_dds": ["clk_50", "rst_n", "dac", "dac_gnd", "led_locked", "led_cmd", "dut/clk10", "dut/rst"],
}

# nome do testbench no run_all.sh (o GHDL grava em minúsculas)
NOME_TB = {"tb_lut": "tb_LUT", "tb_dds": "tb_DDS"}


# ---------------------------------------------------------------------------
# VCD
# ---------------------------------------------------------------------------

class Wave:
    """Valores de um sinal: tempos de mudança (fs) e valores (texto, como no VCD)."""

    def __init__(self, times: list[int], values: list[str]):
        self.t = np.array(times, dtype=np.int64)
        self.v = values

    def at(self, t_fs: float) -> str:
        i = int(np.searchsorted(self.t, t_fs, side="right")) - 1
        return self.v[i] if i >= 0 else "x"

    def int_at(self, t_fs: float) -> int | None:
        return to_int(self.at(t_fs))

    def ints(self) -> np.ndarray:
        return np.array([(-1 if (x := to_int(v)) is None else x) for v in self.v], dtype=np.int64)

    def segments(self, t0: float, t1: float) -> list[tuple[float, float, str]]:
        """Trechos (início, fim, valor) dentro de [t0, t1]."""
        i0 = max(int(np.searchsorted(self.t, t0, side="right")) - 1, 0)
        i1 = int(np.searchsorted(self.t, t1, side="left"))
        out = []
        for i in range(i0, max(i1, i0 + 1)):
            a = max(float(self.t[i]), t0)
            b = min(float(self.t[i + 1]), t1) if i + 1 < len(self.t) else t1
            if b > a:
                out.append((a, b, self.v[i]))
        return out

    def rises(self) -> np.ndarray:
        """Tempos das bordas de subida (para sinais de 1 bit)."""
        return np.array([t for t, v in zip(self.t, self.v) if v == "1"], dtype=np.int64)

    def changes(self) -> list[tuple[int, str]]:
        return list(zip(self.t.tolist(), self.v))


def to_int(v: str) -> int | None:
    return int(v, 2) if v and set(v) <= {"0", "1"} else None


def read_vcd(path: Path) -> dict[str, Wave]:
    ids: dict[str, list[str]] = {}
    scope: list[str] = []
    data: dict[str, tuple[list[int], list[str]]] = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if tok[0] == "$scope":
                scope.append(tok[2])
            elif tok[0] == "$upscope":
                scope.pop()
            elif tok[0] == "$var":
                name = "/".join(scope[1:] + [tok[4].split("[")[0]])  # sem o nome do testbench
                ids.setdefault(tok[3], []).append(name.lower())
            elif tok[0] == "$enddefinitions":
                break
        data = {i: ([], []) for i in ids}
        t = 0
        for line in f:
            c = line[:1]
            if c == "#":
                t = int(line[1:])
            elif c == "b":
                val, ident = line[1:].split()
                if ident in data:
                    data[ident][0].append(t)
                    data[ident][1].append(val)
            elif c and c in "01xzXZuU-":
                ident = line[1:].strip()
                if ident in data:
                    data[ident][0].append(t)
                    data[ident][1].append(c.lower())
    waves = {}
    for ident, names in ids.items():
        w = Wave(*data[ident])
        for n in names:
            waves[n] = w
    return waves


# ---------------------------------------------------------------------------
# desenho
# ---------------------------------------------------------------------------

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
        "lines.linewidth": 1.0,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })


def milhar(v: int) -> str:
    """Inteiro com espaço separando os milhares (262 143)."""
    return f"{int(v):,}".replace(",", " ")


def num(v: float, _pos=None) -> str:
    """Número com vírgula decimal."""
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}"
    return f"{v:.6g}".replace(".", ",")


def virgula(ax, eixos: str = "xy") -> None:
    if "x" in eixos:
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(num))
    if "y" in eixos:
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(num))


def fmt_valor(v: str, fmt: str) -> str:
    x = to_int(v)
    if x is None:
        return "X" if "x" in v or "u" in v else v.upper()
    if fmt == "hex":
        return f"{x:X}"
    if fmt == "bin":
        return v
    return str(x)


def timing(ax, t0: float, t1: float, rows: list, unit: str = "ns", marks: list | None = None,
           clocks: np.ndarray | None = None) -> None:
    """Diagrama de tempo. rows: (rótulo, Wave, 'bit' | 'hex' | 'dec' | 'bin')."""
    s = FS[unit]
    n = len(rows)
    h, gap = 1.0, 0.55
    span = (t1 - t0) / s
    slope = span * 0.006
    fig = ax.figure
    ax_in = ax.get_position().width * fig.get_figwidth()
    centers = []
    for i, (label, w, kind) in enumerate(rows):
        y = (n - 1 - i) * (h + gap)
        centers.append(y + h / 2)
        segs = [(a / s, b / s, v) for a, b, v in w.segments(t0, t1)]
        if kind == "bit":
            xs, ys = [], []
            for a, b, v in segs:
                lvl = {"1": y + h * 0.9, "0": y + h * 0.1}.get(v)
                if lvl is None:
                    ax.add_patch(plt.Rectangle((a, y + 0.1 * h), b - a, 0.8 * h, facecolor=LIGHT,
                                               edgecolor=GRAY, hatch="////", lw=0.5))
                    xs += [np.nan]
                    ys += [np.nan]
                else:
                    xs += [a, b]
                    ys += [lvl, lvl]
            ax.plot(xs, ys, color=INK, lw=1.0, solid_joinstyle="miter")
        else:
            for a, b, v in segs:
                sl = min(slope, (b - a) / 2)
                top, bot, mid = y + 0.9 * h, y + 0.1 * h, y + 0.5 * h
                poly = [(a, mid), (a + sl, top), (b - sl, top), (b, mid), (b - sl, bot), (a + sl, bot)]
                unknown = to_int(v) is None
                ax.add_patch(plt.Polygon(poly, closed=True, facecolor=LIGHT if unknown else "white",
                                         edgecolor=INK, lw=0.8))
                txt = fmt_valor(v, kind)
                width_in = (b - a - 2 * sl) / span * ax_in
                if len(txt) * 6.5 * 0.55 / 72 < width_in:
                    ax.text((a + b) / 2, mid, txt, ha="center", va="center", fontsize=6.5,
                            family="DejaVu Sans Mono")
    if clocks is not None:
        for c in clocks:
            if t0 <= c <= t1:
                ax.axvline(c / s, color=GRAY, lw=0.4, ls=":", zorder=0)
    for t, txt in marks or []:
        ax.axvline(t / s, color=ACCENT, lw=0.8, ls="--", zorder=0)
        if txt:
            ax.text(t / s, n * (h + gap) - gap * 0.2, txt, color=ACCENT, fontsize=7, ha="center", va="bottom",
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
    ax.set_yticks(centers)
    ax.set_yticklabels([r[0] for r in rows])
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(t0 / s, t1 / s)
    ax.set_ylim(-gap, n * (h + gap) + (0.55 if marks else 0))
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel(f"tempo ({unit})")
    virgula(ax, "x")


def stairs(ax, w: Wave, t0: float, t1: float, unit: str, offset: float = 0.0, **kw) -> None:
    """Valor inteiro do sinal em degraus, com o tempo medido a partir de offset."""
    s = FS[unit]
    xs, ys = [], []
    for a, b, v in w.segments(t0, t1):
        x = to_int(v)
        xs += [(a - offset) / s, (b - offset) / s]
        ys += [np.nan if x is None else x] * 2
    kw.setdefault("color", ACCENT)
    kw.setdefault("lw", 1.0)
    ax.plot(xs, ys, **kw)


def eixo_codigo(ax) -> None:
    ax.set_ylim(-8, 263)
    ax.set_yticks([0, 64, 128, 192, 255])
    ax.set_ylabel("código")
    ax.grid(color="#D5DDE5", lw=0.4)


def salvar(fig, nome: str) -> None:
    OUT.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{nome}.{ext}", bbox_inches="tight", metadata={"CreationDate": None} if ext == "pdf" else {})
    plt.close(fig)
    print(f"  figuras/{nome}.png / .pdf")


def read_mif(name: str) -> np.ndarray:
    text = (FPGA / "lut" / name).read_text(encoding="utf-8")
    vals = re.findall(r"^\s*\d+\s*:\s*(\d+)\s*;", text, re.M)
    return np.array([int(v) for v in vals])


def mudancas(w: Wave) -> list[tuple[int, int | None]]:
    return [(t, to_int(v)) for t, v in w.changes()]


# ---------------------------------------------------------------------------
# figuras de cada testbench
# ---------------------------------------------------------------------------

def fig_frequency_translator(W):
    f, m = W["frequency"], W["ftw"]
    fv = f.ints()
    mv = np.array([m.int_at(t + 500_000) for t in f.t])  # 0,5 ns depois de cada entrada
    ok = fv >= 0
    fv, mv = fv[ok], mv[ok]
    err = fv * 2.0 ** 32 / 10e6 - mv
    fig, (a, b) = plt.subplots(2, 1, figsize=(LARGURA, 4.8))
    a.plot(fv / 1e3, mv / 1e6, color=ACCENT, lw=1.4)
    a.set_ylabel(r"FTW, $M$ ($\times 10^6$)")
    a.grid(color="#D5DDE5", lw=0.4)
    virgula(a)
    zoom = fv <= 2000
    b.plot(fv[zoom], err[zoom], ".", ms=1.6, color=INK)
    b.set_ylim(-0.05, 1.05)
    b.set_xlim(0, 2000)
    b.set_ylabel("erro de $M$ (LSB)")
    b.set_xlabel("frequência de entrada (Hz)")
    b.grid(color="#D5DDE5", lw=0.4)
    virgula(b)
    i = int(np.argmax(np.abs(err)))
    b.text(0.99, 0.5, f"maior erro em toda a faixa (0 a {milhar(fv.max())} Hz):\n"
           f"{num(round(float(err[i]), 5))} LSB em f = {milhar(fv[i])} Hz, ou "
           f"{num(round(float(err[i]) * 10e6 / 2 ** 32 * 1e3, 3))} mHz",
           transform=b.transAxes, ha="right", va="center", fontsize=7.5,
           bbox={"facecolor": "white", "edgecolor": "#D5DDE5", "pad": 3})
    c = b.twinx()
    c.set_ylim(np.array(b.get_ylim()) * 10e6 / 2 ** 32 * 1e3)
    c.set_ylabel("erro de frequência (mHz)")
    virgula(c, "y")
    a.set_xlim(0, fv.max() / 1e3)
    a.set_xlabel("frequência de entrada (kHz)")
    a.set_title("(a) palavra de sintonia para as 2$^{18}$ entradas", fontsize=8.5, loc="left")
    b.set_title("(b) erro de truncamento de $M$, de 0 a 2 kHz", fontsize=8.5, loc="left")
    fig.subplots_adjust(hspace=0.55)
    fig.align_ylabels()
    salvar(fig, "tb_frequency_translator")


def fig_word_adder(W):
    fig, ax = plt.subplots(figsize=(LARGURA, 1.6))
    timing(ax, 0, 5e6, [("ftw", W["a"], "hex"), ("feedback", W["b"], "hex"), ("wOut", W["s"], "hex")], "ns")
    salvar(fig, "tb_word_adder")


def fig_phase_register(W):
    clk, rst = W["clk"], W["rst"]
    t_rst = rst.changes()[-1][0]  # último reset (assíncrono, no fim)
    fig, (a, b) = plt.subplots(2, 1, figsize=(LARGURA, 4.0), gridspec_kw={"hspace": 0.7})
    rows = [("clk", clk, "bit"), ("rst", rst, "bit"), ("word", W["word"], "hex"), ("wOut", W["q"], "hex")]
    timing(a, 0, 900e6, rows, "ns", clocks=clk.rises())
    timing(b, t_rst - 450e6, t_rst + 250e6, rows, "ns", marks=[(t_rst, "reset assíncrono")], clocks=clk.rises())
    salvar(fig, "tb_phase_register")


def fig_truncator(W):
    fig, ax = plt.subplots(figsize=(LARGURA, 1.2))
    timing(ax, 0, 5e6, [("wIn", W["phase"], "hex"), ("bOut", W["addr"], "dec")], "ns")
    salvar(fig, "tb_truncator")


def fig_phase_accumulator(W):
    addr, freq = W["addr"], W["frequency"]
    ch = [(t, v) for t, v in mudancas(freq) if t > 0]
    t_end = float(addr.t[-1])
    fig, axs = plt.subplots(3, 1, figsize=(LARGURA, 6.0), gridspec_kw={"hspace": 0.55})
    stairs(axs[0], addr, 0, ch[0][0], "ms")
    axs[0].set_xlim(0, ch[0][0] / FS["ms"])
    axs[0].set_xlabel("tempo (ms)")
    titulos = ["(a) 1 kHz desde o reset: uma volta da fase por milissegundo",
               "(b) trocas para 100 000 Hz e 262 143 Hz com o acumulador rodando",
               "(c) trocas para 1 Hz, 0 Hz e 123 457 Hz"]
    for ax, titulo in zip(axs, titulos):
        ax.set_title(titulo, fontsize=8.5, loc="left")
    for ax, (i0, i1) in zip(axs[1:], [(0, 1), (2, 4)]):
        t0 = ch[i0][0] - 30e9
        t1 = ch[i1 + 1][0] + 40e9 if i1 + 1 < len(ch) else t_end
        t1 = min(t1, ch[i1][0] + 150e9)
        stairs(ax, addr, t0, t1, "µs", offset=t0)
        for t, v in ch:
            if t0 < t < t1:
                ax.axvline((t - t0) / FS["µs"], color=INK, ls="--", lw=0.7)
                ax.text((t - t0) / FS["µs"] + 0.6, 1100, f"{milhar(v)} Hz", fontsize=7,
                        ha="left", va="top", rotation=90,
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})
        ax.set_xlim(0, (t1 - t0) / FS["µs"])
        ax.set_xlabel("tempo (µs)")
    for ax in axs:
        ax.set_ylim(-20, 1300)
        ax.set_yticks([0, 256, 512, 768, 1023])
        ax.set_ylabel("endereço")
        ax.grid(color="#D5DDE5", lw=0.4)
        virgula(ax, "x")
    salvar(fig, "tb_phase_accumulator")


def fig_out_mux(W):
    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    rows = [("sel", W["sel"], "bin"), ("q_sine", W["q_sine"], "hex"), ("q_saw", W["q_saw"], "hex"),
            ("q_sinc", W["q_sinc"], "hex"), ("q_arb", W["q_arb"], "hex"), ("qout", W["qout"], "hex")]
    timing(ax, 0, 10e6, rows, "ns")
    salvar(fig, "tb_out_mux")


def fig_lut(W):
    clk, addr, q = W["clk"], W["addr"], W["q"]
    edges = clk.rises()
    first = int(np.searchsorted(edges, 100e6, side="right"))  # o teste começa depois da descida de 100 ns
    n = 1025
    titulos = ["(a) seno (ROM)", "(b) rampa (ROM)", "(c) sinc (ROM)", "(d) arbitrária: ECG inicial (RAM)",
               "(e) seno com escrita simultânea na RAM", "(f) arbitrária depois da escrita (RAM)"]
    pattern = np.array([round(128 + 120 * math.sin(2 * math.pi * 3 * a / 1024)) for a in range(1024)])
    tabelas = [read_mif("sine_1024x8.mif"), read_mif("triangle_1024x8.mif"), read_mif("sinc_1024x8.mif"),
               read_mif("ecg_1024x8.mif"), read_mif("sine_1024x8.mif"), pattern]
    fig, axs = plt.subplots(3, 2, figsize=(LARGURA, 6.2), sharex=True, sharey=True,
                            gridspec_kw={"hspace": 0.45, "wspace": 0.08})
    for s, ax in enumerate(axs.flat):
        pts = []
        for k in range(1, n):
            e = first + s * n + k
            pts.append((addr.int_at(edges[e - 1] - 1), q.int_at(edges[e] + 5e5)))
        pts.sort()
        xa = np.array([p[0] for p in pts])
        ya = np.array([p[1] for p in pts])
        ax.plot(np.arange(1024), tabelas[s], color=GRAY, lw=2.2, alpha=0.5, label="esperado (.mif)")
        ax.plot(xa, ya, ".", ms=1.2, color=ACCENT, label="lido na simulação")
        ax.set_title(titulos[s], fontsize=8.5, loc="left")
        eixo_codigo(ax)
        ax.set_xlim(0, 1023)
        ax.set_xticks([0, 256, 512, 768, 1023])
    for ax in axs[-1]:
        ax.set_xlabel("endereço")
    for ax in axs[:, 1]:
        ax.set_ylabel("")
    axs[0, 0].legend(loc="lower left", frameon=False, markerscale=6)
    salvar(fig, "tb_LUT_tabelas")

    fig, ax = plt.subplots(figsize=(LARGURA, 1.9))
    t0 = edges[first] - 60e6
    timing(ax, t0, t0 + 700e6, [("clk", clk, "bit"), ("sel", W["sel"], "bin"), ("addr", addr, "dec"),
                                ("qOut", q, "dec")], "ns", clocks=edges)
    salvar(fig, "tb_LUT_latencia")


def fig_output_register(W):
    clk = W["clk"]
    fig, ax = plt.subplots(figsize=(LARGURA, 1.9))
    timing(ax, 0, 800e6, [("clk", clk, "bit"), ("rst", W["rst"], "bit"), ("d", W["d"], "hex"),
                          ("q", W["q"], "hex")], "ns", clocks=clk.rises())
    salvar(fig, "tb_output_register")


def fig_dds_core(W):
    clk, rst, sel, freq, sample, addr = W["clk"], W["rst"], W["sel"], W["frequency"], W["sample"], W["dut/addr"]
    t_rst = [t for t, v in rst.changes() if v == "0"][0]
    fch = [t for t, _ in freq.changes() if t > t_rst]
    sch = [t for t, _ in sel.changes() if t > 0]
    janelas = [
        ("(a) seno, 100 kHz", t_rst, t_rst + 30e9),
        ("(b) troca de 100 kHz para 262 kHz, sem salto de fase", fch[0] - 12e9, fch[0] + 18e9),
        ("(c) rampa, 7 919 Hz", sch[0], sch[0] + 200e9),
        ("(d) sinc, 7 919 Hz", sch[1], sch[1] + 200e9),
        ("(e) arbitrária, ECG inicial, 100 kHz", sch[2], sch[2] + 20e9),
        ("(f) dente de serra escrito na RAM, 100 kHz", sch[4], sch[4] + 20e9),
    ]
    fig, axs = plt.subplots(3, 2, figsize=(LARGURA, 6.4), sharey=True, gridspec_kw={"hspace": 0.6, "wspace": 0.08})
    for ax, (titulo, t0, t1) in zip(axs.flat, janelas):
        stairs(ax, sample, t0, t1, "µs", offset=t0)
        ax.set_xlim(0, (t1 - t0) / FS["µs"])
        ax.set_title(titulo, fontsize=8.5, loc="left")
        eixo_codigo(ax)
        ax.set_xlabel("tempo (µs)")
        virgula(ax, "x")
    axs[0, 1].axvline((fch[0] - (fch[0] - 12e9)) / FS["µs"], color=INK, ls="--", lw=0.7)
    for ax in axs[:, 1]:
        ax.set_ylabel("")
    salvar(fig, "tb_dds_core_formas")

    fig, ax = plt.subplots(figsize=(LARGURA, 2.4))
    timing(ax, t_rst - 250e6, t_rst + 850e6,
           [("clk", clk, "bit"), ("rst", rst, "bit"), ("frequency", freq, "dec"), ("endereço", addr, "dec"),
            ("sample", sample, "dec")], "ns", clocks=clk.rises(), marks=[(t_rst, "fim do reset")])
    salvar(fig, "tb_dds_core_latencia")


def fig_reset_sync(W):
    clk = W["clk"]
    fig, ax = plt.subplots(figsize=(LARGURA, 1.9))
    rin = W["rst_in"]
    t_fall = [t for t, v in rin.changes() if v == "0"][0]
    t_rise = [t for t, v in rin.changes() if v == "1" and t > t_fall][0]
    timing(ax, t_fall - 200e6, t_rise + 250e6,
           [("clk", clk, "bit"), ("rst_in", rin, "bit"), ("chain", W["dut/chain"], "bin"),
            ("rst_out", W["rst_out"], "bit")], "ns", clocks=clk.rises(),
           marks=[(t_fall, "rst_in cai"), (t_rise, "rst_in sobe")])
    salvar(fig, "tb_reset_sync")


def fig_vjtag_dr(W):
    cdr, udr = W["vs_cdr"], W["vs_udr"]
    t0 = cdr.rises()[0] - 400e6
    t1 = [t for t, v in udr.changes() if v == "0" and t > t0][1] + 300e6
    rows = [("tck", W["tck"], "bit"), ("ir_in", W["ir_in"], "bin"), ("vs_cdr", cdr, "bit"),
            ("vs_sdr", W["vs_sdr"], "bit"), ("vs_udr", udr, "bit"), ("tdi", W["tdi"], "bit"),
            ("tdo", W["tdo"], "bit"), ("dr", W["dut/dr"], "hex"), ("cmd_data", W["cmd_data"], "hex"),
            ("cmd_toggle", W["cmd_toggle"], "bit")]
    fig, ax = plt.subplots(figsize=(LARGURA, 3.8))
    timing(ax, t0, t1, rows, "µs")
    salvar(fig, "tb_vjtag_dr")


def fig_cmd_sync(W):
    tog = W["src_toggle"]
    t = [t for t, _ in tog.changes() if t > 0][0]
    rows = [("src_clk (tck)", W["src_clk"], "bit"), ("src_toggle", tog, "bit"), ("src_data", W["src_data"], "hex"),
            ("clk (10 MHz)", W["clk"], "bit"), ("sync", W["dut/sync"], "bin"), ("dst_valid", W["dst_valid"], "bit"),
            ("dst_data", W["dst_data"], "hex")]
    fig, ax = plt.subplots(figsize=(LARGURA, 2.8))
    timing(ax, t - 250e6, t + 650e6, rows, "ns", clocks=W["clk"].rises(), marks=[(t, "comando na origem")])
    salvar(fig, "tb_cmd_sync")


def fig_control_registers(W):
    rst = W["rst"]
    t_rst = [t for t, v in rst.changes() if v == "0"][0]
    rows = [("clk", W["clk"], "bit"), ("cmd_valid", W["cmd_valid"], "bit"), ("cmd_ir", W["cmd_ir"], "bin"),
            ("cmd_data", W["cmd_data"], "hex"), ("frequency", W["frequency"], "dec"), ("sel", W["sel"], "bin"),
            ("lut_we", W["lut_we"], "bit"), ("lut_waddr", W["lut_waddr"], "dec"),
            ("lut_wdata", W["lut_wdata"], "hex"), ("activity", W["activity"], "bit")]
    fig, ax = plt.subplots(figsize=(LARGURA, 3.6))
    timing(ax, t_rst - 100e6, t_rst + 1500e6, rows, "ns", clocks=W["clk"].rises())
    salvar(fig, "tb_control_registers")


def fig_jtag_control(W):
    cdr = W["vs_cdr"]
    t0 = cdr.rises()[0] - 300e6
    valid = W["dut/cmd_valid"]
    t_valid = valid.rises()[0]
    rows = [("tck", W["tck"], "bit"), ("vs_sdr", W["vs_sdr"], "bit"), ("vs_udr", W["vs_udr"], "bit"),
            ("tdi", W["tdi"], "bit"), ("tck_toggle", W["dut/tck_toggle"], "bit"), ("clk (10 MHz)", W["clk"], "bit"),
            ("sync", W["dut/sync/sync"], "bin"), ("cmd_valid", valid, "bit"), ("frequency", W["frequency"], "dec")]
    fig, ax = plt.subplots(figsize=(LARGURA, 3.4))
    timing(ax, t0, t_valid + 700e6, rows, "µs")
    salvar(fig, "tb_jtag_control")


def fig_system(W):
    sample, freq, sel, act, addr = W["sample"], W["frequency"], W["sel"], W["activity"], W["core/addr"]
    t_end = float(max(sample.t[-1], freq.t[-1]))
    fch = [(t, v) for t, v in mudancas(freq) if t > 0]
    sch = [(t, v) for t, v in mudancas(sel) if t > 0]
    acts = act.t[act.t > 0]

    fig, (a, b, c) = plt.subplots(3, 1, figsize=(LARGURA, 4.6), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.2, 1.0], "hspace": 0.15})
    stairs(a, sample, 0, t_end, "ms", rasterized=True, lw=0.6)
    eixo_codigo(a)
    a.set_ylabel("amostra do DAC")
    b.step([0] + [t / FS["ms"] for t, _ in fch] + [t_end / FS["ms"]],
           [1] + [v / 1e3 for _, v in fch] + [fch[-1][1] / 1e3], where="post", color=INK)
    b.set_ylabel("f (kHz)")
    b.set_ylim(-10, 115)
    b.grid(color="#D5DDE5", lw=0.4)
    nomes = {0: "seno", 1: "rampa", 2: "sinc", 3: "arbitrária"}
    cores = {0: "#FCE3CF", 1: "#FFF4D6", 2: "#D9EDEA", 3: "#DCE3EE"}
    pts = [(0.0, 0)]
    for t, v in sch:
        if v != pts[-1][1]:
            pts.append((t / FS["ms"], v))
    for (x0, v), (x1, _) in zip(pts, pts[1:] + [(t_end / FS["ms"], 0)]):
        c.axvspan(x0, x1, 0.35, 1.0, color=cores[v], label=nomes[v])
    c.vlines(acts / FS["ms"], 0, 0.3, color=ACCENT, lw=0.3)
    lut0, lut1 = acts[len(acts) // 2] / FS["ms"], acts[-3] / FS["ms"]
    c.text((lut0 + lut1) / 2, 0.15, "1024 comandos de escrita na LUT", ha="center", va="center", fontsize=7,
           bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})
    c.set_yticks([0.15, 0.68])
    c.set_yticklabels(["JTAG", "forma"])
    c.tick_params(axis="y", length=0)
    c.set_ylim(0, 1)
    c.set_xlim(0, t_end / FS["ms"])
    c.set_xlabel("tempo (ms)")
    handles, labels = c.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    c.legend(uniq.values(), uniq.keys(), loc="upper center", bbox_to_anchor=(0.5, -0.75), ncol=4, frameon=False)
    virgula(c, "x")
    fig.align_ylabels()
    salvar(fig, "tb_system_visao_geral")

    # zoom no comando que muda a frequência e no da forma enviada pela LUT
    upl = np.array([round(128 + 90 * math.sin(2 * math.pi * a / 1024) + 30 * math.sin(6 * math.pi * a / 1024))
                    for a in range(1024)])
    t_f = [t for t, v in fch if v == 100_000][0]
    t_last = t_end - 40e9
    fig, (a, b) = plt.subplots(2, 1, figsize=(LARGURA, 4.2), gridspec_kw={"hspace": 0.55})
    t0 = t_f - 30e9
    stairs(a, sample, t0, t_f + 40e9, "µs", offset=t0)
    a.axvline((t_f - t0) / FS["µs"], color=INK, ls="--", lw=0.7)
    a.text((t_f - t0) / FS["µs"] + 0.8, 250, "comando IR 01: f = 100 000 Hz", fontsize=7.5, va="top",
           bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
    a.set_xlim(0, 70)
    a.set_title("(a) mudança de frequência pelo JTAG, de 1 kHz para 100 kHz", fontsize=8.5, loc="left")
    xs, ys = [], []
    for t0_, t1_, v in addr.segments(t_last - 300e6, t_end):
        x = to_int(v)
        xs += [(t0_ + 300e6 - t_last) / FS["µs"], (t1_ + 300e6 - t_last) / FS["µs"]]
        ys += [upl[x]] * 2 if x is not None else [np.nan] * 2
    b.plot(xs, ys, color=GRAY, lw=2.4, alpha=0.6, label="LUT enviada (esperado)")
    stairs(b, sample, t_last, t_end, "µs", offset=t_last, label="saída do DAC")
    b.set_xlim(0, 40)
    b.set_title("(b) forma arbitrária enviada pelo JTAG (1024 escritas), a 50 kHz", fontsize=8.5, loc="left")
    b.legend(loc="lower right", frameon=False)
    for ax in (a, b):
        eixo_codigo(ax)
        ax.set_xlabel("tempo (µs)")
        virgula(ax, "x")
    salvar(fig, "tb_system_detalhes")


def fig_dds(W):
    clk50, clk10, locked, rst_n, rst, dac = (W["clk_50"], W["dut/clk10"], W["led_locked"], W["rst_n"], W["dut/rst"],
                                             W["dac"])
    t_lock = locked.rises()[0]
    rows = [("clk_50", clk50, "bit"), ("clk10", clk10, "bit"), ("led_locked", locked, "bit"),
            ("rst (interno)", rst, "bit"), ("dac", dac, "hex")]
    fig, ax = plt.subplots(figsize=(LARGURA, 2.4))
    timing(ax, t_lock - 150e6, t_lock + 650e6, rows, "ns", marks=[(t_lock, "PLL travado")])
    salvar(fig, "tb_DDS_pll")

    t_up = [t for t, v in rst_n.changes() if v == "1"][0]
    t_down = [t for t, v in rst_n.changes() if v == "0" and t > t_up][0]
    t_end = t_down + 60e9
    fig, ax = plt.subplots(figsize=(LARGURA, 2.4))
    stairs(ax, dac, 0, t_end, "ms", lw=0.9)
    eixo_codigo(ax)
    ax.set_ylabel("código no DAC")
    for t, txt, ha in [(t_up, "KEY[0] solto", "left"), (t_down, "KEY[0] apertado", "right")]:
        ax.axvline(t / FS["ms"], color=INK, ls="--", lw=0.7)
        ax.text(t / FS["ms"], 258, f" {txt} ", fontsize=7.5, ha=ha, va="top")
    ax.set_xlim(0, t_end / FS["ms"])
    ax.set_xlabel("tempo (ms)")
    virgula(ax, "x")
    salvar(fig, "tb_DDS_saida")


FIGURAS = {
    "tb_frequency_translator": fig_frequency_translator,
    "tb_word_adder": fig_word_adder,
    "tb_phase_register": fig_phase_register,
    "tb_truncator": fig_truncator,
    "tb_phase_accumulator": fig_phase_accumulator,
    "tb_out_mux": fig_out_mux,
    "tb_lut": fig_lut,
    "tb_output_register": fig_output_register,
    "tb_dds_core": fig_dds_core,
    "tb_reset_sync": fig_reset_sync,
    "tb_vjtag_dr": fig_vjtag_dr,
    "tb_cmd_sync": fig_cmd_sync,
    "tb_control_registers": fig_control_registers,
    "tb_jtag_control": fig_jtag_control,
    "tb_system": fig_system,
    "tb_dds": fig_dds,
}


def main(args: list[str]) -> int:
    simular = "--sem-simular" not in args
    pedidos = [a.lower() for a in args if not a.startswith("--")] or list(SINAIS)
    desconhecidos = [p for p in pedidos if p not in SINAIS]
    if desconhecidos:
        print("testbench desconhecido:", ", ".join(desconhecidos))
        return 1
    if simular:
        WORK.mkdir(exist_ok=True)
        for tb in pedidos:
            linhas = ["$ version 1.1"] + [f"/{tb}/{s}" for s in SINAIS[tb]]
            (WORK / f"{NOME_TB.get(tb, tb)}.opt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
        cmd = [str(TB_DIR / "run_all.sh")] + [NOME_TB.get(tb, tb) for tb in pedidos]
        if subprocess.run(cmd, env={**os.environ, "VCD": "1"}).returncode != 0:
            print("Algum testbench falhou; as figuras não foram geradas.")
            return 1
    estilo()
    print("Desenhando:")
    for tb in pedidos:
        vcd = WORK / f"{NOME_TB.get(tb, tb)}.vcd"
        if not vcd.exists():
            print(f"  {vcd.name} não existe; rode sem --sem-simular")
            return 1
        FIGURAS[tb](read_vcd(vcd))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

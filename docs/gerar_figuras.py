"""Gera as figuras da documentação.

    docs/jogo/preview.svg          animação da roda de fase (README principal)
    docs/img/luts-{light,dark}.svg formas de onda das LUTs (fpga/README.md)
    docs/img/filtro-{light,dark}.svg resposta do filtro de reconstrução (analog/README.md)

Uso (precisa de numpy e matplotlib):  python docs/gerar_figuras.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Cores do logo (docs/logo)
THEMES = {
    "light": {"bg": "#EEF2F5", "text": "#12233A", "muted": "#5B6B80", "grid": "#D5DDE5", "accent": "#E8711A",
              "line2": "#12807A"},
    "dark": {"bg": "#0B1626", "text": "#E6EDF5", "muted": "#8FA1B6", "grid": "#22344D", "accent": "#FF9A3D",
             "line2": "#4FD1C5"},
}
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "'Space Grotesk', 'Segoe UI', Helvetica, Arial, sans-serif"


# ---------------------------------------------------------------------------
# Animação da roda de fase
# ---------------------------------------------------------------------------

def preview_svg() -> str:
    """Acumulador de 8 bits, LUT de 16 posições, M = 16, fase inicial 8 (meio do setor)."""
    t = THEMES["dark"]
    n_bits, p_bits, m, ph0 = 8, 4, 16, 8
    full, bins = 1 << n_bits, 1 << p_bits
    clocks, hold = 32, 6
    slots = clocks + hold
    clk_s = 0.32
    dur = f"{slots * clk_s:.2f}s"
    lut = [round(128 + 127 * math.sin(2 * math.pi * k / bins)) for k in range(bins)]
    phases = [(ph0 + m * k) % full for k in range(clocks)]
    codes = [lut[p >> (n_bits - p_bits)] for p in phases]

    W, H = 880, 356
    cx, cy, R = 160, 186, 84
    x0, x1, yt, yb = 372, 852, 96, 280
    ym = (yt + yb) / 2
    dx = (x1 - x0) / clocks

    def yv(code: float) -> float:
        return ym - (code - 128) / 127 * (yb - yt) / 2 * 0.92

    def key_times(n: int) -> str:
        return ";".join(f"{i / n:.4f}" for i in range(n))

    def anim(attr: str, values: list[str], kind: str = "animate") -> str:
        extra = ' type="rotate"' if kind == "animateTransform" else ""
        return (f'<{kind} attributeName="{attr}"{extra} dur="{dur}" repeatCount="indefinite" calcMode="discrete" '
                f'keyTimes="{key_times(len(values))}" values="{";".join(values)}"/>')

    def per_slot(seq: list) -> list:
        return seq + [seq[-1]] * hold

    def show_only(k: int) -> str:
        """visibility: visível só no slot k (o último clock fica visível durante a pausa)."""
        start = k / slots
        end = (k + 1) / slots if k < clocks - 1 else 1.0
        if k == 0:
            vals, kts = ["visible", "hidden"], [0, end]
        elif end >= 1.0:
            vals, kts = ["hidden", "visible"], [0, start]
        else:
            vals, kts = ["hidden", "visible", "hidden"], [0, start, end]
        return (f'<animate attributeName="visibility" dur="{dur}" repeatCount="indefinite" calcMode="discrete" '
                f'keyTimes="{";".join(f"{v:.4f}" for v in kts)}" values="{";".join(vals)}"/>')

    out: list[str] = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
      f'role="img" aria-label="Animação do DDS: a roda de fase avança M = 16 a cada clock e a LUT desenha um seno em degraus">')
    a(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{t["bg"]}" stroke="{t["grid"]}"/>')

    # cabeçalho
    a(f'<text x="28" y="44" font-family="{SANS}" font-size="21" font-weight="700" fill="{t["text"]}">Roda de fase</text>')
    a(f'<text x="28" y="66" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
      f'acumulador de {n_bits} bits · LUT de {bins} posições · M = {m}</text>')
    a(f'<text x="{x1}" y="44" text-anchor="end" font-family="{MONO}" font-size="14" fill="{t["text"]}">'
      f'f<tspan font-size="10" dy="3">out</tspan><tspan dy="-3"> = </tspan>'
      f'<tspan fill="{t["accent"]}">M</tspan> · f<tspan font-size="10" dy="3">clk</tspan>'
      f'<tspan dy="-3"> / 2</tspan><tspan font-size="10" dy="-6">N</tspan></text>')
    a(f'<text x="{x1}" y="66" text-anchor="end" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
      f'{full // m} clocks por volta · uma amostra por clock</text>')

    # roda
    bin_deg = 360 / bins
    a0 = math.radians(-90)
    a1 = math.radians(-90 + bin_deg)
    wedge = (f"M{cx},{cy} L{cx + R * math.cos(a0):.2f},{cy + R * math.sin(a0):.2f} "
             f"A{R},{R} 0 0 1 {cx + R * math.cos(a1):.2f},{cy + R * math.sin(a1):.2f} Z")
    rot_wedge = [f"{(ph >> (n_bits - p_bits)) * bin_deg:.2f} {cx} {cy}" for ph in phases]
    a(f'<path d="{wedge}" fill="{t["accent"]}" fill-opacity="0.18">'
      f'{anim("transform", per_slot(rot_wedge), "animateTransform")}</path>')
    a(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{t["grid"]}" stroke-width="1.5"/>')
    for k in range(bins):
        ang = math.radians(-90 + k * bin_deg)
        a(f'<circle cx="{cx + R * math.cos(ang):.2f}" cy="{cy + R * math.sin(ang):.2f}" r="2.5" fill="{t["muted"]}"/>')
        a(f'<text x="{cx + (R + 15) * math.cos(ang):.2f}" y="{cy + (R + 15) * math.sin(ang) + 3.5:.2f}" '
          f'text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{t["muted"]}">{k}</text>')
    rot_ptr = [f"{ph / full * 360:.2f} {cx} {cy}" for ph in phases]
    a(f'<g>{anim("transform", per_slot(rot_ptr), "animateTransform")}'
      f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - R + 10}" stroke="{t["accent"]}" stroke-width="4" '
      f'stroke-linecap="round"/><circle cx="{cx}" cy="{cy - R + 10}" r="3" fill="{t["text"]}"/></g>')
    a(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{t["accent"]}"/>')

    # LUT entre a roda e o gráfico
    bx, by, bw, bh = 294, ym - 17, 50, 34
    a(f'<line x1="{cx + R + 28}" y1="{ym}" x2="{bx - 4}" y2="{ym}" stroke="{t["muted"]}" stroke-width="1.5"/>')
    a(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="7" fill="none" stroke="{t["muted"]}" stroke-width="1.5"/>')
    a(f'<text x="{bx + bw / 2}" y="{ym + 4.5}" text-anchor="middle" font-family="{MONO}" font-size="13" '
      f'fill="{t["text"]}">LUT</text>')
    a(f'<path d="M{bx + bw + 4},{ym} H{x0 - 8} m-6,-5 l6,5 l-6,5" fill="none" stroke="{t["muted"]}" stroke-width="1.5"/>')

    # gráfico
    for v, dash in ((255, "4 4"), (128, ""), (1, "4 4")):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        a(f'<line x1="{x0}" y1="{yv(v):.2f}" x2="{x1}" y2="{yv(v):.2f}" stroke="{t["grid"]}"{da}/>')

    stairs = []
    for k, c in enumerate(codes):
        x = x0 + k * dx
        stairs.append(f"{'M' if k == 0 else 'L'}{x:.2f},{yv(c):.2f} L{x + dx:.2f},{yv(c):.2f}")

    # filtro de reconstrução: dois polos reais em 0,12·f_clk, em regime (aquecido por 4 voltas)
    os_ = 8
    alpha = 1 - math.exp(-2 * math.pi * 0.12 / os_)
    y1 = y2 = 128.0
    pts = []
    for rep in range(5):
        for k, c in enumerate(codes):
            for s in range(os_):
                y1 += alpha * (c - y1)
                y2 += alpha * (y1 - y2)
                if rep == 4:
                    pts.append(f"{x0 + (k + s / os_) * dx:.2f},{yv(y2):.2f}")
    reveal = [f"{(k + 1) * dx:.2f}" for k in range(clocks)]
    a(f'<clipPath id="rv"><rect x="{x0}" y="{yt - 10}" height="{yb - yt + 20}" width="0">'
      f'{anim("width", per_slot(reveal))}</rect></clipPath>')
    a(f'<g clip-path="url(#rv)">')
    a(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{t["line2"]}" stroke-width="2.2"/>')
    a(f'<path d="{" ".join(stairs)}" fill="none" stroke="{t["text"]}" stroke-width="1.8"/>')
    a("</g>")
    cxs = [f"{x0 + k * dx:.2f}" for k in range(clocks)]
    cys = [f"{yv(c):.2f}" for c in codes]
    a(f'<circle r="5.5" fill="{t["accent"]}" cx="{cxs[0]}" cy="{cys[0]}">'
      f'{anim("cx", per_slot(cxs))}{anim("cy", per_slot(cys))}</circle>')

    # legenda do gráfico
    ly = yb + 24
    a(f'<line x1="{x0}" y1="{ly - 4}" x2="{x0 + 18}" y2="{ly - 4}" stroke="{t["text"]}" stroke-width="2"/>')
    a(f'<text x="{x0 + 24}" y="{ly}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">saída do DAC</text>')
    a(f'<line x1="{x0 + 136}" y1="{ly - 4}" x2="{x0 + 154}" y2="{ly - 4}" stroke="{t["line2"]}" stroke-width="2.2"/>')
    a(f'<text x="{x0 + 160}" y="{ly}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">após o filtro</text>')

    # registrador de fase e leituras, um grupo por clock
    bw_, gap = 22, 4
    bx0 = cx - (8 * bw_ + 7 * gap) / 2
    by0 = 306
    a(f'<text x="{bx0 - 10}" y="{by0 + 17}" text-anchor="end" font-family="{MONO}" font-size="11" '
      f'fill="{t["muted"]}">fase</text>')
    for i in range(8):
        hi = i < p_bits
        a(f'<rect x="{bx0 + i * (bw_ + gap):.1f}" y="{by0}" width="{bw_}" height="26" rx="5" '
          f'fill="{t["accent"] if hi else t["grid"]}" fill-opacity="{0.18 if hi else 0.35}" '
          f'stroke="{t["accent"] if hi else t["grid"]}"/>')
    for k, (ph, c) in enumerate(zip(phases, codes)):
        bits = f"{ph:08b}"
        g = [f'<g visibility="hidden">{show_only(k)}']
        for i, b in enumerate(bits):
            g.append(f'<text x="{bx0 + i * (bw_ + gap) + bw_ / 2:.1f}" y="{by0 + 18}" text-anchor="middle" '
                     f'font-family="{MONO}" font-size="13" font-weight="600" '
                     f'fill="{t["accent"] if i < p_bits else t["muted"]}">{b}</text>')
        g.append(f'<text x="{x1}" y="{by0 + 18}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{t["text"]}">'
                 f'clock {k:2d} · fase {ph:3d} · endereço {ph >> (n_bits - p_bits):2d} · '
                 f'<tspan fill="{t["accent"]}">código {c:3d}</tspan></text>')
        g.append("</g>")
        a("".join(g))
    a(f'<text x="{bx0 + 2 * (bw_ + gap) - gap / 2:.1f}" y="{by0 + 42}" text-anchor="middle" font-family="{MONO}" '
      f'font-size="10" fill="{t["accent"]}">endereço</text>')
    a(f'<text x="{bx0 + 6 * (bw_ + gap) - gap / 2:.1f}" y="{by0 + 42}" text-anchor="middle" font-family="{MONO}" '
      f'font-size="10" fill="{t["muted"]}">truncados</text>')
    a("</svg>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Gráficos (matplotlib)
# ---------------------------------------------------------------------------

def style(ax, t):
    ax.set_facecolor("none")
    for s in ax.spines.values():
        s.set_color(t["grid"])
    ax.tick_params(colors=t["muted"], labelsize=9)
    ax.grid(color=t["grid"], linewidth=0.6)
    ax.title.set_color(t["text"])
    ax.xaxis.label.set_color(t["muted"])
    ax.yaxis.label.set_color(t["muted"])


def read_mif(path: Path) -> np.ndarray:
    vals = re.findall(r"^\s*\d+\s*:\s*(\d+)\s*;", path.read_text(encoding="utf-8"), re.M)
    return np.array([int(v) for v in vals])


def luts_figure(theme: str) -> None:
    t = THEMES[theme]
    lut_dir = ROOT / "fpga" / "lut"
    tables = [("Seno (sine_LUT)", "sine_1024x8.mif"), ("Triângulo (saw_LUT)", "triangle_1024x8.mif"),
              ("Sinc (sinc_LUT)", "sinc_1024x8.mif"), ("ECG sintético (arbitrária)", "ecg_1024x8.mif")]
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.6), sharey=True)
    fig.patch.set_alpha(0)
    for ax, (title, name) in zip(axes, tables):
        v = read_mif(lut_dir / name)
        style(ax, t)
        ax.plot(np.arange(len(v)), v, color=t["accent"], linewidth=1.4)
        ax.set_title(title, fontsize=10.5, loc="left", color=t["text"])
        ax.set_xlim(0, 1023)
        ax.set_ylim(0, 255)
        ax.set_xticks([0, 512, 1023])
        ax.set_yticks([0, 128, 255])
        ax.set_xlabel("endereço", fontsize=9)
    axes[0].set_ylabel("código", fontsize=9)
    fig.tight_layout()
    fig.savefig(DOCS / "img" / f"luts-{theme}.svg", transparent=True, metadata={"Date": None})
    plt.close(fig)


def filter_figure(theme: str) -> None:
    """Sallen-Key passa-baixas de ganho 1 da simulação: R11 = R12 = 48 Ω, C3 = C4 = 3,3 nF."""
    t = THEMES[theme]
    r, c = 48.0, 3.3e-9
    f0 = 1 / (2 * math.pi * r * c)
    q = 0.5
    f = np.logspace(3, 8, 600)
    s = 1j * f / f0
    h = 1 / (s ** 2 + s / q + 1)
    db = 20 * np.log10(np.abs(h))
    f3 = f0 * math.sqrt(math.sqrt(2) - 1)

    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_alpha(0)
    style(ax, t)
    ax.semilogx(f, db, color=t["accent"], linewidth=2)
    ax.axvline(f3, color=t["muted"], linestyle="--", linewidth=1)
    ax.axvline(10e6, color=t["line2"], linestyle="--", linewidth=1)
    ax.text(f3 * 1.08, -55, f"−3 dB\n{f3 / 1e3:.0f} kHz", color=t["muted"], fontsize=9)
    h10 = 20 * math.log10(abs(1 / ((1j * 10e6 / f0) ** 2 + (1j * 10e6 / f0) / q + 1)))
    ax.text(10e6 * 1.08, -20, f"$f_{{clk}}$ = 10 MHz\n{h10:.0f} dB", color=t["line2"], fontsize=9)
    ax.set_xlim(1e3, 1e8)
    ax.set_ylim(-70, 5)
    ax.set_xlabel("frequência (Hz)", fontsize=9)
    ax.set_ylabel("ganho (dB)", fontsize=9)
    ax.set_title(f"Filtro de reconstrução: Sallen-Key de 2ª ordem, f₀ = {f0 / 1e6:.2f} MHz, Q = 0,5".replace(".", ","),
                 fontsize=10.5, loc="left", color=t["text"])
    fig.tight_layout()
    fig.savefig(DOCS / "img" / f"filtro-{theme}.svg", transparent=True, metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["svg.hashsalt"] = "dds"
    plt.rcParams["font.family"] = "sans-serif"
    (DOCS / "img").mkdir(exist_ok=True)
    (DOCS / "jogo" / "preview.svg").write_text(preview_svg(), encoding="utf-8")
    for theme in THEMES:
        luts_figure(theme)
        filter_figure(theme)
    print("Figuras geradas em docs/")


if __name__ == "__main__":
    main()

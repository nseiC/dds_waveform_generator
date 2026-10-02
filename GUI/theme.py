"""Identidade visual da interface: cores, fontes, estilos ttk e o símbolo do logo.

As cores são as mesmas do logo em ``docs/logo/``. As fontes da marca (Space Grotesk e
JetBrains Mono) são usadas se estiverem instaladas no sistema; senão, a interface cai
nas fontes padrão da plataforma.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont, ttk

PALETTES = {
    "escuro": {
        "bg": "#0B1626",          # fundo da janela (fundo do logo escuro)
        "panel": "#111E31",       # painéis
        "panel_head": "#15243A",  # faixa de título dos painéis
        "raised": "#1A2A41",      # campos e botões
        "hover": "#22354F",
        "pressed": "#2A3F5C",
        "border": "#2A3D57",
        "text": "#E6EDF5",
        "muted": "#9AA8BA",
        "dim": "#7D8CA3",
        "accent": "#FF9A3D",
        "accent_hover": "#FFAD62",
        "accent_pressed": "#E8862C",
        "on_accent": "#0B1626",
        "select": "#2A2216",      # item selecionado (laranja bem escuro)
        "header_bg": "#060E1A",
        "header_fg": "#E6EDF5",
        "header_muted": "#9AA8BA",
        "plot_bg": "#08111E",
        "grid": "#18273C",
        "axis": "#3A4D68",
        "trace": "#FF9A3D",
        "ok": "#7FD1AE",
        "err": "#FF8A80",
        "info": "#5AA9FF",
    },
    "claro": {
        "bg": "#E3E9EF",
        "panel": "#FFFFFF",
        "panel_head": "#F3F6F9",
        "raised": "#F6F8FA",
        "hover": "#E9EEF3",
        "pressed": "#DCE3EA",
        "border": "#C9D3DE",
        "text": "#12233A",
        "muted": "#4A5A70",
        "dim": "#5B6B80",
        "accent": "#E8711A",
        "accent_hover": "#F0832F",
        "accent_pressed": "#D2620F",
        "on_accent": "#12233A",
        "select": "#FBE3D0",
        "header_bg": "#12233A",   # faixa da marca continua escura
        "header_fg": "#EEF2F5",
        "header_muted": "#A9B6C6",
        "plot_bg": "#FFFFFF",
        "grid": "#E6EBF0",
        "axis": "#9AA8BA",
        "trace": "#E8711A",
        "ok": "#0E7A5F",
        "err": "#C0362C",
        "info": "#1F5FBF",
    },
}
DEFAULT_THEME = "escuro"
HEADER_ACCENT = "#FF9A3D"  # o símbolo no cabeçalho é sempre a versão de fundo escuro

UI_FONTS = ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Cantarell", "Noto Sans",
            "DejaVu Sans", "Liberation Sans")
DISPLAY_FONTS = ("Space Grotesk",)
MONO_FONTS = ("JetBrains Mono", "Cascadia Mono", "Consolas", "SF Mono", "Menlo",
              "DejaVu Sans Mono", "Liberation Mono", "Courier New")


def _pick(families: set[str], candidates, fallback: str) -> str:
    return next((c for c in candidates if c in families), fallback)


def make_fonts(root: tk.Misc) -> dict[str, tkfont.Font]:
    """Cria as fontes nomeadas da interface e ajusta as fontes padrão do Tk."""
    families = set(tkfont.families(root))
    default = tkfont.nametofont("TkDefaultFont", root)
    ui = _pick(families, UI_FONTS, default.actual("family"))
    mono = _pick(families, MONO_FONTS, tkfont.nametofont("TkFixedFont", root).actual("family"))
    display = _pick(families, DISPLAY_FONTS, ui)

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
        tkfont.nametofont(name, root).configure(family=ui, size=10)
    tkfont.nametofont("TkFixedFont", root).configure(family=mono, size=10)

    return {
        "ui": tkfont.Font(root, family=ui, size=10),
        "ui_bold": tkfont.Font(root, family=ui, size=10, weight="bold"),
        "caption": tkfont.Font(root, family=ui, size=8, weight="bold"),
        "brand": tkfont.Font(root, family=display, size=15, weight="bold"),
        "brand_sub": tkfont.Font(root, family=mono, size=9),
        "mono": tkfont.Font(root, family=mono, size=10),
        "mono_sm": tkfont.Font(root, family=mono, size=9),
        "mono_xs": tkfont.Font(root, family=mono, size=8),
        "mono_lg": tkfont.Font(root, family=mono, size=17),
    }


def apply_style(root: tk.Misc, name: str, fonts: dict[str, tkfont.Font]) -> dict[str, str]:
    """Aplica a paleta ``name`` aos estilos ttk e retorna o dicionário de cores."""
    p = PALETTES[name]
    s = ttk.Style(root)
    s.theme_use("clam")

    def flat(style, bg, **kw):
        s.configure(style, background=bg, lightcolor=bg, darkcolor=bg, **kw)

    s.configure(".", background=p["panel"], foreground=p["text"], fieldbackground=p["raised"],
                bordercolor=p["border"], lightcolor=p["panel"], darkcolor=p["panel"],
                troughcolor=p["raised"], selectbackground=p["accent"],
                selectforeground=p["on_accent"], insertcolor=p["text"],
                focuscolor=p["accent"], font=fonts["ui"])
    s.map(".", foreground=[("disabled", p["dim"])])

    # Molduras e textos
    s.configure("TFrame", background=p["panel"])
    s.configure("App.TFrame", background=p["bg"])
    s.configure("PanelHead.TFrame", background=p["panel_head"])
    s.configure("Header.TFrame", background=p["header_bg"])
    s.configure("Status.TFrame", background=p["header_bg"])
    s.configure("TLabel", background=p["panel"], foreground=p["text"])
    s.configure("Muted.TLabel", foreground=p["muted"])
    s.configure("Value.TLabel", font=fonts["mono"])
    s.configure("Unit.TLabel", foreground=p["muted"], font=fonts["mono"])
    s.configure("Hint.TLabel", foreground=p["muted"], font=fonts["mono_xs"])
    s.configure("Error.TLabel", foreground=p["err"], font=fonts["mono_xs"])
    s.configure("Caption.TLabel", foreground=p["muted"], font=fonts["caption"])
    s.configure("PanelTitle.TLabel", background=p["panel_head"], font=fonts["ui_bold"])
    s.configure("PanelInfo.TLabel", background=p["panel_head"], foreground=p["muted"],
                font=fonts["mono_sm"])
    s.configure("Header.TLabel", background=p["header_bg"], foreground=p["header_fg"],
                font=fonts["brand"])
    s.configure("HeaderSub.TLabel", background=p["header_bg"], foreground=p["header_muted"],
                font=fonts["brand_sub"])
    s.configure("Status.TLabel", background=p["header_bg"], foreground=p["header_muted"],
                font=fonts["mono_xs"])
    s.configure("StatusMsg.TLabel", background=p["header_bg"], foreground=p["header_fg"])
    s.configure("ConnOn.TLabel", background=p["header_bg"], foreground=PALETTES["escuro"]["ok"],
                font=fonts["caption"])
    s.configure("ConnOff.TLabel", background=p["header_bg"], foreground=p["header_muted"],
                font=fonts["caption"])
    s.configure("TSeparator", background=p["border"])

    # Botões
    flat("TButton", p["raised"], foreground=p["text"], bordercolor=p["border"],
         padding=(12, 5), relief="flat", focusthickness=1)
    s.map("TButton",
          background=[("disabled", p["panel"]), ("pressed", p["pressed"]), ("active", p["hover"])],
          lightcolor=[("disabled", p["panel"]), ("pressed", p["pressed"]), ("active", p["hover"])],
          darkcolor=[("disabled", p["panel"]), ("pressed", p["pressed"]), ("active", p["hover"])],
          bordercolor=[("focus", p["accent"])])
    flat("Accent.TButton", p["accent"], foreground=p["on_accent"], bordercolor=p["accent"],
         font=fonts["ui_bold"], padding=(14, 5))
    s.map("Accent.TButton",
          background=[("disabled", p["raised"]), ("pressed", p["accent_pressed"]),
                      ("active", p["accent_hover"])],
          lightcolor=[("disabled", p["raised"]), ("pressed", p["accent_pressed"]),
                      ("active", p["accent_hover"])],
          darkcolor=[("disabled", p["raised"]), ("pressed", p["accent_pressed"]),
                     ("active", p["accent_hover"])],
          foreground=[("disabled", p["dim"])],
          bordercolor=[("disabled", p["border"]), ("focus", p["text"])])
    flat("Small.TButton", p["panel_head"], foreground=p["muted"], bordercolor=p["panel_head"],
         padding=(8, 1), font=fonts["caption"])
    s.map("Small.TButton",
          background=[("pressed", p["pressed"]), ("active", p["hover"])],
          lightcolor=[("pressed", p["pressed"]), ("active", p["hover"])],
          darkcolor=[("pressed", p["pressed"]), ("active", p["hover"])],
          foreground=[("active", p["text"])])

    # Campos
    for style in ("TEntry", "TCombobox", "TSpinbox"):
        s.configure(style, fieldbackground=p["raised"], foreground=p["text"],
                    bordercolor=p["border"], lightcolor=p["raised"], darkcolor=p["raised"],
                    background=p["raised"], arrowcolor=p["muted"], insertcolor=p["text"],
                    selectbackground=p["accent"], selectforeground=p["on_accent"], padding=(6, 4))
        s.map(style,
              bordercolor=[("focus", p["accent"])],
              lightcolor=[("focus", p["accent"])],
              fieldbackground=[("readonly", p["raised"]), ("disabled", p["panel"])],
              foreground=[("disabled", p["dim"])],
              background=[("active", p["hover"]), ("pressed", p["pressed"])],
              arrowcolor=[("disabled", p["dim"]), ("active", p["text"])])
    s.map("TCombobox", selectbackground=[("readonly", p["raised"])],
          selectforeground=[("readonly", p["text"])])

    # Seleção da forma de onda
    s.configure("TRadiobutton", background=p["panel"], foreground=p["text"],
                indicatorbackground=p["raised"], indicatorforeground=p["accent"],
                upperbordercolor=p["border"], lowerbordercolor=p["border"], padding=(2, 4))
    s.map("TRadiobutton",
          background=[("active", p["panel"])],
          indicatorbackground=[("pressed", p["hover"]), ("selected", p["raised"])],
          upperbordercolor=[("selected", p["accent"]), ("focus", p["accent"])],
          lowerbordercolor=[("selected", p["accent"]), ("focus", p["accent"])])

    # Progresso, rolagem e divisórias
    s.configure("Horizontal.TProgressbar", troughcolor=p["raised"], background=p["accent"],
                bordercolor=p["header_bg"], lightcolor=p["accent"], darkcolor=p["accent"],
                thickness=6)
    s.configure("Vertical.TScrollbar", background=p["raised"], troughcolor=p["plot_bg"],
                bordercolor=p["plot_bg"], lightcolor=p["raised"], darkcolor=p["raised"],
                arrowcolor=p["muted"], gripcount=0)
    s.map("Vertical.TScrollbar", background=[("active", p["hover"])])
    s.configure("TPanedwindow", background=p["bg"])
    s.configure("Sash", sashthickness=6, gripcount=0, background=p["bg"],
                lightcolor=p["bg"], darkcolor=p["bg"], bordercolor=p["bg"])

    # Listas abertas pelos Combobox (criadas depois disto)
    root.option_add("*TCombobox*Listbox.background", p["raised"])
    root.option_add("*TCombobox*Listbox.foreground", p["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["on_accent"])
    root.option_add("*TCombobox*Listbox.font", fonts["ui"])
    return p


def style_popdown(combobox: ttk.Combobox, p: dict[str, str]) -> None:
    """Recolore a lista de um Combobox que já foi aberta (troca de tema em execução)."""
    try:
        popdown = combobox.tk.call("ttk::combobox::PopdownWindow", combobox)
        combobox.tk.call(f"{popdown}.f.l", "configure", "-background", p["raised"],
                         "-foreground", p["text"], "-selectbackground", p["accent"],
                         "-selectforeground", p["on_accent"])
    except tk.TclError:
        pass


def style_menu(menu: tk.Menu, p: dict[str, str]) -> None:
    menu.configure(background=p["panel"], foreground=p["text"], activebackground=p["hover"],
                   activeforeground=p["text"], selectcolor=p["accent"], borderwidth=0,
                   activeborderwidth=0, relief="flat")


# ------------------------------------------------------------------ símbolo

# Mesma geometria do logo (sistema de 120 × 120): roda de fase e senoide quantizada.
_STEPS = [(60.0, 44.4), (63.9, 44.4), (63.9, 39.2), (67.7, 39.2), (67.7, 38.1), (71.6, 38.1),
          (71.6, 41.4), (75.4, 41.4), (75.4, 48.3), (79.3, 48.3), (79.3, 57.5), (83.1, 57.5),
          (83.1, 67.3), (87.0, 67.3), (87.0, 75.6), (90.9, 75.6), (90.9, 80.8), (94.7, 80.8),
          (94.7, 81.9), (98.6, 81.9), (98.6, 78.6), (102.4, 78.6), (102.4, 71.7), (106.3, 71.7),
          (106.3, 62.5), (110.1, 62.5), (110.1, 52.7), (114.0, 52.7)]
MARK_VIEW = (4, 14, 116, 92)  # recorte usado no ícone: x, y, largura, altura


def draw_mark(canvas: tk.Canvas, height: float, ink: str, accent: str, x0=0.0, y0=0.0) -> float:
    """Desenha o símbolo do logo com ``height`` px de altura; retorna a largura."""
    vx, vy, vw, vh = MARK_VIEW
    s = height / vh

    def pt(x, y):
        return x0 + (x - vx) * s, y0 + (y - vy) * s

    stroke = max(2, round(3.5 * s))
    cx, cy = pt(30, 60)
    r = 22 * s
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=ink, width=stroke)
    ar = 10 * s
    canvas.create_arc(cx - ar, cy - ar, cx + ar, cy + ar, start=0, extent=45, style="arc",
                      outline=ink, width=max(1, round(1.8 * s)))
    px, py = pt(45.6, 44.4)
    canvas.create_line(cx, cy, px, py, fill=ink, width=stroke, capstyle="round")
    hub = 3 * s
    canvas.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill=ink, outline="")
    qx, _ = pt(60, 44.4)
    canvas.create_line(px, py, qx, py, fill=accent, width=max(1, round(2.4 * s)),
                       dash=(max(2, round(2 * s)), max(2, round(3 * s))))
    canvas.create_line(*[c for xy in _STEPS for c in pt(*xy)], fill=accent,
                       width=max(2, round(4 * s)), joinstyle="miter")
    dr = 4.8 * s
    canvas.create_oval(px - dr, py - dr, px + dr, py + dr, fill=accent, outline="")
    return vw * s

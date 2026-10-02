"""Interface gráfica do gerador DDS: frequência, forma de onda e LUT arbitrária
pelo Virtual JTAG (USB-Blaster)."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import theme
from dds_jtag import (
    F_CLK, FREQ_MAX, GENERATED_SHAPES, LUT_DEPTH, LUT_WIDTH, N_ACC, WAVEFORMS, DdsJtag,
    DdsJtagError, find_quartus, generate_lut, list_cables, load_lut, output_frequency,
    tuning_word,
)

ANY_CABLE = "(automático)"
HERE = os.path.dirname(os.path.abspath(__file__))
LUT_DIR = os.path.join(HERE, "..", "lut")
ICON_PATH = os.path.join(HERE, "..", "docs", "logo", "icon.png")


class Worker(threading.Thread):
    """Thread dona da conexão: abre o quartus_stp e executa as tarefas em fila.

    Toda chamada ao DdsJtag acontece aqui, nunca na thread do Tk.
    Eventos vão para ``events`` como (tipo, self, dado).
    """

    def __init__(self, events: queue.Queue, cable, device, instance, quartus_dir):
        super().__init__(daemon=True)
        self.events = events
        self.params = dict(cable=cable, device=device, instance=instance, quartus_dir=quartus_dir)
        self.jobs: queue.Queue = queue.Queue()
        self.cancel = threading.Event()  # interrompe a escrita da LUT

    def submit(self, name: str, fn):
        """Agenda ``fn(dds)``; o resultado volta como evento "done"."""
        self.jobs.put((name, fn))

    def stop(self):
        self.cancel.set()
        self.jobs.put(None)

    def emit(self, kind, payload=None):
        self.events.put((kind, self, payload))

    def run(self):
        dds = DdsJtag(**self.params, log=lambda line: self.emit("log", line), auto_open=False)
        try:
            dds.open()
        except DdsJtagError as exc:
            self.emit("open_failed", str(exc))
            return
        if self.cancel.is_set():  # cancelado enquanto abria
            dds.close()
            return
        self.emit("connected", dds.info())
        try:
            while (job := self.jobs.get()) is not None:
                name, fn = job
                try:
                    self.emit("done", (name, fn(dds)))
                except DdsJtagError as exc:
                    self.emit("failed", (name, str(exc)))
                    if not dds.is_open:
                        self.emit("lost", str(exc))
                        return
        finally:
            dds.close()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DDS Waveform Generator")
        self.geometry("1240x800")
        self.minsize(1120, 720)

        self.io: Worker | None = None
        self.connected = False
        self.events: queue.Queue = queue.Queue()
        self.lut: list[int] | None = None
        self._cables = {}

        self.fonts = theme.make_fonts(self)
        self.theme_var = tk.StringVar(value=theme.DEFAULT_THEME)
        self.pal = theme.apply_style(self, self.theme_var.get(), self.fonts)
        self._set_icon()

        try:
            self.quartus_dir = find_quartus()
        except DdsJtagError as exc:
            self.quartus_dir = None
            messagebox.showerror("Quartus", str(exc))

        self._build_ui()
        self._recolor()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(20, self._poll)
        self.refresh_cables()

    # ------------------------------------------------------------------ UI

    def _set_icon(self):
        try:
            self._icon = tk.PhotoImage(file=ICON_PATH).subsample(16)  # 1024 px -> 64 px
            self.iconphoto(True, self._icon)
        except tk.TclError:
            pass

    def _build_ui(self):
        self.configure(menu=self._build_menu())
        self._build_header()
        self._build_toolstrip()
        self._build_statusbar()

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=6)
        body.add(self._build_properties(body), weight=0)
        work = ttk.Panedwindow(body, orient="vertical")
        body.add(work, weight=1)
        work.add(self._build_plot(work), weight=3)
        work.add(self._build_console(work), weight=2)
        self.after_idle(lambda: body.sashpos(0, 300))

    def _build_menu(self) -> tk.Menu:
        bar = tk.Menu(self)
        arquivo = tk.Menu(bar, tearoff=False)
        arquivo.add_command(label="Abrir LUT...", command=self.open_lut, accelerator="Ctrl+O")
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self.on_close, accelerator="Ctrl+Q")
        exibir = tk.Menu(bar, tearoff=False)
        exibir.add_radiobutton(label="Tema escuro", value="escuro", variable=self.theme_var,
                               command=self._change_theme)
        exibir.add_radiobutton(label="Tema claro", value="claro", variable=self.theme_var,
                               command=self._change_theme)
        exibir.add_separator()
        exibir.add_command(label="Limpar console", command=self.clear_log)
        bar.add_cascade(label="Arquivo", menu=arquivo)
        bar.add_cascade(label="Exibir", menu=exibir)
        self.bind_all("<Control-o>", lambda e: self.open_lut())
        self.bind_all("<Control-q>", lambda e: self.on_close())
        self._menus = [bar, arquivo, exibir]
        return bar

    def _build_header(self):
        head = ttk.Frame(self, style="Header.TFrame", padding=(14, 8))
        head.pack(fill="x", side="top")
        self.mark = tk.Canvas(head, width=44, height=34, highlightthickness=0, borderwidth=0)
        self.mark.pack(side="left", padx=(0, 10))
        ttk.Label(head, text="DDS", style="Header.TLabel").pack(side="left")
        ttk.Label(head, text="WAVEFORM GENERATOR", style="HeaderSub.TLabel").pack(
            side="left", padx=(10, 0), pady=(5, 0))
        ttk.Label(head, text="Síntese Digital Direta · Cyclone IV E · Virtual JTAG",
                  style="HeaderSub.TLabel").pack(side="right", pady=(5, 0))

    def _toolgroup(self, parent, caption: str) -> ttk.Frame:
        """Grupo da barra de ferramentas: controles em cima, legenda embaixo."""
        group = ttk.Frame(parent, padding=(10, 6, 10, 4))
        group.pack(side="left", fill="y")
        body = ttk.Frame(group)
        body.pack(side="top", fill="both", expand=True)
        ttk.Label(group, text=caption.upper(), style="Caption.TLabel").pack(side="bottom", pady=(4, 0))
        return body

    def _build_toolstrip(self):
        strip = ttk.Frame(self)
        strip.pack(fill="x", side="top")
        ttk.Separator(self).pack(fill="x", side="top")
        pad = {"padx": 3, "pady": 2}

        # Conexão: cabo e dispositivo à esquerda, botão principal ocupando as duas linhas
        conn = self._toolgroup(strip, "Conexão JTAG")
        ttk.Label(conn, text="Cabo", style="Muted.TLabel").grid(row=0, column=0, sticky="w", **pad)
        self.cable_var = tk.StringVar(value=ANY_CABLE)
        self.cable_cb = ttk.Combobox(conn, textvariable=self.cable_var, width=21, state="readonly")
        self.cable_cb.grid(row=0, column=1, sticky="we", **pad)
        self.cable_cb.bind("<<ComboboxSelected>>", lambda e: self._show_chain())
        self.refresh_btn = ttk.Button(conn, text="Atualizar", command=self.refresh_cables)
        self.refresh_btn.grid(row=0, column=2, sticky="we", **pad)
        ttk.Label(conn, text="Device", style="Muted.TLabel").grid(row=1, column=0, sticky="w", **pad)
        ids = ttk.Frame(conn)
        ids.grid(row=1, column=1, columnspan=2, sticky="w")
        self.device_var = tk.IntVar(value=1)
        ttk.Spinbox(ids, from_=1, to=16, width=3, textvariable=self.device_var,
                    font=self.fonts["mono"]).pack(side="left", **pad)
        ttk.Label(ids, text="Instance", style="Muted.TLabel").pack(side="left", padx=(12, 3))
        self.instance_var = tk.IntVar(value=0)
        ttk.Spinbox(ids, from_=0, to=255, width=3, textvariable=self.instance_var,
                    font=self.fonts["mono"]).pack(side="left", **pad)
        self.connect_btn = ttk.Button(conn, text="Conectar", style="Accent.TButton", width=12,
                                      command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3, rowspan=2, sticky="ns", padx=(10, 3), pady=2)
        self.chain_var = tk.StringVar(value="")
        ttk.Label(conn, textvariable=self.chain_var, style="Hint.TLabel").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=3)

        ttk.Separator(strip, orient="vertical").pack(side="left", fill="y", pady=8)

        # LUT arbitrária: origem dos dados à esquerda, envio à direita
        lut = self._toolgroup(strip, "LUT arbitrária")
        ttk.Button(lut, text="Abrir arquivo...", command=self.open_lut).grid(
            row=0, column=0, columnspan=2, sticky="we", **pad)
        self.shape_var = tk.StringVar(value=GENERATED_SHAPES[0])
        ttk.Combobox(lut, textvariable=self.shape_var, values=GENERATED_SHAPES, width=14,
                     state="readonly").grid(row=1, column=0, sticky="we", **pad)
        ttk.Button(lut, text="Gerar", command=self.generate).grid(row=1, column=1, sticky="we", **pad)
        self.send_btn = ttk.Button(lut, text="Enviar ao FPGA", style="Accent.TButton",
                                   command=self.send_lut)
        self.send_btn.grid(row=0, column=2, sticky="we", padx=(10, 3), pady=2)
        self.cancel_btn = ttk.Button(lut, text="Cancelar", command=self.cancel_lut, state="disabled")
        self.cancel_btn.grid(row=1, column=2, sticky="we", padx=(10, 3), pady=2)

    def _panel(self, parent, title: str, info_var: tk.StringVar | None = None):
        """Painel com faixa de título (estilo painel acoplado); retorna (painel, cabeçalho)."""
        panel = ttk.Frame(parent)
        head = ttk.Frame(panel, style="PanelHead.TFrame", padding=(12, 6))
        head.pack(fill="x")
        ttk.Label(head, text=title, style="PanelTitle.TLabel").pack(side="left")
        if info_var is not None:
            ttk.Label(head, textvariable=info_var, style="PanelInfo.TLabel").pack(
                side="left", padx=(12, 0))
        ttk.Separator(panel).pack(fill="x")
        return panel, head

    def _section(self, parent, caption: str, right: str = "") -> ttk.Frame:
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=14, pady=(14, 6))
        ttk.Label(row, text=caption.upper(), style="Caption.TLabel").pack(side="left")
        if right:
            ttk.Label(row, text=right, style="Caption.TLabel").pack(side="right")
        body = ttk.Frame(parent)
        body.pack(fill="x", padx=14)
        return body

    def _build_properties(self, parent):
        panel, _ = self._panel(parent, "Propriedades")

        # Frequência
        freq = self._section(panel, "Frequência de saída")
        row = ttk.Frame(freq)
        row.pack(fill="x")
        self.freq_var = tk.StringVar(value="1000")
        entry = ttk.Entry(row, textvariable=self.freq_var, width=10, font=self.fonts["mono_lg"],
                          justify="right")
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.apply_frequency())
        ttk.Label(row, text="Hz", style="Unit.TLabel").pack(side="left", padx=(8, 0))
        ttk.Button(freq, text="Aplicar", style="Accent.TButton",
                   command=self.apply_frequency).pack(fill="x", pady=(8, 8))
        grid = ttk.Frame(freq)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        self.m_var, self.hex_var, self.freal_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for r, (key, var) in enumerate((("M (FTW)", self.m_var), ("Hex", self.hex_var),
                                        ("f real", self.freal_var))):
            ttk.Label(grid, text=key, style="Muted.TLabel").grid(row=r, column=0, sticky="w", pady=1)
            ttk.Label(grid, textvariable=var, style="Value.TLabel").grid(row=r, column=1, sticky="e")
        self.freq_err_var = tk.StringVar()
        ttk.Label(freq, textvariable=self.freq_err_var, style="Error.TLabel").pack(anchor="w")
        self.freq_var.trace_add("write", lambda *a: self._update_ftw())
        self._update_ftw()

        # Forma de onda
        wave = self._section(panel, "Forma de onda", right="SEL")
        wave.columnconfigure(0, weight=1)
        self.wave_var = tk.IntVar(value=0)
        for r, (name, sel) in enumerate(WAVEFORMS.items()):
            rb = ttk.Radiobutton(wave, text=name, value=sel, variable=self.wave_var,
                                 command=self.apply_waveform)
            rb.grid(row=r, column=0, sticky="we")
            code = ttk.Label(wave, text=f"{sel:02b}", style="Unit.TLabel")
            code.grid(row=r, column=1, sticky="e")
            code.bind("<Button-1>", lambda e, b=rb: b.invoke())

        # Parâmetros fixos do hardware
        hw = self._section(panel, "Sistema")
        hw.columnconfigure(1, weight=1)
        rows = (
            ("f_clk", f"{F_CLK / 1e6:g} MHz"),
            ("Acumulador", f"{N_ACC} bits"),
            ("Δf", f"{F_CLK / 2 ** N_ACC * 1e3:.3f} mHz"),
            ("LUT", f"{LUT_DEPTH} × {LUT_WIDTH} bits"),
            ("Faixa", f"0 – {FREQ_MAX} Hz"),
        )
        for r, (key, value) in enumerate(rows):
            ttk.Label(hw, text=key, style="Muted.TLabel").grid(row=r, column=0, sticky="w", pady=1)
            ttk.Label(hw, text=value, style="Value.TLabel").grid(row=r, column=1, sticky="e")
        return panel

    def _build_plot(self, parent):
        self.lut_var = tk.StringVar(value="")
        panel, _ = self._panel(parent, f"LUT arbitrária  ·  {LUT_DEPTH} × {LUT_WIDTH} bits",
                               self.lut_var)
        self.canvas = tk.Canvas(panel, height=220, highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw_lut())
        return panel

    def _build_console(self, parent):
        panel, head = self._panel(parent, "Console")
        ttk.Button(head, text="LIMPAR", style="Small.TButton", command=self.clear_log).pack(side="right")
        cons = ttk.Frame(panel, padding=(12, 6))
        cons.pack(fill="x", side="bottom")
        ttk.Separator(panel).pack(fill="x", side="bottom")
        body = ttk.Frame(panel)
        body.pack(fill="both", expand=True)
        self.log_text = tk.Text(body, wrap="word", height=8, font=self.fonts["mono_sm"],
                                state="disabled", borderwidth=0, highlightthickness=0,
                                padx=12, pady=8)
        sb = ttk.Scrollbar(body, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        ttk.Label(cons, text="Tcl >>", style="Unit.TLabel").pack(side="left", padx=(0, 8))
        self.tcl_entry = ttk.Entry(cons, font=self.fonts["mono"])
        self.tcl_entry.pack(side="left", fill="x", expand=True)
        self.tcl_entry.bind("<Return>", lambda e: self.run_tcl())
        ttk.Button(cons, text="Executar", command=self.run_tcl).pack(side="left", padx=(8, 0))
        return panel

    def _build_statusbar(self):
        bar = ttk.Frame(self, style="Status.TFrame", padding=(12, 4))
        bar.pack(fill="x", side="bottom")
        self.conn_label = ttk.Label(bar, text="●  DESCONECTADO", style="ConnOff.TLabel")
        self.conn_label.pack(side="left")
        self.status_var = tk.StringVar(value="Desconectado")
        ttk.Label(bar, textvariable=self.status_var, style="StatusMsg.TLabel").pack(
            side="left", padx=(16, 0))
        ttk.Label(bar, text=f"f_clk {F_CLK / 1e6:g} MHz  ·  N {N_ACC}  ·  IR 2 / DR 18",
                  style="Status.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(bar, length=160, maximum=LUT_DEPTH)
        self.progress.pack(side="right", padx=(0, 16))

    # ------------------------------------------------------------- tema

    def _change_theme(self):
        self.pal = theme.apply_style(self, self.theme_var.get(), self.fonts)
        self._recolor()

    def _recolor(self):
        """Cores dos widgets que não são ttk (Canvas, Text, menus)."""
        p = self.pal
        self.configure(background=p["bg"])
        for menu in self._menus:
            theme.style_menu(menu, p)
        for cb in self._comboboxes():
            theme.style_popdown(cb, p)
        self.mark.configure(background=p["header_bg"])
        self.mark.delete("all")
        theme.draw_mark(self.mark, 34, p["header_fg"], theme.HEADER_ACCENT)
        self.canvas.configure(background=p["plot_bg"])
        self._draw_lut()
        self.log_text.configure(background=p["plot_bg"], foreground=p["text"],
                                insertbackground=p["text"], selectbackground=p["select"],
                                selectforeground=p["text"])
        self.log_text.tag_configure("ok", foreground=p["ok"])
        self.log_text.tag_configure("err", foreground=p["err"])
        self.log_text.tag_configure("tcl", foreground=p["info"])
        self.log_text.tag_configure("quartus", foreground=p["dim"])

    def _comboboxes(self, widget=None):
        for child in (widget or self).winfo_children():
            if isinstance(child, ttk.Combobox):
                yield child
            yield from self._comboboxes(child)

    # ------------------------------------------------------------ cabos

    def refresh_cables(self):
        if not self.quartus_dir:
            return
        self.refresh_btn.configure(state="disabled")
        self.status_var.set("Procurando cabos (jtagconfig)...")

        def work():
            try:
                cables, err = list_cables(self.quartus_dir), None
            except DdsJtagError as exc:
                cables, err = [], str(exc)
            self.events.put(("call", None, lambda: self._cables_done(cables, err)))

        threading.Thread(target=work, daemon=True).start()

    def _cables_done(self, cables, err):
        self.refresh_btn.configure(state="normal")
        self._cables = {c.name: c for c in cables}
        self.cable_cb.configure(values=[ANY_CABLE] + list(self._cables))
        if self.cable_var.get() not in self._cables and len(cables) == 1:
            self.cable_var.set(cables[0].name)
        self._show_chain()
        if err:
            self.status_var.set(err)
        elif not cables:
            self.status_var.set("Nenhum cabo JTAG encontrado.")
        elif not self.io:
            self.status_var.set(f"{len(cables)} cabo(s) encontrado(s). Desconectado.")

    def _show_chain(self):
        c = self._cables.get(self.cable_var.get())
        if not c:
            self.chain_var.set("")
        elif c.warning:
            self.chain_var.set(f"⚠ {c.warning}")
        else:
            self.chain_var.set("Cadeia: " + " | ".join(c.devices) if c.devices else "Cadeia vazia")

    # ---------------------------------------------------------- conexão

    def toggle_connection(self):
        if self.io:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        if not self.quartus_dir:
            messagebox.showerror("Quartus", "Quartus não encontrado.")
            return
        cable = self.cable_var.get()
        cable = None if cable in ("", ANY_CABLE) else cable
        try:
            device, instance = int(self.device_var.get()), int(self.instance_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Conexão", "Device e Instance devem ser inteiros.")
            return
        self.connect_btn.configure(text="Cancelar", style="TButton")
        self.conn_label.configure(text="●  CONECTANDO", style="ConnOff.TLabel")
        self.status_var.set("Iniciando quartus_stp e abrindo o dispositivo...")
        self.connected = False
        self.io = Worker(self.events, cable, device, instance, self.quartus_dir)
        self.io.start()

    def _connected(self, info):
        self.connected = True
        self.connect_btn.configure(text="Desconectar", style="TButton")
        self.conn_label.configure(text="●  CONECTADO", style="ConnOn.TLabel")
        cable, device, instance = info
        self.status_var.set(f"Conectado: {cable}  {device}  instance {instance}")
        self._log(f"conectado a {cable}, {device}, instance {instance}", "ok")

    def disconnect(self, reason: str | None = None, show_error: bool = False):
        """Solta a conexão sem esperar o quartus_stp: a thread fecha sozinha."""
        if not self.io:
            return
        self.io.stop()
        self.io = None
        was_connected, self.connected = self.connected, False
        self.connect_btn.configure(text="Conectar", style="Accent.TButton")
        self.conn_label.configure(text="●  DESCONECTADO", style="ConnOff.TLabel")
        self._lut_busy(False)
        self.status_var.set(reason or "Desconectado")
        if was_connected or reason:
            self._log(reason or "desconectado", "err" if reason else None)
        if show_error and reason:
            messagebox.showerror("Conexão", reason)

    def _submit(self, name: str, fn, busy_msg: str) -> bool:
        if not self.connected:
            self.status_var.set("Conecte antes de enviar.")
            return False
        self.status_var.set(busy_msg)
        self.io.submit(name, fn)
        return True

    def _poll(self):
        try:
            for _ in range(200):  # não monopoliza a thread do Tk
                kind, worker, payload = self.events.get_nowait()
                if kind == "call":
                    payload()
                    continue
                if worker is not self.io:
                    continue  # evento de uma conexão antiga/abandonada
                if kind == "log":
                    self._log(payload, "quartus")
                elif kind == "connected":
                    self._connected(payload)
                elif kind == "open_failed":
                    self.disconnect("Falha na conexão: " + payload, show_error=True)
                elif kind == "lost":
                    self.disconnect("Conexão perdida: " + payload)
                elif kind == "progress":
                    self.progress.configure(value=payload[0])
                    self.status_var.set(f"Enviando LUT: {payload[0]}/{payload[1]}")
                elif kind == "done":
                    self._job_done(*payload)
                elif kind == "failed":
                    self._job_failed(*payload)
        except queue.Empty:
            pass
        self.after(20, self._poll)

    def _job_done(self, name, result):
        if name == "tcl":
            self._log(result if result else "(ok)", "ok")
            self.status_var.set("Comando Tcl executado.")
        elif name == "lut":
            self._lut_busy(False)
            msg = (f"LUT enviada ({result} valores)." if result == LUT_DEPTH
                   else f"Envio cancelado após {result} valores.")
            self._log(msg, "ok")
            self.status_var.set(msg)
        else:
            self._log(name, "ok")
            self.status_var.set(name)

    def _job_failed(self, name, error):
        if name == "lut":
            self._lut_busy(False)
        self._log(f"{name}: {error}", "err")
        self.status_var.set(f"Erro: {error}")

    # ---------------------------------------------------- frequência / onda

    def _parse_freq(self) -> int | None:
        try:
            f = int(self.freq_var.get().strip().replace("_", ""))
        except ValueError:
            return None
        return f if 0 <= f <= FREQ_MAX else None

    def _update_ftw(self):
        f = self._parse_freq()
        if f is None:
            self.freq_err_var.set(f"Valor inteiro de 0 a {FREQ_MAX} Hz.")
            for var in (self.m_var, self.hex_var, self.freal_var):
                var.set("—")
            return
        m = tuning_word(f)
        self.freq_err_var.set("")
        self.m_var.set(str(m))
        self.hex_var.set(f"0x{m:08X}")
        self.freal_var.set(f"{output_frequency(m):.4f} Hz")

    def apply_frequency(self):
        f = self._parse_freq()
        if f is None:
            messagebox.showerror("Frequência", f"Digite um inteiro de 0 a {FREQ_MAX} Hz.")
            return
        self._submit(f"frequência = {f} Hz", lambda dds: dds.set_frequency(f), "Enviando frequência...")

    def apply_waveform(self):
        sel = self.wave_var.get()
        name = next(n for n, v in WAVEFORMS.items() if v == sel)
        self._submit(f"forma de onda = {name}", lambda dds: dds.set_waveform(sel), "Enviando forma de onda...")

    # ---------------------------------------------------------------- LUT

    def open_lut(self):
        path = filedialog.askopenfilename(
            title="LUT arbitrária", initialdir=LUT_DIR if os.path.isdir(LUT_DIR) else None,
            filetypes=[("LUT", "*.mif *.txt *.csv *.hex"), ("Todos", "*")])
        if not path:
            return
        try:
            self._set_lut(load_lut(path), os.path.basename(path))
        except DdsJtagError as exc:
            messagebox.showerror("LUT", str(exc))

    def generate(self):
        shape = self.shape_var.get()
        self._set_lut(generate_lut(shape), f"gerada: {shape}")

    def _set_lut(self, values: list[int], source: str):
        self.lut = values
        self.lut_var.set(f"{source}  —  mín {min(values)}, máx {max(values)}")
        self.progress.configure(value=0)
        self._draw_lut()

    def _draw_lut(self):
        c, p = self.canvas, self.pal
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        left, right, top, bottom = 52, 18, 32, 40
        pw, ph = w - left - right, h - top - bottom
        if pw < 20 or ph < 20:
            return
        font = self.fonts["mono_xs"]

        def x_of(i):
            return left + pw * i / (LUT_DEPTH - 1)

        def y_of(v):
            return top + ph * (1 - v / 255)

        for k in range(9):  # 8 divisões em cada eixo
            x = left + pw * k / 8
            y = top + ph * k / 8
            c.create_line(x, top, x, top + ph, fill=p["grid"])
            c.create_line(left, y, left + pw, y, fill=p["grid"])
        c.create_rectangle(left, top, left + pw, top + ph, outline=p["axis"])
        c.create_line(left, y_of(128), left + pw, y_of(128), fill=p["axis"], dash=(4, 4))
        for v in (0, 64, 128, 192, 255):
            c.create_text(left - 8, y_of(v), text=str(v), anchor="e", fill=p["muted"], font=font)
        for i in (0, 256, 512, 768, 1023):
            c.create_text(x_of(i), top + ph + 6, text=str(i), anchor="n", fill=p["muted"], font=font)
        c.create_text(left + pw / 2, top + ph + 22, text="amostra", anchor="n", fill=p["dim"],
                      font=font)
        c.create_text(left - 8, top - 20, text="código", anchor="e", fill=p["dim"], font=font)

        if not self.lut:
            c.create_text(left + pw / 2, top + ph / 2 - 10, text="Nenhuma LUT carregada",
                          fill=p["muted"], font=self.fonts["ui_bold"])
            c.create_text(left + pw / 2, top + ph / 2 + 12, fill=p["dim"], font=font,
                          text="Abra um arquivo ou gere uma forma na barra de ferramentas")
            return
        n = len(self.lut)
        pts = []
        for i, v in enumerate(self.lut):
            pts += [left + pw * i / (n - 1), y_of(v)]
        c.create_line(*pts, fill=p["trace"], width=2)

    def send_lut(self):
        if self.lut is None:
            messagebox.showinfo("LUT", "Abra um arquivo ou gere uma forma antes de enviar.")
            return
        values, worker = list(self.lut), self.io

        def job(dds):
            return dds.write_lut(values, progress=lambda d, t: worker.emit("progress", (d, t)),
                                 cancel=worker.cancel)

        if worker:
            worker.cancel.clear()
        if self._submit("lut", job, "Enviando LUT..."):
            self.progress.configure(value=0)
            self._lut_busy(True)

    def cancel_lut(self):
        if self.io:
            self.io.cancel.set()

    def _lut_busy(self, busy: bool):
        self.send_btn.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy else "disabled")

    # ------------------------------------------------------------ console

    def run_tcl(self):
        cmd = self.tcl_entry.get().strip()
        if not cmd:
            return
        if self._submit("tcl", lambda dds: dds.tcl(cmd), "Executando Tcl..."):
            self._log("> " + cmd, "tcl")
            self.tcl_entry.delete(0, "end")

    def _log(self, text: str, tag: str | None = None):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n", tag or ())
        if int(self.log_text.index("end-1c").split(".")[0]) > 5000:
            self.log_text.delete("1.0", "1000.0")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def on_close(self):
        self.disconnect()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()

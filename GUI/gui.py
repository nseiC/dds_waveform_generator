"""Interface gráfica do gerador DDS: frequência, forma de onda e LUT arbitrária
pelo Virtual JTAG (USB-Blaster)."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from dds_jtag import (
    FREQ_MAX, GENERATED_SHAPES, LUT_DEPTH, WAVEFORMS, DdsJtag, DdsJtagError,
    find_quartus, generate_lut, list_cables, load_lut, output_frequency, tuning_word,
)

ANY_CABLE = "(automático)"
LUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lut")


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
        self.title("Gerador DDS")
        self.geometry("900x720")
        self.minsize(720, 560)

        self.io: Worker | None = None
        self.connected = False
        self.events: queue.Queue = queue.Queue()
        self.lut: list[int] | None = None
        self._cables = {}

        try:
            self.quartus_dir = find_quartus()
        except DdsJtagError as exc:
            self.quartus_dir = None
            messagebox.showerror("Quartus", str(exc))

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(20, self._poll)
        self.refresh_cables()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        pad = {"padx": 4, "pady": 4}

        # Conexão
        conn = ttk.LabelFrame(self, text="Conexão")
        conn.pack(fill="x", **pad)
        ttk.Label(conn, text="Cabo:").grid(row=0, column=0, sticky="w", **pad)
        self.cable_var = tk.StringVar(value=ANY_CABLE)
        self.cable_cb = ttk.Combobox(conn, textvariable=self.cable_var, width=32, state="readonly")
        self.cable_cb.grid(row=0, column=1, sticky="we", **pad)
        self.cable_cb.bind("<<ComboboxSelected>>", lambda e: self._show_chain())
        self.refresh_btn = ttk.Button(conn, text="Atualizar", command=self.refresh_cables)
        self.refresh_btn.grid(row=0, column=2, **pad)
        ttk.Label(conn, text="Device:").grid(row=0, column=3, **pad)
        self.device_var = tk.IntVar(value=1)
        ttk.Spinbox(conn, from_=1, to=16, width=4, textvariable=self.device_var).grid(row=0, column=4, **pad)
        ttk.Label(conn, text="Instance:").grid(row=0, column=5, **pad)
        self.instance_var = tk.IntVar(value=0)
        ttk.Spinbox(conn, from_=0, to=255, width=4, textvariable=self.instance_var).grid(row=0, column=6, **pad)
        self.connect_btn = ttk.Button(conn, text="Conectar", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=7, **pad)
        self.chain_var = tk.StringVar(value="")
        ttk.Label(conn, textvariable=self.chain_var, foreground="#555").grid(
            row=1, column=0, columnspan=8, sticky="w", padx=4)
        conn.columnconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        # Frequência
        freq = ttk.LabelFrame(top, text="Frequência")
        freq.pack(side="left", fill="both", expand=True, padx=(0, 4))
        row = ttk.Frame(freq)
        row.pack(fill="x", **pad)
        self.freq_var = tk.StringVar(value="1000")
        entry = ttk.Entry(row, textvariable=self.freq_var, width=12, font=("Monospace", 11))
        entry.pack(side="left", **pad)
        entry.bind("<Return>", lambda e: self.apply_frequency())
        ttk.Label(row, text="Hz").pack(side="left")
        ttk.Button(row, text="Aplicar", command=self.apply_frequency).pack(side="left", **pad)
        self.ftw_var = tk.StringVar()
        ttk.Label(freq, textvariable=self.ftw_var, foreground="#555").pack(anchor="w", padx=8, pady=(0, 6))
        self.freq_var.trace_add("write", lambda *a: self._update_ftw())
        self._update_ftw()

        # Forma de onda
        wave = ttk.LabelFrame(top, text="Forma de onda")
        wave.pack(side="left", fill="both")
        self.wave_var = tk.IntVar(value=0)
        for name, sel in WAVEFORMS.items():
            ttk.Radiobutton(wave, text=name, value=sel, variable=self.wave_var,
                            command=self.apply_waveform).pack(side="left", **pad)

        # LUT arbitrária
        lut = ttk.LabelFrame(self, text=f"LUT arbitrária ({LUT_DEPTH} × 8 bits)")
        lut.pack(fill="x", **pad)
        bar = ttk.Frame(lut)
        bar.pack(fill="x")
        ttk.Button(bar, text="Abrir arquivo...", command=self.open_lut).pack(side="left", **pad)
        self.shape_var = tk.StringVar(value=GENERATED_SHAPES[0])
        ttk.Combobox(bar, textvariable=self.shape_var, values=GENERATED_SHAPES, width=14,
                     state="readonly").pack(side="left", **pad)
        ttk.Button(bar, text="Gerar", command=self.generate).pack(side="left", **pad)
        self.cancel_btn = ttk.Button(bar, text="Cancelar", command=self.cancel_lut, state="disabled")
        self.cancel_btn.pack(side="right", **pad)
        self.send_btn = ttk.Button(bar, text="Enviar ao FPGA", command=self.send_lut)
        self.send_btn.pack(side="right", **pad)
        self.progress = ttk.Progressbar(bar, length=160, maximum=LUT_DEPTH)
        self.progress.pack(side="right", **pad)
        self.lut_var = tk.StringVar(value="Nenhuma LUT carregada.")
        ttk.Label(lut, textvariable=self.lut_var, foreground="#555").pack(anchor="w", padx=8)
        self.canvas = tk.Canvas(lut, height=150, background="#111", highlightthickness=0)
        self.canvas.pack(fill="x", **pad)
        self.canvas.bind("<Configure>", lambda e: self._draw_lut())

        # Log e console Tcl
        log = ttk.LabelFrame(self, text="Log")
        log.pack(fill="both", expand=True, **pad)
        body = ttk.Frame(log)
        body.pack(fill="both", expand=True)
        self.log_text = tk.Text(body, wrap="word", height=8, font=("Monospace", 9), state="disabled",
                                background="#111", foreground="#ddd")
        self.log_text.tag_configure("ok", foreground="#8d8")
        self.log_text.tag_configure("err", foreground="#f77")
        self.log_text.tag_configure("tcl", foreground="#6cf")
        self.log_text.tag_configure("quartus", foreground="#888")
        sb = ttk.Scrollbar(body, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        cons = ttk.Frame(log)
        cons.pack(fill="x")
        ttk.Label(cons, text="Tcl:").pack(side="left", **pad)
        self.tcl_entry = ttk.Entry(cons, font=("Monospace", 10))
        self.tcl_entry.pack(side="left", fill="x", expand=True, **pad)
        self.tcl_entry.bind("<Return>", lambda e: self.run_tcl())
        ttk.Button(cons, text="Executar", command=self.run_tcl).pack(side="left", **pad)
        ttk.Button(cons, text="Limpar log", command=self.clear_log).pack(side="left", **pad)

        # Status
        self.status_var = tk.StringVar(value="Desconectado")
        ttk.Label(self, textvariable=self.status_var).pack(fill="x", side="bottom", padx=6, pady=2)

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
        self.connect_btn.configure(text="Cancelar")
        self.status_var.set("Iniciando quartus_stp e abrindo o dispositivo...")
        self.connected = False
        self.io = Worker(self.events, cable, device, instance, self.quartus_dir)
        self.io.start()

    def _connected(self, info):
        self.connected = True
        self.connect_btn.configure(text="Desconectar")
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
        self.connect_btn.configure(text="Conectar")
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
            self.ftw_var.set(f"Valor inteiro de 0 a {FREQ_MAX} Hz.")
            return
        m = tuning_word(f)
        self.ftw_var.set(f"M = {m}   (0x{m:08X})   f real = {output_frequency(m):.4f} Hz")

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
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        mid = h - 4 - (h - 8) * 128 / 255
        c.create_line(0, mid, w, mid, fill="#333", dash=(3, 3))
        if not self.lut or w < 2:
            return
        n = len(self.lut)
        pts = []
        for i, v in enumerate(self.lut):
            pts += [i * (w - 1) / (n - 1), h - 4 - (h - 8) * v / 255]
        c.create_line(*pts, fill="#6cf")

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

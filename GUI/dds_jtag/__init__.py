"""Controle do DDS pelo Virtual JTAG (``sld_virtual_jtag``) através do USB-Blaster.

Mantém um ``quartus_stp -s`` (shell Tcl do Signal Tap) aberto e usa os comandos
``device_virtual_ir_shift`` / ``device_virtual_dr_shift`` para escrever nos
registradores do FPGA.

Protocolo (IR de 2 bits, DR de 18 bits, instance index 0):

    IR 00  nenhuma operação
    IR 01  frequência em Hz (18 bits, 0 a 262 143)
    IR 10  forma de onda (2 bits de baixo): 00 seno, 01 rampa, 10 sinc, 11 arbitrária
    IR 11  escrita na LUT arbitrária: addr(17..8) & dado(7..0)

Exemplo::

    from dds_jtag import DdsJtag

    with DdsJtag() as dds:            # único cabo, device 1, instance 0
        dds.set_waveform(0)
        dds.set_frequency(440)
"""

from __future__ import annotations

import glob
import os
import queue
import re
import subprocess
import threading
from dataclasses import dataclass

__all__ = [
    "DdsJtag",
    "DdsJtagError",
    "CableInfo",
    "StpSession",
    "WAVEFORMS",
    "GENERATED_SHAPES",
    "find_quartus",
    "list_cables",
    "load_lut",
    "generate_lut",
    "tuning_word",
    "output_frequency",
]

# --------------------------------------------------------------------------
# Parâmetros do hardware (devem bater com o VHDL)
# --------------------------------------------------------------------------

F_CLK = 10_000_000          # clock do acumulador de fase (Hz)
N_ACC = 32                  # bits do acumulador
S_FRAC = 24                 # bits fracionários da constante do frequency_translator
K_FTW = round(2 ** (N_ACC + S_FRAC) / F_CLK)  # 7 205 759 404

DR_LENGTH = 18
FREQ_MAX = 2 ** 18 - 1
LUT_DEPTH = 1024
LUT_WIDTH = 8

IR_NOP, IR_FREQ, IR_SEL, IR_LUT = 0, 1, 2, 3
WAVEFORMS = {"Seno": 0, "Rampa": 1, "Sinc": 2, "Arbitrária": 3}


class DdsJtagError(Exception):
    """Erro de comunicação com o quartus_stp, o cabo ou o FPGA."""


def tuning_word(f_hz: int) -> int:
    """FTW calculada como no frequency_translator: (f * K) >> 24, truncada."""
    return (f_hz * K_FTW) >> S_FRAC


def output_frequency(ftw: int) -> float:
    """Frequência gerada por uma FTW: M * f_clk / 2^N."""
    return ftw * F_CLK / 2 ** N_ACC


# --------------------------------------------------------------------------
# Localização do Quartus
# --------------------------------------------------------------------------

def find_quartus() -> str:
    """Retorna o diretório ``.../quartus`` (o que contém ``bin/quartus_stp``).

    Ordem: $QUARTUS_ROOTDIR, depois instalações comuns em ~/intelFPGA*,
    ~/altera*, /opt/intelFPGA*, /opt/altera* (a versão mais nova primeiro).
    """
    env = os.environ.get("QUARTUS_ROOTDIR")
    if env and os.path.isfile(os.path.join(env, "bin", "quartus_stp")):
        return env

    home = os.path.expanduser("~")
    patterns = [
        f"{home}/intelFPGA*/*/quartus",
        f"{home}/altera*/*/quartus",
        "/opt/intelFPGA*/*/quartus",
        "/opt/altera*/*/quartus",
    ]
    found = [p for pat in patterns for p in glob.glob(pat)
             if os.path.isfile(os.path.join(p, "bin", "quartus_stp"))]
    if not found:
        raise DdsJtagError(
            "Quartus não encontrado. Defina QUARTUS_ROOTDIR apontando para a "
            "pasta 'quartus' da instalação."
        )

    def version_key(path: str):
        ver = os.path.basename(os.path.dirname(path))
        return [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", ver)]

    return sorted(found, key=version_key, reverse=True)[0]


# --------------------------------------------------------------------------
# Listagem de cabos (via jtagconfig)
# --------------------------------------------------------------------------

@dataclass
class CableInfo:
    name: str                 # ex.: "USB-Blaster [1-1.1]"
    devices: list[str]        # linhas de dispositivos da cadeia JTAG
    warning: str = ""         # ex.: "Unable to lock chain - Insufficient port permissions"


def list_cables(quartus_dir: str | None = None, timeout: float = 15.0) -> list[CableInfo]:
    """Lista os cabos JTAG e os dispositivos da cadeia usando ``jtagconfig``."""
    quartus_dir = quartus_dir or find_quartus()
    exe = os.path.join(quartus_dir, "bin", "jtagconfig")
    try:
        out = subprocess.run([exe], capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DdsJtagError(f"Falha ao executar jtagconfig: {exc}") from exc

    cables: list[CableInfo] = []
    for line in out.splitlines():
        m = re.match(r"^\s*\d+\)\s+(.+?)\s*$", line)
        if m:
            cables.append(CableInfo(name=m.group(1), devices=[]))
        elif cables and line.strip():
            text = line.strip()
            if re.match(r"^[0-9A-Fa-f]{8}\s", text):
                cables[-1].devices.append(text)
            else:
                cables[-1].warning = text
    return cables


# --------------------------------------------------------------------------
# Sessão quartus_stp
# --------------------------------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def tcl_quote(text: str) -> str:
    """Cita uma string como uma única palavra Tcl, sem substituições."""
    if not re.search(r"[{}\\]", text):
        return "{" + text + "}"
    return '"' + re.sub(r'([\\"$\[\]{}])', r"\\\1", text) + '"'


class StpSession:
    """Shell ``quartus_stp -s`` controlado por pipes.

    Cada comando é embrulhado num ``catch`` que imprime ``@@<n> OK|ERR <resultado>``
    numa linha só (quebras de linha escapadas), o que separa a resposta das
    mensagens "Info:" que o Quartus imprime.
    """

    def __init__(self, quartus_dir: str, log=None, start_timeout: float = 60.0):
        exe = os.path.join(quartus_dir, "bin", "quartus_stp")
        self._log = log or (lambda line: None)
        try:
            self._proc = subprocess.Popen(
                [exe, "-s"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace",
            )
        except OSError as exc:
            raise DdsJtagError(f"Falha ao iniciar quartus_stp: {exc}") from exc
        self._lines: queue.Queue = queue.Queue()
        self._seq = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._reader, daemon=True).start()
        self.command("info patchlevel", timeout=start_timeout)  # espera o banner

    def _reader(self):
        for line in self._proc.stdout:
            self._lines.put(_ANSI.sub("", line.rstrip("\r\n")))
        self._lines.put(None)

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None

    def command(self, tcl: str, timeout: float = 30.0) -> str:
        """Executa uma linha de Tcl e devolve o resultado (ou levanta DdsJtagError)."""
        with self._lock:
            if not self.alive:
                raise DdsJtagError("O quartus_stp não está em execução.")
            self._seq += 1
            tag = f"@@{self._seq} "
            wrapped = (
                r'if {[catch {%s} __r]} {set __s ERR} else {set __s OK}; '
                r'puts "%s$__s [string map [list \\ {\\} \n {\n}] $__r]"; flush stdout'
            ) % (tcl, tag)
            try:
                self._proc.stdin.write(wrapped + "\n")
                self._proc.stdin.flush()
            except OSError as exc:
                raise DdsJtagError(f"quartus_stp não aceita comandos: {exc}") from exc

            while True:
                try:
                    line = self._lines.get(timeout=timeout)
                except queue.Empty:
                    self.kill()
                    raise DdsJtagError(
                        f"Sem resposta do quartus_stp em {timeout:.0f} s "
                        "(cabo desconectado?). Sessão encerrada."
                    ) from None
                if line is None:
                    raise DdsJtagError("O quartus_stp terminou inesperadamente.")
                pos = line.find(tag)
                if pos < 0:
                    if line.strip() and line.strip() != "tcl>":
                        self._log(line)
                    continue
                status, _, payload = line[pos + len(tag):].partition(" ")
                result = re.sub(r"\\(.)", lambda m: "\n" if m.group(1) == "n" else m.group(1), payload)
                if status == "OK":
                    return result
                raise DdsJtagError(re.sub(r"^ERROR:\s*", "", result.strip()))

    def raw(self, tcl: str, timeout: float = 30.0) -> str:
        """Executa Tcl digitado pelo usuário (chaves desbalanceadas viram erro)."""
        return self.command("uplevel #0 " + tcl_quote(tcl), timeout)

    def kill(self):
        if self.alive:
            self._proc.kill()

    def close(self):
        if not self.alive:
            return
        try:
            self._proc.stdin.write("exit\n")
            self._proc.stdin.flush()
            self._proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            self.kill()


# --------------------------------------------------------------------------
# DDS
# --------------------------------------------------------------------------

# Trava o JTAG, desloca o IR uma vez e um DR por valor da lista.
_PROC_SHIFT = (
    "proc dds_shift {inst ir len vals} {"
    "device_lock -timeout 10000; "
    "set e [catch {"
    "device_virtual_ir_shift -instance_index $inst -ir_value $ir -no_captured_ir_value; "
    "foreach v $vals {device_virtual_dr_shift -instance_index $inst -length $len "
    "-dr_value $v -value_in_hex -no_captured_dr_value}"
    "} r]; "
    "device_unlock; "
    "if {$e} {error $r}; "
    "return [llength $vals]}"
)


class DdsJtag:
    """Conexão com o DDS.

    :param cable: nome do cabo como no jtagconfig (ex. ``"USB-Blaster [1-1.1]"``)
        ou ``None`` para o único cabo presente.
    :param device: posição do FPGA na cadeia JTAG (1 = primeiro).
    :param instance: instance index do Virtual JTAG (0 se só há um).
    :param log: função chamada com as mensagens do quartus_stp.
    """

    LUT_CHUNK = 64  # escritas por comando: dá progresso sem pesar no pipe

    def __init__(self, cable: str | None = None, device: int = 1, instance: int = 0,
                 quartus_dir: str | None = None, log=None, auto_open: bool = True):
        self.cable = cable
        self.device = device
        self.instance = instance
        self.quartus_dir = quartus_dir or find_quartus()
        self.device_name = ""
        self._log = log
        self._stp: StpSession | None = None
        if auto_open:
            self.open()

    # ---- ciclo de vida ------------------------------------------------

    def open(self) -> None:
        if self._stp:
            return
        stp = StpSession(self.quartus_dir, log=self._log)
        try:
            cable = self._pick_cable(stp)
            device = self._pick_device(stp, cable)
            stp.command(f"open_device -hardware_name {tcl_quote(cable)} -device_name {tcl_quote(device)}")
            stp.command(_PROC_SHIFT)
        except DdsJtagError:
            stp.close()
            raise
        self._stp, self.cable, self.device_name = stp, cable, device

    def _pick_cable(self, stp: StpSession) -> str:
        try:
            names = stp.command('join [get_hardware_names] "\\n"').splitlines()
        except DdsJtagError:
            names = []  # o Quartus dá erro em vez de lista vazia
        if self.cable:
            if self.cable not in names:
                raise DdsJtagError(f"Cabo '{self.cable}' não encontrado. Disponíveis: {names or 'nenhum'}.")
            return self.cable
        if not names:
            raise DdsJtagError("Nenhum cabo JTAG encontrado (USB-Blaster conectado e com permissão?).")
        if len(names) > 1:
            raise DdsJtagError(f"Mais de um cabo disponível, escolha um: {names}.")
        return names[0]

    def _pick_device(self, stp: StpSession, cable: str) -> str:
        names = stp.command(f'join [get_device_names -hardware_name {tcl_quote(cable)}] "\\n"').splitlines()
        for name in names:
            if name.startswith(f"@{self.device}:"):
                return name
        raise DdsJtagError(f"Device {self.device} não existe na cadeia. Disponíveis: {names or 'nenhum'}.")

    def close(self) -> None:
        stp, self._stp = self._stp, None
        if not stp:
            return
        if stp.alive:
            try:
                stp.command("close_device", timeout=5)
            except DdsJtagError:
                pass
        stp.close()

    @property
    def is_open(self) -> bool:
        return bool(self._stp and self._stp.alive)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    def info(self) -> tuple[str, str, int]:
        """(cabo, device, instance) conectados."""
        return self.cable or "", self.device_name, self.instance

    # ---- operações -----------------------------------------------------

    def shift(self, ir: int, values: list[int]) -> None:
        """Seleciona a instrução ``ir`` e desloca cada valor num DR de 18 bits."""
        stp = self._check_open()
        digits = (DR_LENGTH + 3) // 4
        words = " ".join(f"{v:0{digits}X}" for v in values)
        stp.command(f"dds_shift {self.instance} {ir} {DR_LENGTH} {{{words}}}")

    def set_frequency(self, f_hz: int) -> None:
        if not 0 <= f_hz <= FREQ_MAX:
            raise DdsJtagError(f"Frequência fora da faixa: 0 a {FREQ_MAX} Hz.")
        self.shift(IR_FREQ, [f_hz])

    def set_waveform(self, sel: int) -> None:
        if not 0 <= sel <= 3:
            raise DdsJtagError("Forma de onda deve ser de 0 a 3.")
        self.shift(IR_SEL, [sel])

    def write_lut(self, values: list[int], progress=None, cancel: threading.Event | None = None) -> int:
        """Escreve a LUT arbitrária a partir do endereço 0. Retorna quantos valores foram escritos."""
        check_lut(values)
        words = [(addr << LUT_WIDTH) | v for addr, v in enumerate(values)]
        for start in range(0, len(words), self.LUT_CHUNK):
            if cancel and cancel.is_set():
                return start
            self.shift(IR_LUT, words[start:start + self.LUT_CHUNK])
            if progress:
                progress(min(start + self.LUT_CHUNK, len(words)), len(words))
        return len(words)

    def tcl(self, command: str) -> str:
        """Executa um comando Tcl qualquer no quartus_stp (depuração)."""
        return self._check_open().raw(command)

    def _check_open(self) -> StpSession:
        if not self.is_open:
            raise DdsJtagError("Conexão JTAG não está aberta.")
        return self._stp


# --------------------------------------------------------------------------
# Arquivos de LUT
# --------------------------------------------------------------------------

_RADIX = {"BIN": 2, "OCT": 8, "DEC": 10, "UNS": 10, "HEX": 16}


def check_lut(values: list[int]) -> None:
    if len(values) != LUT_DEPTH:
        raise DdsJtagError(f"A LUT precisa ter {LUT_DEPTH} valores (tem {len(values)}).")
    bad = [v for v in values if not 0 <= v < 2 ** LUT_WIDTH]
    if bad:
        raise DdsJtagError(f"Valores fora de 0 a {2 ** LUT_WIDTH - 1}: {bad[:5]}.")


def _load_mif(text: str) -> list[int]:
    text = re.sub(r"%.*?%", " ", text, flags=re.S)
    text = re.sub(r"--[^\n]*", " ", text)
    header, body = re.split(r"\bCONTENT\s+BEGIN\b", text, maxsplit=1, flags=re.I)
    opts = {k.upper(): v.strip().upper() for k, v in re.findall(r"(\w+)\s*=\s*([^;]+);", header)}
    depth = int(opts.get("DEPTH", LUT_DEPTH))
    width = int(opts.get("WIDTH", LUT_WIDTH))
    if width != LUT_WIDTH:
        raise DdsJtagError(f"O .mif tem WIDTH = {width}; a LUT é de {LUT_WIDTH} bits.")
    arad = _RADIX.get(opts.get("ADDRESS_RADIX", "HEX"), 16)
    drad = _RADIX.get(opts.get("DATA_RADIX", "HEX"), 16)

    mem = [0] * depth
    body = re.split(r"\bEND\b", body, maxsplit=1, flags=re.I)[0]
    for entry in body.split(";"):
        if ":" not in entry:
            continue
        addr_txt, data_txt = entry.split(":", 1)
        addr_txt = addr_txt.strip()
        values = [int(tok, drad) for tok in data_txt.split()]
        m = re.fullmatch(r"\[\s*(\w+)\s*\.\.\s*(\w+)\s*\]", addr_txt)
        if m:  # [a..b] : v  (ou vários valores repetidos em ciclo)
            lo, hi = int(m.group(1), arad), int(m.group(2), arad)
            for i, addr in enumerate(range(lo, hi + 1)):
                mem[addr] = values[i % len(values)]
        else:
            for i, v in enumerate(values):
                mem[int(addr_txt, arad) + i] = v
    return mem


def load_lut(path: str) -> list[int]:
    """Lê uma LUT de um .mif do Quartus ou de um texto/CSV com um número por item
    (decimal, ou com prefixo 0x / 0b)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as exc:
        raise DdsJtagError(f"Não foi possível ler {path}: {exc}") from exc
    try:
        if re.search(r"\bCONTENT\s+BEGIN\b", text, flags=re.I):
            values = _load_mif(text)
        else:
            values = [int(tok, 0) for tok in re.split(r"[\s,;]+", text) if tok]
    except (ValueError, IndexError) as exc:
        raise DdsJtagError(f"Arquivo de LUT inválido: {exc}") from exc
    check_lut(values)
    return values


def generate_lut(shape: str) -> list[int]:
    """Formas prontas em offset binary (zero em 128, amplitude 127), como as LUTs do projeto."""
    import math

    def code(x: float) -> int:
        return math.floor(128 + 127 * x + 0.5)

    n = LUT_DEPTH
    if shape == "Seno":
        return [code(math.sin(2 * math.pi * k / n)) for k in range(n)]
    if shape == "Quadrada":
        return [code(1 if k < n // 2 else -1) for k in range(n)]
    if shape == "Dente de serra":
        return [code(2 * k / (n - 1) - 1) for k in range(n)]
    if shape == "Triangular":
        return [code(4 * k / n if k < n / 4 else (2 - 4 * k / n if k < 3 * n / 4 else 4 * k / n - 4))
                for k in range(n)]
    raise DdsJtagError(f"Forma desconhecida: {shape}.")


GENERATED_SHAPES = ["Seno", "Quadrada", "Dente de serra", "Triangular"]

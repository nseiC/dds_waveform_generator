# Interface do DDS — Virtual JTAG via USB-Blaster

Interface em Python para controlar o gerador DDS pelo IP **Virtual JTAG**
(`sld_virtual_jtag`), usando o `quartus_stp` do Quartus como ponte para o USB-Blaster.

- `dds_jtag/` — biblioteca (`DdsJtag`, `list_cables`, `load_lut`, `tuning_word`, ...)
- `gui.py` / `run.sh` — interface gráfica (Tkinter)
- `theme.py` — identidade visual da interface (cores do logo, fontes, estilos ttk)
- `exemplo.py` — uso da biblioteca em script
- `udev/51-usbblaster.rules` — permissão de acesso ao USB-Blaster

## Protocolo

Virtual JTAG com **IR de 2 bits**, **DR de 18 bits** (LSB enviado primeiro), instance index 0:

| IR   | Instrução            | Conteúdo do DR                                       |
|------|----------------------|------------------------------------------------------|
| `00` | nenhuma              | —                                                    |
| `01` | frequência           | f em Hz, 0 a 262 143                                 |
| `10` | forma de onda        | bits 1..0: `00` seno, `01` rampa, `10` sinc, `11` arbitrária |
| `11` | escrita na LUT       | `endereço(9..0) & dado(7..0)`                        |

O valor só deve ser aplicado no **Update-DR**. Cada envio é: trava o JTAG
(`device_lock`), `device_virtual_ir_shift` uma vez, um `device_virtual_dr_shift`
por valor, destrava. A LUT inteira são 1024 deslocamentos, em blocos de 64.

A GUI também mostra a FTW esperada, calculada como no `frequency_translator`:
`M = (f × 7 205 759 404) >> 24`, com f_clk = 10 MHz. Se mudar o clock ou o
protocolo no VHDL, ajuste as constantes no topo de `dds_jtag/__init__.py`.

## Ambiente

Python 3.12 (com tkinter) em `.venv/`, criado com `uv` (`~/.local/bin/uv`):

```bash
~/.local/bin/uv venv --python 3.12 .venv   # só na primeira vez
./run.sh                                     # GUI
.venv/bin/python exemplo.py                  # script
```

Só usa a biblioteca padrão do Python. O Quartus é localizado automaticamente em
`~/intelFPGA_lite/18.1/quartus` (ou pela variável `QUARTUS_ROOTDIR`).

## Aparência

A interface segue a identidade visual do projeto ([`docs/logo/`](../docs/logo/)):
barra de ferramentas com os grupos *Conexão JTAG* e *LUT arbitrária*, painel de
propriedades (frequência, FTW, forma de onda e parâmetros do sistema), gráfico da LUT
arbitrária, console com log e prompt Tcl, e barra de status com o estado da conexão
e o progresso do envio da LUT. Os painéis são redimensionáveis pelas divisórias.

Tema escuro (padrão) ou claro em **Exibir → Tema**. Para a tipografia da marca,
instale as fontes **Space Grotesk** e **JetBrains Mono** (Google Fonts); sem elas, a
interface usa as fontes do sistema. As cores ficam em `PALETTES`, no topo de `theme.py`.

## Permissão do USB-Blaster (uma vez só, precisa de sudo)

```bash
sudo cp udev/51-usbblaster.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Depois reconecte o cabo e mate o `jtagd` antigo (`killall jtagd`).
`jtagconfig` deve listar os dispositivos da cadeia, sem "Insufficient port permissions".

## Uso

1. Grave o `.sof` do DDS (com o Virtual JTAG) na placa, com a chave RUN/PROG em **RUN**.
2. Feche o Programmer e o Signal Tap: eles disputam o cabo com a GUI.
3. `./run.sh` → **Conectar** (Device 1 = o FPGA na cadeia, Instance 0).
4. Frequência → **Aplicar**; forma de onda → clique na opção.
5. LUT arbitrária: **Abrir arquivo...** (`.mif` do Quartus, ou texto/CSV com 1024
   valores de 0 a 255) ou **Gerar**, e então **Enviar ao FPGA**.

O campo **Tcl** executa qualquer comando no `quartus_stp` aberto, útil para depurar
(ex.: `get_device_names -hardware_name {USB-Blaster [1-1.1]}`).

Se o cabo for desconectado e o `jtagconfig` der "Server error", reinicie o servidor: `killall jtagd`.

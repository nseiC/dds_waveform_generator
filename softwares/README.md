# Softwares utilizados

[← Voltar ao início](../README.md) · [Instrumentos utilizados](../instruments/README.md)

Programas usados no projeto, do FPGA à placa analógica e ao texto do TCC. As imagens são de
divulgação dos fabricantes.

<table>
  <tr>
    <td width="25%" align="center"><img src="quartus.png" alt="Logo do Intel Quartus Prime" width="110"></td>
    <td>
      <b>Intel Quartus Prime Lite 18.1</b><br>
      Ambiente de projeto para FPGAs da Intel.<br>
      <sub>Síntese, posicionamento e roteamento, análise de tempo (TimeQuest), RTL Viewer,
      Platform Designer (IP do Virtual JTAG) e Programmer. O <code>quartus_stp</code> faz a ponte
      entre a <a href="../GUI/README.md">interface</a> e o USB-Blaster
      (<a href="../fpga/README.md">parte digital</a>).</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="ltspice.png" alt="Logo do LTspice" width="150"></td>
    <td>
      <b>LTspice 26</b> (Analog Devices)<br>
      Simulador SPICE, usado no Linux pelo Wine.<br>
      <sub>Simulação da placa analógica com o modelo comportamental do DAC0800
      (<a href="../analog/simulation">analog/simulation</a> e
      <a href="../analog/modelos/DAC0800/README.md">analog/modelos/DAC0800</a>).</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="altium.png" alt="Logo do Altium Designer" width="150"></td>
    <td>
      <b>Altium Designer</b><br>
      Ferramenta de projeto de placas de circuito impresso.<br>
      <sub>Esquemático e layout da placa analógica
      (<a href="../analog/layout">analog/layout</a>).</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="vscode.jpeg" alt="Logo do Visual Studio Code" width="110"></td>
    <td>
      <b>Visual Studio Code</b> (Microsoft)<br>
      Editor de código.<br>
      <sub>Edição do código VHDL, dos scripts e da interface em Python, dos READMEs e do texto
      do TCC.</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="claude.jpeg" alt="Logo do Claude" width="110"></td>
    <td>
      <b>Claude</b> (Anthropic), pelo Claude Code<br>
      Assistente de inteligência artificial.<br>
      <sub>Apoio, sob a orientação e a revisão do autor, na escrita do código VHDL e dos
      testbenches, dos scripts e da interface em Python, da documentação e do texto do TCC, e
      na análise das medidas de bancada.</sub>
    </td>
  </tr>
</table>

## Outros programas

| Programa | Uso |
|---|---|
| GHDL 5.0.1 | Simulação dos 16 testbenches do projeto digital ([testbenches](../fpga/README.md#testbenches)) |
| Python 3.12, com Tkinter, NumPy, Matplotlib e PyInstaller | Interface gráfica, executável da interface e scripts das figuras |
| LaTeX (TeX Live e Overleaf) | Texto do TCC, no modelo da COELE-CM da UTFPR ([overleaf](../overleaf)) |
| KiCad | Visualização do projeto da placa importado do Altium, para as imagens do esquemático, do layout e da vista 3D |
| ModelSim-Altera | Simulação do [código legado](../fpga/legado/README.md) |
| Git e GitHub | Controle de versões e publicação do repositório |

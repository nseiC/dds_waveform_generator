# Instrumentos utilizados

[← Voltar ao início](../README.md) · [Softwares utilizados](../softwares/README.md) · [Resultados de bancada](../analog/resultados/README.md)

Equipamentos usados no desenvolvimento do gerador e nos ensaios em bancada. As imagens são de
divulgação dos fabricantes.

<table>
  <tr>
    <td width="30%" align="center"><img src="de2-115.jpeg" alt="Placa Terasic DE2-115" width="220"></td>
    <td>
      <b>Terasic DE2-115</b><br>
      Placa de desenvolvimento com o FPGA Intel Cyclone IV E EP4CE115F29C7.<br>
      <sub>Recebe o projeto digital. Dela vêm o oscilador de 50 MHz, o botão KEY[0] (reset), os
      LEDs de estado, o conector de expansão JP5 (GPIO) ligado ao DAC e o USB-Blaster embutido,
      usado para gravar o FPGA e para o controle pelo Virtual JTAG
      (<a href="../fpga/README.md">parte digital</a>).</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="tbs1102b.jpeg" alt="Osciloscópio Tektronix TBS1102B" width="220"></td>
    <td>
      <b>Tektronix TBS1102B</b><br>
      Osciloscópio digital de 2 canais, 100 MHz e 2 GS/s.<br>
      <sub>Usado em todas as medidas de bancada: formas de onda, contador de frequência e FFT.
      As telas e os pontos de cada medida, salvos em PNG, CSV e SET, estão em
      <a href="../analog/resultados/README.md">analog/resultados</a>.</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="et-2042f.jpg" alt="Multímetro Minipa ET-2042F" width="120"></td>
    <td>
      <b>Minipa ET-2042F</b><br>
      Multímetro digital True RMS.<br>
      <sub>Conferência das tensões de alimentação da placa analógica e da continuidade das
      linhas do barramento do DAC, no diagnóstico do bit 2
      (<a href="../analog/resultados/README.md#teste-dos-pesos-dos-bits">teste dos pesos dos bits</a>).</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="ps-5000.jpg" alt="Fonte de alimentação ICEL Manaus PS-5000" width="220"></td>
    <td>
      <b>ICEL Manaus PS-5000</b><br>
      Fonte de alimentação de bancada de dois canais, 0 a 32 V e 0 a 3 A.<br>
      <sub>Alimentação da placa analógica (<a href="../analog/README.md">parte analógica</a>).</sub>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="cruzer_blade.jpeg" alt="Pendrive SanDisk Cruzer Blade de 16 GB" width="160"></td>
    <td>
      <b>SanDisk Cruzer Blade, 16 GB</b><br>
      Pendrive USB.<br>
      <sub>Guardou as telas e os dados salvos pelo osciloscópio. Parte das capturas foi
      recuperada com o <code>fsck.vfat</code> depois de o pendrive ser retirado durante uma
      gravação (<a href="../analog/resultados/README.md">detalhes</a>).</sub>
    </td>
  </tr>
</table>

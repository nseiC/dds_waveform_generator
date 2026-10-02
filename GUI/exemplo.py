"""Exemplo de uso da biblioteca em script (sem GUI)."""
from dds_jtag import WAVEFORMS, DdsJtag, generate_lut, list_cables, output_frequency, tuning_word

for c in list_cables():
    print(c.name, c.devices, c.warning)

with DdsJtag() as dds:  # ou DdsJtag("USB-Blaster [1-1.1]", device=1, instance=0)
    print("Conectado:", dds.info())

    dds.set_waveform(WAVEFORMS["Seno"])
    dds.set_frequency(440)
    m = tuning_word(440)
    print(f"440 Hz -> M = {m}, f real = {output_frequency(m):.4f} Hz")

    dds.write_lut(generate_lut("Quadrada"), progress=lambda d, t: print(f"\rLUT {d}/{t}", end=""))
    print()
    dds.set_waveform(WAVEFORMS["Arbitrária"])

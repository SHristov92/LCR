# LCR meter analog front end (Rev A)

This is the 1 kHz to 30 MHz AFE for the LCR meter. The controller and UI is the
JC3248W535EN (ESP32-S3, 3.5" touch display).

Architecture (Option B): a two-channel ratiometric V-I bridge, down-converted to a
low IF and digitised by a stereo audio ADC over I2S. The ESP32-S3 does the vector math.

- `LCR_AFE.pdf` is the full schematic as a PDF (6 pages).
- `LCR_AFE.kicad_pro` / `*.kicad_sch` is the KiCad project. It was written in KiCad 7
  format and opens in KiCad 7, 8 and 9.
- `LCR.kicad_sym` is the project symbol library (SA612A, rail power symbols).
- `LCR_AFE_bom.csv` is a grouped BOM taken from the netlist.
- `tools/` holds the Python script that generated the schematic. It is only useful for
  regenerating from scratch. Once the schematic is edited in KiCad, KiCad becomes the source of truth.

## Signal chain

```
AD9851 DDS ─ LPF 45 MHz ─ ADA4817 x2 ─ 49.9Ω ─ NODE_A ─ Rref (relay) ─ NODE_B ═ DUT ─ GND
                                                 │                       │
                                            ADA4817 buf             ADA4817 buf
                                                 │ V_A                    │ V_B
                                        SA612A mixer ◄── Si5351 LO ──► SA612A mixer
                                                 │ IF ~5 kHz              │
                                        IF amp / bypass sw        IF amp / bypass sw
                                                 └──► CS5343 L      R ◄──┘ ── I2S ──► ESP32-S3
```

`Z = Rref · V_B / (V_A − V_B)`, computed as complex numbers from a DFT at the IF bin on
both channels. Open/short/load compensation follows. Because both channels are captured
at the same time, source amplitude and phase drift cancel out.

## Sheets

| Page | Sheet | Contents |
|---|---|---|
| 2 | Power | USB-C 5 V in (sink, 5.1k CC), polyfuse, LM27762 ±4.0 V, LP5907 3.3 V, ferrite-isolated +5V_DDS / +5V_A |
| 3 | Stimulus | AD9851 (serial mode, 30 MHz ref × 6 = 180 MHz), 5th-order 200 Ω Butterworth LPF, ADA4817 gain-2 driver, SN74LVC2T45 3.3→5 V translators |
| 4 | Bridge | 5 range resistors (10 Ω … 100 kΩ, 0.1 %) on signal relays, BNC DUT port, clamp diodes, two ADA4817 FET-input buffers |
| 5 | Mixers | Si5351A (CLK0 LO, CLK1 12.288 MHz codec MCLK, CLK2 30 MHz DDS ref), 2× SA612A, ADA4807 diff-to-single IF amps (gain 2, fc ≈ 17 kHz), TS5A3159 bypass switches for direct sampling below ~20 kHz |
| 6 | ADC_Control | CS5343 (I2S master, Fs 48 kHz), PCA9555 I/O expander, I2C pull-ups, J3 controller header |

## Connection to the JC3248W535EN (J3, 2×5 header)

The 8 signals use the free GPIOs on the board's P2 and P3 connectors. GPIO46 is a
strapping pin and GPIO5 sits on the battery divider, so neither is used.

| J3 pin | Signal | ESP32-S3 GPIO | Board connector |
|---|---|---|---|
| 1, 2 | GND | GND | P3 pin 1 |
| 3 | I2C SDA (Si5351 0x60, PCA9555 0x20) | GPIO17 | P3 |
| 4 | I2C SCL | GPIO18 | P3 |
| 5 | I2S BCLK (codec → MCU) | GPIO15 | P2 |
| 6 | I2S WS / LRCK (codec → MCU) | GPIO16 | P2 |
| 7 | I2S DIN (codec SDOUT) | GPIO7 | P2 |
| 8 | DDS W_CLK | GPIO6 | P2 |
| 9 | DDS FQ_UD | GPIO9 | P2 |
| 10 | DDS DATA (serial into D7) | GPIO14 | P2 |

The AFE has its own USB-C supply. Only GND is shared with the controller. The board
pinout comes from a third-party write-up (done.land), so check it against your unit before wiring.

## PCA9555 map (0x20)

| Pin | Function |
|---|---|
| IO0_0 … IO0_4 | Range relays K1…K5 (10 Ω, 100 Ω, 1 kΩ, 10 kΩ, 100 kΩ), active high |
| IO0_5 | BYPASS: 1 = direct sampling (f ≲ 20 kHz), 0 = mixer/IF path |
| IO0_6 | DDS RESET (active high) |
| IO0_7, IO1_x | spare |

## Firmware notes

- Si5351: CLK2 = 30 MHz (DDS ref), CLK1 = 12.288 MHz (CS5343 MCLK → Fs 48 kHz, 256×),
  CLK0 = f + f_IF. Pick f_IF so a block holds a whole number of IF cycles, e.g. 6 kHz at Fs 48 kHz (8 samples per cycle).
- AD9851: D0=D1=1 and D2=0 are strapped in hardware. After RESET, one W_CLK pulse then one FQ_UD
  pulse puts it in serial mode. Then shift 40 bits LSB first on D7 and set the 6× REFCLK multiplier bit in W0.
- Direct mode (f below ~20 kHz): set BYPASS=1 and run the DFT at f itself.
- Use range relays so that |Z| ≈ Rref. Above ~5 MHz, use only the 10 Ω and 100 Ω ranges.
- Calibrate open, short and a known load per range and per frequency point.

## Open items / verify before layout

- I chose component values from datasheet equations and typical application circuits. They have
  not been simulated or built yet. In particular, check the LPF values against the AD9851 image
  rejection you need, the SA612A input level (~50 mVpp), and the IF amp gain against the CS5343
  full scale (~1.87 Vpp at 3.3 V).
- The relay symbol is a generic SPDT (`A1/A2/11/12/14`). Choose the real part (e.g. Panasonic
  TQ2SA or a reed relay) and map its footprint pins.
- I haven't checked whether the AD9851 at 5 V accepts the LVC2T45 B-side levels at 30 MHz REFCLK.
  Scope REFCLK on the first build.
- No ERC was run in the KiCad GUI (KiCad 7 CLI has no ERC). Connectivity was checked from the exported netlist.
  Every net has at least two nodes, apart from the pins deliberately marked no-connect. Run ERC once in KiCad.
- Connections are made with net labels rather than drawn wires. Tidy the layout in KiCad as needed.

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from kgen import *
from sexp import parse, dump

OUT = sys.argv[1]

# ---------------------------------------------------------------- custom library
SA612 = '''(symbol "SA612A" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
  (property "Reference" "U" (at -7.62 11.43 0) (effects (font (size 1.27 1.27)) (justify left)))
  (property "Value" "SA612A" (at 2.54 11.43 0) (effects (font (size 1.27 1.27)) (justify left)))
  (property "Footprint" "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
  (property "Datasheet" "https://www.nxp.com/docs/en/data-sheet/SA612A.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
  (property "ki_description" "Double-balanced mixer and oscillator, 500 MHz, SO-8" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
  (symbol "SA612A_0_1" (rectangle (start -7.62 10.16) (end 7.62 -10.16) (stroke (width 0.254) (type default)) (fill (type background))))
  (symbol "SA612A_1_1"
    (pin input line (at -10.16 5.08 0) (length 2.54) (name "IN_A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    (pin input line (at -10.16 2.54 0) (length 2.54) (name "IN_B" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
    (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
    (pin output line (at 10.16 2.54 180) (length 2.54) (name "OUT_A" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    (pin output line (at 10.16 -2.54 180) (length 2.54) (name "OUT_B" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
    (pin input line (at -10.16 -2.54 0) (length 2.54) (name "OSC_E" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
    (pin passive line (at -10.16 -5.08 0) (length 2.54) (name "OSC_B" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
    (pin power_in line (at 0 12.7 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))))'''
CUSTOM['SA612A'] = parse(SA612)[0]
for rail in ['+5V', '+5V_DDS', '+5V_A', '+3V3A', '+4V']:
    make_power_symbol(rail, '+5V')
make_power_symbol('-4V', '-5V')

R_FP = 'Resistor_SMD:R_0603_1608Metric'
C_FP = 'Capacitor_SMD:C_0603_1608Metric'
C_FP_BIG = 'Capacitor_SMD:C_0805_2012Metric'

def R(sh, val, x, y, a, b, fp=R_FP):
    return sh.add('Device:R', next_ref('R'), val, x, y, {'1': a, '2': b}, fp=fp)
def C(sh, val, x, y, a, b, fp=C_FP):
    return sh.add('Device:C', next_ref('C'), val, x, y, {'1': a, '2': b}, fp=fp)
def L(sh, val, x, y, a, b, fp='Inductor_SMD:L_0805_2012Metric'):
    return sh.add('Device:L', next_ref('L'), val, x, y, {'1': a, '2': b}, fp=fp)
def FB(sh, x, y, a, b):
    return sh.add('Device:FerriteBead_Small', next_ref('FB'), 'BLM18PG221', x, y, {'1': a, '2': b}, fp='Inductor_SMD:L_0603_1608Metric')
def decap(sh, x, y, rail, vals=('100n', '10u')):
    for i, v in enumerate(vals):
        C(sh, v, x + i * 7.62, y, rail, 'GND', fp=C_FP if v.endswith('n') or v.endswith('p') else C_FP_BIG)
def pwrflag(sh, x, y, net):
    sh.add('power:PWR_FLAG', next_ref('#FLG'), 'PWR_FLAG', x, y, {'1': net})

sheets = []
REFCOUNT['U'] = 3
# ================================================================ 1. POWER
pw = Sheet('Power', 'power.kicad_sch', 'Power: USB-C 5 V in, +/-4 V analog, 3.3 V, filtered 5 V rails', 'A4')
sheets.append(pw)
pw.text('POWER\nUSB-C 5 V (sink, 5.1k on CC). Polyfuse 500 mA.\n'
        'LM27762: low-noise +/-4.0 V for the op-amps (VOUT+ = 1.2 V*(1+R1/R2), VOUT- = -1.22 V*(1+R3/R4)).\n'
        'LP5907-3.3: +3V3A for Si5351, CS5343, PCA9555, level shifters.\n'
        'Ferrite-isolated +5V_DDS (AD9851) and +5V_A (SA612 mixers).', 15, 15, 1.5)
pw.add('Connector:USB_C_Receptacle_USB2.0_16P', 'J1', 'USB_C_Power', 40, 80,
       {'A1': 'GND', 'A4': 'VBUS', 'A5': 'CC1', 'B5': 'CC2', 'A6': 'NC', 'B6': 'NC', 'A7': 'NC', 'B7': 'NC',
        'A8': 'NC', 'B8': 'NC', 'S1': 'GND'}, fp='Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal')
R(pw, '5.1k', 70, 110, 'CC1', 'GND'); R(pw, '5.1k', 80, 110, 'CC2', 'GND')
pw.add('Device:Polyfuse', 'F1', '500mA', 70, 65, {'1': 'VBUS', '2': '+5V'}, fp='Fuse:Fuse_1206_3216Metric')
C(pw, '22u', 80, 65, '+5V', 'GND', fp=C_FP_BIG)
pwrflag(pw, 90, 60, '+5V'); pwrflag(pw, 100, 60, 'GND'); pwrflag(pw, 90, 75, 'VBUS')
# LM27762
pw.add('Regulator_SwitchedCapacitor:LM27762', 'U1', 'LM27762', 150, 80,
       {'1': 'NC', '2': 'FB_P', '3': '+5V', '4': 'GND', '5': 'CP', '6': '-4V', '7': 'FB_N', '8': '+5V',
        '9': 'CFLY_N', '10': 'CFLY_P', '11': '+4V', '12': '+5V', '13': 'GND'})
C(pw, '4.7u', 120, 110, '+5V', 'GND', fp=C_FP_BIG)
C(pw, '1u', 130, 110, 'CFLY_P', 'CFLY_N')
C(pw, '4.7u', 140, 110, 'CP', 'GND', fp=C_FP_BIG)
R(pw, '232k 1%', 185, 50, '+4V', 'FB_P'); R(pw, '100k 1%', 185, 75, 'FB_P', 'GND')
C(pw, '2.2u', 200, 50, '+4V', 'GND', fp=C_FP_BIG)
R(pw, '226k 1%', 185, 105, '-4V', 'FB_N'); R(pw, '100k 1%', 185, 130, 'FB_N', 'GND')
C(pw, '2.2u', 200, 105, '-4V', 'GND', fp=C_FP_BIG)
# LP5907
pw.add('Regulator_Linear:LP5907MFX-3.3', 'U2', 'LP5907MFX-3.3', 150, 150,
       {'1': '+5V', '2': 'GND', '3': '+5V', '5': '+3V3A'})
C(pw, '1u', 125, 150, '+5V', 'GND'); C(pw, '1u', 175, 150, '+3V3A', 'GND')
# filtered 5 V rails
FB(pw, 60, 160, '+5V', '+5V_DDS'); decap(pw, 70, 160, '+5V_DDS'); pwrflag(pw, 40, 160, '+5V_DDS')
FB(pw, 60, 185, '+5V', '+5V_A'); decap(pw, 70, 185, '+5V_A'); pwrflag(pw, 40, 185, '+5V_A')

# ================================================================ 2. STIMULUS
st = Sheet('Stimulus', 'stimulus.kicad_sch', 'Stimulus: AD9851 DDS, 45 MHz LPF, DUT driver')
sheets.append(st)
st.text('STIMULUS\nAD9851 in serial mode (D0=D1=1, D2=0, data on D7), REFCLK 30 MHz from Si5351 CLK2, 6x PLL on -> 180 MHz.\n'
        'IOUT full scale 10.2 mA (RSET 3.92k) into 100 ohm (doubly terminated 200 ohm filter) -> ~1 Vpp.\n'
        '5th-order Butterworth LPF, fc 45 MHz, 200 ohm. Driver ADA4817 gain 2 -> ~2 Vpp, 49.9 ohm source (NODE_A).\n'
        'SN74LVC2T45 translate 3.3 V controller/clock signals to the 5 V DDS logic.', 15, 15, 1.5)
st.add('Interface:AD9851', 'U3', 'AD9851', 120, 120,
       {'1': 'GND', '2': 'GND', '3': '+5V_DDS', '4': '+5V_DDS', '25': 'DDS_D7', '26': 'GND', '27': 'GND', '28': 'GND',
        '7': 'DDS_WCLK_5V', '8': 'DDS_FQUD_5V', '9': 'REFCLK_5V', '22': 'DDS_RESET_5V',
        '10': 'GND', '11': '+5V_DDS', '23': '+5V_DDS', '24': 'GND', '5': 'GND', '6': '+5V_DDS',
        '12': 'RSET', '13': 'NC', '14': 'NC', '15': '+5V_DDS', '16': 'GND', '17': 'DACBP',
        '20': 'IOUTB', '21': 'DDS_IOUT'})
R(st, '3.92k 1%', 150, 140, 'RSET', 'GND')
C(st, '10n', 160, 140, 'DACBP', '+5V_DDS')
R(st, '200', 170, 140, 'IOUTB', 'GND')
decap(st, 95, 175, '+5V_DDS', ('100n', '100n', '10u'))
R(st, '10k', 70, 150, 'DDS_RESET_5V', 'GND')
# level translators (DIR=VCCA -> A to B)
for i, (a1, b1, a2, b2) in enumerate([('DDS_WCLK', 'DDS_WCLK_5V', 'DDS_FQUD', 'DDS_FQUD_5V'),
                                       ('DDS_DATA', 'DDS_D7', 'DDS_RESET', 'DDS_RESET_5V'),
                                       ('REFCLK_3V3', 'REFCLK_5V', 'GND', 'NC')]):
    y = 70 + i * 40
    st.add('Logic_LevelTranslator:SN74LVC2T45DCUR', next_ref('U'), 'SN74LVC2T45DCUR', 45, y,
           {'1': '+3V3A', '2': a1, '3': a2, '4': 'GND', '5': '+3V3A', '6': b2, '7': b1, '8': '+5V_DDS'})
    C(st, '100n', 25, y + 20, '+3V3A', 'GND'); C(st, '100n', 65, y + 20, '+5V_DDS', 'GND')
# LPF  C-L-C-L-C, 200 ohm, fc = 45 MHz Butterworth
R(st, '200', 190, 80, 'DDS_IOUT', 'GND')
C(st, '11p C0G', 200, 80, 'DDS_IOUT', 'GND')
L(st, '1.1u', 210, 80, 'DDS_IOUT', 'LPF_M')
C(st, '36p C0G', 220, 80, 'LPF_M', 'GND')
L(st, '1.1u', 230, 80, 'LPF_M', 'DDS_FILT')
C(st, '11p C0G', 240, 80, 'DDS_FILT', 'GND')
R(st, '200', 250, 80, 'DDS_FILT', 'GND')
# driver
C(st, '1u', 260, 120, 'DDS_FILT', 'DRV_IN')
R(st, '10k', 270, 140, 'DRV_IN', 'GND')
st.add('Amplifier_Operational:ADA4817-1ARD', next_ref('U'), 'ADA4817-1ARD', 300, 120,
       {'1': 'DRV_FB', '2': 'DRV_INN', '3': 'DRV_IN', '4': '-4V', '6': 'DRV_OUT', '7': '+4V', '8': '+4V', '9': '-4V'})
R(st, '499', 330, 140, 'DRV_FB', 'DRV_INN'); R(st, '499', 340, 140, 'DRV_INN', 'GND')
R(st, '49.9 1%', 340, 110, 'DRV_OUT', 'NODE_A')
decap(st, 290, 165, '+4V', ('100n', '10u')); decap(st, 310, 165, '-4V', ('100n', '10u'))

# ================================================================ 3. BRIDGE
br = Sheet('Bridge', 'bridge.kicad_sch', 'V-I bridge: range resistors, DUT port, FET-input buffers')
sheets.append(br)
br.text('V-I BRIDGE (DUT LO grounded)\nNODE_A -> Rref (one relay closed) -> NODE_B = DUT HI.  Z = Rref * V_B / (V_A - V_B).\n'
        'Both nodes are buffered by ADA4817 (FET input, 1 GHz) and measured simultaneously -> ratiometric,\n'
        'source amplitude/phase drift cancels. Open/short/load compensation removes relay and fixture parasitics.\n'
        'Ranges: 10 / 100 / 1k / 10k / 100k (0.1%). Use only 10 and 100 ohm above ~5 MHz.', 15, 15, 1.5)
ranges = ['10', '100', '1k', '10k', '100k']
for i, rv in enumerate(ranges):
    x = 40 + i * 45
    k = next_ref('K')
    br.add('Relay:Relay_SPDT', k, 'TQ2SA-5V', x, 80,
           {'11': 'NODE_A', '14': 'RR%d' % i, '12': 'NC', 'A1': '+5V', 'A2': 'COIL%d' % i},
           fp='')
    R(br, rv + ' 0.1%', x + 25, 80, 'RR%d' % i, 'NODE_B')
    br.add('Device:D', next_ref('D'), '1N4148W', x, 110, {'1': '+5V', '2': 'COIL%d' % i},
           fp='Diode_SMD:D_SOD-123')
    br.add('Transistor_FET:2N7002', next_ref('Q'), '2N7002', x + 15, 120,
           {'1': 'GATE%d' % i, '2': 'GND', '3': 'COIL%d' % i}, fp='Package_TO_SOT_SMD:SOT-23')
    R(br, '100', x, 140, 'RLY%d' % i, 'GATE%d' % i)
    R(br, '100k', x + 15, 145, 'GATE%d' % i, 'GND')
br.add('Connector:Conn_Coaxial', 'J2', 'DUT (BNC)', 270, 70, {'1': 'NODE_B', '2': 'GND'},
       fp='Connector_Coaxial:BNC_Amphenol_B6252HB-NPP3G-50_Horizontal')
br.add('Device:D', next_ref('D'), 'BAV199 low-leak', 260, 110, {'1': '+4V', '2': 'NODE_B'}, fp='Diode_SMD:D_SOD-323')
br.add('Device:D', next_ref('D'), 'BAV199 low-leak', 260, 130, {'1': 'NODE_B', '2': '-4V'}, fp='Diode_SMD:D_SOD-323')
for i, (node, outn) in enumerate([('NODE_A', 'VA_BUF'), ('NODE_B', 'VB_BUF')]):
    y = 190 + i * 50
    u = next_ref('U')
    br.add('Amplifier_Operational:ADA4817-1ARD', u, 'ADA4817-1ARD', 80, y,
           {'1': 'FB_%s' % outn, '2': 'FB_%s' % outn, '3': node, '4': '-4V', '6': outn, '7': '+4V', '8': '+4V', '9': '-4V'})
    decap(br, 120, y, '+4V', ('100n', '10u')); decap(br, 140, y, '-4V', ('100n', '10u'))
    R(br, '0 (FB link)', 160, y, outn, 'FB_%s' % outn)
br.text('Buffers: unity gain, FB pin tied to -IN; a 0 ohm link from OUT to FB allows a series isolation\n'
        'resistor to be fitted later if the long run to the mixers rings.', 180, 200, 1.27)

# ================================================================ 4. MIXERS
mx = Sheet('Mixers', 'mixers.kicad_sch', 'Down-conversion: Si5351 LO, SA612A mixers, IF amps, bypass switches')
sheets.append(mx)
mx.text('DOWN-CONVERSION\nSi5351A: CLK0 = LO (f + IF, IF ~ 5 kHz), CLK1 = 12.288 MHz codec MCLK, CLK2 = 30 MHz AD9851 REFCLK.\n'
        'Both channels use identical SA612A mixers driven by the same LO -> V/I ratio keeps phase.\n'
        'IF amp: ADA4807 diff-to-single, gain 2, fc ~17 kHz.  Below ~20 kHz the TS5A3159 switches select the\n'
        'direct (un-mixed) path (BYPASS=1). Switch nodes are AC-coupled and biased at 1.65 V (VMID).', 15, 15, 1.5)
mx.add('Oscillator:Si5351A-B-GT', next_ref('U'), 'Si5351A-B-GT', 60, 90,
       {'1': '+3V3A', '2': 'XA', '3': 'XB', '4': 'I2C_SCL', '5': 'I2C_SDA', '6': 'CLK2', '7': '+3V3A', '8': 'GND',
        '9': 'CLK1', '10': 'CLK0'})
mx.add('Device:Crystal_GND24', next_ref('Y'), '25MHz 8pF', 25, 120, {'1': 'XA', '3': 'XB', '2': 'GND', '4': 'GND'}, fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
decap(mx, 40, 140, '+3V3A', ('100n', '100n', '10u'))
R(mx, '33', 95, 70, 'CLK0', 'LO')
R(mx, '33', 105, 70, 'CLK1', 'CODEC_MCLK')
R(mx, '33', 115, 70, 'CLK2', 'REFCLK_3V3')
R(mx, '1k', 95, 110, 'LO', 'LO_ATT'); R(mx, '100', 105, 110, 'LO_ATT', 'GND')
uif = next_ref('U')
for ch, (buf, ifn, sw_out, dirn) in enumerate([('VA_BUF', 'IF_A', 'ADC_INL', 'A'), ('VB_BUF', 'IF_B', 'ADC_INR', 'B')]):
    y = 90 + ch * 95
    x0 = 150
    # attenuator to mixer (~50 mVpp)
    R(mx, '2k', x0, y - 20, buf, 'MXI_' + dirn); R(mx, '51', x0 + 8, y - 20, 'MXI_' + dirn, 'GND')
    C(mx, '100n', x0 + 16, y - 20, 'MXI_' + dirn, 'MX1_' + dirn)
    C(mx, '100n', x0 + 16, y + 10, 'MX2_' + dirn, 'GND')
    C(mx, '100n', x0, y + 10, 'LO_ATT', 'MXLO_' + dirn)
    mx.add('LCR:SA612A', next_ref('U'), 'SA612A', x0 + 45, y,
           {'1': 'MX1_' + dirn, '2': 'MX2_' + dirn, '3': 'GND', '4': 'MXO_P_' + dirn, '5': 'MXO_N_' + dirn,
            '6': 'MXLO_' + dirn, '7': 'NC', '8': '+5V_A'}, fp='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm')
    decap(mx, x0 + 30, y + 30, '+5V_A', ('100n', '10u'))
    # IF diff amp (ADA4807-2 unit ch+1)
    R(mx, '10k', x0 + 75, y - 15, 'MXO_N_' + dirn, 'IFN_' + dirn)
    R(mx, '10k', x0 + 75, y + 15, 'MXO_P_' + dirn, 'IFP_' + dirn)
    R(mx, '20k', x0 + 85, y - 15, 'IFN_' + dirn, ifn)
    C(mx, '470p C0G', x0 + 95, y - 15, 'IFN_' + dirn, ifn)
    R(mx, '20k', x0 + 85, y + 15, 'IFP_' + dirn, 'GND')
    C(mx, '470p C0G', x0 + 95, y + 15, 'IFP_' + dirn, 'GND')
    unit_pins = {1: {'1': ifn, '2': 'IFN_' + dirn, '3': 'IFP_' + dirn}, 2: {'7': ifn, '6': 'IFN_' + dirn, '5': 'IFP_' + dirn}}[ch + 1]
    mx.add('Amplifier_Operational:ADA4807-2ARM', uif, 'ADA4807-2ARM', x0 + 115, y, unit_pins, unit=ch + 1,
           fp='Package_SO:MSOP-8_3x3mm_P0.65mm')
    # switch inputs (AC coupled, biased at VMID)
    C(mx, '1u', x0 + 135, y - 15, ifn, 'SWIF_' + dirn); R(mx, '100k', x0 + 145, y - 15, 'SWIF_' + dirn, 'VMID')
    R(mx, '1k', x0 + 135, y + 20, buf, 'DIR_' + dirn); R(mx, '1k', x0 + 135, y + 35, 'DIR_' + dirn, 'GND')
    C(mx, '1u', x0 + 145, y + 20, 'DIR_' + dirn, 'SWDIR_' + dirn); R(mx, '100k', x0 + 155, y + 20, 'SWDIR_' + dirn, 'VMID')
    sw = next_ref('U')
    mx.add('Analog_Switch:TS5A3159DBV', sw, 'TS5A3159DBV', x0 + 175, y,
           {'3': 'SWIF_' + dirn, '1': 'SWDIR_' + dirn, '4': sw_out, '6': 'BYPASS'}, unit=1)
    mx.add('Analog_Switch:TS5A3159DBV', sw, 'TS5A3159DBV', x0 + 205, y + 10, {'2': 'GND', '5': '+3V3A'}, unit=2)
    C(mx, '100n', x0 + 220, y + 10, '+3V3A', 'GND')
mx.add('Amplifier_Operational:ADA4807-2ARM', uif, 'ADA4807-2ARM', 60, 250, {'4': '-4V', '8': '+4V'}, unit=3)
decap(mx, 80, 250, '+4V', ('100n',)); decap(mx, 95, 250, '-4V', ('100n',))
mx.text('VMID 1.65 V bias for switch nodes', 120, 235, 1.27)
R(mx, '10k', 130, 250, '+3V3A', 'VMID'); R(mx, '10k', 145, 250, 'VMID', 'GND'); C(mx, '10u', 160, 250, 'VMID', 'GND', fp=C_FP_BIG)

# ================================================================ 5. ADC & CONTROL
ad = Sheet('ADC_Control', 'adc_control.kicad_sch', 'Audio ADC, I/O expander, controller connector', 'A4')
sheets.append(ad)
ad.text('ADC & CONTROL\nCS5343 24-bit stereo ADC, MASTER mode (10k SDOUT pull-up), MCLK 12.288 MHz from Si5351 -> Fs 48 kHz,\n'
        'BCLK/LRCK/SDOUT go to the ESP32-S3 I2S peripheral (slave RX). L = V_A channel, R = V_B channel.\n'
        'PCA9555 @0x20: IO0_0..4 range relays, IO0_5 BYPASS, IO0_6 DDS reset. Si5351 @0x60 shares I2C.\n'
        'J3 -> JC3248W535EN: P3 (GPIO17 SDA, GPIO18 SCL, GND), P2 (GPIO15 BCLK, GPIO16 WS, GPIO7 DIN,\n'
        'GPIO6 W_CLK, GPIO9 FQ_UD, GPIO14 DATA). AFE is powered from its own USB-C.', 15, 15, 1.4)
u = next_ref('U')
ad.add('Audio:CS5343', u, 'CS5343', 70, 100,
       {'1': 'I2S_DIN', '2': 'I2S_BCLK', '3': 'I2S_WS', '4': 'CODEC_MCLK', '5': 'FILT', '6': 'AINL', '7': 'VQ',
        '8': 'AINR', '9': 'GND', '10': '+3V3A'})
R(ad, '10k', 35, 70, '+3V3A', 'I2S_DIN')
for i, n in enumerate(['FILT', 'VQ']):
    C(ad, '1u', 100 + i * 20, 130, n, 'GND'); C(ad, '100n', 108 + i * 20, 130, n, 'GND')
decap(ad, 40, 140, '+3V3A', ('100n', '10u'))
for i, (src, dst) in enumerate([('ADC_INL', 'AINL'), ('ADC_INR', 'AINR')]):
    C(ad, '1u', 100 + i * 25, 70, src, 'AIN_C%d' % i)
    R(ad, '100', 108 + i * 25, 70, 'AIN_C%d' % i, dst)
    C(ad, '180p C0G', 116 + i * 25, 70, dst, 'GND')
ad.add('Interface_Expansion:PCA9555PW', next_ref('U'), 'PCA9555PW', 200, 105,
       {'1': 'NC', '2': 'GND', '3': 'GND', '21': 'GND', '22': 'I2C_SCL', '23': 'I2C_SDA', '24': '+3V3A', '12': 'GND',
        '4': 'RLY0', '5': 'RLY1', '6': 'RLY2', '7': 'RLY3', '8': 'RLY4', '9': 'BYPASS', '10': 'DDS_RESET', '11': 'NC',
        '13': 'NC', '14': 'NC', '15': 'NC', '16': 'NC', '17': 'NC', '18': 'NC', '19': 'NC', '20': 'NC'})
C(ad, '100n', 240, 140, '+3V3A', 'GND')
R(ad, '4.7k', 240, 70, '+3V3A', 'I2C_SDA'); R(ad, '4.7k', 250, 70, '+3V3A', 'I2C_SCL')
ad.add('Connector_Generic:Conn_02x05_Odd_Even', 'J3', 'To JC3248W535EN', 160, 165,
       {'1': 'GND', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL', '5': 'I2S_BCLK', '6': 'I2S_WS',
        '7': 'I2S_DIN', '8': 'DDS_WCLK', '9': 'DDS_FQUD', '10': 'DDS_DATA'},
       fp='Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical')
ad.text('J3 pinout: 1,2 GND | 3 SDA=GPIO17 | 4 SCL=GPIO18 | 5 BCLK=GPIO15 | 6 WS=GPIO16 |\n'
        '7 DIN=GPIO7 | 8 W_CLK=GPIO6 | 9 FQ_UD=GPIO9 | 10 DATA=GPIO14', 110, 185, 1.27)

# ================================================================ render
from collections import defaultdict
uses = defaultdict(set)
for sh in sheets:
    for p in sh.parts:
        for n in p['conns'].values():
            uses[n].add(sh.name)
global_nets = {n for n, s in uses.items() if len(s) > 1 and n not in POWER_NETS and n != 'NC'}

root_uuid = U()
os.makedirs(OUT, exist_ok=True)
for i, sh in enumerate(sheets):
    sh.page = i + 2
    body = sh.render(global_nets, root_uuid)
    open(os.path.join(OUT, sh.fname), 'w').write(sh.file_text(body))

# root sheet
rs = []
for i, sh in enumerate(sheets):
    x, y, w, h = 25 + (i % 3) * 85, 70 + (i // 3) * 50, 65, 30
    rs.append('(sheet (at %g %g) (size %g %g) (fields_autoplaced) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid %s)\n'
              '  (property "Sheetname" %s (at %g %g 0) (effects (font (size 1.27 1.27)) (justify left bottom)))\n'
              '  (property "Sheetfile" %s (at %g %g 0) (effects (font (size 1.27 1.27)) (justify left top)))\n'
              '  (instances (project %s (path %s (page %s)))))'
              % (x, y, w, h, sh.sym_uuid, q(sh.name), x, y - 0.7, q(sh.fname), x, y + h + 0.6, q(PROJECT), q('/' + root_uuid), q(str(sh.page))))
blocks = ('LCR METER ANALOG FRONT END  (1 kHz - 30 MHz)\n\n'
          'Signal chain: AD9851 DDS -> LPF -> ADA4817 driver -> 49.9R -> NODE_A -> Rref (relay ranged) -> NODE_B = DUT -> GND\n'
          'V_A and V_B are buffered, mixed to a ~5 kHz IF by two SA612A on a common Si5351 LO, and digitised\n'
          'together by a CS5343 stereo ADC over I2S. The ESP32-S3 (JC3248W535EN) runs a DFT on both channels:\n'
          '    Z = Rref * V_B / (V_A - V_B)   (complex), then open/short/load compensation.\n'
          'Below ~20 kHz the mixers are bypassed and the signals are sampled directly.')
rs.append('(text %s (at 30 20 0) (effects (font (size 2 2)) (justify left top)) (uuid %s))' % (q(blocks), U()))
root = ('(kicad_sch (version 20230121) (generator eeschema)\n(uuid %s)\n(paper "A4")\n'
        '(title_block (title "LCR meter AFE - top level") (date "2026-11-18") (rev "A") (company "LCR meter 1 kHz - 30 MHz"))\n'
        '(lib_symbols)\n%s\n(sheet_instances (path "/" (page "1")))\n)\n') % (root_uuid, '\n'.join(rs))
open(os.path.join(OUT, PROJECT + '.kicad_sch'), 'w').write(root)

# custom library file
libtxt = '(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n'
for name, node in CUSTOM.items():
    libtxt += dump(node, 1) + '\n'
open(os.path.join(OUT, 'LCR.kicad_sym'), 'w').write(libtxt + ')\n')
open(os.path.join(OUT, 'sym-lib-table'), 'w').write(
    '(sym_lib_table\n  (version 7)\n  (lib (name "LCR")(type "KiCad")(uri "${KIPRJMOD}/LCR.kicad_sym")(options "")(descr "LCR project symbols"))\n)\n')
pro = {"meta": {"filename": PROJECT + ".kicad_pro", "version": 1},
       "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
       "sheets": [[root_uuid, ""]] + [[sh.sym_uuid, sh.name] for sh in sheets],
       "text_variables": {}}
open(os.path.join(OUT, PROJECT + '.kicad_pro'), 'w').write(json.dumps(pro, indent=2))
print('global nets:', sorted(global_nets))

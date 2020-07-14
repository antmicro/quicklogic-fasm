import argparse
from pathlib import Path
import json


OSC_CTRL_1_REG = 0x40005484
CLK_CONTROL_F_0_REG = 0x40004020

header = [
    '    mww 0x40004c4c 0x00000180',
    '    mww 0x40004610 0x00000007',
    '    mww 0x40004088 0x0000003f',
    '    mww 0x40004044 0x00000007',
    '    mww 0x4000404c 0x00000006',
    '    mww 0x40004064 0x00000001',
    '    mww 0x40004070 0x00000001',
    '    mww 0x4000411c 0x00000006',
    '    mww 0x40005310 0x1acce551',
    '    mww 0x40004054 0x00000001',
    '    sleep 100',
    '    mww 0x40014000 0x0000bdff',
    '    sleep 100',
]

footer = [
    '    sleep 100',
    '    mww 0x40014000 0x00000000',
    '    mww 0x400047f0 0x00000000',
    '    sleep 100',
    '    mww 0x400047f4 0x00000000',
    '    mww 0x40004088 0x00000000',
    '    mww 0x40004094 0x00000000',
    '    mww 0x400047f8 0x00000090',
    '    mww 0x40004040 0x00000295',
    '    mww 0x40004048 0x00000001',
    '    mww 0x4000404c 0x0000003f',
    '    sleep 100',
    '    mww 0x40004c4c 0x000009a0',
    '    sleep 100',
]


def gen_mww(reg, val):
    mww = ["    mww %s %s" % (reg, val)]
    return mww

def dec2hex(val):
    assert type(val) == str or type(val) == int
    if type(val) == str:
        return "0x%08x" % (int(val))
    else:
        return "0x%08x" % (val)

def gen_osc_setting(freq):
    reg = OSC_CTRL_1_REG
    val = (int((freq / 32768) - 3) & 0xFFF)
    return gen_mww(dec2hex(reg), dec2hex(val))

def gen_clk_divider_setting(div):
    reg = CLK_CONTROL_F_0_REG
    enable = 0x200
    assert div > 1
    val = (div - 2) | enable
    return gen_mww(dec2hex(reg), dec2hex(val))

def gen_openocd_proc(cfg):
    cfg.insert(0, 'proc load_bitstream {} {')
    cfg.insert(1, '    echo "Loading bitstream..."')
    cfg.append('    echo "Bitstream loaded successfully!"')
    cfg.append('}')
    return cfg

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts QuickLogic bitstream to OpenOCD script"
    )

    parser.add_argument(
        "infile",
        type=Path,
        help="The input file (bitstream)",
    )

    parser.add_argument(
        "outfile",
        type=Path,
        help="The output file (OpenOCD script)",
    )

    parser.add_argument(
        "--osc-freq",
        type=int,
        default=60000000,
        help="Initial frequency of EOS S3 oscillator (default=60MHz)",
    )

    parser.add_argument(
        "--fpga-clk-divider",
        type=int,
        default=12,
        help="Initial divider for EOS S3 FPGA clock (default=12)",
    )

    args = parser.parse_args()

    openocd_script = header

    with open(args.infile, 'rb') as bitstream:
        while True:
            data = bitstream.read(4)
            if not data:
                break
            bitword = int.from_bytes(data, 'little')
            line = '    mww 0x40014ffc 0x{:08x}'.format(bitword)
            openocd_script.append(line)

    openocd_script.extend(footer)
    openocd_script.extend(gen_osc_setting(args.osc_freq))
    openocd_script.extend(gen_clk_divider_setting(args.fpga_clk_divider))

    openocd_script = gen_openocd_proc(openocd_script)

    with open(args.outfile, 'w') as openocd:
        openocd.write('\n'.join(openocd_script))

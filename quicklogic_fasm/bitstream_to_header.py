import argparse
from pathlib import Path

header = "uint32_t	axFPGABitStream[] = {\n\t"
footer = "\n};\n"
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts QuickLogic bitstream to header script"
    )

    parser.add_argument(
        "infile",
        type=Path,
        help="The input file (bitstream)",
    )

    parser.add_argument(
        "outfile",
        type=Path,
        help="The output file (Header script)",
    )

    args = parser.parse_args()

    headerscript = header

    with open(args.infile, 'rb') as bitstream:
        counter = 1
        while True:
            data = bitstream.read(4)
            if not data:
                break
            bitword = int.from_bytes(data, 'little')
            line = '0x{:08x}, '.format(bitword)
            if(counter is 10):
                headerscript += line + "\n\t"
                counter = 1
            else:
                headerscript += line 
                counter += 1
    
    data = headerscript[:-3]
    data += footer
    with open(args.outfile, 'w') as headerfile:
        headerfile.write(data)

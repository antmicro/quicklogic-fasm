import argparse
from pathlib import Path
import re

header = "uint32_t	axFPGABitStream[] = {\n\t"
footer = "\n};\n"
memheader = "uint32_t   axFPGAMemInit[] = {\n\t "
memfooter = "\n\n};\n"
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

    line_parser = re.compile(r'(?P<addr>0x4001[89ab])[xX0-9a-f]+:(?P<data>[xX0-9a-f]+).*')

    fp = open(Path(args.infile.parent).joinpath("ram.mem"), 'r')
    file_data = fp.readlines()

    counter = 0
    wordcount = 0
    headerdata = memheader
    prev_addr = None
    curr_headerdata = ""
    curr_addr = ""

    for line in file_data:
        linematch = line_parser.match(line)

        if linematch:
            curr_addr = linematch.group('addr')
            curr_data = linematch.group('data')
        else:
            continue

        if prev_addr is not None and  (prev_addr != curr_addr):
            headerdata += prev_addr + "000, " + hex(wordcount) + ",\n\t " + curr_headerdata + "\n\t "
            prev_addr = curr_addr
            wordcount = 0
            counter = 0
            curr_headerdata = ""

        prev_addr = curr_addr
        curr_headerdata += curr_data

        counter += 1
        wordcount += 1
        if counter is 10:
            curr_headerdata += ",\n\t "
            counter = 0
        else:
            curr_headerdata += ", "


    if (wordcount != 0): 
        headerdata += prev_addr + "000, " + hex(wordcount) + ",\n\t " + curr_headerdata 
 
    data += headerdata[:-2]
    data += footer

    with open(args.outfile, 'w') as headerfile:
        headerfile.write(data)


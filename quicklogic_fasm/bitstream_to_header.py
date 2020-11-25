import argparse
from pathlib import Path
import re

header = "uint32_t	axFPGABitStream[] = {\n\t"
footer = "\n};\n"
memheader = "uint32_t   axFPGAMemInit[] = {\n\t"
memfooter = "\n\n};\n"
iomuxheader = "uint32_t   axFPGAIOMuxInit[] = {\n\t"
iomuxfooter = "\n};\n"
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

    ############# BITSTREAM ARRAY #################
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
    
    # last line will have ', \n\t' so remove these 4 characters!
    data = headerscript[:-4]
    data += footer
    #############################################

    ############# MEMINIT ARRAY ################# 
    line_parser = re.compile(r'(?P<addr>0x4001[89ab])[xX0-9a-f]+:(?P<data>[xX0-9a-f]+).*')

    # RAM initialization is always generated as ram.mem
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
    ###########################################
    
    ############# IOMUX ARRAY ################# 
    iomuxdata = iomuxheader

    # if bitstream file == NAME.bit, then the iomux binary will be generated as:
    # NAME_iomux.bin, use this to locate the iomux binary
    iomuxbin_file = Path(args.infile.parent).joinpath(args.infile.stem + "_iomux.bin")

    with open(iomuxbin_file, 'rb') as iomuxbin:
        counter = 1
        while True:
            regaddr = iomuxbin.read(4)
            if not regaddr:
                break
            regval = iomuxbin.read(4)
            if not regval:
                break
            regaddrword = int.from_bytes(regaddr, 'little')
            regvalword = int.from_bytes(regval, 'little')
            line = '0x{:08x}, 0x{:08x},\n\t'.format(regaddrword,regvalword)
            iomuxdata += line

        # at the end we will have the last line with ,\n\t remove 3 chars
        iomuxdata = iomuxdata[:-3]
        # add the footer
        iomuxdata += iomuxfooter

    # add the iomux data into the main file:
    data += iomuxdata
    ###########################################

    
    ############# FINAL HEADER FILE #################
    with open(args.outfile, 'w') as headerfile:
        headerfile.write(data)
    #################################################
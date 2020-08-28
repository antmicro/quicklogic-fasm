import argparse
import re
from pathlib import Path

jlink_header = [
    'w4 0x40004c4c 0x00000180',
    'w4 0x40004610 0x00000007',
    'w4 0x40004088 0x0000003f',
    'w4 0x40004044 0x00000007',
    'w4 0x4000404c 0x00000006',
    'w4 0x40004064 0x00000001',
    'w4 0x40004070 0x00000001',
    'w4 0x4000411c 0x00000006',
    'w4 0x40005310 0x1acce551',
    'w4 0x40004054 0x00000001',
    'sleep 100',
    'w4 0x40014000 0x0000bdff',
    'sleep 100',
]

jlink_footer = [
    'sleep 100',
    'w4 0x40014000 0x00000000',
    'w4 0x400047f0 0x00000000',
    'sleep 100',
    'w4 0x400047f4 0x00000000',
    'w4 0x40004088 0x00000000',
    'w4 0x40004094 0x00000000',
    'w4 0x400047f8 0x00000090',
    'w4 0x40004040 0x00000295',
    'w4 0x40004048 0x00000001',
    'w4 0x4000404c 0x0000003f',
    'sleep 100',
    'w4 0x40004c4c 0x000009a0',
    'sleep 100',
]

header = "uint32_t	axFPGABitStream[] = {\n\t "
footer = "\n\n};\n"

memheader = "uint32_t	axFPGAMemInit[] = {\n\t "
memfooter = "\n\n};\n"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts QuickLogic JLINK script to Header file"
    )

    parser.add_argument(
        "infile",
        type=Path,
        help="The input file (JLink script)",
    )

    parser.add_argument(
        "outfile",
        type=Path,
        help="The output file (Header file)",
    )

    args = parser.parse_args()

    line_parser = re.compile(r'^\s*w4 0x40014ffc,\s*(?P<data>[xX0-9a-f]+).*')

    fp = open(args.infile, 'r') 
    file_data = fp.readlines()

    counter = 0
    headerdata = header
    for line in file_data:
        linematch = line_parser.match(line)
        if linematch:
            curr_data = linematch.group('data')
        else:    
            continue

        headerdata += curr_data
        counter += 1
        if counter is 10:
            headerdata += ",\n\t "
            counter = 0
        else:
            headerdata += ", "
    
    data = headerdata[:-4]
    data += footer

    line_parser = re.compile(r'^\s*w4 (?P<addr>0x4001[89ab])[xX0-9a-f]+,\s*(?P<data>[xX0-9a-f]+).*')

    fp = open(args.infile, 'r') 
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

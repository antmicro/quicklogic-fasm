#!/usr/bin/env python3
from fasm_utils import fasm_assembler
from fasm import FasmLine
import math
import os

class QLAssembler(fasm_assembler.FasmAssembler):

    BANKSTARTBITIDX = []
    MAXBL = 0
    MAXWL = 0
    NUMOFBANKS = 1

    def __init__(self, db):
        '''Class for generating bitstream for QuickLogic's QL732B FPGA.

        Class inherits from fasm_assembler.FasmAssembler class, and implements
        enable_feature method, as well as produce_bitstream method. It contains
        the bitstream generation process for QL732B device.
        :param BANKSTARTBITIDX: contains the bit offset for a given bank
        :param MAXBL: the maximum value for bit line
        :param MAXWL: the maximum value for word line
        :param NUMOFBANLS: the number of config bit banks
        '''
        super().__init__(db)
        self.BANKNUMBITS = math.ceil(self.MAXBL / (self.NUMOFBANKS / 2))
        self.memdict = dict()
        self.membaseaddress = {'X18Y30' : '0x4001b000', 'X1Y30' : '0x4001a000', 'X33Y2' : '0x40018000', 'X33Y16' : '0x40019000'}

    def populate_meminit(self, fasmline: FasmLine):
        featurevalue = fasmline.set_feature.value
        baseaddress = int (self.membaseaddress[fasmline.set_feature.feature[:-13]], 16)
        for i in range(fasmline.set_feature.start //18, (fasmline.set_feature.end + 1) //18):
            value = featurevalue & 262143
            featurevalue = featurevalue >> 18
            self.memdict[baseaddress+i*4] = value;
    

    def enable_feature(self, fasmline: FasmLine):
        if fasmline.set_feature.value == 0:
            self._configuredbit = False
            return

        feature = self.db.get_feature(fasmline.set_feature.feature)
        if feature is None and "RAM.RAM.INIT" in fasmline.set_feature.feature:
            self.populate_meminit(fasmline)
            self._configuredbit = True
            return

        if feature is None:
            raise fasm_assembler.FasmLookupError(
                'FASM line "{}" tries to enable unavailable feature'
                .format(fasmline)
            )

        for coord in feature.coords:
            if coord.isset:
                self.set_config_bit((coord.x, coord.y), fasmline)
            else:
                self.clear_config_bit((coord.x, coord.y), fasmline)

        # TODO: Remove the "configuredbit" test. Not only that it does not have
        # much sense, it also disallows duplicated fasm features in the input
        # file.
        self._configuredbit = True

    def calc_bitidx(self, banknum, bitnum):
        '''calculates the bit index (Y coordinate) and .

        Parameters
        ----------
        banknum: Bank number.
        bitnum: bit number in bank.
        '''
        raise NotImplementedError()

    def produce_bitstream(self, outfilepath: str, verbose=False):
        def get_value_for_coord(wlidx, wlshift, bitidx):
            coord = (wlidx + wlshift, bitidx)
            if coord not in self.configbits:
                return -1
            else:
                return self.configbits[coord]

        bitstream = []

        for wlidx in range(self.MAXWL // 2 - 1, -1, -1):
            for bitnum in range(0, self.BANKNUMBITS):
                currval = 0
                for banknum in range(self.NUMOFBANKS - 1, -1, -1):
                    val = 1
                    bitidx = self.calc_bitidx(banknum, bitnum)
                    if (bitidx == -1):
                        continue
                    if banknum >= self.NUMOFBANKS // 2:
                        val = get_value_for_coord(wlidx, self.MAXWL // 2, bitidx)
                    else:
                        val = get_value_for_coord(wlidx, 0, bitidx)

                    if val == 1:
                        currval = currval | (1 << banknum)
                if verbose:
                    print('{}_{}:  {:02X}'.format(wlidx, bitnum, currval))
                bitstream.append(currval)

        if verbose:
            print('Size of bitstream:  {}B'.format(len(bitstream) * 4))

        with open(outfilepath, 'w+b') as output:
            for batch in bitstream:
                output.write(batch.to_bytes(4, 'little'))

        mem_file = os.path.join(os.path.dirname(outfilepath), "ram.mem")
        with open(mem_file, 'w') as output:
            for x,y in self.memdict.items():
                output.write("0x{:08x}:0x{:08x}\n".format(x,y))

    def read_bitstream(self, bitfilepath):
        '''Reads bitstream from file.

        Parameters
        ----------
        bitfilepath: str
            A path to the binary file with bitstream
        '''
        bitstream = []
        with open(bitfilepath, 'rb') as input:
            while True:
                bytes = input.read(4)
                if not bytes:
                    break
                bitstream.append(int.from_bytes(bytes, 'little'))

        def set_bit(wlidx, wlshift, bitidx, value):
            coord = (wlidx + wlshift, bitidx)
            if value == 1:
                self.set_config_bit(coord, None)
            else:
                self.clear_config_bit(coord, None)

        val = iter(bitstream)
        for wlidx in reversed(range(self.MAXWL // 2)):
            for bitnum in range(self.BANKNUMBITS):
                currval = next(val)
                for banknum in reversed(range(self.NUMOFBANKS)):
                    bit = (currval >> banknum) & 1
                    bitidx = 0

                    if banknum in (0, 8, 16, 24):
                        if bitnum in (0, 1):
                            continue
                        else:
                            bitidx = self.BANKSTARTBITIDX[banknum] + bitnum - 2
                    else:
                        bitidx = self.BANKSTARTBITIDX[banknum] + bitnum

                    if banknum >= self.NUMOFBANKS // 2:
                        set_bit(wlidx, self.MAXWL // 2, bitidx, bit)
                    else:
                        set_bit(wlidx, 0, bitidx, bit)

    def disassemble(self, outfilepath: str = None, verbose=False):
        '''Converts bitstream to FASM lines.

        This method converts the bits obtained with `read_bitstream` method
        to FASM lines and returns them. It also can save FASM lines to a file.

        Parameters
        ----------
        outfilepath: str
            An optional path to the output file containing FASM lines
        verbose: bool
            If true, the verbose messages will be printed in stdout

        Returns
        -------
        list: A list of FASM lines
        '''
        unknown_bits = set([coord for coord, val in self.configbits.items()
                            if bool(val)])

        features = []
        for feature in self.db:
            for bit in feature.coords:
                coord = (bit.x, bit.y)
                if coord not in self.configbits \
                        or bool(self.configbits[coord]) != bit.isset:
                    break
            else:
                features.append(feature.signature)
                unknown_bits -= set([(bit.x, bit.y) for bit in feature.coords])
                if verbose:
                    print(f'{feature.signature}')

        if outfilepath is not None:
            with open(outfilepath, 'w') as fasm_file:
                print(*features, sep='\n', file=fasm_file)

                if len(unknown_bits):
                    for bit in unknown_bits:
                        print(f'{{ unknown_bit =  "{bit.x}_{bit.y}"}}',
                              file=fasm_file)
        return features


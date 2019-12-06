from fasm_utils import fasm_assembler
from fasm import FasmLine
import math


class QL732BAssembler(fasm_assembler.FasmAssembler):

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
        self.BANKSTARTBITIDX = [0, 43, 88, 133, 178, 223, 268, 313,
                                673, 628, 583, 538, 493, 448, 403, 358,
                                0, 43, 88, 133, 178, 223, 268, 313,
                                673, 628, 583, 538, 493, 448, 403, 358]
        self.MAXBL = 716
        self.MAXWL = 844

        self.NUMOFBANKS = 32

        self.BANKNUMBITS = math.ceil(self.MAXBL / (self.NUMOFBANKS / 2))

    def enable_feature(self, fasmline: FasmLine):
        feature = self.db.get_feature(fasmline.set_feature.feature)

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

    def produce_bitstream(self, outfilepath: str):

        def get_value_for_coord(bitidx, wlidx, wlshift):
            if (bitidx, wlidx + wlshift) not in self.configbits:
                return -1
            else:
                return self.configbits[(bitidx, wlidx + wlshift)]

        bitstream = []

        for wlidx in range(self.MAXWL // 2 - 1, -1, -1):
            # print(wlidx)
            for bitnum in range(0, self.BANKNUMBITS):
                # print(bitnum)
                currval = 0
                for banknum in range(self.NUMOFBANKS - 1, -1, -1):
                    # print('{}_{}_{} {}'.format(wlidx, bitnum, banknum, len(self.BANKSTARTBITIDX)))
                    val = 1
                    bitidx = 0
                    if banknum in (0, 8, 16, 24):
                        if bitnum in (0, 1):
                            val = 0
                            continue
                        else:
                            bitidx = self.BANKSTARTBITIDX[banknum] + bitnum - 2
                    else:
                        bitidx = self.BANKSTARTBITIDX[banknum] + bitnum

                    if banknum >= self.NUMOFBANKS // 2:
                        val = get_value_for_coord(bitidx, wlidx, self.MAXWL // 2)
                    else:
                        val = get_value_for_coord(bitidx, wlidx, 0)

                    if val == -1:
                        val = 0

                    if val == 1:
                        currval = currval | (1 << banknum)
                print('{}_{}:  {:02X}'.format(wlidx, bitnum, currval))
                bitstream.append(currval)

        print('Size of bitstream:  {}B'.format(len(bitstream) * 4))

        with open(outfilepath, 'w+b') as output:
            for batch in bitstream:
                output.write(batch.to_bytes(4, 'little'))

#!/usr/bin/env python3
from quicklogic_fasm.qlassembler import QLAssembler as qlasm

class QL732BAssembler(qlasm.QLAssembler):

    bank_start_idx = [0, 43, 88, 133, 178, 223, 268, 313,
                      673, 628, 583, 538, 493, 448, 403, 358,
                      0, 43, 88, 133, 178, 223, 268, 313,
                      673, 628, 583, 538, 493, 448, 403, 358]

    def __init__(self, db):
        '''Class for generating bitstream for QuickLogic's QL732B FPGA.

        Class inherits from QLAssembler class, and wraps it
        with ql732b specific parameters.
        :param MAXBL: the maximum value for bit line
        :param MAXWL: the maximum value for word line
        :param NUMOFBANKS: the number of config bit banks, source: QLAL4SB3.xml
        :param BANKSTARTBITIDX: contains the bit offset for a given bank, source: QLAL4SB3.xml
        '''
        self.BANKSTARTBITIDX = self.bank_start_idx
        self.MAXBL = 716
        self.MAXWL = 844
        self.NUMOFBANKS = 32
        super().__init__(db)

    def calc_bitidx(self, banknum, bitnum):
        '''calculates the bit index (Y coordinate) and .

        Parameters
        ----------
        banknum: Bank number.
        bitnum: bit number in bank.
        '''
        if banknum in (0, 8, 16, 24):
            if bitnum in (0, 1):
                return -1
            else:
                return self.BANKSTARTBITIDX[banknum] + bitnum - 2
        else:
            return self.BANKSTARTBITIDX[banknum] + bitnum

#!/usr/bin/env python3
from quicklogic_fasm.qlassembler import QLAssembler as qlasm

class QL725AAssembler(qlasm.QLAssembler):

    def __init__(self, db):
        '''Class for generating bitstream for QuickLogic's QL725A FPGA.

        Class inherits from QLAssembler class, and wraps it
        with ql725a specific parameters.
        :param MAXBL: the maximum value for bit line
        :param MAXWL: the maximum value for word line
        '''
        super().__init__(db, 884, 886)

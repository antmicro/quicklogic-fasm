#!/usr/bin/env python3
import csv


class MacroSpecificBit(object):
    '''Represents single entry in macro*Table_*.csv'''

    def __init__(self, full_bit_name, wl, bl):
        self.full_bit_name = full_bit_name
        self.wl = int(wl)
        self.bl = int(bl)

    @property
    def macro_type(self):
        '''Macro type, e.g. "macro", "macro_interface", etc.'''
        return self.full_bit_name.split('.', 2)[1]

    @property
    def bit_type(self):
        '''Bit type, e.g. "I_highway", "I_invblock", etc.'''
        return self.full_bit_name.split('.', 3)[2]

    @property
    def bit_name(self):
        '''Name without macro_type prefix.'''
        return self.full_bit_name.split('.', 2)[2]

    def __repr__(self):
        args = [f'{k}={repr(v)}' for k, v in self.__dict__.items()]
        return f'{__class__.__name__}({", ".join(args)})'


class MacroSpecificBitsTable(dict):
    '''macro_type -> [MacroSpecificBit, ...] mapping'''

    def parse(self, file_name):
        with open(file_name, 'r') as f:
            entries = None
            for line in csv.reader(f):
                assert len(line) == 3, f'len(line) = {len(line)}; line = {line}'
                entry = MacroSpecificBit(*line)
                # All entries in file should have the same macro_type
                if entries is None:
                    macro_type = entry.macro_type
                    entries = self.setdefault(macro_type, [])
                entries.append(entry)


class DeviceMacroCoord(object):
    '''Represents single entry in DeviceMacroCoord_*.csv'''

    def __init__(self, row, column, name, wl, bl, macro_type):
        self.row = int(row)
        self.column = int(column)
        self.name = name
        self.wl = int(wl)
        self.bl = int(bl)
        self.macro_type = macro_type

    def __repr__(self):
        args = [f'{k}={repr(v)}' for k, v in self.__dict__.items()]
        return f'{__class__.__name__}({", ".join(args)})'


class DeviceMacroCoordsTable(list):

    def parse(self, file_name):
        with open(file_name, 'r') as f:
            for line in csv.reader(f):
                assert len(line) == 6, f'len(line) = {len(line)}; line = {line}'
                self.append(DeviceMacroCoord(*line))

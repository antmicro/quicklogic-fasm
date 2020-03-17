#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import itertools
from configbitsfile import MacroSpecificBit


def _cellmatrix2html(cm):
    import html
    html_template = '''<!doctype html>
    <html>
        <head>
            <meta charset="utf-8"/>
            <title></title>
            <style type="text/css">
              body {{
                font-family: sans-serif;
                background-color: #424242;
                padding: 0;
                margin: 0;
                font-size: 10px;
                display: grid;
                grid-template-columns: auto repeat({cols}, auto) auto;
                grid-template-rows: auto repeat({rows}, auto) auto;
                grid-gap: 1px;
              }}
              body > div {{
                display: flex;
                align-content: center;
                justify-content: center;
                background-color: #212121;
                min-height: 2em;
                min-width: 14em;
                flex-wrap: wrap;
                color: white;
              }}
              body > div.header {{
                background-color: transparent;
                font-weight: bold;
                min-width: 4em;
              }}
              body > div > div {{
                display: inline-block;
                white-space: nowrap;
                margin: 1px;
                padding: 1px 4px;
                opacity: 0.5;
              }}
              .cell-origin {{
                font-weight: bold;
                opacity: 1;
              }}
              .group-logic         {{ color: #fff176; }}
              .group-ram           {{ color: #7986cb; }}
              .group-assp          {{ color: #ba68c8; }}
              .group-mult          {{ color: #ff8a65; }}
              .group-espxxin       {{ color: #e57373; }}
              .group-espxxout      {{ color: #81c784; }}
              .group-io            {{ color: #4dd0e1; }}
              .group-clock_network {{ color: #90a4ae; }}
            </style>
        </head>
        <body>
        {slots}
        </body>
    </html>'''
    slot_template = '<div style="grid-column: {col}; grid-row: {row};">{cells}</div>\n'  # noqa: E501
    header_template = '<div class="header" style="grid-column: {col}; grid-row: {row};">{content}</div>\n'  # noqa: E501
    cell_template = '<div class="{classes}" title="{description}">{name}</div>'  # noqa: E501

    slots = []
    for x in range(cm.geometry.width):
        slots.append(header_template.format(
            col=x + 2,
            row=1,
            content=x + cm.geometry.x))
        slots.append(header_template.format(
            col=x + 2,
            row=cm.geometry.height + 2,
            content=x + cm.geometry.x))
    for y in range(cm.geometry.height):
        slots.append(header_template.format(
            row=y + 2,
            col=1,
            content=y + cm.geometry.y))
        slots.append(header_template.format(
            row=y + 2,
            col=cm.geometry.width + 2,
            content=y + cm.geometry.y))

    for pos in cm.geometry:
        cells = []
        for cell in cm.at(pos.x, pos.y):
            name = f'{cell.name}' if cell.name else f'({cell.group})'
            classes = [f'group-{cell.group.lower()}']
            if cell.position == pos:
                classes.append('cell-origin')
            description = [
                f'Name: {cell.name}',
                f'Group: {cell.group}',
                f'Type: {cell.type}',
                f'Position: {cell.position}',
                f'Regions: [{",".join([str(r) for r in cell.regions])}]',
                f'IO: {cell.io}',
                f'Alias: {cell.alias}',
            ]

            name = html.escape(name)
            classes = html.escape(' '.join(classes))
            description = html.escape('\n'.join(description))

            cells.append(cell_template.format(
                name=name, classes=classes, description=description))
        slots.append(slot_template.format(
            cells=' '.join(cells), col=pos.x + 2, row=pos.y + 2))
    slots = ''.join(slots)
    print(html_template.format(
        rows=cm.geometry.height,
        cols=cm.geometry.width,
        slots=slots))


class NumberPair(object):
    def __init__(self, a, b=None):
        if b is None and isinstance(a, list):
            b, a = a[1], a[0]
        elif a.__class__ is self.__class__:
            b, a = a._b, a._a
        self._a = int(a)
        self._b = int(b)

    def __getitem__(self, key):
        if key == 0:
            return self._a
        elif key == 1:
            return self._b
        else:
            raise IndexError()

    def __init_subclass__(cls, members):
        cls._members = members

    def __getattr__(self, name):
        if name == self._members[0]:
            return self._a
        elif name == self._members[1]:
            return self._b

    def __setattr__(self, name, value):
        if name == self._members[0]:
            self._a = value
        elif name == self._members[1]:
            self._b = value
        else:
            super().__setattr__(name, value)

    def __add__(self, other):
        return self.__class__(self._a + other._a, self._b + other._b)

    def __sub__(self, other):
        return self.__class__(self._a - other._a, self._b - other._b)

    def __eq__(self, other):
        return self._a == other._a and self._b == other._b

    def __str__(self):
        return f'({self._a}, {self._b})'

    def __iter__(self):
        return (self._a, self._b).__iter__()


class Position(NumberPair, members=['x', 'y']):
    pass


class Size(NumberPair, members=['width', 'height']):
    pass


class Rectangle(object):
    def __init__(self, *args):
        if len(args) == 4:
            self.position = Position(args[0], args[1])
            self.size = Size(args[2], args[3])
        elif len(args) == 2:
            self.position = Position(args[0])
            self.size = Size(args[1])
        elif len(args) == 0:
            self.position = Position(0, 0)
            self.size = Size(0, 0)

    def __getattr__(self, name):
        if name in ('x', 'y'):
            return getattr(self.position, name)
        if name in ('width', 'height'):
            return getattr(self.size, name)

    def __setattr__(self, name, value):
        if name in ('x', 'y'):
            return setattr(self.position, name, value)
        if name in ('width', 'height'):
            return setattr(self.size, name, value)
        else:
            super().__setattr__(name, value)

    def __str__(self):
        return f'({self.width}x{self.height} @ ({self.x}, {self.y}))'

    def __iter__(self):
        for y in range(self.size.height):
            for x in range(self.size.width):
                yield Position(x + self.position.x, y + self.position.y)


def _spreadsheet_address_to_position(letterNum: str):
    '''Converts spreadsheet-like address (e.g. "A1") to zero-based [col,row]
    position.
    '''
    row = 0
    col = 0
    lettersCount = 0
    for c in letterNum:
        if c.isalpha():
            col *= 26  # number of letters from A to Z
            col += ord(c.upper()) - ord('A') + 1
            lettersCount += 1
        else:
            break
    row = int(letterNum[lettersCount:])
    return Position(col - 1, row - 1)


class Cell(object):
    def __init__(self, group, position, name='', type='', io='', alias=''):
        self.group = group
        self.type = type
        self.name = name
        self.position = position
        self.io = io
        self.alias = alias
        self.regions = []

    def __str__(self):
        return f'{self.group}'


class CellMatrix(object):
    def __init__(self, rect=Rectangle()):
        self.geometry = rect
        self._data = [[] for _ in range(rect.width * rect.height)]
        pass

    def at_rel(self, x, y):
        assert x < self.geometry.width, f'{x} < {self.geometry.width}'
        assert y < self.geometry.height, f'{y} < {self.geometry.height}'
        assert len(self._data) > y * self.geometry.width + x, \
            f'{len(self._data)} > {y} * {self.geometry.width} + {x}'
        return self._data[y * self.geometry.width + x]

    def at(self, x, y):
        return self.at_rel(x - self.geometry.x, y - self.geometry.y)

    def add_cell(self, cell):
        for x, y in itertools.chain([cell.position], *cell.regions):
            slot = self.at(x, y)
            if cell not in slot:
                slot.append(cell)


class InvPortsInfo(dict):
    '''bit name -> [port name, ...] mapping for single cell type'''
    def __init__(self, type):
        self.cell_type = type

    @property
    def macro_type(self):
        # Do not use "name" attribute from cell type group ("<LOGIC ...", etc),
        # as it is a bit different than macro type used in CSV files.
        if len(self) > 0:
            some_key = next(iter(self.keys()))
            return MacroSpecificBit(some_key, 0, 0).macro_type
        else:
            return None


class InvPortsInfoTable(dict):
    '''cell type -> InvPortInfo mapping'''
    def __init__(self):
        self.supported_bit_types = set()

    def add(self, port_info):
        for bit_name in port_info.keys():
            bit_type = MacroSpecificBit(bit_name, 0, 0).bit_type
            self.supported_bit_types.add(bit_type)
        self[port_info.cell_type] = port_info


def _parse_matrix(matrix):
    attrs = matrix.attrib
    return Rectangle(
        int(attrs['START_COLUMN']), int(attrs['START_ROW']),
        int(attrs['COLUMNS']), int(attrs['ROWS']))


class TechFile(object):
    def __init__(self):
        self._xml = None
        self.cells = CellMatrix()
        self.inv_ports_info = InvPortsInfoTable()

    def parse(self, file_name):
        self._xml = ET.parse(file_name).getroot()
        geometry = self._parse_geometry()
        self.cells = CellMatrix(geometry)
        self._parse_placement()

        self._parse_inv_ports_info()

    def _parse_inv_ports_info(self):
        inv_ports_info = self._xml.find('./Programming/CdlToInvPortInfo')
        for cell_bits in inv_ports_info:
            ipi = InvPortsInfo(cell_bits.tag)
            for bit in cell_bits:
                bit_name = bit.attrib['cdl_name']
                port_name = bit.attrib['mport_name']
                is_zinv = bool(int(bit.attrib['non_inverted_value']))
                # remove [] because it leads to FASM module error
                port_name = port_name.replace('[', '_').replace(']', '_')
                ipi.setdefault(bit_name, []).append((port_name, is_zinv))
            self.inv_ports_info.add(ipi)

    def _parse_geometry(self):
        ranges = {
            'ColStartNum': [], 'ColEndNum': [],
            'RowStartNum': [], 'RowEndNum': [],
        }
        quadrants = self._xml.find('./Placement/Quadrants')
        for q in quadrants:
            for k, v in q.attrib.items():
                if k in ranges:
                    ranges[k].append(int(v))
        cs = min(ranges['ColStartNum'] or [0])
        ce = max(ranges['ColEndNum'] or [cs])
        rs = min(ranges['RowStartNum'] or [0])
        re = max(ranges['RowEndNum'] or [rs])
        return Rectangle(cs, rs, ce - cs + 1, re - rs + 1)

    def _parse_placement(self):
        cell_groups = self._xml.find('./Placement')
        for cg in cell_groups:
            # Ignore quadrants
            if cg.tag == 'Quadrants':
                continue
            # LOGIC group has unique way of describing cells
            elif cg.tag == 'LOGIC':
                logicmatrix = cg.find('LOGICMATRIX')
                if logicmatrix is not None:
                    logic_geometry = _parse_matrix(logicmatrix)
                    logic_holes = []

                    exceptions = cg.find('EXCEPTIONS')
                    for e in exceptions:
                        logic_holes.append(_spreadsheet_address_to_position(e.tag) + logic_geometry.position)  # noqa: E501
                        # TODO: handle 'isBlankZone' attr?

                    for pos in logic_geometry:
                        if pos not in logic_holes:
                            self.cells.add_cell(Cell(
                                group='LOGIC',
                                position=pos,
                                type='LOGIC'))

            # Common placement tags
            for c in cg.iter('Cell'):
                # TODO: add clock attributes?
                cell = (Cell(group=cg.tag,
                        position=Position(c.attrib['column'], c.attrib['row']),
                        name=c.attrib.get('name', ''),
                        io=c.attrib.get('io', ''),
                        alias=c.attrib.get('alias', ''),
                        type=c.attrib.get('type', '')))
                for matrix in c:
                    if matrix.tag.startswith('Matrix'):
                        region = _parse_matrix(matrix)
                        cell.regions.append(region)
                self.cells.add_cell(cell)


if __name__ == '__main__':
    tf = TechFile()
    tf.parse(sys.argv[1])
    _cellmatrix2html(tf.cells)

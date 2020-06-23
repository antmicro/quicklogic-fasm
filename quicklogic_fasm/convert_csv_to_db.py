#!/usr/bin/env python3
import csv
import argparse
from collections import defaultdict
from fasm_utils.db_entry import DbEntry
from fasm_utils.segbits import Bit
from techfile_to_cell_loc import TechFile
from contextlib import nullcontext


class QLDbEntry(DbEntry):
    '''Class for extracting DB entries from CSV files for QuickLogic FPGAs.

    The class offers additional constructors for CSV files to generate
    DBEntry objects. It additionaly verifies the consistency of the
    coordinates, and flattens the hierarchical entries.

    Attributes
    ----------
    macrotype_to_celltype: dict
        Map from macro type to hardware cell type.
    dbentrytemplate: str
        The format for flattened macro database for QuickLogic.
        The fields are following:
        * site[0] - cell row
        * site[1] - cell column
        * ctype - cell type, can be LOGIC, QMUX, GMUX, INTERFACE
        * spectype - the subtype for a given ctype, used to group inverters
    '''

    macrotype_to_celltype = {
        'macro': 'LOGIC',
        'macro_clk': 'QMUX',
        'macro_gclk': 'GMUX',
        'macro_interface': 'INTERFACE',
        'macro_interface_left': 'INTERFACE',
        'macro_interface_right': 'INTERFACE',
        'macro_interface_top': 'INTERFACE',
        'macro_interface_top_left': 'INTERFACE',
        'macro_interface_top_right': 'INTERFACE'
    }

    # A map of grid row coordinates to bit WL ranges.
    # Taken from QL732B_cdl.cmd
    wl_map = {
        1: (1, 28,),
        2: (29, 56,),
        3: (57, 84,),
        4: (85, 112,),
        5: (113, 140,),
        6: (141, 168,),
        7: (169, 196,),
        8: (197, 224,),
        9: (225, 252,),
        10: (253, 281,),
        11: (282, 309,),
        12: (310, 337,),
        13: (338, 365,),
        14: (366, 393,),
        15: (394, 421,),
        16: (422, 449,),
        17: (450, 477,),
        18: (478, 505,),
        19: (506, 533,),
        20: (534, 561,),
        21: (562, 589,),
        22: (590, 617,),
        23: (618, 645,),
        24: (646, 674,),
        25: (675, 702,),
        26: (703, 730,),
        27: (731, 758,),
        28: (759, 786,),
        29: (787, 814,),
        30: (815, 842,),
    }

    # A map of grid col coortinates to bit BL ranges
    # Taken from QL732B_cdl.cmd
    bl_map = {
        0: (1, 21,),
        1: (22, 42,),
        2: (43, 63,),
        3: (64, 84,),
        4: (85, 105,),
        5: (106, 126,),
        6: (127, 147,),
        7: (148, 168,),
        8: (169, 189,),
        9: (190, 210,),
        10: (211, 231,),
        11: (232, 252,),
        12: (253, 273,),
        13: (274, 294,),
        14: (295, 315,),
        15: (316, 336,),
        16: (337, 357,),
        17: (358, 378,),
        18: (379, 399,),
        19: (400, 420,),
        20: (421, 441,),
        21: (442, 462,),
        22: (463, 483,),
        23: (484, 504,),
        24: (505, 525,),
        25: (526, 546,),
        26: (547, 567,),
        27: (568, 588,),
        28: (589, 609,),
        29: (610, 630,),
        30: (631, 651,),
        31: (652, 672,),
        32: (673, 693,),
        33: (694, 714,),
    }

    dbentrytemplate = 'X{site[0]}Y{site[1]}.{ctype}.{spectype}.{sig}'
    dbroutingentrytemplate = 'X{site[0]}Y{site[1]}.ROUTING.{sig}'
    dbcolclkentrytemplate = 'X{site[0]}Y{site[1]}.CAND{idx}.{sig}'

    def __init__(self,
                 signature: str,
                 coord: tuple,
                 devicecoord=None,
                 macrotype=None,
                 spectype=None):
        super().__init__(signature, [Bit(coord[0], coord[1], True)])
        self.coord = coord
        self.devicecoord = devicecoord
        self.macrotype = macrotype
        self.celltype = (None if self.macrotype is None
                         else self.macrotype_to_celltype[self.macrotype])
        self.is_routing_bit = ('street' in signature) or ('highway' in signature)
        self.is_colclk_bit = ('I_hilojoint' in signature) or ('I_enjoint' in signature)
        self.spectype = spectype
        self.originalsignature = signature

    def simplify_signature(self):
        '''Simplifies the signature by removing redundant / not relevant
        information from it'''

        parts = self.signature.split(".")

        # Remove "Ipsm" and "I_jcb" from the signature
        for word in ["Ipsm", "I_jcb"]:
            if word in parts:
                parts.remove(word)

        # Remove everything before these:
        for word in ["I_highway", "I_street", "I_invblock", "Ipwr_gates", "I_if_block"]:
            if word in parts:
                idx = parts.index(word)
                parts = parts[idx:]

        # Remove everything before "IQTFC_Z_*"
        for part in parts:
            if part.startswith("IQTFC_Z_"):
                idx = parts.index(part)
                parts = parts[idx:]
                break

        # Remove everything before these:
        for word in ["I_hilojoint", "I_enjoint"]:
            if word in parts:
                idx = parts.index(word)
                parts = parts[idx:]

        self.signature = ".".join(parts)

    @staticmethod
    def _get_grid_coord(wl, bl):
        """
        Returns the device grid position as (col, row) of the a bit with the
        given wl and bl indices.
        """
        row = None
        col = None

        for i, (l, h) in QLDbEntry.wl_map.items():
            if wl >= l and wl <= h:
                row = i
                break

        for i, (l, h) in QLDbEntry.bl_map.items():
            if bl >= l and bl <= h:
                col = i
                break

        return col, row

    @staticmethod
    def _get_cand_index(signature):
        """
        Extracts index of the CAND cell from the macro name
        """

        # This map translates between the last "I<n>" field value and the
        # actual CAND cell index.
        INDEX_MAP = {
            10: 0,
            9: 1,
            8: 2,
            7: 3,
            6: 4,
        }

        # Split the signature
        parts = signature.split(".")

        # Get the last "I<n>" field
        for i, word in enumerate(parts):
            if word in ["I_hilojoint", "I_enjoint"]:
                part = parts[i-1]
                break
        else:
            assert False, signature

        # Decode the index
        idx = int(part[1:])

        # Remap the index
        assert idx in INDEX_MAP, (signature, idx)
        return INDEX_MAP[idx]

    def update_signature(self, simplify=False):
        '''Updates the signature for flattened entry so it follows the format
        introduced in `dbentrytemplate`.
        '''

        self.signature = self.originalsignature

        if self.is_routing_bit:
            self.simplify_signature()
            self.signature = self.dbroutingentrytemplate.format(
                site=self.devicecoord,
                sig=self.signature)

        elif self.is_colclk_bit:
            self.simplify_signature()
            site = self._get_grid_coord(self.coord[0], self.coord[1])
            cand = self._get_cand_index(self.originalsignature)
            self.signature = self.dbcolclkentrytemplate.format(
                site=site,
                idx=cand,
                sig=self.signature)

        elif self.macrotype is not None:
            self.simplify_signature()
            self.signature = self.dbentrytemplate.format(
                site=self.devicecoord,
                ctype=self.macrotype_to_celltype[self.macrotype],
                spectype=self.spectype,
                sig=self.signature)

    @classmethod
    def _fix_signature(cls, signature: str):
        '''Removes not readable characters for fasm module from CSV entries.
        '''
        return signature.replace('<', '_').replace('>', '_')

    @classmethod
    def from_csv_line(cls, csvline: list) -> 'QLDbEntry':
        '''Reads the DbEntry from parsed flattened CSV line.'''
        return cls(cls._fix_signature(csvline[0]),
                   (int(csvline[1]), int(csvline[2])))

    @classmethod
    def from_csv_line_unflattened(cls, csvline: list) -> 'QLDbEntry':
        '''Reads the initial DbEntry from unflattened CSV line.'''
        macrotype = csvline[5]
        devicecoord = (int(csvline[1]), int(csvline[0]))
        bitcoord = (int(csvline[3]), int(csvline[4]))
        signature = cls._fix_signature(csvline[2])

        return cls(signature,
                   bitcoord,
                   devicecoord,
                   macrotype,
                   macrotype)

    def gen_flatten_macro_type(self, macrodbdata: list, invertermap: dict):
        '''Flattens the unflattened DbEntry based on the entries from the list
        of DbEntry objects that match the macrotype of this DbEntry and yields
        all flattened entries.

        Parameters
        ----------
        macrodbdata: list
            List of DbEntry objects that contains the macro configuration bits.
        invertermap: dict
            Dictionary that for each inverter name tells what inputs are
            inverted and for what kind of cell.
        '''
        for dbentry in macrodbdata:
            bitname = dbentry.signature.replace('.' + self.macrotype + '.', '')
            newsignature = self.signature + \
                dbentry.signature.replace('.' + self.macrotype, '')
            newspectype = self.celltype
            keymacrotype = self.macrotype
            # all macrotypes macro_interface* have the same set of bits
            if keymacrotype.startswith('macro_interface'):
                keymacrotype = 'macro_interface'
            if keymacrotype in invertermap and \
                    bitname in invertermap[keymacrotype]:
                info = invertermap[keymacrotype][bitname]
                part = '{}.{}'.format("ZINV" if info["is_zinv"] else "INV",
                                      info["invertedsignals"])
                newspectype = info["celltype"]

                if newspectype in ['QMUX', 'GMUX']:
                    newsignature += "." + part
                else:
                    newsignature = part

            newcoord = (self.coords[0].x + dbentry.coords[0].x,
                        self.coords[0].y + dbentry.coords[0].y)
            assert newcoord[0] < 844 and newcoord[1] < 716, \
                "Coordinate values are exceeding the maximum values: \
                 computed ({} {}) limit ({} {})".format(newcoord[0],
                                                        newcoord[1],
                                                        844, 716)
            newentry = QLDbEntry(
                newsignature,
                newcoord,
                self.devicecoord,
                self.macrotype,
                newspectype)
            newentry.update_signature(True)
            yield newentry


def process_csv_data(inputfile: str):
    '''Converts the CSV file to corresponding CSV line tuples.

    Parameters
    ----------
    inputfile: str
        Name of the CSV file

    Returns
    -------
        list: list of tuples containing CSV fields
    '''
    res = []
    with open(inputfile, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            res.append(row)
    return res


def convert_to_db(csvdata: list, flattened=True):
    '''Converts the CSV files to the DB file.

    Parameters
    ----------
    csvdata: list
        List of lines from parsed CSV file
    flattened: boolean
        Determines if it contains the unflattened file that needs to be
        processed using the other delivered CSV files.
    '''
    res = []
    for row in csvdata:
        res.append(QLDbEntry.from_csv_line(row)
                   if flattened
                   else QLDbEntry.from_csv_line_unflattened(row))
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert QuickLogic CSV bit definitions to DB format"
    )

    parser.add_argument(
        "infile",
        type=str,
        help="The input CSV file to convert to DB format"
    )

    parser.add_argument(
        "outfile",
        type=str,
        help="The output DB file"
    )

    parser.add_argument(
        "--routing-bits-outfile",
        type=str,
        help="The additional output file that will store routing bits separately"
    )

    parser.add_argument(
        "--include",
        nargs='+',
        help="The list of include files to use for macro replacement"
    )

    parser.add_argument(
        "--macro-names",
        nargs='+',
        help="The list of macro names corresponding to the include files"
    )

    parser.add_argument(
        "--techfile",
        type=str,
        help="The input TechFile XML file"
    )
    args = parser.parse_args()

    # Load CSV files. If the CSV is flattened, just print the output
    if not args.include:
        csvdata = process_csv_data(args.infile)
        dbdata = convert_to_db(csvdata)

        for entry in dbdata:
            entry.update_signature(True)

        with open(args.outfile, 'w') as output:
            output.writelines([str(d) for d in dbdata])
        exit(0)
    elif (args.include and not args.macro_names) or \
         (len(args.include) != len(args.macro_names)):
        print("You need to provide the names of macros to be replaced by the \
               given includes")
        exit(1)

    # Load top CSV and convert it to QuickLogic database
    macrotopcsv = process_csv_data(args.infile)
    macrotop = convert_to_db(macrotopcsv, flattened=False)

    required_macros = set([dbentry.macrotype for dbentry in macrotop])

    for macro in required_macros:
        if macro not in args.macro_names:
            print("WARNING: some of the macros from the {} file are not \
                   supported by given includes:  {}".format(args.infile,
                                                            macro))

    # Load includes for top
    macrolibrary = {}
    for macrotype, include in zip(args.macro_names, args.include):
        includecsv = process_csv_data(include)
        dbentries = convert_to_db(includecsv)
        macrolibrary[macrotype] = dbentries

    # Load techfile for additional information for inverters
    tech_file = TechFile()
    tech_file.parse(args.techfile)
    cells_matrix = tech_file.cells
    inv_ports_info = tech_file.inv_ports_info

    # Convert inv_ports_info hierarchical dictionary so it maps the DB entry
    # name to specific cell type and the list of inverted signals
    invertermap = defaultdict(dict)
    for celltype in inv_ports_info.keys():
        for invtype in inv_ports_info[celltype]:
            names = [b[0] for b in inv_ports_info[celltype][invtype]]
            zinv = [b[1] for b in inv_ports_info[celltype][invtype]]
            assert len(set(zinv)) == 1, (names, zinv)
            invertedsignals = '__'.join(names)
            macrotype = invtype.split('.')[1]
            invertername = invtype.replace('.{}.'.format(macrotype), '')
            invertermap[macrotype][invertername] = {
                'celltype': celltype,
                'invertedsignals': invertedsignals,
                'is_zinv': zinv[0]
            }

    coordset = defaultdict(int)
    nameset = defaultdict(int)
    coordtoorig = {}

    timesrepeated = 0
    timesrepeatedname = 0

    flattenedlibrary = []

    # Flatten the top database based on inputs
    for dbentry in macrotop:
        if dbentry.macrotype in macrolibrary:
            for flattenedentry in dbentry.gen_flatten_macro_type(
                    macrolibrary[dbentry.macrotype], invertermap):
                flattenedlibrary.append(flattenedentry)

    # Save the final database and perform sanity checks
    with open(args.outfile, 'w') as output:
        with (open(args.routing_bits_outfile, 'w')
                if args.routing_bits_outfile else nullcontext()) as routingoutput:
            for flattenedentry in flattenedlibrary:
                if flattenedentry.is_routing_bit and args.routing_bits_outfile:
                    routingoutput.write(str(flattenedentry))
                else:
                    output.write(str(flattenedentry))
                coordstr = str(flattenedentry).split(' ')[-1]
                featurestr = str(flattenedentry).split(' ')[0]
                if coordstr not in coordtoorig:
                    coordtoorig[coordstr] = flattenedentry
                else:
                    print("ORIG: {}".format(coordtoorig[coordstr]))
                    print("CURR: {}".format(flattenedentry))
                if coordstr in coordset:
                    timesrepeated += 1
                if featurestr in nameset:
                    print("ERROR: Duplicated fasm feature '{}'".format(featurestr))
                    timesrepeatedname += 1
                coordset[coordstr] += 1
                nameset[featurestr] += 1

    print("Times the coordinates were repeated:  {}".format(timesrepeated))
    print("Max repetition count: {}".format(max(coordset.values())))
    print("Times the names were repeated:  {}".format(timesrepeatedname))
    print("Max repetition count: {}".format(max(nameset.values())))
    print("Max WL: {}".format(
        max([int(x.split('_')[0]) for x in coordset.keys()])))
    print("Max BL: {}".format(
        max([int(x.split('_')[1]) for x in coordset.keys()])))

#!/usr/bin/env python3
import csv
import argparse
from collections import defaultdict
from fasm_utils.db_entry import DbEntry
from fasm_utils.segbits import Bit
from techfile_to_cell_loc import TechFile
from contextlib import nullcontext
from cdl_parser import read_and_parse_cdl_file

cdl_file=""

# A map of grid row coordinates to bit WL ranges.
wl_map = {
}

# A map of grid col coortinates to bit BL ranges
bl_map = {
}

maxcord_x = 0
maxcord_y = 0

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

        for i, (l, h) in wl_map.items():
            if wl >= l and wl <= h:
                row = i
                break

        for i, (l, h) in bl_map.items():
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
            assert newcoord[0] < maxcord_x and newcoord[1] < maxcord_y, \
                "Coordinate values are exceeding the maximum values: \
                 computed ({} {}) limit ({} {})".format(newcoord[0],
                                                        newcoord[1],
                                                        maxcord_x, maxcord_y)
            newentry = QLDbEntry(
                newsignature,
                newcoord,
                self.devicecoord,
                self.macrotype,
                newspectype)
            newentry.update_signature(True)
            yield newentry

def identify_exclusive_feature_groups(entries):
    """
    Identifies exclusive FASM features and creates groups of them. Returns a
    dict indexed by group names containing sets of the features.
    """

    groups = {}

    # Scan entries, form groups
    for entry in entries:

        # Get the feature and split it into fields
        feature = entry.signature
        parts = feature.split(".")

        # Check if this feature may be a part of a group.
        # This is EOS-S3 specific. Each routing mux is encoded as one-hot.
        # A mux feature has "I_pg<n>" suffix.
        if parts[1] == "ROUTING" and parts[-1].startswith("I_pg"):

            # Create a group
            group = ".".join(parts[:-1])
            if group not in groups:
                groups[group] = set()

            # Add the feature to the group
            groups[group].add(feature)

    return groups


def group_entries(entries, groups):
    """
    Groups exclusive features together by identifying all bits that are common
    to each group and then making each feature clear them. Leave bits that are
    set intact.
    """

    # Index entries by their signatures
    entries = {e.signature: e for e in entries}

    # Identify zero bits for each group
    zero_bits = {}
    for group, features in groups.items():

        # Collect bits
        bits = set()
        for feature in features:
            for bit in entries[feature].coords:
                bits.add(Bit(x=bit.x, y=bit.y, isset=False))

        # Store bits
        zero_bits[group] = bits

    # Group entries by adding zero-bits to them
    for group, features in groups.items():
        bits = zero_bits[group]

        for feature in features:
            entry = entries[feature]

            # Append zero bits
            for bit in bits:

                # Do not add the bit cleared if it is set
                key = Bit(x=bit.x, y=bit.y, isset=True)
                if key in entry.coords:
                    continue

                # Do not add it if it is already cleared
                if bit in entry.coords:
                    continue

                # Add the cleared bit
                entry.coords.append(bit)

            # Sort bits
            entry.coords.sort(key=lambda bit: (bit.x, bit.y))

    # Return entries as a list
    return list(entries.values())


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
        "--cdl",
        required=True,
        help="The path to device specific cdl file"
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

    cdl_file = args.cdl
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

    # Load WL- and BL-maps
    cdl_data = read_and_parse_cdl_file(cdl_file)
    wl_map = cdl_data["wl_map"]
    bl_map = cdl_data["bl_map"]

    maxcord_x = list(wl_map.values())[-1][-1] + 2
    maxcord_y = list(bl_map.values())[-1][-1] + 2

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

    # Identify exclusive feature groups
    groups = identify_exclusive_feature_groups(flattenedlibrary)
    # Group entries
    flattenedlibrary = group_entries(flattenedlibrary, groups)

    # Save the final database and perform sanity checks
    with open(args.outfile, 'w') as output:
        with (open(args.routing_bits_outfile, 'w')
                if args.routing_bits_outfile else nullcontext()) as routingoutput:
            for flattenedentry in flattenedlibrary:
                if flattenedentry.is_routing_bit and args.routing_bits_outfile:
                    routingoutput.write(str(flattenedentry))
                else:
                    output.write(str(flattenedentry))

                coordstr = str(flattenedentry).split(' ', maxsplit=1)[-1]
                featurestr = flattenedentry.signature
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

    max_wl = max([b.x for e in flattenedlibrary for b in e.coords])
    print("Max WL: {}".format(max_wl))
    max_bl = max([b.y for e in flattenedlibrary for b in e.coords])
    print("Max BL: {}".format(max_bl))

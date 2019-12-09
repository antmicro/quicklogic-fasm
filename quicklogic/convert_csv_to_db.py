import csv
import argparse
from collections import defaultdict
from fasm_utils.db_entry import DbEntry
from fasm_utils.segbits import Bit


class QLDbEntry(DbEntry):
    '''Class for extracting DB entries from CSV files for QuickLogic FPGAs.

    The class offers additional constructors for CSV files to generate
    DBEntry objects. It additionaly verifies the consistency of the
    coordinates, and flattens the hierarchical entries.
    '''
    def __init__(self,
                 signature: str,
                 coord: tuple,
                 devicecoord=None,
                 macrotype=None):
        super().__init__(signature, [Bit(coord[0], coord[1], True)])
        self.devicecoord = devicecoord
        self.macrotype = macrotype

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
        return cls(cls._fix_signature(csvline[2]),
                   (int(csvline[3]), int(csvline[4])),
                   (int(csvline[0]), int(csvline[1])),
                   csvline[5])

    def gen_flatten_macro_type(self, macrodbdata: list):
        '''Flattens the unflattened DbEntry based on the entries from the list
        of DbEntry objects that match the macrotype of this DbEntry and yields
        all flattened entries.

        Parameters
        ----------
        macrodbdata: list
            List of DbEntry objects that contains the macro configuration bits.
        '''
        for dbentry in macrodbdata:
            newsignature = self.signature + \
                dbentry.signature.replace('.' + self.macrotype, '')
            newcoord = (self.coords[0].x + dbentry.coords[0].x,
                        self.coords[0].y + dbentry.coords[0].y)
            assert newcoord[0] < 844 and newcoord[1] < 716, \
                "Coordinate values are exceeding the maximum values: \
                 computed ({} {}) limit ({} {})".format(newcoord[0],
                                                        newcoord[1],
                                                        844, 716)
            yield QLDbEntry(newsignature, newcoord)


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
        "--include",
        nargs='+',
        help="The list of include files to use for macro replacement"
    )

    parser.add_argument(
        "--macro-names",
        nargs='+',
        help="The list of macro names corresponding to the include files"
    )
    args = parser.parse_args()

    if not args.include:
        csvdata = process_csv_data(args.infile)
        dbdata = convert_to_db(csvdata)
        with open(args.outfile, 'w') as output:
            output.writelines([str(d) for d in dbdata])
        exit(0)
    elif (args.include and not args.macro_names) or \
         (len(args.include) != len(args.macro_names)):
        print("You need to provide the names of macros to be replaced by the \
               given includes")
        exit(1)

    macrotopcsv = process_csv_data(args.infile)
    macrotop = convert_to_db(macrotopcsv, flattened=False)

    required_macros = set([dbentry.macrotype for dbentry in macrotop])

    for macro in required_macros:
        if macro not in args.macro_names:
            print("WARNING: some of the macros from the {} file are not \
                   supported by given includes:  {}".format(args.infile,
                                                            macro))

    macrolibrary = {}
    for macrotype, include in zip(args.macro_names, args.include):
        includecsv = process_csv_data(include)
        dbentries = convert_to_db(includecsv)
        macrolibrary[macrotype] = dbentries

    coordset = defaultdict(int)
    nameset = defaultdict(int)
    coordtoorig = {}

    timesrepeated = 0
    timesrepeatedname = 0

    with open(args.outfile, 'w') as output:
        for dbentry in macrotop:
            if dbentry.macrotype in macrolibrary:
                for flattenedentry in dbentry.gen_flatten_macro_type(
                        macrolibrary[dbentry.macrotype]):
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

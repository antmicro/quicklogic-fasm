import csv
import argparse
from collections import defaultdict
from fasm_utils.db_entry import DbEntry
from fasm_utils.segbits import Bit


class QLDbEntry(DbEntry):
    def __init__(self, signature: str, coord: tuple, devicecoord=None, macrotype=None):
        super().__init__(signature, [Bit(coord[0], coord[1], True)])
        self.devicecoord = devicecoord
        self.macrotype = macrotype

    @classmethod
    def _fix_signature(cls, signature: str):
        return signature.replace('<', '_').replace('>', '_')


    @classmethod
    def from_csv_line(cls, csvline: list) -> 'QLDbEntry':
        return cls(cls._fix_signature(csvline[0]), (int(csvline[1]), int(csvline[2])))


    @classmethod
    def from_csv_line_unflattened(cls, csvline: list) -> 'QLDbEntry':
        return cls(cls._fix_signature(csvline[2]),
                   (int(csvline[3]), int(csvline[4])),
                   (int(csvline[0]), int(csvline[1])),
                   csvline[5])


    def gen_flatten_macro_type(self, macrodbdata: list):
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
    res = []
    with open(inputfile, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            res.append(row)
    return res


def convert_to_db(csvdata: list, flattened=True):
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
        if not macro in args.macro_names:
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
                for flattenedentry in dbentry.gen_flatten_macro_type(macrolibrary[dbentry.macrotype]):
                    output.write(str(flattenedentry))
                    if not str(flattenedentry).split(' ')[-1] in coordtoorig:
                        coordtoorig[str(flattenedentry).split(' ')[-1]] = flattenedentry
                    else:
                        print("ORIG: {}".format(coordtoorig[str(flattenedentry).split(' ')[-1]]))
                        print("CURR: {}".format(flattenedentry))
                    if str(flattenedentry).split(' ')[-1] in coordset:
                        timesrepeated += 1
                    if str(flattenedentry).split(' ')[0] in nameset:
                        timesrepeatedname += 1
                    coordset[str(flattenedentry).split(' ')[-1]] += 1
                    nameset[str(flattenedentry).split(' ')[0]] += 1

    print("Times the coordinates were repeated:  {}".format(timesrepeated))
    print("Max repetition count: {}".format(max(coordset.values())))
    print("Times the names were repeated:  {}".format(timesrepeatedname))
    print("Max repetition count: {}".format(max(nameset.values())))
    print("Max WL: {}".format(max([int(x.split('_')[0]) for x in coordset.keys()])))
    print("Max BL: {}".format(max([int(x.split('_')[1]) for x in coordset.keys()])))

#!/usr/bin/env python3
import argparse
import os
import errno
from pathlib import Path
from fasm_utils.database import Database
import pkg_resources
from quicklogic_fasm.qlassembler.pp3.ql725a import QL725AAssembler
from quicklogic_fasm.qlassembler.eos_s3.ql732b import QL732BAssembler

def load_quicklogic_database(db_root):
    '''Creates Database object for QuickLogic Fabric.

    Parameters
    ----------
    db_root: str
        A path to directory containing QuickLogic Database files

    Returns
    -------
    Database: Database object for QuickLogic
    '''
    db = Database(db_root)
    for entry in os.scandir(db_root):
        if entry.is_file() and entry.name.endswith(".db"):
            basename = os.path.basename(entry.name)
            db.add_table(basename, entry.path)
    return db


def main():

    parser = argparse.ArgumentParser(
        description="Converts FASM file to the bitstream or the other way around"
    )

    parser.add_argument(
        "infile",
        type=Path,
        help="The input file (FASM, or bitstream when disassembling)"
    )

    parser.add_argument(
        "outfile",
        type=Path,
        help="The output file (bitstream, or FASM when disassembling)"
    )

    parser.add_argument(
        "--dev-type",
        type=str,
        required=True,
        help="Device type (supported: eos-s3, pp3)"
    )

    parser.add_argument(
        "--db-root",
        type=str,
        default=None,
        help="Path to the fasm database (defaults based on device type)"
    )

    parser.add_argument(
        "--default-bitstream",
        type=str,
        default=None,
        help="Path to an external default bitstream to overlay FASM on"
    )

    parser.add_argument(
        "--no-default-bitstream",
        action="store_true",
        help="Do not use any default bitstream (i.e. use all-zero blank)"
    )

    parser.add_argument(
        "-d", "--disassemble",
        action="store_true",
        help="Disasseble bitstream"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Adds some verbose messages during bitstream production"
    )

    args = parser.parse_args()

    db_dir = ""
    if (args.db_root is not None):
        db_dir = args.db_root
    else:
        if (args.dev_type == "ql-pp3"):
            db_dir = Path(pkg_resources.resource_filename('quicklogic_fasm', 'ql725a'))
        elif (args.dev_type == "ql-eos-s3"):
            db_dir = Path(pkg_resources.resource_filename('quicklogic_fasm', 'ql732b'))
        elif (args.dev_type == "ql-pp3e"):
            db_dir = Path(pkg_resources.resource_filename('quicklogic_fasm', 'ql732b')) # FIXME: add proper PP3E support
        else:
            print("Unsuported device type")
            exit(errno.EINVAL)

    if not args.infile.exists:
        print("The input file does not exist")
        exit(errno.ENOENT)

    if not args.outfile.parent.is_dir():
        print("The path to file is not a valid directory")
        exit(errno.ENOTDIR)

    print("Using FASM database: {}".format(db_dir))
    db = load_quicklogic_database(db_dir)

    assembler = None
    if (args.dev_type == "ql-pp3"):
        assembler = QL725AAssembler(db)
    elif (args.dev_type == "ql-eos-s3"):
        assembler = QL732BAssembler(db)
    elif (args.dev_type == "ql-pp3e"):
        assembler = QL732BAssembler(db) # FIXME: add proper PP3E support
    else:
        print("Unsuported device type")
        exit(errno.EINVAL)

    if not args.disassemble:

        # Load default bitstream
        if not args.no_default_bitstream:

            if args.default_bitstream is not None:
                default_bitstream = args.default_bitstream

                if not os.path.isfile(default_bitstream):
                    print("The default bitstream '{}' does not exist".format(
                        default_bitstream
                    ))
                    exit(errno.ENOENT)

            else:
                default_bitstream = os.path.join(
                    db_dir, "default_bitstream.bin")

                if not os.path.isfile(default_bitstream):
                    print("WARNING: No default bistream in the database")
                    default_bitstream = None

            if default_bitstream is not None:
                assembler.read_bitstream(default_bitstream)

        assembler.parse_fasm_filename(str(args.infile))
        assembler.produce_bitstream(str(args.outfile), verbose=args.verbose)
    else:
        assembler.read_bitstream(str(args.infile))
        assembler.disassemble(str(args.outfile), verbose=args.verbose)


if __name__ == "__main__":
    main()

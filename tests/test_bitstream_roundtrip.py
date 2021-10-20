#!/usr/bin/env python3
import os
import sys
import tempfile
import subprocess
import tarfile

import pytest

# =============================================================================


def bitstream_roundtrip(bitstream_file, device):
    """
    Bitstream -> FASM -> bitstream ->FASM round-trip test
    """

    basedir = os.path.dirname(__file__)
    ql_fasm = "qlfasm"

    with tempfile.TemporaryDirectory() as tempdir:

        # Unpack the bitstream
        bitstream = os.path.join(basedir, "assets", bitstream_file)
        tar = tarfile.open(name=bitstream)
        tar.extractall(path=tempdir)

        # Disassemble the bitstream
        bitstream1 = os.path.join(tempdir, os.path.basename(bitstream).replace(".tar.gz", ""))
        fasm1 = os.path.join(tempdir, "fasm1.fasm")
        args = "{} --dev-type {} -d {} {}".format(
            ql_fasm,
            device,
            bitstream1,
            fasm1
        )
        subprocess.check_call(args, shell=True)

        # Assemble the FASM back to bitstream
        bitstream2 = os.path.join(tempdir, "bitstream2.bit")
        args = "{} --dev-type {} --no-default-bitstream {} {}".format(
            ql_fasm,
            device,
            fasm1,
            bitstream2
        )
        subprocess.check_call(args, shell=True)

        # Disassemble to FASM again
        fasm2 = os.path.join(tempdir, "fasm2.fasm")
        args = "{} --dev-type {} -d {} {}".format(
            ql_fasm,
            device,
            bitstream2,
            fasm2
        )
        subprocess.check_call(args, shell=True)

        # Compare both FASM files
        with open(fasm1, "r") as fp:
            fasm_lines1 = sorted(list(fp.readlines()))
        with open(fasm2, "r") as fp:
            fasm_lines2 = sorted(list(fp.readlines()))

        assert len(fasm_lines1) == len(fasm_lines2)
        for l1, l2 in zip(fasm_lines1, fasm_lines2):
            assert l1 == l2

# =============================================================================


def test_bitstream_roundtrip_pp3():
    bitstream_roundtrip("ql3p1k_ql725a.bin.tar.gz", "ql-pp3")

def test_bitstream_roundtrip_eos_s3():
    bitstream_roundtrip("qlal4s3b_ql732b.bin.tar.gz", "ql-eos-s3")

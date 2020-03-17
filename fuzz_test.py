#!/usr/bin/env python3
import argparse
import tempfile
import os
import random
from subprocess import call
import filecmp
from fasm_utils.database import Database


parser = argparse.ArgumentParser(description="qlfasm disassembler fuzz test")
parser.add_argument("-o", "--outdir", help="Where to store generated files")
args = parser.parse_args()


MIN_FEATURES = 1
MAX_FEATURES = 100

DB_FILES_DIR = os.path.join(
    os.path.dirname(__file__),
    'quicklogic_fasm',
    'ql732b')
QLFASM_PATH = os.path.join(
    os.path.dirname(__file__), 'quicklogic_fasm', 'qlfasm.py')

print('\rLoading db...\033[K', end='')

db = Database(DB_FILES_DIR)
db.add_table('macro', os.path.join(DB_FILES_DIR, 'macro.db'))
db.add_table('colclk', os.path.join(DB_FILES_DIR, 'colclk.db'))
db.add_table('testmacro', os.path.join(DB_FILES_DIR, 'testmacro.db'))
features = [f.signature for f in db]
del db

tmpdir = None
tmpdir_obj = None
if not args.outdir:
    tmpdir_obj = tempfile.TemporaryDirectory(prefix='qlfasm-fuzzer-')
    tmpdir = tmpdir_obj.name
else:
    if os.path.isdir(args.outdir):
        tmpdir = args.outdir
        os.makedirs(os.path.join(tmpdir, 'failed'))
        os.makedirs(os.path.join(tmpdir, 'passed'))
    else:
        raise NotADirectoryError


def do_test(id):
    fasm_name = os.path.join(tmpdir, f'{id:06d}.gen.fasm')
    bit_name = os.path.join(tmpdir, f'{id:06d}.gen.fasm.bit')
    disasm_fasm_name = os.path.join(tmpdir, f'{id:06d}.disasm.fasm')
    disasm_bit_name = os.path.join(tmpdir, f'{id:06d}.disasm.fasm.bit')

    num = random.randint(MIN_FEATURES, MAX_FEATURES)
    random_features = [
        features[random.randint(0, len(features) - 1)] for _ in range(num)]
    with open(fasm_name, 'w') as fasm_file:
        print(*random_features, sep='\n', file=fasm_file)

    try:
        call([
            '/usr/bin/env', 'python3',
            QLFASM_PATH, fasm_name, bit_name])
        call([
            '/usr/bin/env', 'python3',
            QLFASM_PATH, '-d', bit_name, disasm_fasm_name])
        call([
            '/usr/bin/env', 'python3',
            QLFASM_PATH, disasm_fasm_name, disasm_bit_name])

        success = filecmp.cmp(bit_name, disasm_bit_name, shallow=False)

        if args.outdir:
            move_to = 'passed' if success else 'failed'
            for name in (
                    fasm_name,
                    bit_name,
                    disasm_fasm_name,
                    disasm_bit_name):
                if os.path.exists(name):
                    os.rename(
                        name,
                        os.path.join(tmpdir, move_to, os.path.basename(name)))
        elif success:
            for name in (
                    fasm_name,
                    bit_name,
                    disasm_fasm_name,
                    disasm_bit_name):
                if os.path.exists(name):
                    os.remove(name)
    except os.error:
        for name in (fasm_name, bit_name, disasm_fasm_name, disasm_bit_name):
            if os.path.exists(name):
                os.remove(name)
        raise

    return success


print('\rRunning...\033[K', end='')

num_failed = 0
num_tests = 0
while True:
    if not do_test(num_tests):
        num_failed += 1
    num_tests += 1
    print(f'\rFailed tests: {num_failed}/{num_tests}\033[K', end='')

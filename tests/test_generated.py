"""The generated files the repository carries, held to their generation.

re/Wings.lst and re/functions.csv (tools/disasm.py), re/songplay.lst (tools/disasm_player.py)
and the contact sheets of ref/sheets/ (tools/ppkc.py --sheets) are versioned, so that a reader
can browse the annotated disassembly and the artwork without running anything.  A committed
file that went stale would mislead that reader: each is made again here, into a directory of
its own and never in place, and compared byte for byte.  None of them needs the Kickstart ROM.
"""
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.without_rom


def generate(out, *command):
    subprocess.run([sys.executable, *command, str(out)], cwd=ROOT, check=True,
                   capture_output=True)


def test_the_listings_are_their_regeneration(tmp_path):
    generate(tmp_path, 'tools/disasm.py', '--out')
    generate(tmp_path, 'tools/disasm_player.py', '--out')
    for name in ('Wings.lst', 'functions.csv', 'songplay.lst'):
        assert (tmp_path / name).read_bytes() == (ROOT / 're' / name).read_bytes(), (
            're/%s is not what tools/disasm.py and tools/disasm_player.py make: regenerate '
            'and commit it' % name)


def test_the_contact_sheets_are_their_regeneration(tmp_path):
    generate(tmp_path, 'tools/ppkc.py', '--sheets')
    made = sorted(os.listdir(tmp_path))
    committed = sorted(name for name in os.listdir(ROOT / 'ref' / 'sheets')
                       if name.endswith('.png'))
    assert made == committed
    for name in made:
        assert (tmp_path / name).read_bytes() == (ROOT / 'ref' / 'sheets' / name).read_bytes(), (
            'ref/sheets/%s is not what tools/ppkc.py --sheets makes: regenerate and commit it'
            % name)

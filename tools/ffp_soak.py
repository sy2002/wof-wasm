"""A long differential run of src/ffp.c against mathffp in the Kickstart ROM.

Outside the test suite, because a million operands per operation take minutes:

    .venv/bin/python tools/ffp_soak.py            1,000,000 per operation
    .venv/bin/python tools/ffp_soak.py 50000      fewer, for a quick look

The operands are shaped like the corpus of tests/test_oracle_ffp.py, from a seed given on
the command line, so a run can be repeated.  Needs tests/libwofcore.dylib
(tools/build.py --native) and original/kick.rom.
"""
import ctypes
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, HERE)

import ffp                                                  # noqa: E402
import test_oracle_ffp as corpus                            # noqa: E402
from oracle import ccr_text                                 # noqa: E402

DYLIB = os.path.join(ROOT, 'tests', 'libwofcore.dylib')


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260920

    lib = ctypes.CDLL(DYLIB)
    lib.wt_ffp.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    lib.wt_ffp.restype = ctypes.c_int
    out = (ctypes.c_uint32 * 4)()
    reference = ffp.Reference()

    print('%d operands per operation, seed %d, mathffp %s' % (count, seed, reference.id_string))
    total_bad = 0
    for index, operation in enumerate(ffp.OPERATIONS):
        rng = random.Random(seed + index)
        started = time.time()
        traps = bad = 0
        for d0, d1 in corpus.random_cases(rng, operation, count):
            lib.wt_ffp(index, d0, d1, out)
            got = (out[0], out[1], out[2], out[3])
            try:
                want = reference.call(operation, d0, d1)
            except ffp.Trap as trap:
                traps += 1
                if got[3] != trap.vector:
                    bad += 1
                    if bad <= 3:
                        print('  %08X %08X: the original traps, the port answers %s' % (d0, d1, got))
                continue
            if got[3] or (got[0], got[1], got[2]) != (want.d0, want.d1, want.ccr):
                bad += 1
                if bad <= 3:
                    print('  %08X %08X: rom d0=%08X d1=%08X %s, port d0=%08X d1=%08X %s trap=%d'
                          % (d0, d1, want.d0, want.d1, want.flags,
                             got[0], got[1], ccr_text(got[2]), got[3]))
        total_bad += bad
        print('%-4s %9d operands, %7d traps, %d differ   (%.0f s)'
              % (operation, count, traps, bad, time.time() - started))
    print('SOAK', 'PASSED' if total_bad == 0 else 'FAILED (%d)' % total_bad)
    return 0 if total_bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

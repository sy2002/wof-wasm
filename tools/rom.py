"""The Kickstart ROM the project uses, and the one check of it that the build, the headless
original, the oracle's reference and the test suite share.

The ROM is not part of the repository: whoever clones it places their own copy at
original/kick.rom.  The build takes the system font and the key conversion from it, the
headless original runs its mathffp and its RawKeyConvert, and the oracle tests hold the
port's floating point against it (SPEC.md sections 5 and 8).

    .venv/bin/python tools/rom.py        prints whether original/kick.rom is the expected image
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'original', 'kick.rom')

SIZE = 262144
MD5 = '82a21c1890cae844b3df741f2762d48d'
SHA1 = '891e9a547772fe0c6c19b610baf8bc4ea7fcb785'

IDENTITY = ('Kickstart 1.3, revision 34.5, the A500 and A2000 image (exec 34.2 of 28 October '
            '1987), 262,144 bytes, MD5 %s, SHA-1 %s' % (MD5, SHA1))
WHERE = ('It is not part of this repository: place your own copy there.  Cloanto\'s Amiga '
         'Forever sells this image, and a real Amiga 500 with Kickstart 1.3 gives it too.')


class RomError(RuntimeError):
    """original/kick.rom is missing or is not the expected image; the message says which and
    where to get the right one."""


def problem(path=PATH):
    """None when the file at `path` is the expected image, otherwise the one message that
    says what is wrong, what is needed and where to get it."""
    if not os.path.isfile(path):
        what = 'original/kick.rom is missing'
    else:
        with open(path, 'rb') as handle:
            data = handle.read()
        if len(data) == SIZE and hashlib.sha1(data).hexdigest() == SHA1:
            return None
        what = ('original/kick.rom is not the expected image (%d bytes, SHA-1 %s)'
                % (len(data), hashlib.sha1(data).hexdigest()))
    return ('%s. The build and the tests need %s. %s' % (what, IDENTITY, WHERE))


def read(path=PATH):
    """The ROM's bytes, or RomError with the message."""
    message = problem(path)
    if message:
        raise RomError(message)
    with open(path, 'rb') as handle:
        return handle.read()


def main():
    message = problem()
    if message:
        print(message)
        return 1
    print('original/kick.rom: %s' % IDENTITY)
    return 0


if __name__ == '__main__':
    sys.exit(main())

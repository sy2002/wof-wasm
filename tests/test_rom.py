"""The Kickstart ROM check (tools/rom.py) that the build, the headless original, the oracle's
reference and the suite share.  Without the right image in original/kick.rom every test but the
ones marked `without_rom` skips with the check's message (tests/conftest.py)."""
import hashlib
import sys

import pytest

import conftest

sys.path.insert(0, str(conftest.ROOT / 'tools'))
import rom  # noqa: E402

IDENTITY = ['Kickstart 1.3', 'revision 34.5', 'A500 and A2000', 'exec 34.2 of 28 October 1987',
            '262,144 bytes', rom.MD5, rom.SHA1, 'original/kick.rom', 'Amiga Forever']


@pytest.mark.without_rom
def test_a_missing_rom_is_named_with_what_is_needed_and_where_to_get_it(tmp_path):
    message = rom.problem(str(tmp_path / 'kick.rom'))
    assert message.startswith('original/kick.rom is missing.'), message
    assert all(part in message for part in IDENTITY), message


@pytest.mark.without_rom
def test_a_wrong_image_is_named_with_its_size_and_checksum(tmp_path):
    wrong = bytes(rom.SIZE)
    (tmp_path / 'kick.rom').write_bytes(wrong)
    message = rom.problem(str(tmp_path / 'kick.rom'))
    assert message.startswith('original/kick.rom is not the expected image (262144 bytes, SHA-1 %s)'
                              % hashlib.sha1(wrong).hexdigest()), message
    assert all(part in message for part in IDENTITY), message
    with pytest.raises(rom.RomError, match='is not the expected image'):
        rom.read(str(tmp_path / 'kick.rom'))


def test_the_placed_rom_is_the_expected_image():
    """Skips with the message, as every test here, when it is not."""
    data = rom.read()
    assert len(data) == rom.SIZE
    assert hashlib.md5(data).hexdigest() == rom.MD5
    assert hashlib.sha1(data).hexdigest() == rom.SHA1

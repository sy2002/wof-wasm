"""dist/wof.html: one file, no network, small enough to hand to someone.

SPEC section 9 accepts M0 when the page opens from file://, shows the test pattern at a
steady emulated 60 Hz, plays a test tone after a key press and makes no network request.
The first and the last of those are decided here; the two in the middle need eyes and ears.
"""
import base64
import re
import subprocess

import build as buildtool

SIZE_LIMIT = 2 * 1024 * 1024

# Anything that would reach outside the file.  data: URLs stay: they are the file itself.
FORBIDDEN = [
    (r'https?:', 'an absolute URL'),
    (r'\bfetch\s*\(', 'a fetch call'),
    (r'\bXMLHttpRequest\b', 'an XMLHttpRequest'),
    (r'\bimportScripts\s*\(', 'importScripts'),
    (r'\bimport\s*\(', 'a dynamic import'),
    (r'^\s*import\s+', 'a static import'),
    (r'<script[^>]*\ssrc\s*=', 'an external script'),
    (r'<link[^>]*href\s*=\s*"(?!data:)', 'an external stylesheet or resource'),
    (r'@import\b', 'a CSS import'),
    (r'\bnew\s+EventSource\b', 'an EventSource'),
    (r'\bnew\s+WebSocket\b', 'a WebSocket'),
    (r'\bnavigator\.sendBeacon\b', 'a beacon'),
    (r'\bWebAssembly\.instantiateStreaming\b', 'streaming instantiation, which file:// refuses'),
    (r'\bSharedArrayBuffer\b', 'a SharedArrayBuffer, which file:// refuses'),
]


def test_page_is_one_file_under_the_size_limit(built):
    size = built.stat().st_size
    assert size < SIZE_LIMIT, '%d bytes, over the %d byte limit' % (size, SIZE_LIMIT)


def test_page_reaches_for_nothing_outside_itself(page):
    for pattern, what in FORBIDDEN:
        found = re.search(pattern, page, re.M)
        assert not found, '%s in dist/wof.html: %r' % (what, found.group(0))


def test_page_carries_the_core_and_the_game_files(page, blob, game_file_names):
    wasm = base64.b64decode(re.sub(
        r'\s+', '', re.search(r'id="wof-wasm" type="text/wof-base64">(.*?)</script>',
                              page, re.S).group(1)))
    assert wasm[:4] == b'\0asm', 'the inlined core is not a WebAssembly module'
    assert blob[:4] == b'WOFS'
    assert int.from_bytes(blob[8:12], 'big') == len(game_file_names)


def test_packed_files_are_the_disk_files(blob, game_file_names):
    """Every entry in the directory names a file on the disk and carries its exact bytes,
    and the executable is not among them: it is not game content, its tables are extracted
    from it at build time (SPEC 3.1, 5)."""
    count = int.from_bytes(blob[8:12], 'big')
    directory = int.from_bytes(blob[12:16], 'big')
    names = []

    for i in range(count):
        entry = blob[directory + i * 40:directory + (i + 1) * 40]
        name = entry[:32].rstrip(b'\0').decode('ascii')
        offset = int.from_bytes(entry[32:36], 'big')
        length = int.from_bytes(entry[36:40], 'big')
        assert offset + length <= len(blob), name
        assert blob[offset:offset + length] == (buildtool.GAME_PATH / name).read_bytes(), name
        names.append(name)

    assert names == game_file_names
    assert 'Wings' not in names


def test_the_inlined_script_parses(page, tmp_path):
    script = re.search(r'<script>(.*?)</script>\s*</body>', page, re.S).group(1)
    path = tmp_path / 'bundle.js'
    path.write_text(script, encoding='utf-8')
    subprocess.run(['node', '--check', str(path)], check=True, capture_output=True)


def test_the_inlined_audio_worklet_parses(page, tmp_path):
    """The worklet is a string in the bundle, so nothing but a test notices if it is broken."""
    script = re.search(r'<script>(.*?)</script>\s*</body>', page, re.S).group(1)
    literal = re.search(r"const WORKLET_SOURCE = ('(?:[^'\\]|\\.)*');", script).group(1)
    source = literal[1:-1].encode('utf-8').decode('unicode_escape')
    assert 'registerProcessor' in source
    path = tmp_path / 'worklet.js'
    path.write_text(source, encoding='utf-8')
    subprocess.run(['node', '--check', str(path)], check=True, capture_output=True)

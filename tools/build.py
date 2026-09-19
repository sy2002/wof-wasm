#!/usr/bin/env python3
"""Build dist/wof.html, the whole port as one self-contained file (SPEC.md section 5).

    .venv/bin/python tools/build.py [--native] [--quiet]

    --native   also build tests/libwofcore.dylib from the same sources with Apple clang

Steps
  1. extract tables from the original executable into src/gen/   (M1, hook below)
  2. pack the game files of SPEC 3.1 into one blob with a directory
  3. compile src/*.c to dist/core.wasm
  4. inline CSS, JavaScript, the wasm and the blob into web/index.html

The output loads from file:// with a double click: nothing is fetched, imported or streamed,
because none of those work from a file URL and because the page must make no network request
at all.  That is also why the JavaScript modules in web/ are concatenated here instead of
being loaded as ES modules: this script is the bundler that SPEC 6.2 allows.
"""
import argparse
import base64
import os
import pathlib
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
WEB = os.path.join(ROOT, 'web')
DIST = os.path.join(ROOT, 'dist')
TESTS = os.path.join(ROOT, 'tests')
GAME = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury')
GAME_PATH = pathlib.Path(GAME)

WASM = os.path.join(DIST, 'core.wasm')
PAGE = os.path.join(DIST, 'wof.html')
DYLIB = os.path.join(TESTS, 'libwofcore.dylib')

# The shell, in dependency order.  They share one scope once concatenated.
MODULES = ['core.js', 'video.js', 'input.js', 'audio.js', 'clock.js', 'overlay.js', 'main.js']

# SPEC 3.1: everything on the disk that is not the executable and not a non-game file.
SKIP_NAMES = {'Wings', 'UFXintro', 'wingt'}

CC_WASM = ['-target', 'wasm32-freestanding', '-std=c11', '-O2', '-Wall', '-Wextra',
           '-nostdlib', '-Wl,--no-entry']
CC_NATIVE = ['-std=c11', '-O2', '-Wall', '-Wextra', '-dynamiclib']

FS_MAGIC = b'WOFS'
FS_VERSION = 1
FS_NAME_MAX = 32
FS_ENTRY = 40
FS_HEADER = 16

SIZE_LIMIT = 2 * 1024 * 1024


def sources():
    return sorted(os.path.join(SRC, f) for f in os.listdir(SRC) if f.endswith('.c'))


# --------------------------------------------------------------- 1. tables (M1 hook)

def extract_tables(log):
    """Hook for SPEC 5 step 1: re/tables.toml -> src/gen/tables.c, tables.h.

    Every constant table, name list, text and tuning value the port needs comes out of the
    original executable here, because hand-written sources hold no game content.  The
    manifest and tools/extract_tables.py arrive with M1; until then there is nothing to
    extract and the core has no generated sources.
    """
    manifest = os.path.join(ROOT, 're', 'tables.toml')
    extractor = os.path.join(ROOT, 'tools', 'extract_tables.py')
    if not os.path.exists(manifest) or not os.path.exists(extractor):
        log('tables    skipped, re/tables.toml and tools/extract_tables.py arrive with M1')
        return
    subprocess.run([sys.executable, extractor], check=True, cwd=ROOT)
    log('tables    extracted into src/gen/')


# ------------------------------------------------------------------ 2. pack the files

def game_files():
    """Paths of the game's files, relative to the disk's Wings_of_Fury directory, which is
    the original's current directory and therefore the namespace its loaders use."""
    out = []
    for folder, dirs, names in os.walk(GAME):
        dirs.sort()
        for name in sorted(names):
            if name in SKIP_NAMES or name.startswith('.') or name.endswith('.info'):
                continue
            out.append(os.path.relpath(os.path.join(folder, name), GAME))
    return sorted(out)


def pack_fs(log):
    names = game_files()
    if not names:
        raise SystemExit('no game files found under %s' % GAME)

    data = bytearray()
    directory = bytearray()
    start = FS_HEADER + FS_ENTRY * len(names)

    for name in names:
        encoded = name.encode('ascii')
        if len(encoded) > FS_NAME_MAX:
            raise SystemExit('file name longer than %d bytes: %s' % (FS_NAME_MAX, name))
        with open(os.path.join(GAME, name), 'rb') as handle:
            body = handle.read()
        while len(data) % 4:
            data.append(0)
        directory += encoded.ljust(FS_NAME_MAX, b'\0')
        directory += (start + len(data)).to_bytes(4, 'big')
        directory += len(body).to_bytes(4, 'big')
        data += body

    blob = bytearray(FS_MAGIC)
    blob += FS_VERSION.to_bytes(4, 'big')
    blob += len(names).to_bytes(4, 'big')
    blob += FS_HEADER.to_bytes(4, 'big')
    blob += directory
    blob += data

    log('files     %d files, %d bytes packed' % (len(names), len(blob)))
    return bytes(blob)


# ---------------------------------------------------------------------- 3. compile

def compile_wasm(log):
    os.makedirs(DIST, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'ziglang', 'cc'] + CC_WASM + ['-o', WASM] + sources(),
                   check=True, cwd=ROOT)
    log('core      %s, %d bytes' % (os.path.relpath(WASM, ROOT), os.path.getsize(WASM)))
    with open(WASM, 'rb') as handle:
        return handle.read()


def compile_native(log):
    """The same sources as a native shared library, for the ctypes tests (SPEC 5)."""
    subprocess.run(['clang'] + CC_NATIVE + ['-o', DYLIB] + sources(), check=True, cwd=ROOT)
    log('native    %s, %d bytes' % (os.path.relpath(DYLIB, ROOT), os.path.getsize(DYLIB)))


# --------------------------------------------------------------------- 4. assemble

IMPORT = re.compile(r"^import\s*\{([^}]*)\}\s*from\s*'\./[\w.]+\.js';\s*$")
EXPORT = re.compile(r'^export\s+(?=(?:async\s+)?(?:function|const|let|class)\s)')


def bundle_js():
    """Concatenate web/*.js into one scope, dropping the ES module syntax that holds them
    together in the sources.  The stripping is deliberately narrow - a whole-line import, a
    leading export keyword - and everything it produces is checked afterwards."""
    parts = []
    wanted = set()

    for name in MODULES:
        with open(os.path.join(WEB, name), encoding='utf-8') as handle:
            text = handle.read()
        if name == 'audio.js':
            text = inline_worklet(text)

        lines = []
        for line in text.split('\n'):
            found = IMPORT.match(line)
            if found:
                wanted.update(part.strip() for part in found.group(1).split(',') if part.strip())
                continue
            lines.append(EXPORT.sub('', line))
        parts.append('/* --- web/%s --- */\n%s' % (name, '\n'.join(lines).strip()))

    code = '\n\n'.join(parts)

    for keyword in ('import', 'export'):
        stray = re.search(r'^\s*%s\b' % keyword, code, re.M)
        if stray:
            raise SystemExit('module syntax left in the bundle: %s' % stray.group(0).strip())
    for name in sorted(wanted):
        if not re.search(r'\b(?:function|const|let|class)\s+%s\b' % re.escape(name), code):
            raise SystemExit('imported name %s is not defined in the bundle' % name)

    return "(function () {\n'use strict';\n\n%s\n\n})();\n" % code


def inline_worklet(text):
    """The AudioWorklet processor is a separate script: it runs in the audio thread and is
    handed to the browser as a Blob URL, so it enters the bundle as a string, not as code."""
    token = "'@@WOF_WORKLET_SOURCE@@'"
    if token not in text:
        raise SystemExit('web/audio.js no longer contains the worklet placeholder')
    with open(os.path.join(WEB, 'worklet.js'), encoding='utf-8') as handle:
        source = handle.read()
    quoted = source.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    return text.replace(token, "'%s'" % quoted)


def base64_block(data, width=120):
    text = base64.b64encode(data).decode('ascii')
    return '\n'.join(text[i:i + width] for i in range(0, len(text), width))


def assemble(wasm, blob, log):
    with open(os.path.join(WEB, 'index.html'), encoding='utf-8') as handle:
        page = handle.read()
    with open(os.path.join(WEB, 'style.css'), encoding='utf-8') as handle:
        css = handle.read()

    page = page.replace('@@WOF_CSS@@', css.strip())
    page = page.replace('@@WOF_JS@@', bundle_js())
    page = page.replace('@@WOF_WASM_BASE64@@', base64_block(wasm))
    page = page.replace('@@WOF_FS_BASE64@@', base64_block(blob))

    left = re.search(r'@@WOF_\w+@@', page)
    if left:
        raise SystemExit('placeholder %s was not filled in' % left.group(0))

    os.makedirs(DIST, exist_ok=True)
    with open(PAGE, 'w', encoding='utf-8') as handle:
        handle.write(page)

    size = os.path.getsize(PAGE)
    log('page      %s, %d bytes (%.2f MiB)' % (os.path.relpath(PAGE, ROOT), size, size / 1048576))
    if size > SIZE_LIMIT:
        raise SystemExit('dist/wof.html is %d bytes, over the %d byte limit' % (size, SIZE_LIMIT))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--native', action='store_true',
                        help='also build tests/libwofcore.dylib with Apple clang')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    log = (lambda message: None) if args.quiet else print

    extract_tables(log)
    blob = pack_fs(log)
    wasm = compile_wasm(log)
    if args.native:
        compile_native(log)
    assemble(wasm, blob, log)


if __name__ == '__main__':
    main()

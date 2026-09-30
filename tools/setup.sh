#!/bin/sh
# Sets a clone of the repository up for building and testing (README.md):
#
#     sh tools/setup.sh
#
# makes .venv with the machine's python3 (or $PYTHON) and installs requirements.txt into it,
# says whether Node and the two browsers the page tests drive are there, checks the Kickstart
# ROM (tools/rom.py) and builds dist/wof.html, dist/core.wasm and tests/libwofcore.dylib.
# Running it again is harmless: an existing .venv is kept and brought to the pinned versions.

cd "$(dirname "$0")/.." || exit 1
PYTHON=${PYTHON:-python3}

echo "== Python environment (.venv, requirements.txt)"
if [ ! -x .venv/bin/python ]; then
    "$PYTHON" -m venv .venv || { echo "could not make .venv with $PYTHON"; exit 1; }
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt \
    || { echo "could not install requirements.txt into .venv"; exit 1; }
.venv/bin/python --version

echo "== Node and the browsers (the WebAssembly tests and the page tests)"
missing=""
if command -v node >/dev/null 2>&1; then
    echo "node $(node --version)"
else
    echo "missing: Node (https://nodejs.org); the WebAssembly and page tests need it"
    missing="yes"
fi
CHROME=${WOF_CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
FIREFOX=${WOF_FIREFOX:-/Applications/Firefox.app/Contents/MacOS/firefox}
if [ -x "$CHROME" ]; then echo "Chrome: $CHROME"; else
    echo "missing: Google Chrome at $CHROME (set WOF_CHROME); tests/test_page.py skips without it"
    missing="yes"; fi
if [ -x "$FIREFOX" ]; then echo "Firefox: $FIREFOX"; else
    echo "missing: Firefox at $FIREFOX (set WOF_FIREFOX); tests/test_firefox.py skips without it"
    missing="yes"; fi

echo "== The Kickstart ROM (original/kick.rom)"
.venv/bin/python tools/rom.py || {
    echo "The build and nearly every test need it. Place it and run tools/setup.sh again."
    exit 1
}

echo "== The build"
.venv/bin/python tools/build.py --native || { echo "the build failed"; exit 1; }

echo "== Done. Play: open dist/wof.html. Verify: README.md, section Build and verify."
if [ -n "$missing" ]; then
    echo "   (Some tests will skip: see 'missing' above.)"
fi

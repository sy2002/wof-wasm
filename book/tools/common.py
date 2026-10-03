"""What the book's generators share: the paths, the manifests, the comparison for --check,
and the port's native core with the game's files loaded.

Nothing here writes a file.  The generators (listings.py, figures.py, webfont.py) each make
their files into a directory they are given, so that --check can make them into a temporary
directory and compare them with the committed ones byte for byte, the way
tests/test_generated.py holds the repository's own generated files.
"""
import filecmp
import os
import pathlib
import sys
import tomllib

BOOK = pathlib.Path(__file__).resolve().parent.parent
ROOT = BOOK.parent
DOCS = BOOK / 'docs'
GENERATED = DOCS / 'generated'
LISTINGS = GENERATED / 'listings'
FIGURES = GENERATED / 'figures'
FONTS = DOCS / 'fonts'
PAGE = ROOT / 'dist' / 'wof.html'
DYLIB = ROOT / 'tests' / 'libwofcore.dylib'

for folder in (ROOT / 'tools', ROOT / 'tests'):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


class Failure(Exception):
    """A generator cannot make what its manifest asks for; the message says what and why."""


def manifest(name):
    """One of the book's manifests, book/<name>.toml."""
    with open(BOOK / name, 'rb') as handle:
        return tomllib.load(handle)


def rel(path):
    """A path as the repository names it."""
    return pathlib.Path(path).resolve().relative_to(ROOT).as_posix()


def files_under(folder):
    """Every file below a directory, as paths relative to it, sorted."""
    folder = pathlib.Path(folder)
    if not folder.exists():
        return []
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()
                  and p.name != '.DS_Store')


def compare(made, committed, only=None):
    """The differences between a fresh generation and the committed files, one line each:
    a file that differs, one that is missing, one that is committed but no longer made.
    With `only`, the names of a generator's own files in a directory it shares with another
    (docs/generated/tables/), the committed files outside them are none of its business."""
    made_files, committed_files = files_under(made), files_under(committed)
    if only is not None:
        committed_files = [name for name in committed_files if name in only]
    problems = []
    for name in sorted(set(made_files) | set(committed_files)):
        if name not in committed_files:
            problems.append('missing  %s' % rel(pathlib.Path(committed) / name))
        elif name not in made_files:
            problems.append('stale    %s (no longer made)' % rel(pathlib.Path(committed) / name))
        elif not filecmp.cmp(pathlib.Path(made) / name, pathlib.Path(committed) / name,
                             shallow=False):
            problems.append('differs  %s' % rel(pathlib.Path(committed) / name))
    return problems


def replace_tree(made, committed, only=None):
    """The committed directory made equal to a fresh generation: files written where they
    differ, removed where they are no longer made, and nothing touched that is equal, so
    that a second run changes no modification time.  With `only`, as for compare(), no
    committed file outside those names is removed."""
    made, committed = pathlib.Path(made), pathlib.Path(committed)
    wanted = set(files_under(made))
    for name in files_under(committed):
        if name not in wanted and (only is None or name in only):
            (committed / name).unlink()
    for name in sorted(wanted):
        source, target = made / name, committed / name
        if target.exists() and filecmp.cmp(source, target, shallow=False):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    for folder in sorted((p for p in committed.rglob('*') if p.is_dir()), reverse=True):
        if not any(folder.iterdir()):
            folder.rmdir()


def need_build():
    """The built repository the figures and the font are made from: the page with the
    game's files in it and the native library of the same sources."""
    missing = [rel(p) for p in (PAGE, DYLIB) if not p.exists()]
    if missing:
        raise Failure('%s missing: run .venv/bin/python tools/build.py --native first'
                      % ' and '.join(missing))


def port_build():
    """tests/conftest.py imports the port's tools/build.py as `build`; this directory's own
    build.py, first on the path of a script run from here, must not stand in for it."""
    import importlib.util
    path = ROOT / 'tools' / 'build.py'
    loaded = sys.modules.get('build')
    if loaded is not None and pathlib.Path(getattr(loaded, '__file__', '')) == path:
        return
    spec = importlib.util.spec_from_file_location('build', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['build'] = module
    spec.loader.exec_module(module)


_core = None


def core():
    """The port's core as the tests reach it (tests/conftest.py, class Ported), on the file
    system packed into dist/wof.html, so that a figure shows exactly the bytes the page
    plays.  One process holds one copy of the core's statics: every caller gets the same
    object and resets it as it needs."""
    global _core
    if _core is None:
        need_build()
        port_build()
        import conftest
        page = PAGE.read_text(encoding='utf-8')
        _core = conftest.Ported(conftest.payload(page, 'wof-fs'))
    return _core

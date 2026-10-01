"""MkDocs hook: the playable game in the site.

The game is the repository's own page, dist/wof.html, built from the sources and committed at
every merge.  It is never committed a second time under book/: every build adds it to the
site's files as play/wof.html, beside the page that embeds it (docs/play.md), so that MkDocs
copies it into the site unchanged, a link to it is checked like any other, and the book always
plays the repository's game.  mkdocs serve watches the file and rebuilds when it changes.
"""
import os

from mkdocs.exceptions import PluginError
from mkdocs.structure.files import File

TARGET = 'play/wof.html'


def page(config):
    return os.path.normpath(os.path.join(os.path.dirname(config.config_file_path),
                                         '..', 'dist', 'wof.html'))


def on_files(files, config, **kwargs):
    source = page(config)
    if not os.path.isfile(source):
        raise PluginError('the game, %s, is missing: it is the repository\'s committed page '
                          '(git checkout dist/wof.html, or tools/build.py)' % source)
    files.append(File.generated(config, TARGET, abs_src_path=source))
    return files


def on_serve(server, config, builder, **kwargs):
    server.watch(page(config))
    return server

"""MkDocs hook: links into the repository.

A page links to a file of the repository with the book's own scheme, `repo:`, written as
[`re/notes/keys.md`](repo:re/notes/keys.md#the-commands), [`src/portkeys.c`](repo:src/portkeys.c)
or [`re/notes/`](repo:re/notes/); `repo:` alone is the repository itself.  This hook rewrites
every such target to the repository on GitHub: <repo_url>/blob/<branch>/<path> for a file,
<repo_url>/tree/<branch>/<path> for a directory, the anchor kept, where repo_url is mkdocs.yml's
and the branch is extra.repo_branch.  It works on the page's HTML after the Markdown is rendered,
so a link in a sidebar, a caption or a table is rewritten like any other, and no other link is
touched.  An underscore in a link's target, a repo: one or any other, is written %5F, because
tools/mdcheck.py reads a bare one as emphasis; the hook decodes it in every link.  A target
that does not exist is a warning, which fails a strict build; book/tools/links.py checks the
anchors as well, at every build of book/tools/build.py.
"""
import logging
import os
import re
from urllib.parse import unquote

log = logging.getLogger('mkdocs.hooks.links')

HREF = re.compile(r'href="repo:([^"#]*)(#[^"]*)?"')
UNDERSCORE = re.compile(r'href="[^"]*%5[Ff][^"]*"')


def repository(config):
    return os.path.normpath(os.path.join(os.path.dirname(config.config_file_path), '..'))


def on_page_content(html, page, config, **kwargs):
    root = repository(config)
    base = config.repo_url.rstrip('/')
    branch = config.extra.get('repo_branch', 'main')

    def rewrite(m):
        path, anchor = unquote(m.group(1)), unquote(m.group(2) or '')
        if not path:
            return 'href="%s%s"' % (base, anchor)
        full = os.path.join(root, path)
        if not os.path.exists(full):
            log.warning('%s links to repo:%s, which is not in the repository', page.file.src_uri, path)
        kind = 'tree' if path.endswith('/') or os.path.isdir(full) else 'blob'
        return 'href="%s/%s/%s/%s%s"' % (base, kind, branch, path.rstrip('/'), anchor)

    html = HREF.sub(rewrite, html)
    # %5F is an underscore (RFC 3986 counts it unreserved); every link of the pages writes it
    # so for tools/mdcheck.py, and the site carries it plain.
    return UNDERSCORE.sub(lambda m: m.group(0).replace('%5F', '_').replace('%5f', '_'), html)

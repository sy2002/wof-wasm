"""MkDocs hook: a Pygments lexer for the lines of re/Wings.lst, the fence language `wingslst`.

Pygments has no lexer for this listing's format (the address, the instruction's bytes, the
68000 mnemonic and its operands, the generated comment), so the book brings its own and
registers it before any page is highlighted: a fence written ```wingslst highlights the
address, dims the bytes, and tells the mnemonics, registers, numbers, labels and comments
apart.  The colours are stylesheets/book.css's.
"""
from pygments import lexers
from pygments.lexer import RegexLexer, bygroups
from pygments.token import Comment, Keyword, Name, Number, Punctuation, Text, Whitespace

__all__ = ['WingsListingLexer']

REGISTER = r'\b(?:[ad][0-7]|sp|pc|sr|ccr|usp)\b'


class WingsListingLexer(RegexLexer):
    name = 'Wings listing'
    aliases = ['wingslst']
    filenames = []

    tokens = {
        'root': [
            (r'^;.*\n?', Comment.Single),                         # a header or a note line
            (r'^([A-Za-z_]\w*)(:)(\s*\n?)', bygroups(Name.Label, Punctuation, Whitespace)),
            (r'^([0-9a-f]{6})(\s+)([0-9a-f]+)(\s+)',
             bygroups(Name.Constant, Whitespace, Comment.Special, Whitespace), 'instruction'),
            (r'.+\n?', Text),
            (r'\n', Whitespace),
        ],
        'instruction': [
            (r'([a-z]+(?:\.[bwls])?)', Keyword, 'operands'),
            (r'\n', Whitespace, '#pop'),
            (r'.', Text),
        ],
        'operands': [
            (r'\n', Whitespace, '#pop:2'),
            (r'([ \t]+)(;.*)', bygroups(Whitespace, Comment.Single)),
            (r'[ \t]+', Whitespace),
            (REGISTER, Name.Builtin),
            (r'\.[bwl]\b', Name.Builtin),               # the size of an index register
            (r'#?-?\$[0-9a-f]+(?:\.[lw])?', Number.Hex),
            (r'#-?\d+', Number.Integer),
            (r'[A-Za-z_]\w*', Name),
            (r'[(),+\-/*]', Punctuation),
            (r'.', Text),
        ],
    }


# Pygments finds a lexer by its alias in this table and imports the module named there, which
# is this hook's own, already loaded by MkDocs under its name.
lexers.LEXERS['WingsListingLexer'] = (__name__, WingsListingLexer.name,
                                      tuple(WingsListingLexer.aliases), (), ())
lexers._lexer_cache[WingsListingLexer.name] = WingsListingLexer

#!/usr/bin/env python3
"""Recursive-descent disassembler for the original `Wings` executable.

Generates   re/Wings.lst        annotated listing (code, strings, data)
            re/functions.csv    function inventory

Both are versioned and held to this regeneration by tests/test_generated.py, which writes them
into a directory of its own with --out DIR.

Reads (optional, hand-maintained; regenerate after editing them)
            re/names.txt        "<hex addr> <name> [; comment]"   code labels and data/global names
            re/libbases.txt     "<hex addr of base variable> <library>"   for naming OS calls

Addresses are those of tools/hunk.py's fixed load layout:
    CODE 0x010000   DATA 0x023000   BSS 0x028000      A4 (small-data base) = 0x02AFFE

How code is found
  1. control flow from: program entry, every relocated pointer into CODE (far-call table, handler
     tables), every LINK A5 prologue
  2. `jsr d16(a4)` is resolved through the far-call table at the start of DATA
  3. Aztec C `switch` dispatchers are resolved through their word-offset tables
  4. addresses taken with pc-relative lea/pea that are not strings are tried as code
  5. whatever is still unclaimed is decoded speculatively and accepted only if it is a clean
     instruction stream; such blocks are marked "(found by gap sweep)" in the listing
"""
import argparse
import bisect
import collections
import csv
import os
import re
import struct

from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000

import hunk

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
EXE = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'Wings')
A4 = 0x02AFFE
STR_MAX = 48                      # strings are truncated to this many characters in comments
TERMINATORS = (0x4E75, 0x4E73, 0x4E77, 0x4E72, 0x4AFC)


# ----------------------------------------------------------------------------- inputs
def load_names(path):
    names, comments = {}, {}
    if os.path.exists(path):
        for line in open(path):
            line = line.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            body, _, com = line.partition(';')
            parts = body.split()
            if len(parts) >= 2:
                a = int(parts[0], 16)
                names[a] = parts[1]
                if com.strip():
                    comments[a] = com.strip()
    return names, comments


def load_fd(fd_dir):
    libs = {}
    for fn in os.listdir(fd_dir):
        if not fn.endswith('_lib.fd'):
            continue
        bias, table = 30, {}
        for line in open(os.path.join(fd_dir, fn), errors='replace'):
            line = line.strip()
            if line.startswith('##bias'):
                bias = int(line.split()[1])
            elif line.startswith('##') or line.startswith('*') or not line:
                continue
            else:
                table[bias] = line.split('(')[0]
                bias += 6
        libs[fn[:-7]] = table
    return libs


# ----------------------------------------------------------------------------- image
class Image:
    def __init__(self, exe=EXE):
        self.segs = hunk.load(exe)
        self.lo = self.segs[0]['base']
        self.hi = max(s['base'] + len(s['data']) for s in self.segs)
        self.mem = bytearray(self.hi)
        for s in self.segs:
            self.mem[s['base']:s['base'] + len(s['data'])] = s['data']
        self.code_lo, self.code_hi = self.segs[0]['base'], self.segs[0]['base'] + len(self.segs[0]['data'])
        self.data_lo, self.data_hi = self.segs[1]['base'], self.segs[1]['base'] + len(self.segs[1]['data'])
        self.relocs = {}                                   # address of a relocated long -> its value
        for s in self.segs:
            for _target, offs in s['relocs']:
                for o in offs:
                    self.relocs[s['base'] + o] = self.u32(s['base'] + o)

    def u16(self, a):
        return struct.unpack('>H', self.mem[a:a + 2])[0]

    def s16(self, a):
        return struct.unpack('>h', self.mem[a:a + 2])[0]

    def u32(self, a):
        return struct.unpack('>L', self.mem[a:a + 4])[0]

    def in_code(self, a):
        return self.code_lo <= a < self.code_hi

    def cstring(self, a, min_len=1):
        """Printable NUL-terminated string at a, else None."""
        if not (self.lo <= a < self.hi):
            return None
        end = self.mem.find(b'\0', a, min(a + 4096, self.hi))
        if end < 0 or end - a < min_len:
            return None
        raw = self.mem[a:end]
        if all(32 <= c < 127 or c in (9, 10, 13) for c in raw):
            return raw.decode('latin1')
        return None

    def far_target(self, d16):
        a = A4 + d16
        if self.data_lo <= a < self.data_hi - 5 and self.u16(a) == 0x4EF9:
            return self.u32(a + 2)
        return None


# ----------------------------------------------------------------------------- traversal
class Analysis:
    def __init__(self, img):
        self.img = img
        self.md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
        self.insn = {}                                     # addr -> (size, mnemonic, op_str)
        self.funcs = set()
        self.labels = set()
        self.calls = collections.defaultdict(set)          # call site -> targets
        self.switches = {}                                 # table addr -> (entries, base)
        self.pcrefs = set()                                # pc-relative data references into CODE
        self.strings = {}                                  # addr -> python string (referenced literals)
        self.swept = set()                                 # block starts found by the gap sweep
        self.text = {}                                     # addr -> length of unreferenced text runs
        self.work = []
        self.re_pc = re.compile(r'\$([0-9a-f]+)\(pc\)')

    def decode(self, a):
        got = list(self.md.disasm(bytes(self.img.mem[a:a + 12]), a, count=1))
        return got[0] if got else None

    def seed(self, a, is_func):
        if self.img.in_code(a) and not (a & 1):
            (self.funcs if is_func else self.labels).add(a)
            self.work.append(a)

    def run(self):
        img = self.img
        while self.work:
            pc = self.work.pop()
            while img.in_code(pc) and pc not in self.insn:
                ins = self.decode(pc)
                if ins is None:
                    break
                self.insn[pc] = (ins.size, ins.mnemonic, ins.op_str)
                w = img.u16(pc)
                stop = False
                if w in TERMINATORS:
                    stop = True
                elif w & 0xF000 == 0x6000:                                # Bcc / BRA / BSR
                    cond, d = (w >> 8) & 0xF, w & 0xFF
                    tgt = pc + 2 + (img.s16(pc + 2) if d == 0 else (d - 256 if d & 0x80 else d))
                    if cond == 1:
                        self.seed(tgt, True)
                        self.calls[pc].add(tgt)
                    else:
                        self.seed(tgt, False)
                        stop = cond == 0
                elif w & 0xF0F8 == 0x50C8:                                # DBcc
                    self.seed(pc + 2 + img.s16(pc + 2), False)
                elif w == 0x4EFB and img.u16(pc - 4) == 0x303B:           # Aztec C switch dispatch
                    # cmp.l #N,d0 / bcc default / asl.l #1,d0 / move.w tbl(pc,d0.w),d0 / jmp base(pc,d0.w)
                    s8 = lambda v: v - 256 if v & 0x80 else v
                    base = pc + 2 + s8(img.u16(pc + 2) & 0xFF)
                    tbl = pc - 2 + s8(img.u16(pc - 2) & 0xFF)
                    n = None
                    for back in range(6, 24, 2):
                        if img.u16(pc - 4 - back) == 0xB0BC:
                            n = img.u32(pc - 2 - back)
                            break
                    if n is None or n > 512:
                        n = max(0, (pc - 4 - tbl) // 2)
                    self.switches[tbl] = (n, base)
                    for i in range(n):
                        self.seed(base + img.s16(tbl + 2 * i), False)
                    stop = True
                elif w & 0xFF80 == 0x4E80:                                # JSR / JMP
                    is_jmp, ea, tgt = bool(w & 0x40), w & 0x3F, None
                    if ea == 0x39:
                        tgt = img.u32(pc + 2)
                    elif ea == 0x38:
                        tgt = img.s16(pc + 2) & 0xFFFFFFFF
                    elif ea == 0x3A:
                        tgt = pc + 2 + img.s16(pc + 2)
                    elif ea == 0x2C:
                        tgt = img.far_target(img.s16(pc + 2))
                    if tgt is not None and img.in_code(tgt):
                        local = is_jmp and ea != 0x2C and abs(tgt - pc) < 0x400 and tgt not in self.funcs
                        self.seed(tgt, not local)
                        self.calls[pc].add(tgt)
                    stop = is_jmp
                else:
                    for m in self.re_pc.finditer(ins.op_str):             # lea/pea/move x(pc)
                        self.pcrefs.add(int(m.group(1), 16))
                if stop:
                    break
                pc += ins.size

    def covered(self):
        cov = bytearray(self.img.code_hi)
        for a, (size, _, _) in self.insn.items():
            cov[a:a + size] = b'\1' * size
        for a, s in self.strings.items():
            cov[a:a + len(s) + 1] = b'\2' * (len(s) + 1)
        for tbl, (n, _) in self.switches.items():
            cov[tbl:tbl + 2 * n] = b'\3' * (2 * n)
        for a, n in self.text.items():
            cov[a:a + n] = b'\2' * n
        return cov

    @staticmethod
    def _printable(c):
        return 32 <= c < 127 or c in (0, 9, 10, 13)

    def text_run(self, a, cov):
        """Length of the run of printable bytes starting at a (unclaimed bytes only)."""
        b = a
        while b < self.img.code_hi and not cov[b] and self._printable(self.img.mem[b]):
            b += 1
        n = b - a
        letters = sum(1 for c in self.img.mem[a:b] if c == 32 or 65 <= c <= 90 or 97 <= c <= 122)
        return n if n >= 12 and letters >= 0.7 * n else 0

    def looks_like_code(self, a, end, cov):
        """Clean instruction stream from a that reaches a terminator or known code before `end`."""
        start = a
        ok = self._looks_like_code(a, end, cov)
        if ok:
            blob = self.img.mem[start:min(start + 64, end)]
            if len(blob) >= 8 and sum(map(self._printable, blob)) >= 0.95 * len(blob):
                return False                                # prose decodes as valid 68k
        return ok

    def _looks_like_code(self, a, end, cov):
        n = 0
        while a < end:
            if a in self.insn:
                return n >= 1
            if cov[a]:
                return False
            w = self.img.u16(a)
            ins = self.decode(a)
            if ins is None or w == 0x0000 or a + ins.size > end:
                return False
            n += 1
            if w in TERMINATORS or w & 0xFFC0 == 0x4EC0 or w & 0xFF00 == 0x6000:
                return True
            a += ins.size
        return a in self.insn and n >= 1

    def analyse(self):
        img = self.img
        self.seed(img.code_lo, True)
        a = img.data_lo                                    # far-call table: certainly code
        while img.u16(a) == 0x4EF9 and (a + 2) in img.relocs:
            self.seed(img.u32(a + 2), True)
            a += 6
        far_end = a
        for a in range(img.code_lo, img.code_hi - 3, 2):
            if img.u16(a) == 0x4E55:
                self.seed(a, True)
        self.run()

        # Other pointers into CODE are string literals (Aztec C keeps them in the code hunk),
        # data tables, or routines referenced by address. Classify each one.
        refs = set(self.pcrefs) | {v for where, v in img.relocs.items()
                                   if img.in_code(v) and not (img.data_lo <= where < far_end)}
        changed = True
        while changed:
            changed = False
            cov = self.covered()
            for r in sorted(refs):
                if not img.in_code(r) or cov[r] or r in self.strings:
                    continue
                s = img.cstring(r)
                if s is not None:
                    self.strings[r] = s
                    changed = True
                elif not (r & 1) and self.looks_like_code(r, img.code_hi, cov):
                    self.seed(r, True)
                    self.run()
                    refs |= self.pcrefs
                    changed = True
                if changed:
                    break

        # gap sweep
        while True:
            cov = self.covered()
            found = False
            a = img.code_lo
            while a < img.code_hi:
                if cov[a]:
                    a += 1
                    continue
                if a & 1:
                    tr = self.text_run(a, cov)
                    if tr:
                        self.text[a] = tr
                        found = True
                        break
                    a += 1
                    continue
                end = a
                while end < img.code_hi and not cov[end]:
                    end += 1
                tr = self.text_run(a, cov)
                if tr:
                    self.text[a] = tr
                    found = True
                    break
                if self.looks_like_code(a, end + 12, cov) and img.cstring(a, 6) is None:
                    prev_is_term = any(img.u16(a - k) in TERMINATORS and (a - k) in self.insn for k in (2,))
                    self.seed(a, prev_is_term or img.u16(a) == 0x4E75)
                    self.swept.add(a)
                    self.run()
                    found = True
                    break
                a = end
            if not found:
                break
        return self


# ----------------------------------------------------------------------------- output
def main(argv=None):
    parser = argparse.ArgumentParser(description='Regenerate the listing and the function inventory.')
    parser.add_argument('--out', default=os.path.join(ROOT, 're'),
                        help='the directory for Wings.lst and functions.csv (default re/); the '
                             'status column is always taken from re/functions.csv')
    args = parser.parse_args(argv)
    img = Image()
    names, name_comments = load_names(os.path.join(ROOT, 're', 'names.txt'))
    libbases, _ = load_names(os.path.join(ROOT, 're', 'libbases.txt'))
    fd = load_fd(os.path.join(HERE, 'fd'))
    an = Analysis(img).analyse()
    insn, funcs, labels = an.insn, an.funcs, an.labels
    cov = an.covered()

    case_of = {}
    for tbl, (n, base) in an.switches.items():
        for i in range(n):
            case_of[tbl + 2 * i] = (i, base + img.s16(tbl + 2 * i))

    def name_of(a):
        if a in names:
            return names[a]
        if a in funcs:
            return 'sub_%06x' % a
        if a in labels and a in insn:
            return 'loc_%06x' % a
        if a in an.strings:
            return 'str_%06x' % a
        if img.data_lo <= a < img.hi:
            return 'g_%06x' % a
        return '$%06x' % a

    flist = sorted(funcs)
    fend = {f: (flist[i + 1] if i + 1 < len(flist) else img.code_hi) for i, f in enumerate(flist)}

    def func_of(a):
        i = bisect.bisect_right(flist, a) - 1
        return flist[i] if i >= 0 else None

    callers, callees = collections.defaultdict(set), collections.defaultdict(set)
    for site, tgts in an.calls.items():
        f = func_of(site)
        for t in tgts:
            if t in funcs and f is not None:
                callers[t].add(f)
                callees[f].add(t)

    slot_of = {}
    a = img.data_lo
    while img.u16(a) == 0x4EF9 and (a + 2) in img.relocs:
        slot_of.setdefault(img.u32(a + 2), a - A4)
        a += 6
    far_table_end = a

    re_a4 = re.compile(r'(-?)\$([0-9a-f]+)\(a4\)')
    re_a5 = re.compile(r'(?<!-)\$([0-9a-f]+)\(a5\)')
    re_pc = re.compile(r'\$([0-9a-f]+)\(pc\)')
    finfo = collections.defaultdict(lambda: dict(os=[], strings=[], globals=set(), args=set()))
    out = []
    emit = out.append
    emit('; Wings of Fury (Amiga) main executable - generated by tools/disasm.py, do not edit by hand.')
    emit('; Names come from re/names.txt, library bases from re/libbases.txt; regenerate after editing.')
    emit('; CODE %06x-%06x  DATA %06x-%06x  A4=%06x  far-call table %06x-%06x' % (
        img.code_lo, img.code_hi, img.data_lo, img.data_hi, A4, img.data_lo, far_table_end))

    def short(s):
        s = s.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return '"%s%s"' % (s[:STR_MAX], '...' if len(s) > STR_MAX else '')

    def dump_data(a, b, guess_strings):
        while a < b:
            if a in case_of:
                emit('%06x          dc.w    $%04x                        ; switch case %d -> %s' % (
                    a, img.u16(a), case_of[a][0], name_of(case_of[a][1])))
                a += 2
                continue
            if a in an.text:
                n = an.text[a]
                head = bytes(img.mem[a:a + n]).split(b'\0')[0].decode('latin1')
                emit('%06x          dc.b    <text, %d bytes> %s' % (a, n, short(head)))
                a += n
                continue
            s = an.strings.get(a)
            if s is None and guess_strings:
                s = img.cstring(a, 4)
            if s is not None and a + len(s) + 1 <= b:
                emit('%06x          dc.b    %s,0' % (a, short(s)))
                a += len(s) + 1
                continue
            if a in img.relocs and a + 4 <= b:
                emit('%06x          dc.l    %s' % (a, name_of(img.relocs[a])))
                a += 4
                continue
            if a + 2 <= b and not a & 1:
                emit('%06x          dc.w    $%04x' % (a, img.u16(a)))
                a += 2
            else:
                emit('%06x          dc.b    $%02x' % (a, img.mem[a]))
                a += 1

    a, cur_a6, cur_func = img.code_lo, None, None
    while a < img.code_hi:
        if a in funcs and a in insn:
            cur_func, cur_a6 = a, None
            kind = 'C' if img.u16(a) == 0x4E55 else 'asm'
            emit('')
            emit('; ' + '=' * 100)
            hdr = '; %s   [%s]' % (name_of(a), kind)
            if kind == 'C':
                hdr += '  frame=%d' % -img.s16(a + 2)
            if a in slot_of:
                hdr += '  far-call slot %d(a4)' % slot_of[a]
            if a in an.swept:
                hdr += '  (found by gap sweep)'
            emit(hdr)
            if a in name_comments:
                emit(';   ' + name_comments[a])
            if callers[a]:
                emit(';   callers: ' + ', '.join(name_of(c) for c in sorted(callers[a])))
            emit('%s:' % name_of(a))
        elif a in labels and a in insn:
            emit('%s:%s' % (name_of(a), '        ; (found by gap sweep)' if a in an.swept else ''))
        if a in insn:
            size, mn, ops = insn[a]
            notes, w = [], img.u16(a)
            for m in re_a4.finditer(ops):
                d = int(m.group(2), 16) * (-1 if m.group(1) else 1)
                if w & 0xFF80 == 0x4E80 and (w & 0x3F) == 0x2C:
                    ft = img.far_target(d)
                    notes.append('-> ' + (name_of(ft) if ft else '?'))
                else:
                    notes.append(name_of(A4 + d))
                    finfo[cur_func]['globals'].add(A4 + d)
                    if mn.startswith('movea') and ops.endswith(', a6'):
                        cur_a6 = A4 + d
            if ops.endswith(', a6') and ops.startswith('$4.w'):
                cur_a6 = 'exec'
            for m in re_a5.finditer(ops):
                finfo[cur_func]['args'].add(int(m.group(1), 16))
            for m in re_pc.finditer(ops):
                tgt = int(m.group(1), 16)
                if tgt in an.strings:
                    notes.append(short(an.strings[tgt]))
                    finfo[cur_func]['strings'].append(an.strings[tgt])
                elif tgt in funcs or tgt in names:
                    notes.append(name_of(tgt))
            for ra in range(a + 2, a + size - 3, 2):
                if ra in img.relocs:
                    v = img.relocs[ra]
                    s = an.strings.get(v) or (img.cstring(v, 3) if v >= img.data_lo else None)
                    notes.append(short(s) if s is not None else name_of(v))
                    if s is not None:
                        finfo[cur_func]['strings'].append(s)
            if w in (0x4EAE, 0x4EEE):                             # jsr/jmp d16(a6): OS call
                lvo = -img.s16(a + 2)
                lib = 'exec' if cur_a6 == 'exec' else libbases.get(cur_a6)
                fn = fd.get(lib, {}).get(lvo) if lib else None
                if fn:
                    label = '%s.%s' % (lib, fn)
                else:
                    label = '%s LVO -%d' % (lib or ('base@' + name_of(cur_a6) if cur_a6 else 'a6=?'), lvo)
                notes.append(label)
                finfo[cur_func]['os'].append(label)
            line = '%06x  %-20s %-10s %s' % (a, img.mem[a:a + size].hex()[:20], mn, ops)
            if notes:
                line = '%-78s ; %s' % (line, ' | '.join(dict.fromkeys(notes)))
            emit(line)
            a += size
        else:
            b = a
            while b < img.code_hi and b not in insn:
                b += 1
            dump_data(a, b, guess_strings=False)
            a = b

    emit('')
    emit('; ' + '=' * 100)
    emit('; DATA hunk (initialised part %06x-%06x, the rest up to %06x is zero-filled BSS)' % (
        img.data_lo, img.data_lo + 0x3C60, img.data_hi))
    a = img.data_lo
    while a < far_table_end:
        emit('%06x          jmp     %-28s ; far-call slot %d(a4)' % (a, name_of(img.u32(a + 2)), a - A4))
        a += 6
    init_end = img.data_lo + 0x3C60
    marks = sorted(x for x in names if far_table_end <= x < img.data_hi)
    bounds = [far_table_end] + marks + [init_end]
    for i in range(len(bounds) - 1):
        if bounds[i] in names:
            emit('%s:' % names[bounds[i]])
        if bounds[i] < init_end:
            dump_data(bounds[i], min(bounds[i + 1], init_end), guess_strings=True)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, 'Wings.lst'), 'w') as f:
        f.write('\n'.join(out) + '\n')

    status_path = os.path.join(ROOT, 're', 'functions.csv')
    csv_path = os.path.join(args.out, 'functions.csv')
    old_status = {}                                               # hand-edited column survives regeneration
    if os.path.exists(status_path):
        for r in csv.DictReader(open(status_path, newline='')):
            old_status[r['addr']] = r.get('status') or 'todo'

    rows = []
    for fa in flist:
        if fa not in insn:
            continue
        kind = 'C' if img.u16(fa) == 0x4E55 else 'asm'
        info = finfo[fa]
        rows.append(dict(
            addr='%06x' % fa, name=name_of(fa), kind=kind, span=fend[fa] - fa,
            frame=(-img.s16(fa + 2) if kind == 'C' else ''),
            a5_args=' '.join(str(x) for x in sorted(info['args'])) if kind == 'C' else '',
            far_slot=slot_of.get(fa, ''), callers=len(callers[fa]),
            calls=' '.join(name_of(c) for c in sorted(callees[fa])),
            os_calls=' '.join(dict.fromkeys(info['os'])),
            globals=len(info['globals']),
            strings=' | '.join(short(s) for s in dict.fromkeys(info['strings']))[:200],
            status=old_status.get('%06x' % fa, 'todo')))
    with open(csv_path, 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    n_code = sum(1 for x in cov[img.code_lo:img.code_hi] if x == 1)
    n_str = sum(1 for x in cov[img.code_lo:img.code_hi] if x == 2)
    n_tbl = sum(1 for x in cov[img.code_lo:img.code_hi] if x == 3)
    total = img.code_hi - img.code_lo
    print('functions: %d (C: %d, asm: %d), %d found by gap sweep' % (
        len(rows), sum(r['kind'] == 'C' for r in rows), sum(r['kind'] == 'asm' for r in rows), len(an.swept)))
    print('CODE hunk %d bytes: code %d (%.1f%%), referenced strings %d, switch tables %d, unexplained %d' % (
        total, n_code, 100.0 * n_code / total, n_str, n_tbl, total - n_code - n_str - n_tbl))
    print('listing lines: %d' % len(out))


if __name__ == '__main__':
    main()

"""The operating system as the headless original sees it: one Python method per library call.

A method is named os_<library>_<Function>, takes its arguments from the registers the
library's fd file names, and returns the value for D0, or None when the call has no result.
The machine in headless.py parks the emulated program, calls the method and returns to the
caller.  A call without a method here ends the run with an error that names it, so that
nothing the game asks for is ever answered by accident.

Nothing here knows anything about the game except three habits of its code, each noted where
it matters: the 4 GB allocation that flushes memory, the two fake segments of the music
player, and the register CIA-A PRA read through a mirror address.
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAME_DIR = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury')

ADF_IMAGE = os.path.join(ROOT, 'original', 'wof.adf')
DISK_DIR = 'Wings_of_Fury'                # where on the disk the game's own directory is

MODE_NEWFILE = 1006
ERROR_OBJECT_NOT_FOUND = 205
ERROR_OBJECT_WRONG_TYPE = 212
ERROR_NO_MORE_ENTRIES = 232
IND_ADDHANDLER, IND_REMHANDLER = 9, 10
DOS_TRUE = 0xFFFFFFFF

BLOCK = 512
ROOT_BLOCK = 880                          # of a double-density disk
HASH_SIZE = BLOCK // 4 - 56               # 72 chains per directory


def name_hash(name):
    """The file system's name hash, which decides a directory entry's chain.  An old file
    system disk is not international, so upper case is plain ASCII."""
    value = len(name)
    for letter in name:
        value = (value * 13 + ord(letter.upper() if 'a' <= letter <= 'z' else letter)) & 0x7FF
    return value % HASH_SIZE


def adf_order(parts, image=ADF_IMAGE, _cache={}):
    """One directory of the original disk image, as [(chain, name)] in the order the file
    system hands the entries out: chain 0 upward, and inside a chain from its head, which is
    the order ExNext walks.  Returns None when the image is not there."""
    key = (image, tuple(p.lower() for p in parts))
    if key in _cache:
        return _cache[key]
    if not os.path.isfile(image):
        return None
    with open(image, 'rb') as f:
        disk = f.read()

    def block(number):
        return disk[number * BLOCK:(number + 1) * BLOCK]

    def entries(header):
        out = []
        for chain in range(HASH_SIZE):
            at = struct.unpack_from('>L', header, 24 + 4 * chain)[0]
            while at:
                record = block(at)
                length = record[BLOCK - 80]
                out.append((chain, at, record[BLOCK - 79:BLOCK - 79 + length].decode('latin1')))
                at = struct.unpack_from('>L', record, BLOCK - 16)[0]
        return out

    here = block(ROOT_BLOCK)
    for part in [DISK_DIR] + list(parts):
        found = next((at for _, at, name in entries(here) if name.lower() == part.lower()), None)
        if found is None:
            _cache[key] = None
            return None
        here = block(found)
    _cache[key] = [(chain, name) for chain, _, name in entries(here)]
    return _cache[key]


class HarnessError(RuntimeError):
    pass


def signed32(value):
    return value - (1 << 32) if value & 0x80000000 else value


class AmigaOS:
    """Mixed into the machine.  Uses: reg, setreg, o (the oracle), cstr, nested, alloc, free,
    deliver_vblanks, lib_base, video_hz, and the logs set up in os_init."""

    def os_init(self, files=None):
        self.handles = {}
        self.next_handle = 0x1000
        self.overlay = {name.lower(): bytes(data) for name, data in (files or {}).items()}
        self.deleted = set()              # what DeleteFile took away; the disk itself is read-only
        self.ioerr = 0
        self.files_log = []               # (call, name, found)
        # The same log with the VBlank each call happened at.  A port test replays a run's
        # schedule and compares what it opened, call for call, against this (SPEC 8).
        self.files_at = []                # (vblank, call, name, found)
        self.formatted = []               # what RawDoFmt produced
        self.devices = []
        self.input_handlers = []          # (is_Data, is_Code) of input.device handlers
        self.servers = []                 # (priority, order, is_Data, is_Code) of VBlank servers
        self.next_signal = 15
        self.segments = []
        self.player_calls = []
        self.loaded = {}                  # name -> [(address, size, hunk)] of a real LoadSeg
        self.loaded_history = []          # (name, [(address, size)]) of every real LoadSeg

    # ------------------------------------------------------------------------ exec

    def os_exec_OpenLibrary(self):
        name = self.cstr(self.reg('a1'))
        if name == 'mathffp.library':
            if not self.math_vectors:
                raise HarnessError('the game opens mathffp.library, which the harness runs from '
                                   'original/kick.rom; no such library was found there')
            return self.math_base
        return self.lib_base.get(name.split('.')[0], 0)

    os_exec_OldOpenLibrary = os_exec_OpenLibrary

    def os_exec_CloseLibrary(self):
        return None

    def os_exec_AllocMem(self):
        return self.alloc(self.reg('d0'), self.reg('d1'))

    def os_exec_FreeMem(self):
        self.free(self.reg('a1'))
        return None

    def os_exec_AvailMem(self):
        return 0x400000                   # above the 400,000 bytes main compares it with

    def os_exec_AddIntServer(self):
        number, node = self.reg('d0'), self.reg('a1')
        if number != 5:
            raise HarnessError('AddIntServer for interrupt %d; only VBlank servers are modelled' % number)
        priority = struct.unpack('b', self.o.read(node + 9, 1))[0]
        self.servers.append((priority, len(self.servers), self.o.r32(node + 14), self.o.r32(node + 18)))
        return None

    def os_exec_RemIntServer(self):
        code = self.o.r32(self.reg('a1') + 18)
        self.servers = [s for s in self.servers if s[3] != code]
        return None

    def os_exec_Forbid(self):
        return None

    os_exec_Permit = os_exec_Disable = os_exec_Enable = os_exec_Forbid

    def os_exec_FindTask(self):
        return self.scratch_task          # a zeroed Task record

    def os_exec_SetTaskPri(self):
        return 0

    def os_exec_AllocSignal(self):
        self.next_signal += 1
        return self.next_signal

    def os_exec_FreeSignal(self):
        return None

    def os_exec_SetSignal(self):
        return 0

    def os_exec_AddPort(self):
        return None

    os_exec_RemPort = os_exec_AddPort

    def os_exec_OpenDevice(self):
        name, request = self.cstr(self.reg('a0')), self.reg('a1')
        self.o.w32(request + 0x14, self.lib_base['device'])      # io_Device
        self.o.write(request + 0x1F, b'\0')                       # io_Error
        self.devices.append(name)
        return 0

    def os_exec_CloseDevice(self):
        return None

    def os_exec_DoIO(self):
        request = self.reg('a1')
        command, data = self.o.r16(request + 0x1C), self.o.r32(request + 0x28)
        if command == IND_ADDHANDLER:
            self.input_handlers.append((self.o.r32(data + 14), self.o.r32(data + 18)))
        elif command == IND_REMHANDLER:
            code = self.o.r32(data + 18)
            self.input_handlers = [h for h in self.input_handlers if h[1] != code]
        else:
            raise HarnessError('DoIO command %d is not modelled' % command)
        self.o.write(request + 0x1F, b'\0')
        return 0

    def os_exec_RawDoFmt(self):
        """The format subset of exec: %d %u %x %c %s, with l, a width, 0 and - flags, a .limit.
        Arguments are 16 bits wide unless l is given.  Every character goes through the
        caller's PutChProc, as 68000 code, with A3 carried from call to call."""
        text = self.o.read(self.reg('a0'), 512).split(b'\0')[0]
        data, putch, putdata = self.reg('a1'), self.reg('a2'), self.reg('a3')
        out = bytearray()
        i = 0
        while i < len(text):
            c = text[i]
            i += 1
            if c != 0x25:
                out.append(c)
                continue
            if i < len(text) and text[i] == 0x25:
                out.append(0x25)
                i += 1
                continue
            left = zero = long = False
            if i < len(text) and text[i] == 0x2D:
                left, i = True, i + 1
            if i < len(text) and text[i] == 0x30:
                zero, i = True, i + 1
            width = 0
            while i < len(text) and 0x30 <= text[i] <= 0x39:
                width, i = width * 10 + text[i] - 0x30, i + 1
            limit = None
            if i < len(text) and text[i] == 0x2E:
                limit, i = 0, i + 1
                while i < len(text) and 0x30 <= text[i] <= 0x39:
                    limit, i = limit * 10 + text[i] - 0x30, i + 1
            if i < len(text) and text[i] == 0x6C:
                long, i = True, i + 1
            kind = chr(text[i])
            i += 1
            if kind == 's':
                pointer = self.o.r32(data)
                data += 4
                field = self.o.read(pointer, 512).split(b'\0')[0] if pointer else b''
                if limit is not None:
                    field = field[:limit]
            else:
                if long:
                    value = self.o.r32(data)
                    data += 4
                    signed = signed32(value)
                else:
                    value = self.o.r16(data)
                    data += 2
                    signed = value - (1 << 16) if value & 0x8000 else value
                if kind == 'd':
                    field = str(signed).encode()
                elif kind == 'u':
                    field = str(value).encode()
                elif kind == 'x':
                    field = ('%x' % value).encode()
                elif kind == 'c':
                    field = bytes([value & 0xFF])
                else:
                    raise HarnessError('RawDoFmt: %%%s is not modelled' % kind)
            if len(field) < width:
                fill = b'0' if zero and not left else b' '
                field = field + b' ' * (width - len(field)) if left else fill * (width - len(field)) + field
            out += field
        self.formatted.append(out.decode('latin1'))
        for c in bytes(out) + b'\0':
            regs = self.nested(putch, {'d0': c, 'a3': putdata})
            putdata = regs[8 + 3]
        return None

    def _refuse(self, what):
        raise HarnessError('the program called %s: it is on its way out through a crash report' % what)

    def os_exec_Alert(self):
        self._refuse('exec.Alert')

    def os_exec_Debug(self):
        self._refuse('exec.Debug')

    # ------------------------------------------------------------------- intuition

    # --------------------------------------------------------------------- devices

    def os_device_RawKeyConvert(self):
        """console.device turns a raw key event into characters.  The game opens the device in
        keyboard_open (0x0205F0) and calls this for every key its text entry and its in-flight
        commands look at, always with keyMap 0, which means the system's default.  The routine
        is pure: it reads the event, the keymap and nothing of the device, so the real one runs
        from the owner's Kickstart ROM, as the mathffp routines do.  The keymap that a 0 stands
        for is the ROM's own default (headless._find_rom_console)."""
        if self.rom_rawkeyconvert is None or self.rom_keymap is None:
            raise HarnessError('the game converts a raw key code with console.device RawKeyConvert, '
                               'which the harness runs from original/kick.rom; it was not found there')
        keymap = self.reg('a2') or self.rom_keymap
        registers = {'a0': self.reg('a0'), 'a1': self.reg('a1'), 'd1': self.reg('d1'),
                     'a2': keymap, 'a6': 0}
        return self.nested(self.rom_rawkeyconvert, registers)[0]

    def os_intuition_CloseWorkBench(self):
        return 1

    def os_intuition_OpenWorkBench(self):
        return 1

    # -------------------------------------------------------------------- graphics
    # No logic reads a drawing result (re/notes/drawing.md), so drawing calls do nothing.
    # The calls that fill in a record the program reads afterwards do that and no more.

    def os_graphics_OwnBlitter(self):
        return None

    os_graphics_DisownBlitter = os_graphics_BltClear = os_graphics_BltTemplate = os_graphics_OwnBlitter
    os_graphics_RectFill = os_graphics_OwnBlitter

    def os_graphics_BltBitMap(self):
        return 0

    def os_graphics_WaitTOF(self):
        self.deliver_vblanks(1)
        return None

    def os_graphics_InitBitMap(self):
        bitmap, depth, width, height = self.reg('a0'), self.reg('d0'), self.reg('d1'), self.reg('d2')
        self.o.w16(bitmap, ((width + 15) >> 3) & 0xFFFE)             # BytesPerRow
        self.o.w16(bitmap + 2, height)                               # Rows
        self.o.write(bitmap + 4, bytes([0, depth & 0xFF, 0, 0]))     # Flags, Depth, pad
        return None

    def os_graphics_InitRastPort(self):
        port = self.reg('a1')
        self.o.write(port, bytes(100))
        self.o.write(port + 0x18, b'\xff\xff')                       # Mask, FgPen
        self.o.write(port + 0x1B, b'\xff\x01')                       # AOlPen, DrawMode JAM2
        self.o.w16(port + 0x22, 0xFFFF)                              # LinePtrn
        return None

    def os_graphics_Move(self):
        port = self.reg('a1')
        self.o.w16(port + 0x24, self.reg('d0'))                      # cp_x
        self.o.w16(port + 0x26, self.reg('d1'))                      # cp_y
        return None

    os_graphics_Draw = os_graphics_Move

    def os_graphics_SetAPen(self):
        self.o.write(self.reg('a1') + 0x19, bytes([self.reg('d0') & 0xFF]))
        return None

    def os_graphics_SetBPen(self):
        self.o.write(self.reg('a1') + 0x1A, bytes([self.reg('d0') & 0xFF]))
        return None

    def os_graphics_SetDrMd(self):
        self.o.write(self.reg('a1') + 0x1C, bytes([self.reg('d0') & 0xFF]))
        return None

    def os_graphics_Text(self):
        port, count = self.reg('a1'), self.reg('d0') & 0xFFFF
        self.o.w16(port + 0x24, self.o.r16(port + 0x24) + 8 * count)  # topaz 8 moves the pen
        return None

    # ------------------------------------------------------------------------- dos
    # Files come from original/disk, which is never written: what the program saves goes
    # into `overlay` and is read back from there.

    def _resolve(self, name):
        """The host path of one of the game's paths.  Case is ignored, as on the Amiga."""
        here = GAME_DIR
        for part in [p for p in name.split(':', 1)[-1].split('/') if p]:
            found = None
            if os.path.isdir(here):
                for entry in sorted(os.listdir(here)):
                    if entry.lower() == part.lower():
                        found = entry
                        break
            if found is None:
                return None
            here = os.path.join(here, found)
        return here

    def file_bytes(self, name):
        if name.lower() in self.overlay:
            return self.overlay[name.lower()]
        if name.lower() in self.deleted:
            return None
        path = self._resolve(name)
        if path is None or not os.path.isfile(path):
            return None
        with open(path, 'rb') as f:
            return f.read()

    def _handle(self, name, data, write):
        self.next_handle += 4
        self.handles[self.next_handle] = {'name': name, 'data': bytearray(data), 'pos': 0, 'write': write}
        return self.next_handle

    def _open_existing(self, call):
        name = self.cstr(self.reg('d1'))
        data = self.file_bytes(name)
        self.files_log.append((call, name, data is not None))
        self.files_at.append((getattr(self, 'vblanks', 0), call, name, data is not None))
        if data is None:
            self.ioerr = ERROR_OBJECT_NOT_FOUND
            return 0
        return self._handle(name, data, False)

    def directory_entries(self, name):
        """The entries of one of the game's directories, in the order ExNext hands them out:
        the disk image's own order, then whatever a run has saved through the overlay, each at
        the head of its chain, where the file system puts a new entry.  Entries the disk has
        but the extracted directory has not are left out, so that what a run lists is what it
        can also open."""
        parts = [p for p in name.split(':', 1)[-1].split('/') if p]
        here = self._resolve(name)
        present = set(os.listdir(here)) if here and os.path.isdir(here) else set()
        prefix = ('/'.join(parts) + '/').lower() if parts else ''
        order = adf_order(parts)
        if order is None:                     # no disk image: the extracted directory, by name
            order = [(name_hash(entry), entry) for entry in sorted(present)]
        order = [(chain, entry) for chain, entry in order
                 if entry in present and (prefix + entry).lower() not in self.deleted]
        known = {entry.lower() for _, entry in order}
        for path in self.overlay:
            entry = path[len(prefix):]
            if not path.startswith(prefix) or '/' in entry or entry in known:
                continue
            chain = name_hash(entry)
            at = next((i for i, (c, _) in enumerate(order) if c >= chain), len(order))
            order.insert(at, (chain, entry))
            known.add(entry)
        return [entry for _, entry in order]

    def _dir_handle(self, name):
        self.next_handle += 4
        self.handles[self.next_handle] = {'name': name, 'entries': self.directory_entries(name),
                                          'at': 0}
        return self.next_handle

    def os_dos_Lock(self):
        """A lock on a file, or on a directory: the load and save dialog locks the game's own
        directory, which it names with a 0 (sub_018a06)."""
        address = self.reg('d1')
        name = self.cstr(address) if address else ''
        path = self._resolve(name)
        if path is not None and os.path.isdir(path):
            self.files_log.append(('Lock dir', name, True))
            self.files_at.append((getattr(self, 'vblanks', 0), 'Lock dir', name, True))
            return self._dir_handle(name)
        return self._open_existing('Lock')

    def os_dos_UnLock(self):
        self.handles.pop(self.reg('d1'), None)
        return None

    def _file_info(self, block, name, directory, size):
        """A FileInfoBlock.  fib_FileName is a plain string, not a BSTR: dos gives the caller
        the name the file system's BSTR holds, terminated."""
        text = name.split('/')[-1].encode('latin1')[:106]
        self.o.write(block, bytes(260))
        self.o.w32(block + 4, 2 if directory else 0xFFFFFFFD)        # fib_DirEntryType
        self.o.write(block + 8, text + b'\0')                        # fib_FileName
        self.o.w32(block + 120, 2 if directory else 0xFFFFFFFD)      # fib_EntryType
        self.o.w32(block + 124, size)                                # fib_Size
        self.o.w32(block + 128, (size + BLOCK - 1) // BLOCK)         # fib_NumBlocks

    def os_dos_Examine(self):
        record, block = self.handles[self.reg('d1')], self.reg('d2')
        if 'entries' in record:
            record['at'] = 0
            self._file_info(block, record['name'] or DISK_DIR, True, 0)
        else:
            self._file_info(block, record['name'], False, len(record['data']))
        return DOS_TRUE

    def os_dos_ExNext(self):
        """The next entry of a directory lock.  The end of the list is a 0 with IoErr
        ERROR_NO_MORE_ENTRIES, which is how the file list of the dialog stops."""
        record, block = self.handles[self.reg('d1')], self.reg('d2')
        if 'entries' not in record:
            self.ioerr = ERROR_OBJECT_WRONG_TYPE
            return 0
        if record['at'] >= len(record['entries']):
            self.ioerr = ERROR_NO_MORE_ENTRIES
            return 0
        name = record['entries'][record['at']]
        record['at'] += 1
        path = '/'.join(filter(None, [record['name'], name]))
        data = self.file_bytes(path)
        here = self._resolve(path)
        self._file_info(block, name, data is None and here is not None and os.path.isdir(here),
                        len(data) if data is not None else 0)
        return DOS_TRUE

    def os_dos_Open(self):
        if self.reg('d2') == MODE_NEWFILE:
            name = self.cstr(self.reg('d1'))
            self.files_log.append(('Open new', name, True))
            self.files_at.append((getattr(self, 'vblanks', 0), 'Open new', name, True))
            self.deleted.discard(name.lower())
            return self._handle(name, b'', True)
        return self._open_existing('Open')

    def os_dos_Close(self):
        record = self.handles.pop(self.reg('d1'), None)
        if record and record['write']:
            self.overlay[record['name'].lower()] = bytes(record['data'])
        return DOS_TRUE

    def os_dos_Read(self):
        record, buffer, length = self.handles[self.reg('d1')], self.reg('d2'), self.reg('d3')
        chunk = bytes(record['data'][record['pos']:record['pos'] + length])
        self.o.write(buffer, chunk)
        record['pos'] += len(chunk)
        return len(chunk)

    def os_dos_Write(self):
        record, buffer, length = self.handles[self.reg('d1')], self.reg('d2'), self.reg('d3')
        record['data'][record['pos']:record['pos'] + length] = self.o.read(buffer, length)
        record['pos'] += length
        return length

    def os_dos_Seek(self):
        record = self.handles[self.reg('d1')]
        old = record['pos']
        origin = {-1: 0, 0: old, 1: len(record['data'])}[signed32(self.reg('d3'))]
        record['pos'] = origin + signed32(self.reg('d2'))
        return old

    def os_dos_IoErr(self):
        return self.ioerr

    def os_dos_DeleteFile(self):
        """Nothing in original/ is ever written, so a deleted file is remembered instead: it is
        gone from the overlay and from what the disk answers, which is what the clear command
        of the high scores does."""
        name = self.cstr(self.reg('d1'))
        existed = self.file_bytes(name) is not None
        self.files_log.append(('DeleteFile', name, existed))
        self.files_at.append((getattr(self, 'vblanks', 0), 'DeleteFile', name, existed))
        self.overlay.pop(name.lower(), None)
        self.deleted.add(name.lower())
        return DOS_TRUE if existed else 0

    def os_dos_Delay(self):
        """Delay counts fiftieths of a second, whatever the video standard."""
        self.deliver_vblanks(self.reg('d1') * self.video_hz // 50)
        return None

    def os_dos_LoadSeg(self):
        """The game loads two segments, the song data and the music player, and calls the first
        long after each segment's link word.  With the music on (the run's `"music"`, the
        default) each is loaded as dos loads it: every hunk into memory of its own with its
        size and a link to the next in front, relocated, BSS zeroed, and the BPTR of the first
        link returned; its entry is watched, so that every call into it is recorded, and runs.
        With the music off each becomes a fake segment whose entry is a stop of its own that
        answers every call with 0, "idle"."""
        name = self.cstr(self.reg('d1'))
        found = self.file_bytes(name)
        self.files_log.append(('LoadSeg', name, found is not None))
        self.files_at.append((getattr(self, 'vblanks', 0), 'LoadSeg', name, found is not None))
        if found is None:
            return 0
        if self.run_spec.get('music'):
            return self.load_segment(name, found)
        block = self.segment_block(len(self.segments))
        self.segments.append(name)
        self.o.w32(block, 0x100)                                     # the segment's size
        self.o.w32(block + 4, 0)                                     # no next segment
        self.o.write(block + 8, b'\x4e\x75')
        return (block + 4) >> 2                                      # a BPTR

    def load_segment(self, name, raw):
        import hunk
        sizes = [len(h['data']) for h in hunk.load(raw)]
        bases = []
        for i, size in enumerate(sizes):
            base = self.segment_alloc(size + 8)
            self.alloc_labels[base] = '%s hunk %d (LoadSeg)' % (name, i)
            bases.append(base)
        hunks = hunk.load(raw, bases=[b + 8 for b in bases])
        for i, (base, h) in enumerate(zip(bases, hunks)):
            self.o.w32(base, len(h['data']) + 8)
            self.o.w32(base + 4, (bases[i + 1] + 4) >> 2 if i + 1 < len(bases) else 0)
            self.o.write(base + 8, bytes(h['data']))
        self.loaded[name.lower()] = [(b + 8, len(h['data']), h) for b, h in zip(bases, hunks)]
        self.loaded_history.append((name.lower(), [(b + 8, len(h['data'])) for b, h in zip(bases, hunks)]))
        self.segment_loaded(name.lower())
        return (bases[0] + 4) >> 2

    def os_dos_UnLoadSeg(self):
        """Every hunk of the list goes, as dos frees them; the harness's allocator never hands
        the memory out again."""
        link = self.reg('d1') << 2
        while link:
            base = link - 4
            nxt = self.o.r32(link) << 2
            self.free(base)
            link = nxt
        return DOS_TRUE

    def os_exec_OpenResource(self):
        """ciaa.resource, for the music player's timer; anything else is not there."""
        name = self.cstr(self.reg('a1'))
        return self.lib_base['ciaa'] if name == 'ciaa.resource' else 0

    def os_ciaa_AddICRVector(self):
        """(D0 bit, A1 Interrupt) the vector of one of CIA-A's interrupts, and its interrupt
        enabled: only timer A, bit 0, is modelled (tools/headless_paula.py, CiaTimer)."""
        bit, node = self.reg('d0') & 0xFF, self.reg('a1')
        if bit != 0:
            raise HarnessError('AddICRVector for CIA-A bit %d; only timer A is modelled' % bit)
        self.paula.timer.vector = (self.o.r32(node + 0x12), self.o.r32(node + 0x0E))
        return 0

    def os_ciaa_RemICRVector(self):
        if self.reg('d0') & 0xFF == 0:
            self.paula.timer.vector = None
        return None

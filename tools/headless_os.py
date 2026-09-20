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

MODE_NEWFILE = 1006
ERROR_OBJECT_NOT_FOUND = 205
IND_ADDHANDLER, IND_REMHANDLER = 9, 10
DOS_TRUE = 0xFFFFFFFF


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
        self.ioerr = 0
        self.files_log = []               # (call, name, found)
        self.formatted = []               # what RawDoFmt produced
        self.devices = []
        self.input_handlers = []          # (is_Data, is_Code) of input.device handlers
        self.servers = []                 # (priority, order, is_Data, is_Code) of VBlank servers
        self.next_signal = 15
        self.segments = []
        self.player_calls = []

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
        if data is None:
            self.ioerr = ERROR_OBJECT_NOT_FOUND
            return 0
        return self._handle(name, data, False)

    def os_dos_Lock(self):
        return self._open_existing('Lock')

    def os_dos_UnLock(self):
        self.handles.pop(self.reg('d1'), None)
        return None

    def os_dos_Examine(self):
        record, block = self.handles[self.reg('d1')], self.reg('d2')
        name = record['name'].split('/')[-1].encode('latin1')[:30]
        self.o.write(block, bytes(260))
        self.o.w32(block + 4, 0xFFFFFFFD)                            # fib_DirEntryType: a file
        self.o.write(block + 8, bytes([len(name)]) + name)           # fib_FileName
        self.o.w32(block + 124, len(record['data']))                 # fib_Size
        return DOS_TRUE

    def os_dos_Open(self):
        if self.reg('d2') == MODE_NEWFILE:
            name = self.cstr(self.reg('d1'))
            self.files_log.append(('Open new', name, True))
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
        name = self.cstr(self.reg('d1'))
        self.files_log.append(('DeleteFile', name, name.lower() in self.overlay))
        self.overlay.pop(name.lower(), None)
        return DOS_TRUE

    def os_dos_Delay(self):
        """Delay counts fiftieths of a second, whatever the video standard."""
        self.deliver_vblanks(self.reg('d1') * self.video_hz // 50)
        return None

    def os_dos_LoadSeg(self):
        """The game loads two segments, the song data and the music player, and calls the first
        long after each segment's link word.  Neither is run here: each becomes a fake segment
        whose entry is a stop of its own, and every call into it is recorded."""
        name = self.cstr(self.reg('d1'))
        self.files_log.append(('LoadSeg', name, self.file_bytes(name) is not None))
        block = self.segment_block(len(self.segments))
        self.segments.append(name)
        self.o.w32(block, 0x100)                                     # the segment's size
        self.o.w32(block + 4, 0)                                     # no next segment
        self.o.write(block + 8, b'\x4e\x75')
        return (block + 4) >> 2                                      # a BPTR

    def os_dos_UnLoadSeg(self):
        return DOS_TRUE

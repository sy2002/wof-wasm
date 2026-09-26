"""Completeness of the comparison (M4, V3 and T3).

Every address the original writes during a mission - in the setup after the briefing, in
its logic tick, in frame_update's tree, in a VBlank server, in the main program between
them - has to be one of three things:

  * a field of the port's registries (src/globals.def, src/mission.def), which both loops
    of tests/m4compare.py compare after every pass;
  * a row of COMPARED: state the port keeps in another form, compared by another check of
    V1, which the row names;
  * a row of EXCLUDED: state the port does not keep, with the reason and the milestone that
    owns it.

A row names the routines that write its range.  A write by any other routine makes the
address uncovered again, because a new writer can mean a new meaning.  The writes come
from tests/m4compare.Recorder, which records them with the phase and the writing routine.
"""
import bisect
import collections

import headless

DATA_START, DATA_END = headless.DATA_START, headless.DATA_END

# (first, last, writers, what it is, how the port carries it)
COMPARED = [
    (0x026E1C, 0x026E3B, {'view_show'},
     'back_rastport, back_vport, front_rastport, front_vport, back_view, front_view, '
     'back_bitmap, front_bitmap: the double buffer',
     'the index of the view in front, compared after every pass (V1, the view check)'),
    (0x027A18, 0x027BD7, {'cmap_file_to_table', 'iff_cmap_to_table', 'mission_display_setup',
                          'view_poke_colours1', 'view_poke_colours2', 'vport_init_bitmap'},
     'coltab_a1 ... coltab_b1_split: the colour tables of both views and the ticker',
     "each viewport's colour tables, compared as the palette of every output row (V1 rows)"),
]

# (first, last, writers, what it is, why the port does not keep it, milestone)
EXCLUDED = [
    (0x02693C, 0x02694F, {'draw_set_target'},
     'draw_planes: the graphics library\'s copy of the plane pointers, never read',
     'the port draws into a viewport by index; the choice of target is compared as the '
     'draw_set_target calls (V1)', 'M4, SPEC 6.6'),
    (0x026E3E, 0x026EB7, {'sounds_load'},
     'the sample pointers of the sound effects',
     'sounds_load is the M8 stand-in: it opens the files and keeps their lengths', 'M8'),
    (0x026F1A, 0x026F1D, {'draw_set_target'},
     'draw_rastport: the RastPort the library draws into',
     'as draw_planes', 'M4, SPEC 6.6'),
    (0x02714E, 0x027151, {'draw_set_target'},
     'draw_bitmap: its BitMap', 'as draw_planes', 'M4, SPEC 6.6'),
    (0x027296, 0x027341, {'screen_game', 'ticker_vport_init', 'view_copy_colours'},
     'vport_ticker: the ticker\'s ViewPort, RasInfo, BitMap and RastPort',
     'the port\'s screen model (src/screen.c) keeps a viewport as position, size and depth; '
     'its picture is compared as the palette of every row (V1 rows)', 'M4, SPEC 6.6'),
    (0x027368, 0x027427, {'sub_011f76', 'sound_slots_clear', 'sound_channels', 'engine_sound', 'sub_012324',
                          'sub_01233e', 'sub_012354', 'sub_012380', 'sub_0123ac'},
     'the eight sound slots of 0x18 bytes: what sounds_load builds, and the sounds the tick '
     'starts, stops and moves (the engine, the lift, a splash, a touch-down)',
     'the sound engine is M8\'s; the two values 0x012132 eases that the rest of the game keeps '
     '(0x02542C, 0x02542E) are registered', 'M8'),
    (0x02772A, 0x02772D, {'load_file'},
     'load_file_len', 'wof_load_file returns the length', 'M1'),
    (0x027748, 0x027A13, {'screen_game', 'view_set_game', 'vport_init_bitmap',
                          'view_copy_colours', 'draw_set_target'},
     'vport_a1, vport_b1, vport_a2, vport_b2, view_a, view_b: the two views and their '
     'viewports (View, ViewPort, RasInfo, BitMap, RastPort); draw_set_target sets the '
     'RastPort\'s plane mask',
     'as vport_ticker; the plane mask is 0xFF >> (8 - depth), which the port\'s '
     'draw_set_target computes the same way', 'M4, SPEC 6.6'),
    (0x027C6C, 0x027C79, {'view_build_copper', 'view_show'},
     'cop_split_index, cop_prev, cop_next, cop_after: the copper lists\' bookkeeping',
     'the port has no copper lists; the split line and the palette of every row are '
     'compared (V1 rows)', 'M4, SPEC 6.6'),
    (0x027C7A, 0x027C7D, {'load_file'},
     'load_file_ptr', 'wof_load_file returns the buffer', 'M1'),
    (0x027DDE, 0x027DE1, {'cop_install'},
     'cop_current: the copper list last installed', 'as cop_split_index', 'M4, SPEC 6.6'),
    (0x027DEC, 0x027DEF, {'player_reset'},
     'player_record: a pointer, always to player_y (0x025078)',
     'the port reaches the player\'s record directly', 'M4'),
    (0x027DF0, 0x027DF3, {'turn_allowed', 'guns'},
     'g_027df0: the enemy aircraft record the walks of 0x01AA6E and 0x01B682 are on, set '
     'before every read',
     'the port walks the records by index', 'M4'),
    (0x027DF4, 0x027DF7, {'deck_span'},
     'g_027df4: a pointer deck_span sets, always to player_start_x',
     'the port reads player_start_x directly', 'M4'),
    (0x027E6A, 0x027F21, {'soundfx_vblank', 'sub_01ea28', 'sub_01eac0', 'sub_01eb4c'},
     'the sound engine\'s channel state, and the audio channels the tick starts and stops',
     'soundfx_vblank and the channel routines are the M8 stand-in', 'M8'),
    (0x027FAC, 0x027FAD, {'line_draw'},
     'line_draw\'s copy of the RastPort\'s plane mask, shifted a plane at a time',
     'the port draws a line in every plane of the target\'s mask at once', 'M4, SPEC 6.6'),
    (0x027FAE, 0x027FB1, {'ffp_mul'},
     'MathBase: mathffp.library\'s base, opened at the first floating-point call',
     'the port\'s floating point is src/ffp.c (SPEC 7.1, point 13)', 'M4'),
    (0x027F62, 0x027F65, {'load_file'},
     'load_file_error: IoErr of the last failed load', 'the port\'s loader returns 0', 'M1'),
    (0x027F86, 0x027FA3, {'blit_clip_setup'},
     'blit_src ... blit_shift: the blit parameters blit_clip_setup leaves',
     'the port blits in C; its blits are held to the blitter model (V5)', 'M1, SPEC 6.6'),
]

# Allocations, by the owner the harness labels them with: (owner, writers, what it is,
# how the port carries it or why not, milestone).  A writer set of None matches any.
ALLOCATOR = {'sub_020874', 'mem_free'}
HEAP = [
    ('*', ALLOCATOR,
     'the game allocator\'s header in front of every allocation and its free chain',
     'the port\'s arena has no headers and hands out zeroed memory (SPEC 7.2)', 'M1'),
    ('load_file', {'load_file', 'rpck_unpack'},
     'a file as load_file reads and unpacks it',
     'wof_load_file reads into arena scratch; the loaders are M1\'s', 'M1'),
    ('display_init', {'cop_install', 'cop_move', 'cop_move_ptr', 'cop_wait', 'cop_colours',
                      'cop_reset', 'cop_set_split_line', 'flip_buffers',
                      'view_poke_colours1', 'view_poke_colours2'},
     'the copper lists of both views',
     'the port has no copper lists; the split line and the palette of every row are '
     'compared (V1 rows)', 'M4, SPEC 6.6'),
    ('display_init', {'byterun1_row'},
     'the planes of both views: the dashboard picture, unpacked in the setup',
     'the port unpacks it into its surfaces with M3\'s decoder (src/iff.c); the headless '
     'original runs no blits, so its planes are not a picture to compare', 'M3'),
    ('load_file', {'shape_mirror_x', 'aircraft_frame'},
     'hellcat.shp and Torpedo.shp: the planes shape_mirror_x mirrors in place when the '
     'aircraft turns, and the marker at +8 of each record aircraft_frame keeps',
     'the port mirrors its converted pixels the same way and keeps the markers in the state; '
     'the markers are compared after every tick (T1)', 'M4'),
    ('sub_0158fe', {'shape_draw'},
     'MaskBuffer: the mask shape_draw builds by CPU for one blit',
     'the port blits with the mask kept at load (re/notes/drawing.md)', 'M1'),
]


# What the M5 scripts write that neither registry holds, beside the rows above, which the
# M4 scripts need (tests/test_weapons.py takes both):
# (first, last, writers, what it is, why the port does not keep it, milestone).
M5_EXCLUDED = [
    # A restart in flight (Control-R, bomb_restart) fades both views to black in the
    # mission's inner loop (fade_out_pair, re/notes/keys.md) before the mission ends.
    (0x027A08, 0x027A0B, {'fade_to_pair'},
     'view_b + 2: the copper buffer of the second view, which every step of a fade swaps '
     'with cop_spare',
     'the port has no copper lists; its fades are held to the original by '
     'test_oracle_m3.py::test_the_fades_agree_with_the_original', 'M3'),
    (0x027A18, 0x027BD7, {'cmap_file_to_table', 'iff_cmap_to_table', 'mission_display_setup',
                          'view_poke_colours1', 'view_poke_colours2', 'vport_init_bitmap',
                          'fade_to_pair'},
     'coltab_a1 ... coltab_b1_split, as a restart\'s fade leaves them',
     'compared as the palette of every row at every pass (V1 rows); the fade between two '
     'passes is held to the original by test_the_fades_agree_with_the_original', 'M3, M4'),
    (0x027C64, 0x027C67, {'fade_to_pair'},
     'cop_spare: the third copper buffer', 'as view_b + 2', 'M3'),
]
# Display memory beside HEAP's rows.
M5_HEAP = [
    ('display_init', {'vblank_server'},
     'the ticker\'s plane, which vblank_server scrolls and fills with glyphs by CPU',
     'the port scrolls its own plane (wof_vblank_ticker); the message pointer and the '
     'counters are registered and compared after every step, and the plane is held to the '
     'original VBlank by VBlank under the oracle (test_the_ticker_matches_the_original)',
     'M4'),
]

# What the M6 scripts write beside the rows above (tests/test_enemy.py takes all three sets):
# the ships' containers, which the mission setup loads on maps d to o.
M6_EXCLUDED = [
    (0x0256A2, 0x0256A5, {'shapes_load'},
     'shapes_load_name: the file name shapes_load is working on, for its error text',
     'the port loads every container at start-up (src/assets.c); a missing file is M1\'s '
     'loader\'s', 'M1'),
    (0x026F34, 0x026F53, {'load_ship_shapes'},
     'battleship_container ... cruiseship_shapes: the four ships\' containers and their '
     'tables of record pointers',
     'the port holds every container from start-up and keeps which ships the mission loaded '
     'in ship_loaded; what the tables hand on is MasterList\'s slots 0xB8 on, which are '
     'registered and compared after every step', 'M4'),
]
M6_HEAP = [
    ('shapes_resolve', {'shapes_resolve'},
     'a ship container\'s table of record pointers, which shapes_resolve allocates and fills '
     'when load_ship_shapes loads the container in the mission setup',
     'the port resolves the names into shape handles at start-up (src/shapes.c); MasterList\'s '
     'slots, which the tables fill, are registered and compared after every step', 'M4'),
]


def _owner(label):
    """'alloc 57 (load_file shapes/wingspalette)' -> 'load_file'."""
    inside = label[label.index('(') + 1:label.rindex(')')] if '(' in label else label
    return inside.split(' ')[0]


class Coverage:
    """The written addresses of one or more recorded runs, sorted into the three kinds."""

    def __init__(self, layout, compared=COMPARED, excluded=EXCLUDED, heap=HEAP):
        self.layout = layout
        self.compared, self.excluded, self.heap = compared, excluded, heap
        self.registered = set()
        for name, addr, elem, count, offset in layout.globals:
            self.registered.update(range(addr, addr + elem * count))
        for table in layout.tables:
            if not table['pool']:
                size = layout.records[table['record']]['orig_size']
                self.registered.update(range(table['addr'], table['addr'] + size * table['count']))
        self.uncovered = collections.defaultdict(set)      # address -> {(window, phase, routine)}
        self.rows_used = collections.Counter()
        self.pool_writes = 0

    def add(self, machine):
        """One recorded run: tests/m4compare.Recorder's mission_writes, at_s and allocations."""
        names = machine.names
        bases = sorted(machine.alloc_labels)
        sizes = dict(machine.alloc_sizes)
        sizes.update(machine.display_allocs)
        pools = []
        for snap in machine.at_s:
            for table in self.layout.tables:
                if not table['pool']:
                    continue
                at = table['addr'] - DATA_START
                pointer = int.from_bytes(snap[at:at + 4], 'big')
                i = bisect.bisect_right(bases, pointer) - 1
                if not pointer or i < 0:
                    continue
                end = bases[i] + sizes.get(bases[i], 0)
                size = self.layout.records[table['record']]['orig_size']
                pools.append((pointer, min(pointer + size * table['count'], end)))
        pools.sort()
        starts = [p for p, _ in pools]

        for address, writes in machine.mission_writes.items():
            writers = {names.routine(start) for _, _, start in writes}
            if DATA_START <= address < DATA_END:
                if address in self.registered:
                    continue
                row = self._data_row(address, writers)
            else:
                i = bisect.bisect_right(starts, address) - 1
                if i >= 0 and any(lo <= address < hi for lo, hi in pools[max(i - 3, 0):i + 1]):
                    self.pool_writes += 1
                    continue
                j = bisect.bisect_right(bases, address) - 1
                label = machine.alloc_labels[bases[j]] if j >= 0 else '?'
                row = self._heap_row(label, writers)
            if row is None:
                self.uncovered[address] |= {(w, p, names.routine(s)) for w, p, s in writes}
            else:
                self.rows_used[row] += 1

    def _data_row(self, address, writers):
        for kind, rows in (('compared', self.compared), ('excluded', self.excluded)):
            for row in rows:
                if row[0] <= address <= row[1] and writers <= row[2]:
                    return (kind, row[0], row[1])
        return None

    def _heap_row(self, label, writers):
        owner = _owner(label)
        rest = set(writers)
        allocator = rest & ALLOCATOR
        if allocator and rest <= ALLOCATOR:
            return ('heap', '*', 'allocator')
        for row in self.heap[1:]:
            if owner == row[0] and rest <= row[1]:
                return ('heap', row[0], ','.join(sorted(row[1]))[:40])
        return None

    def ranges(self):
        """The uncovered addresses as [(first, last, writers)], runs of equal writers."""
        out = []
        for address in sorted(self.uncovered):
            writers = sorted({r for _, _, r in self.uncovered[address]})
            if out and out[-1][1] + 1 == address and out[-1][2] == writers:
                out[-1][1] = address
            else:
                out.append([address, address, writers])
        return [tuple(r) for r in out]

    def unused_rows(self):
        used = {(k, a, b) for k, a, b in self.rows_used if k != 'heap'}
        return ([('compared', r[0], r[1]) for r in self.compared if ('compared', r[0], r[1]) not in used] +
                [('excluded', r[0], r[1]) for r in self.excluded if ('excluded', r[0], r[1]) not in used])


def describe(ranges):
    return '\n'.join('%06X-%06X (%d bytes) written by %s' % (a, b, b - a + 1, ', '.join(w))
                     for a, b, w in ranges)

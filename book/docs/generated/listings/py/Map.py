# tools/map_decode.py, lines 43-72
class Map:
    """One map file: the two leading longs and the record list."""

    def __init__(self, name, data):
        self.name = name
        self.file_length = len(data)
        self.length, self.start = struct.unpack_from('>LL', data, 0)
        # The first long is the file's own length, and the loader reads that many bytes of
        # records after the eight-byte header: the last eight bytes of the list never come
        # from the file.  They are zero everywhere, because the game's allocator asks
        # AllocMem for MEMF_CLEAR (re/notes/map.md).
        self.on_disk = (len(data) - 8) // 2
        self.padding = self.length // 2 - self.on_disk
        self.words = list(struct.unpack_from('>%dH' % self.on_disk, data, 8)) + [0] * self.padding
        # What the loader 0x012ADC computes from the two longs.
        self.extent = (self.length * 4) & 0xFFFF          # world x past the last record
        self.player_x = (self.start * 4 - 8) & 0xFFFF     # where the player starts

    def __len__(self):
        return len(self.words)

    def record(self, index):
        found = fields(self.words[index])
        found['index'] = index
        found['x'] = index * WORLD_PER_RECORD
        found['word'] = self.words[index]
        return found

    def records(self):
        return [self.record(i) for i in range(len(self.words))]

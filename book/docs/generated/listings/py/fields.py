# tools/map_decode.py, lines 32-40
def fields(word):
    """The fields of one map record."""
    return {
        'draw': bool(word & 0x8000),          # bit 15: this record draws its shape
        'slot': (word >> 2) & 0x1FF,          # bits 2-10: the slot in MasterList or AthList
        'height': (word >> 11) & 7,           # bits 11-13: height steps above the horizon
        'low': word & 3,                      # bits 0-1: 1 rides on a ship, 2 stands on the world
        'bit14': bool(word & 0x4000),
    }

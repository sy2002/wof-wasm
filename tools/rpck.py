import struct, sys, os

def unrle(src):
    out = bytearray(); i = 0; n = len(src)
    while i < n:
        c = src[i]; i += 1
        if c >= 0x80:
            k = 256 - c
            out += src[i:i+k]; i += k
        else:
            out += bytes([src[i]]) * (c + 1); i += 1
    return bytes(out)

def load(path):
    raw = open(path, 'rb').read()
    if raw[:4] == b'Rpck':
        size = struct.unpack('>I', raw[4:8])[0]
        out = unrle(raw[8:])
        return out, size
    return raw, len(raw)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        raw0 = open(p, 'rb').read()
        out, size = load(p)
        print('%-16s magic=%s packed=%6d declared=%6d got=%6d %s inner=%s' % (
            os.path.basename(p), raw0[:4], len(raw0), size, len(out),
            'OK' if size == len(out) else 'MISMATCH', out[:4]))

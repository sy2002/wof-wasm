"""dis.py <exe> <start_hex> <len_hex> : disassemble a range of the loaded image."""
import sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000
import hunk

def image(path):
    segs = hunk.load(path)
    return segs

def dis(segs, start, length):
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
    for s in segs:
        if s['base'] <= start < s['base'] + len(s['data']):
            off = start - s['base']
            code = bytes(s['data'][off:off + length])
            addr = start
            while addr < start + length:
                got = False
                for ins in md.disasm(code[addr - start:], addr):
                    got = True
                    print('%06x  %-10s %s' % (ins.address, ins.mnemonic, ins.op_str))
                    addr = ins.address + ins.size
                if addr < start + length:
                    w = code[addr - start:addr - start + 2]
                    print('%06x  dc.w       $%s' % (addr, w.hex()))
                    addr += 2
            return

if __name__ == '__main__':
    segs = image(sys.argv[1])
    dis(segs, int(sys.argv[2], 16), int(sys.argv[3], 16))

# tools/m68k_fix.py, lines 26-31
def asr_word(value):
    """asr.w #1 on a memory word: the result and the condition codes X N Z V C."""
    carry = value & 1
    result = ((value >> 1) | (value & 0x8000)) & 0xFFFF
    ccr = (0x11 if carry else 0) | (0x08 if result & 0x8000 else 0) | (0x04 if result == 0 else 0)
    return result, ccr

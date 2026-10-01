# tools/m68k_fix.py, lines 34-41
def _shift(uc, address, size, register):
    base = uc.reg_read(UC_M68K_REG_A0 + register) & 0xFFFFFFFF
    offset = int.from_bytes(uc.mem_read(address + 2, 2), 'big', signed=True)
    ea = (base + offset) & 0xFFFFFFFF
    result, ccr = asr_word(int.from_bytes(uc.mem_read(ea, 2), 'big'))
    uc.mem_write(ea, result.to_bytes(2, 'big'))
    uc.reg_write(UC_M68K_REG_SR, (uc.reg_read(UC_M68K_REG_SR) & ~0x1F) | ccr)
    uc.reg_write(UC_M68K_REG_PC, address + 4)

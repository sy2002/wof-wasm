# tests/ffp_model.py, lines 176-185, a part of model_01bdfa (lines 115-201)
# 0x01BF2C: vertical speed = airspeed x across / 100, less a drop while slow.
climb = ffp(0x01BF3A, 'mul', ffp(0x01BF32, 'flt', s32(g_025414)), across)
climb = ffp(0x01BF44, 'div', climb, 0xC8000047)                     # 100.0
player_18 = s16(ffp(0x01BF48, 'fix', climb))
if g_025414 < 0x3E8 and player_c == 0:
    if not g_026d43 & 1:
        g_025402 = s16(g_025402 - divs_w(g_025f16, 2))
        if g_025402 < s16(0xEE6C):
            g_025402 = s16(0xEE6C)
    player_18 = s16(player_18 - divs_w(s16(0x3E8 - g_025414), 100))

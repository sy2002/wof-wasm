/* src/player.c, lines 688-698, a part of wof_player_motion (lines 661-715) */
v = wof_ffp_mul(wof_image32(0x025B0Cu + 4u * (uint32_t)(int32_t)wof_g.attitude_index),
                wof_ffp_flt((uint32_t)(int32_t)wof_g.airspeed));
v = wof_ffp_mul(v, along);
v = wof_ffp_add(v, 0xC8000046u);                               /* + 50 */
v = wof_ffp_div(v, 0xC8000047u);                               /* / 100 */
P.speed_x = (int16_t)wof_ffp_fix(v);
P.x = (int16_t)(P.x + (int16_t)(P.speed_x * P.facing));

v = wof_ffp_mul(wof_ffp_flt((uint32_t)(int32_t)wof_g.airspeed), across);
v = wof_ffp_div(v, 0xC8000047u);
P.speed_y = (int16_t)wof_ffp_fix(v);

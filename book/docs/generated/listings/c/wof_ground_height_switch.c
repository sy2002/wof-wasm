/* src/tick.c, lines 57-93, a part of wof_ground_height (lines 46-93) */
    switch (cls) {
    case 0x06:                                 row = 0; break;
    case 0x07:                                 row = 1; break;
    case 0x08: case 0x0B:                      row = 2; break;
    case 0x03:                                 row = 3; break;
    case 0x04:                                 row = 4; break;
    default:
        if (cls >= 0x0F && cls <= 0x1E) {
            row = 5;
            break;
        }
        if (cls < 0x0F)
            return 0;
        switch (cls) {
        case 0xCC:
            ship = &wof_m.ship_records[2];                       /* 0x02549C */
            break;
        case 0xF1: case 0xF3: case 0xF2: case 0xF6:
            ship = &wof_m.ship_records[3];                       /* 0x0254BA */
            break;
        case 0x10C: case 0x10E: case 0x10D: case 0x10F: case 0x110:
            ship = &wof_m.ship_records[1];                       /* 0x02547E */
            break;
        case 0xE5: case 0xE6: case 0xE4: case 0xE7:
            ship = &wof_m.ship_records[0];                       /* 0x025460 */
            break;
        case 0x20: case 0x1F: case 0x21: case 0x26: case 0x23:
        case 0x22: case 0x24: case 0x25: case 0x9F: case 0x27:
            ship = &wof_m.ship_records[4];                       /* carrier_record */
            return (int16_t)(ship->w0e - ship->w14 - wof_g.g_0253ae - wof_g.g_025396);
        default:
            return 0;
        }
        return (int16_t)(ship->w0e - ship->w14 - wof_g.g_0253ae);
    }
    return (int16_t)((int16_t)wof_image16(0x0257C2u + 2u * (uint32_t)row) - (int16_t)((rec >> 11) & 7u));
}

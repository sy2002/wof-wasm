/* src/player.c, lines 329-333, a part of wof_crash (lines 231-370) */
/* 0x01B304: the C call to object_spawn passes the aircraft's x and y words where
 * the map pointer belongs and nothing where the height does: the record is the
 * long (x << 16 | y) less the map list's address, and the height 0. */
wof_object_spawn((uint32_t)((((uint32_t)(uint16_t)P.x << 16) | (uint16_t)P.y) -
                            wof_g.map_list_address), 0, 0);

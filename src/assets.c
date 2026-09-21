/* Loading the game's assets, in the original's own order and through its own routines.
 *
 * init_assets (0x0134BC) loads the font, allocates the pools and calls
 * load_permanent_shapes (0x0129DC), which loads world.shp, hellcat.shp, Torpedo.shp,
 * japplane.shp and 8thscale.shp and writes the mirror marker 2 into every record of the
 * two containers that get mirrored.  Before each mission load_dash_assets (0x01653C) and
 * load_ship_shapes (0x013252) add the dashboard and whichever ships the map holds.
 *
 * M1 loads all of them at start-up, because there is no map and no mission yet and the
 * viewer browses every container.  The ship flags the original tests (0x025377, 0x02537A,
 * 0x02537B, 0x025378) are set by the map loader, which is M4; until then the port cannot
 * make the same choice and does not pretend to.  Two containers that the original loads
 * only for one screen each, selectrank.shp and nightdash.shp, are loaded here too so
 * that the browser can show them.
 *
 * The pools of alloc_pools - Ricochet, Splashes, Smoke, Balloons, MasterList, AthList -
 * belong to the object system and the map, so they arrive with M4; MaskBuffer is a local
 * in src/font.c because text_render is its only user in M1. */
#include "wof.h"
#include "gen/tables.h"

wof_assets_t wof_assets;

/* One container and, when it has a name list, the pointer table shapes_resolve makes.
 * A name that is not in the container gives WOF_NO_SHAPE, and that is the normal case:
 * 84 of the 184 world names are absent from 8thscale.shp (re/notes/shapes.md). */
static int load_one(int slot, const char *file, const uint32_t *list)
{
    wof_container_t *c = &wof_assets.c[slot];

    if (!wof_shapes_load(c, file, list))
        return 0;

    /* The names the container itself carries, for the display list and the browser. */
    for (uint16_t i = 0; i < c->count; i++)
        c->shapes[i].name = c->names[i];

    if (list) {
        uint16_t n = wof_namelist_count(list);
        wof_assets.table[slot] = wof_shapes_resolve(c, list, n);
    }
    wof_assets.loaded[slot] = 1;
    return 1;
}

/* orig 0x0129DC - and the two loops after each of the mirrored containers that store 2
 * into +8 of every record, which is the orientation the pixels have in the file. */
static int load_permanent_shapes(void)
{
    int ok = 1;

    ok &= load_one(WOF_C_WORLD,    wof_tbl_world_shp,    wof_tbl_world_names);
    ok &= load_one(WOF_C_HELLCAT,  wof_tbl_hellcat_shp,  wof_tbl_hellcat_names);
    for (uint16_t i = 0; i < wof_assets.c[WOF_C_HELLCAT].count; i++) {
        wof_assets.c[WOF_C_HELLCAT].shapes[i].marker = 2;
        if (i < sizeof wof_f.marker_hellcat)
            wof_f.marker_hellcat[i] = 2;
    }

    ok &= load_one(WOF_C_TORPEDO,  wof_tbl_torpedo_shp,  wof_tbl_torpedo_names);
    for (uint16_t i = 0; i < wof_assets.c[WOF_C_TORPEDO].count; i++) {
        wof_assets.c[WOF_C_TORPEDO].shapes[i].marker = 2;
        if (i < sizeof wof_f.marker_torpedo)
            wof_f.marker_torpedo[i] = 2;
    }

    ok &= load_one(WOF_C_JAPPLANE, wof_tbl_japplane_shp, wof_tbl_japplane_names);
    ok &= load_one(WOF_C_EIGHTH,   wof_tbl_eighth_shp,   wof_tbl_world_names);
    return ok;
}

/* orig 0x01653C - the dashboard shapes by night_flag.  M1 loads both sets. */
static int load_dash_assets(void)
{
    int ok = 1;

    ok &= load_one(WOF_C_DASH,      wof_tbl_dash_shape_files[0], wof_tbl_dash_names);
    ok &= load_one(WOF_C_NIGHTDASH, wof_tbl_dash_shape_files[1], wof_tbl_dash_names);
    return ok;
}

/* orig 0x013252 - the ships the map holds.  battleship.shp is the one container whose
 * absence the original survives; every other one ends the program. */
static int load_ship_shapes(void)
{
    int ok = 1;

    ok &= load_one(WOF_C_BATTLESHIP, wof_tbl_battleship_shp, wof_tbl_battleship_names);
    ok &= load_one(WOF_C_DESTROYER,  wof_tbl_destroyer_shp,  wof_tbl_destroyer_names);
    ok &= load_one(WOF_C_CRUISESHIP, wof_tbl_cruiseship_shp, wof_tbl_cruiseship_names);
    ok &= load_one(WOF_C_JAPCARRIER, wof_tbl_japcarrier_shp, wof_tbl_japcarrier_names);
    return ok;
}

/* orig 0x018262 loads selectrank.shp raw and addresses its eight records by index; it has
 * no name list.  The browser shows it the same way. */
static int load_rank_shapes(void)
{
    return load_one(WOF_C_SELECTRANK, wof_tbl_selectrank_shp, 0);
}

/* The bare-CMAP palette files, through the reader the game uses for them (0x016DD6). */
static void load_palette(const char *name, uint16_t *table)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *file = wof_load_file(name, &len);

    if (file)
        wof_cmap_file_to_table(file, len, table);
    wof_arena_release(mark);
}

void wof_assets_init(void)
{
    int ok = 1;

    wof_mem_set(&wof_assets, 0, sizeof wof_assets);

    ok &= wof_font_load();
    ok &= load_permanent_shapes();
    ok &= load_dash_assets();
    ok &= load_ship_shapes();
    ok &= load_rank_shapes();

    load_palette(wof_tbl_palette_files[0],       wof_assets.day_palette);
    load_palette(wof_tbl_palette_files[1],       wof_assets.night_palette);
    load_palette(wof_tbl_ocean_palette_files[0], wof_assets.ocean_palette);
    load_palette(wof_tbl_ocean_palette_files[1], wof_assets.night_ocean_palette);

    wof_mission_init();
    wof_assets.ok = ok;
}

/* After a state was loaded: the markers in the state say which way the pixel data of each
 * hellcat.shp and Torpedo.shp record faces, and the containers are brought to match by
 * mirroring, which is its own inverse (re/notes/shapes.md). */
void wof_assets_follow_state(void)
{
    static const int slots[2] = { WOF_C_HELLCAT, WOF_C_TORPEDO };

    for (int k = 0; k < 2; k++) {
        wof_container_t *c = &wof_assets.c[slots[k]];
        const uint8_t   *m = k ? wof_f.marker_torpedo : wof_f.marker_hellcat;

        for (uint16_t i = 0; i < c->count && i < 128; i++)
            if (c->shapes[i].marker != m[i]) {
                wof_shape_mirror_x(&c->shapes[i]);
                c->shapes[i].marker = m[i];
            }
    }
}

uint32_t wof_assets_ready(void)
{
    return (uint32_t)(wof_assets.ok ? 1 : 0);
}

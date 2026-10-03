/* Memory: the static arena that replaces exec AllocMem (SPEC 3.4), and the few block
 * operations the core needs.  Freestanding, so nothing here may call libc; the names are
 * prefixed so that the native test build does not collide with it either. */
#include "wof.h"

/* The shell puts the packed file blob here (about 530 KB) before wof_init, and M1 adds the
 * converted shapes of all twelve containers (about 525 KB), the pointer tables and the
 * scratch that load_file unpacks a file into (the display memory is state).  3 MB leaves room for
 * the map, the object pools and the sound buffers of the later milestones.  This is BSS:
 * it costs nothing in dist/core.wasm, only in the page's linear memory. */
#define WOF_ARENA_SIZE (3u * 1024u * 1024u)

/* The arena has two ends.  Everything that outlives a load - the converted shapes, the
 * pointer tables - grows up from the bottom.  The buffer a file is
 * read and unpacked into is scratch and grows down from the top, so that giving it back is
 * one assignment however much was allocated below it in the meantime.  That is what the
 * original's Free of a just-loaded file amounts to here. */
static uint8_t  arena[WOF_ARENA_SIZE];
static uint32_t arena_used;
static uint32_t arena_top = WOF_ARENA_SIZE;

void wof_mem_set(void *dst, uint8_t value, uint32_t n)
{
    uint8_t *d = (uint8_t *)dst;
    for (uint32_t i = 0; i < n; i++)
        d[i] = value;
}

void wof_mem_copy(void *dst, const void *src, uint32_t n)
{
    uint8_t       *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    for (uint32_t i = 0; i < n; i++)
        d[i] = s[i];
}

int wof_mem_equal(const void *a, const void *b, uint32_t n)
{
    const uint8_t *p = (const uint8_t *)a;
    const uint8_t *q = (const uint8_t *)b;
    for (uint32_t i = 0; i < n; i++)
        if (p[i] != q[i])
            return 0;
    return 1;
}

/* The shell allocates the file blob here before it calls wof_init, so wof_init must not
 * reset the arena.  Nothing is ever freed; out-of-memory returns 0 and the caller checks. */
void *wof_alloc(uint32_t bytes)
{
    uint32_t aligned = (bytes + 7u) & ~7u;

    if (aligned > arena_top - arena_used)
        return 0;
    void *p = &arena[arena_used];
    arena_used += aligned;
    wof_mem_set(p, 0, aligned);
    return p;
}

void wof_arena_reset(void)
{
    arena_used = 0;
    arena_top  = WOF_ARENA_SIZE;
}

uint32_t wof_arena_mark(void)
{
    return arena_top;
}

void wof_arena_release(uint32_t mark)
{
    if (mark >= arena_top && mark <= WOF_ARENA_SIZE)
        arena_top = mark;
}

void *wof_scratch_alloc(uint32_t bytes)
{
    uint32_t aligned = (bytes + 7u) & ~7u;

    if (aligned > arena_top - arena_used)
        return 0;
    arena_top -= aligned;
    void *p = &arena[arena_top];
    wof_mem_set(p, 0, aligned);
    return p;
}

uint32_t wof_arena_size(void) { return WOF_ARENA_SIZE; }
uint32_t wof_arena_used(void) { return arena_used + (WOF_ARENA_SIZE - arena_top); }

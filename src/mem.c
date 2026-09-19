/* Memory: the static arena that replaces exec AllocMem (SPEC 3.4), and the few block
 * operations the core needs.  Freestanding, so nothing here may call libc; the names are
 * prefixed so that the native test build does not collide with it either. */
#include "wof.h"

/* Big enough for the packed file blob (about 530 KB) and the shell's audio scratch buffer.
 * The decoded shapes of M1 will want more; raise it then. */
#define WOF_ARENA_SIZE (2u * 1024u * 1024u)

static uint8_t  arena[WOF_ARENA_SIZE];
static uint32_t arena_used;

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

    if (aligned > WOF_ARENA_SIZE - arena_used)
        return 0;
    void *p = &arena[arena_used];
    arena_used += aligned;
    wof_mem_set(p, 0, aligned);
    return p;
}

void wof_arena_reset(void)
{
    arena_used = 0;
}

uint32_t wof_arena_size(void) { return WOF_ARENA_SIZE; }
uint32_t wof_arena_used(void) { return arena_used; }

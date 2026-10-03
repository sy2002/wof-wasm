/* src/core.c, lines 213-247 */
/* A byte stored at an original address, into the registered global or the table at a
 * fixed address that covers it, as the original's move to that address would.  Returns 0
 * where nothing the port keeps covers the address. */
int wof_original_store8(uint32_t addr, uint8_t value)
{
#define WOF_GLOBAL(n, t, a)                                                            \
    if (addr - (uint32_t)(a) < (uint32_t)sizeof(t)) {                                  \
        ((uint8_t *)&wof_g.n)[sizeof(t) - 1u - (addr - (uint32_t)(a))] = value;        \
        return 1;                                                                      \
    }
#define WOF_GLOBAL_ARRAY(n, t, c, a)                                                   \
    if (addr - (uint32_t)(a) < (uint32_t)(sizeof(t) * (c))) {                          \
        uint32_t at_ = addr - (uint32_t)(a);                                           \
        ((uint8_t *)wof_g.n)[(at_ / sizeof(t)) * sizeof(t) + sizeof(t) - 1u - at_ % sizeof(t)] = value; \
        return 1;                                                                      \
    }
#include "globals.def"
#undef WOF_GLOBAL
#undef WOF_GLOBAL_ARRAY
#define WOF_TABLE(n, r, c, a)                                                          \
    if (addr - (uint32_t)(a) < record_size[rec_##r] * (uint32_t)(c)) {                 \
        uint32_t at_ = addr - (uint32_t)(a);                                           \
        int32_t  b_  = record_byte(rec_##r, at_ % record_size[rec_##r]);               \
                                                                                       \
        if (b_ < 0)                                                                    \
            return 0;                                                                  \
        ((uint8_t *)&wof_m.n[at_ / record_size[rec_##r]])[b_] = value;                 \
        return 1;                                                                      \
    }
#define WOF_POOL(n, r, c, p)
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

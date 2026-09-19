/* Loading a file: the Rpck unwrapper and the loader every asset goes through.
 *
 * The original reads the size with Lock and Examine, opens the file, reads sixteen bytes,
 * decides from the magic whether the body is packed, allocates the result and reads the
 * rest into place (SPEC 3.5).  The port keeps that shape, over the dos glue of src/fs.c,
 * because the sizes and the one-byte overrun below are behaviour the later milestones have
 * to see the same way. */
#include "wof.h"

#define RPCK 0x5270636BuL   /* 'Rpck' */
#define PCKD 0x50636B64uL   /* 'Pckd', rejected; no file on the disk uses it */

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

/* orig 0x01FEE0 - signed-byte RLE.  A control byte below 0 copies -c literals (0x80 means
 * 128), one of 0 or above repeats the next byte c + 1 times.  The original writes until
 * the source is exhausted and ignores the declared size, which is why two files on the
 * disk produce one byte more than declared; here the write stops at dstlen, because the
 * buffer is exactly that big and the declared size is what the callers go by. */
void wof_rpck_unpack(const uint8_t *src, uint32_t srclen, uint8_t *dst, uint32_t dstlen)
{
    uint32_t i = 0, o = 0;

    while (i < srclen) {
        int8_t c = (int8_t)src[i++];

        if (c < 0) {
            uint32_t n = (uint32_t)(-(int32_t)c);
            while (n-- && i < srclen) {
                if (o < dstlen)
                    dst[o] = src[i];
                o++;
                i++;
            }
        } else {
            uint32_t n = (uint32_t)c + 1;
            uint8_t  v = i < srclen ? src[i++] : 0;
            while (n--) {
                if (o < dstlen)
                    dst[o] = v;
                o++;
            }
        }
    }
}

/* orig 0x01FF16 - load_file(name, memory flags).  The flags choose chip or public memory
 * on the machine and mean nothing here, so the port drops them; load_file_public
 * (0x01FEB4) and load_file_chip (0x01FECA) both become this call.
 *
 * The result lives in arena scratch (src/mem.c).  Callers that keep something out of the
 * file take a mark first and release it afterwards, which is the original's Free. */
uint8_t *wof_load_file(const char *name, uint32_t *len)
{
    wof_file_t file;
    uint8_t    header[16];
    int32_t    lock, size, got;

    if (len)
        *len = 0;

    lock = wof_dos_lock(name);
    if (lock < 0)
        return 0;
    size = wof_dos_examine_size(lock);
    wof_dos_unlock(lock);
    if (size <= 0)
        return 0;

    /* The original has a separate path for a file shorter than sixteen bytes, which no
     * file on this disk takes; reading it whole is the same result. */
    if (size < 16) {
        uint8_t *whole = (uint8_t *)wof_scratch_alloc((uint32_t)size);
        if (!whole || !wof_dos_open(&file, name))
            return 0;
        got = wof_dos_read(&file, whole, size);
        wof_dos_close(&file);
        if (got != size)
            return 0;
        if (len)
            *len = (uint32_t)size;
        return whole;
    }

    if (!wof_dos_open(&file, name))
        return 0;
    if (wof_dos_read(&file, header, 16) != 16) {
        wof_dos_close(&file);
        return 0;
    }

    uint32_t magic = be32(header);

    if (magic == PCKD) {                      /* the loader knows it and refuses it */
        wof_dos_close(&file);
        return 0;
    }

    if (magic == RPCK) {
        uint32_t out_len = be32(header + 4);
        uint8_t *out     = (uint8_t *)wof_scratch_alloc(out_len);
        uint32_t mark    = wof_arena_mark();          /* the packed body is scratch too */
        uint8_t *packed  = (uint8_t *)wof_scratch_alloc((uint32_t)size - 8);

        if (!out || !packed) {
            wof_dos_close(&file);
            return 0;
        }
        /* The eight bytes of the stream that came in with the header, then the rest. */
        wof_mem_copy(packed, header + 8, 8);
        got = wof_dos_read(&file, packed + 8, size - 16);
        wof_dos_close(&file);
        if (got != size - 16) {
            wof_arena_release(mark);
            return 0;
        }

        wof_rpck_unpack(packed, (uint32_t)size - 8, out, out_len);
        wof_arena_release(mark);
        if (len)
            *len = out_len;
        return out;
    }

    uint8_t *whole = (uint8_t *)wof_scratch_alloc((uint32_t)size);

    if (!whole) {
        wof_dos_close(&file);
        return 0;
    }
    wof_mem_copy(whole, header, 16);
    got = wof_dos_read(&file, whole + 16, size - 16);
    wof_dos_close(&file);
    if (got != size - 16)
        return 0;
    if (len)
        *len = (uint32_t)size;
    return whole;
}

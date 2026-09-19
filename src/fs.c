/* The virtual file system (SPEC 3.4): the game's files, packed into one blob by
 * tools/build.py and handed to wof_init.  Read-only; writes go to browser storage through
 * the shell, which M0 does not need yet.
 *
 * Container layout, big-endian like everything else the project reads (SPEC 3.5).  The
 * paths are relative to the disk's Wings_of_Fury directory, which is the original's
 * current directory, so the names the ported loaders pass are the original's names.
 *
 *   +0   'WOFS'
 *   +4   u32  version, 1
 *   +8   u32  number of files
 *   +12  u32  offset of the directory
 *   directory, one 40-byte entry per file, sorted by name:
 *   +0   char name[32], NUL-padded
 *   +32  u32  offset of the file data from the start of the blob
 *   +36  u32  length in bytes
 *
 * M0 only proves that the blob arrives; the loaders that read from it are M1. */
#include "wof.h"

#define FS_MAGIC     0x574F4653u  /* 'WOFS' */
#define FS_VERSION   1u
#define FS_NAME_MAX  32u
#define FS_ENTRY     40u
#define FS_HEADER    16u

static const uint8_t *fs_blob;
static uint32_t       fs_len;
static uint32_t       fs_files;
static uint32_t       fs_dir;

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

int wof_fs_open(const uint8_t *blob, uint32_t len)
{
    fs_blob  = 0;
    fs_len   = 0;
    fs_files = 0;
    fs_dir   = 0;

    if (!blob || len < FS_HEADER)
        return 0;
    if (be32(blob) != FS_MAGIC || be32(blob + 4) != FS_VERSION)
        return 0;

    uint32_t files = be32(blob + 8);
    uint32_t dir   = be32(blob + 12);

    if (dir > len || files > (len - dir) / FS_ENTRY)
        return 0;

    fs_blob  = blob;
    fs_len   = len;
    fs_files = files;
    fs_dir   = dir;
    return 1;
}

uint32_t wof_fs_count(void)
{
    return fs_files;
}

static int name_equal(const uint8_t *entry, const char *name)
{
    uint32_t i = 0;

    for (; i < FS_NAME_MAX; i++) {
        uint8_t want = (uint8_t)name[i];
        if (entry[i] != want)
            return 0;
        if (want == 0)
            return 1;
    }
    return name[FS_NAME_MAX] == 0;
}

const uint8_t *wof_fs_find(const char *name, uint32_t *len)
{
    for (uint32_t i = 0; i < fs_files; i++) {
        const uint8_t *entry = fs_blob + fs_dir + i * FS_ENTRY;

        if (!name_equal(entry, name))
            continue;

        uint32_t off = be32(entry + 32);
        uint32_t n   = be32(entry + 36);
        if (off > fs_len || n > fs_len - off)
            return 0;
        if (len)
            *len = n;
        return fs_blob + off;
    }
    return 0;
}

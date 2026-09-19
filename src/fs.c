/* The virtual file system (SPEC 3.4): the game's files, packed into one blob by
 * tools/build.py and handed to wof_init, plus the dos.library calls the ported loaders
 * make on it.
 *
 * Container layout, big-endian like everything else the project reads (SPEC 5 step 2).
 * The paths are relative to the disk's Wings_of_Fury directory, which is the original's
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
 * Lookup ignores case, because AmigaDOS does: the game asks for shapes/Torpedo.shp and
 * shapes/rank.iff where the disk has torpedo.shp and Rank.iff.
 *
 * A lock and a file handle are the same thing here, a directory index, so neither of them
 * allocates and neither can fail for want of memory.  Writes - the high-score file and
 * saved games - go to browser storage through the shell and arrive with M3. */
#include "wof.h"

#define FS_MAGIC     0x574F4653u  /* 'WOFS' */
#define FS_VERSION   1u
#define FS_NAME_MAX  32u
#define FS_ENTRY     40u
#define FS_HEADER    16u

/* dos.library error codes, as the original's callers see them (SPEC 3.4). */
#define ERROR_OBJECT_NOT_FOUND 205

static const uint8_t *fs_blob;
static uint32_t       fs_len;
static uint32_t       fs_files;
static uint32_t       fs_dir;
static int32_t        fs_ioerr;

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

static uint8_t lower(uint8_t c)
{
    return (c >= 'A' && c <= 'Z') ? (uint8_t)(c + 32) : c;
}

int wof_fs_open(const uint8_t *blob, uint32_t len)
{
    fs_blob  = 0;
    fs_len   = 0;
    fs_files = 0;
    fs_dir   = 0;
    fs_ioerr = 0;

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

static const uint8_t *entry_of(uint32_t i)
{
    return fs_blob + fs_dir + i * FS_ENTRY;
}

/* AmigaDOS compares file names without regard to case (SPEC 5 step 2). */
static int name_equal(const uint8_t *entry, const char *name)
{
    uint32_t i = 0;

    for (; i < FS_NAME_MAX; i++) {
        uint8_t want = (uint8_t)name[i];
        if (lower(entry[i]) != lower(want))
            return 0;
        if (want == 0)
            return 1;
    }
    return name[FS_NAME_MAX] == 0;
}

static int32_t find_entry(const char *name)
{
    if (!fs_blob || !name)
        return -1;
    for (uint32_t i = 0; i < fs_files; i++)
        if (name_equal(entry_of(i), name))
            return (int32_t)i;
    return -1;
}

static int entry_range(uint32_t i, uint32_t *off, uint32_t *len)
{
    const uint8_t *e = entry_of(i);
    uint32_t o = be32(e + 32);
    uint32_t n = be32(e + 36);

    if (o > fs_len || n > fs_len - o)
        return 0;
    *off = o;
    *len = n;
    return 1;
}

const uint8_t *wof_fs_find(const char *name, uint32_t *len)
{
    int32_t  i = find_entry(name);
    uint32_t off, n;

    if (i < 0 || !entry_range((uint32_t)i, &off, &n))
        return 0;
    if (len)
        *len = n;
    return fs_blob + off;
}

const char *wof_fs_name(uint32_t index, uint32_t *len)
{
    if (index >= fs_files)
        return 0;
    const uint8_t *e = entry_of(index);
    if (len) {
        uint32_t n = 0;
        while (n < FS_NAME_MAX && e[n])
            n++;
        *len = n;
    }
    return (const char *)e;
}

/* ------------------------------------------------------------------ the dos.library */

int32_t wof_dos_lock(const char *name)
{
    int32_t i = find_entry(name);

    if (i < 0)
        fs_ioerr = ERROR_OBJECT_NOT_FOUND;
    return i;
}

int32_t wof_dos_examine_size(int32_t lock)
{
    uint32_t off, len;

    if (lock < 0 || (uint32_t)lock >= fs_files || !entry_range((uint32_t)lock, &off, &len)) {
        fs_ioerr = ERROR_OBJECT_NOT_FOUND;
        return -1;
    }
    return (int32_t)len;
}

void wof_dos_unlock(int32_t lock)
{
    (void)lock;
}

int wof_dos_open(wof_file_t *f, const char *name)
{
    int32_t i = find_entry(name);

    f->entry = i;
    f->pos   = 0;
    if (i < 0) {
        fs_ioerr = ERROR_OBJECT_NOT_FOUND;
        return 0;
    }
    return 1;
}

int32_t wof_dos_read(wof_file_t *f, uint8_t *dst, int32_t n)
{
    uint32_t off, len;

    if (!f || f->entry < 0 || n <= 0)
        return 0;
    if (!entry_range((uint32_t)f->entry, &off, &len))
        return -1;
    if (f->pos >= len)
        return 0;

    uint32_t left = len - f->pos;
    uint32_t want = (uint32_t)n < left ? (uint32_t)n : left;

    wof_mem_copy(dst, fs_blob + off + f->pos, want);
    f->pos += want;
    return (int32_t)want;
}

void wof_dos_close(wof_file_t *f)
{
    if (f)
        f->entry = -1;
}

int32_t wof_dos_ioerr(void)
{
    return fs_ioerr;
}

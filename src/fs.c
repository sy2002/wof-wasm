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

/* The overlay in front of the disk: a file the game has written shadows the disk's own of
 * the same name, and a deleted one hides it.  What fills it is at the end of this file. */
#define FS_WRITE_MAX 12u          /* six slots of the dialog, the high scores, and room */
#define FS_FILE_MAX  8192u        /* a saved game is 4,258 bytes on this disk */

typedef struct {
    char     name[FS_NAME_MAX + 1];
    uint32_t len;
    uint32_t written;             /* the order files were written in: newer is larger */
    uint8_t  used;
    uint8_t  data[FS_FILE_MAX];
} fs_written_t;

static fs_written_t *written_find(const char *name);
static int           written_index(const fs_written_t *f);
static fs_written_t *written_slot(uint32_t i);
static int           is_deleted(const char *name);

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
    fs_written_t *f = written_find(name);
    int32_t  i;
    uint32_t off, n;

    if (f) {
        if (len)
            *len = f->len;
        return f->data;
    }
    if (is_deleted(name))
        return 0;
    i = find_entry(name);
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

/* A lock and a file handle are the same thing: a directory index, or -2 minus the slot of
 * a file the game has written, so that neither of them allocates. */
int32_t wof_dos_lock(const char *name)
{
    fs_written_t *f = written_find(name);
    int32_t i;

    if (f)
        return -2 - written_index(f);
    if (is_deleted(name)) {
        fs_ioerr = ERROR_OBJECT_NOT_FOUND;
        return -1;
    }
    i = find_entry(name);
    if (i < 0)
        fs_ioerr = ERROR_OBJECT_NOT_FOUND;
    return i;
}

int32_t wof_dos_examine_size(int32_t lock)
{
    uint32_t off, len;

    if (lock <= -2) {
        fs_written_t *f = written_slot((uint32_t)(-2 - lock));

        if (!f) {
            fs_ioerr = ERROR_OBJECT_NOT_FOUND;
            return -1;
        }
        return (int32_t)f->len;
    }
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
    f->entry = wof_dos_lock(name);
    f->pos   = 0;
    return f->entry != -1;
}

int32_t wof_dos_read(wof_file_t *f, uint8_t *dst, int32_t n)
{
    const uint8_t *src;
    uint32_t off, len;

    if (!f || f->entry == -1 || n <= 0)
        return 0;
    if (f->entry <= -2) {
        fs_written_t *w = written_slot((uint32_t)(-2 - f->entry));

        if (!w)
            return -1;
        src = w->data;
        len = w->len;
    } else {
        if (!entry_range((uint32_t)f->entry, &off, &len))
            return -1;
        src = fs_blob + off;
    }
    if (f->pos >= len)
        return 0;

    uint32_t left = len - f->pos;
    uint32_t want = (uint32_t)n < left ? (uint32_t)n : left;

    wof_mem_copy(dst, src + f->pos, want);
    f->pos += want;
    return (int32_t)want;
}

void wof_dos_close(wof_file_t *f)
{
    if (f)
        f->entry = -1;
}

/* is_deleted and the overlay are defined below; this keeps the read path above readable. */

int32_t wof_dos_ioerr(void)
{
    return fs_ioerr;
}

/* ------------------------------------------------------------------ the write side
 *
 * The disk is read-only ground truth, so everything the game writes - the high-score file
 * and the saved games - goes into an overlay in front of it, and the shell copies the
 * overlay into localStorage under the wof: prefix (SPEC 6.2, Storage).  A written file
 * shadows the disk's own of the same name, and a deleted one hides it; both are what
 * AmigaDOS does to the game.
 *
 * The overlay is not part of the core's state.  Files are files: a save state is a
 * snapshot of the running game, and loading one must not un-write a saved game.
 */
static fs_written_t fs_written[FS_WRITE_MAX];
static char         fs_deleted[FS_WRITE_MAX][FS_NAME_MAX + 1];
static uint32_t     fs_write_seq;
static uint32_t     fs_changes;   /* the shell watches this and stores when it moves */

static int name_same(const char *a, const char *b)
{
    uint32_t i = 0;

    for (; i < FS_NAME_MAX; i++) {
        if (lower((uint8_t)a[i]) != lower((uint8_t)b[i]))
            return 0;
        if (!a[i])
            return 1;
    }
    return a[FS_NAME_MAX] == b[FS_NAME_MAX];
}

static void name_copy(char *dst, const char *src)
{
    uint32_t i = 0;

    for (; i < FS_NAME_MAX && src[i]; i++)
        dst[i] = src[i];
    for (; i <= FS_NAME_MAX; i++)
        dst[i] = 0;
}

static fs_written_t *written_find(const char *name)
{
    if (!name)
        return 0;
    for (uint32_t i = 0; i < FS_WRITE_MAX; i++)
        if (fs_written[i].used && name_same(fs_written[i].name, name))
            return &fs_written[i];
    return 0;
}

static int written_index(const fs_written_t *f)
{
    return (int)(f - fs_written);
}

static fs_written_t *written_slot(uint32_t i)
{
    return i < FS_WRITE_MAX && fs_written[i].used ? &fs_written[i] : 0;
}

static int is_deleted(const char *name)
{
    for (uint32_t i = 0; i < FS_WRITE_MAX; i++)
        if (fs_deleted[i][0] && name_same(fs_deleted[i], name))
            return 1;
    return 0;
}

static void undelete(const char *name)
{
    for (uint32_t i = 0; i < FS_WRITE_MAX; i++)
        if (fs_deleted[i][0] && name_same(fs_deleted[i], name))
            fs_deleted[i][0] = 0;
}

void wof_fs_writes_reset(void)
{
    for (uint32_t i = 0; i < FS_WRITE_MAX; i++) {
        fs_written[i].used = 0;
        fs_written[i].len  = 0;
        fs_deleted[i][0]   = 0;
    }
    fs_write_seq = 0;
    fs_changes   = 0;
}

/* orig 0x01FE?? save_file, which is Open(MODE_NEWFILE), Write, Close.  A write replaces
 * whatever was there, under the name in the case it was given. */
int wof_fs_write(const char *name, const uint8_t *data, uint32_t len)
{
    fs_written_t *f = written_find(name);

    if (len > FS_FILE_MAX)
        return 0;
    if (!f)
        for (uint32_t i = 0; i < FS_WRITE_MAX && !f; i++)
            if (!fs_written[i].used)
                f = &fs_written[i];
    if (!f)
        return 0;

    name_copy(f->name, name);
    f->used    = 1;
    f->len     = len;
    f->written = ++fs_write_seq;
    wof_mem_copy(f->data, data, len);
    undelete(name);
    fs_changes++;
    return 1;
}

/* orig dos.DeleteFile.  Control-C deletes the high-score file with no further check
 * (re/notes/highscore.md), and a save over an edited name deletes the file it was edited
 * from (re/notes/frontend.md). */
int wof_fs_delete(const char *name)
{
    fs_written_t *f = written_find(name);
    int existed = 0;

    if (f) {
        f->used = 0;
        existed = 1;
    }
    if (find_entry(name) >= 0 && !is_deleted(name)) {
        for (uint32_t i = 0; i < FS_WRITE_MAX; i++)
            if (!fs_deleted[i][0]) {
                name_copy(fs_deleted[i], name);
                break;
            }
        existed = 1;
    }
    if (existed)
        fs_changes++;
    return existed;
}

uint32_t wof_fs_changes(void) { return fs_changes; }

/* What the shell stores and hands back.  A name of 0 ends the list. */
uint32_t wof_fs_written_count(void)
{
    uint32_t n = 0;

    for (uint32_t i = 0; i < FS_WRITE_MAX; i++)
        if (fs_written[i].used)
            n++;
    return n;
}

static fs_written_t *written_at(uint32_t index)
{
    for (uint32_t i = 0; i < FS_WRITE_MAX; i++)
        if (fs_written[i].used && index-- == 0)
            return &fs_written[i];
    return 0;
}

const char *wof_fs_written_name(uint32_t index)
{
    fs_written_t *f = written_at(index);

    return f ? f->name : 0;
}

const uint8_t *wof_fs_written_data(uint32_t index, uint32_t *len)
{
    fs_written_t *f = written_at(index);

    if (!f)
        return 0;
    if (len)
        *len = f->len;
    return f->data;
}

/* ------------------------------------------------- the game's own directory, in order
 *
 * ExNext walks a directory in the file system's own order: chain 0 upward, and inside a
 * chain from its head, where a real file system puts a new entry (re/notes/frontend.md).
 * The order follows from the names alone, so nothing has to be taken from the disk image:
 * an entry's chain is the AmigaDOS name hash modulo 72, and of two files in one chain the
 * newer comes first.  The dialog only ever shows names that begin with `wof.`, so that is
 * the whole list this has to get right.
 */
static uint16_t name_hash(const char *name)
{
    uint16_t hash = 0;

    while (name[hash])
        hash++;
    uint16_t h = hash;

    for (uint16_t i = 0; i < hash; i++) {
        uint8_t c = (uint8_t)name[i];

        if (c >= 'a' && c <= 'z')
            c = (uint8_t)(c - 32);
        h = (uint16_t)((h * 13u + c) & 0x7FFu);
    }
    return (uint16_t)(h % 72u);
}

static int begins_with_wof(const char *name)
{
    return lower((uint8_t)name[0]) == 'w' && lower((uint8_t)name[1]) == 'o'
        && lower((uint8_t)name[2]) == 'f' && name[3] == '.' && name[4] != 0;
}

/* The n-th name of the game's directory that begins with `wof.`, in ExNext order.  A file
 * the run has written comes before a file of the disk in the same chain, because it is
 * newer; two written files are ordered newest first for the same reason. */
const char *wof_fs_dir_entry(uint32_t index)
{
    const char *best;
    uint32_t    best_key;
    uint32_t    seen = 0;
    uint32_t    last_key = 0;
    const char *last = 0;

    for (;;) {
        best = 0;
        best_key = 0;
        for (uint32_t i = 0; i < FS_WRITE_MAX; i++) {
            if (!fs_written[i].used || !begins_with_wof(fs_written[i].name))
                continue;

            uint32_t key = ((uint32_t)name_hash(fs_written[i].name) << 24)
                         | (0xFFFFFFu - fs_written[i].written);

            if ((!last || key > last_key) && (!best || key < best_key)) {
                best = fs_written[i].name;
                best_key = key;
            }
        }
        for (uint32_t i = 0; i < fs_files; i++) {
            const char *name = (const char *)entry_of(i);

            if (!begins_with_wof(name) || is_deleted(name) || written_find(name))
                continue;

            uint32_t key = ((uint32_t)name_hash(name) << 24) | 0xFFFFFFu;

            if ((!last || key > last_key) && (!best || key < best_key)) {
                best = name;
                best_key = key;
            }
        }
        if (!best)
            return 0;
        if (seen++ == index)
            return best;
        last = best;
        last_key = best_key;
    }
}

uint32_t wof_fs_written_size(uint32_t index)
{
    uint32_t len = 0;

    return wof_fs_written_data(index, &len) ? len : 0;
}

const uint8_t *wof_fs_written_bytes(uint32_t index)
{
    return wof_fs_written_data(index, 0);
}

/* The shell putting back what it stored.  It is wof_fs_write, named for what it is from
 * the outside: the same call the game makes, from the other side of the page. */
int wof_fs_put(const char *name, const uint8_t *data, uint32_t len)
{
    return wof_fs_write(name, data, len);
}

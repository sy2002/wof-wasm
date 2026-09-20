/* What the port did, recorded for the differential tests (SPEC 8).
 *
 * The headless original can be watched by name: an observer records every entry of a
 * routine with its registers and stack arguments, and a test holds that observing changes
 * no step (re/notes/headless.md).  The port needs the same thing from the other side, so
 * that the two can be compared call for call: which file was opened, which song was asked
 * for, and every drawing call with its position, its pens and its draw mode.
 *
 * The recording is compiled into the native test library only.  dist/core.wasm is built
 * without WOF_TRACE and contains none of it, which is why the calls are macros that
 * disappear rather than functions that return early.
 */
#include "wof.h"

#ifdef WOF_TRACE

static wof_trace_t   records[WOF_TRACE_MAX];
static uint32_t      record_count;
static uint32_t      record_dropped;
static wof_globals_t globals_snapshot;
static int           globals_snapshot_taken;

/* The ported globals as they stand at this moment.  The front end takes one where it ends,
 * because the outer loop runs on into the next rank selection in the same pass while the
 * mission is a stand-in, and the comparison belongs at the moment the harness calls S. */
void wof_trace_globals(void)
{
    wof_mem_copy(&globals_snapshot, &wof_s.g, sizeof globals_snapshot);
    globals_snapshot_taken = 1;
}

const wof_globals_t *wof_trace_globals_at(void)
{
    return globals_snapshot_taken ? &globals_snapshot : 0;
}

void wof_trace_reset(void)
{
    record_count           = 0;
    record_dropped         = 0;
    globals_snapshot_taken = 0;
}

uint32_t wof_trace_count(void)   { return record_count; }
uint32_t wof_trace_dropped(void) { return record_dropped; }

const wof_trace_t *wof_trace_at(uint32_t i)
{
    return i < record_count ? &records[i] : 0;
}

static void copy_text(char *dst, const char *src, uint16_t len)
{
    uint16_t i = 0;

    if (src)
        for (; i < len && i < WOF_TRACE_TEXT - 1 && src[i]; i++)
            dst[i] = src[i];
    dst[i] = 0;
}

void wof_trace_add(const char *what, int32_t a, int32_t b, int32_t c, int32_t d,
                   const char *text, uint16_t len)
{
    if (record_count >= WOF_TRACE_MAX) {
        record_dropped++;
        return;
    }

    wof_trace_t *r = &records[record_count++];

    copy_text(r->what, what, 15);
    r->vblank = wof_s.vblanks;
    r->a = a;
    r->b = b;
    r->c = c;
    r->d = d;
    copy_text(r->text, text, len);
}

#endif /* WOF_TRACE */

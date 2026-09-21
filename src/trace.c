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

/* The marked stand-ins that were reached, by marker, in the order they were first reached.
 * A differential test asserts that this is empty: no script may run into code the port has
 * not got yet without the test saying so. */
#define STANDIN_MAX 64

static const char *standin_marker[STANDIN_MAX];
static uint32_t    standin_count[STANDIN_MAX];
static uint32_t    standin_used;

void wof_trace_standin(const char *marker)
{
    for (uint32_t i = 0; i < standin_used; i++)
        if (standin_marker[i] == marker) {
            standin_count[i]++;
            return;
        }
    if (standin_used < STANDIN_MAX) {
        standin_marker[standin_used] = marker;
        standin_count[standin_used++] = 1;
    }
}

uint32_t wof_trace_standins(void) { return standin_used; }

const char *wof_trace_standin_at(uint32_t i, uint32_t *count)
{
    if (i >= standin_used)
        return 0;
    if (count)
        *count = standin_count[i];
    return standin_marker[i];
}

void wof_trace_standins_reset(void)
{
    standin_used = 0;
}

/* ------------------------------------------------------------- the M4 comparisons */

/* The whole state as it stood at step S, for the setup comparison: the outer loop runs on
 * into the inner loop in the same pass, so the state has to be taken there. */
static wof_state_t mission_snapshot;
static int         mission_snapshot_taken;

void wof_trace_mission(void)
{
    wof_mem_copy(&mission_snapshot, &wof_s, sizeof mission_snapshot);
    mission_snapshot_taken = 1;
}

const wof_state_t *wof_trace_mission_state(void)
{
    return mission_snapshot_taken ? &mission_snapshot : 0;
}

/* The whole state as it stood at the end of the last pass (after flip_buffers): the loop
 * runs on into the ticks in the same wof_pass, so the comparison takes it here. */
static wof_state_t pass_snapshot;
static int         pass_snapshot_taken;

static void (*pass_hook)(uint32_t pass, uint32_t end);

void wof_test_set_pass_hook(void (*hook)(uint32_t pass, uint32_t end))
{
    pass_hook = hook;
}

/* The start of a pass, after its wait: the open-loop comparison sets the port's state here. */
void wof_test_pass_start(uint32_t pass)
{
    if (pass_hook)
        pass_hook(pass, 0);
}

void wof_trace_pass_end(void)
{
    wof_mem_copy(&pass_snapshot, &wof_s, sizeof pass_snapshot);
    pass_snapshot_taken = 1;
    if (pass_hook)
        pass_hook(wof_s.f.passes_run, 1);
}

const wof_state_t *wof_trace_pass_state(void)
{
    return pass_snapshot_taken ? &pass_snapshot : 0;
}

/* A test's hook at the end of every tick (the stand-in's and main's own), which is where
 * the half-closed comparison hands the port what the original's tick wrote. */
static void (*tick_hook)(uint32_t tick);

void wof_test_set_tick_hook(void (*hook)(uint32_t tick))
{
    tick_hook = hook;
}

void wof_test_tick_end(uint32_t tick)
{
    if (tick_hook)
        tick_hook(tick);
}

/* And one at step S, where the open-loop comparison sets the port to the original's state
 * at S, so that main's own work between S and the first pass runs on it. */
static void (*step_s_hook)(uint32_t mission);

void wof_test_set_step_s_hook(void (*hook)(uint32_t mission))
{
    step_s_hook = hook;
}

void wof_test_step_s(uint32_t mission)
{
    if (step_s_hook)
        step_s_hook(mission);
}

/* Pokes a run applies to the registered globals at the rank selection's end, which is how
 * the night mission is reached in the comparison (re/notes/porting-m4.md, "Night").  The
 * headless original's run gets the same pokes at the same point (0x01009E). */
#define POKES_MAX 8

static struct { uint32_t offset, size, value; } pokes[POKES_MAX];
static uint32_t poke_count;

void wof_test_poke(uint32_t offset, uint32_t size, uint32_t value)
{
    if (poke_count < POKES_MAX) {
        pokes[poke_count].offset = offset;
        pokes[poke_count].size   = size;
        pokes[poke_count].value  = value;
        poke_count++;
    }
}

void wof_test_pokes_clear(void)
{
    poke_count = 0;
}

void wof_test_poke_after_rank(void)
{
    for (uint32_t i = 0; i < poke_count; i++) {
        uint8_t *at = (uint8_t *)&wof_s.g + pokes[i].offset;

        for (uint32_t b = 0; b < pokes[i].size; b++)
            at[b] = (uint8_t)(pokes[i].value >> (8 * b));
    }
}

#endif /* WOF_TRACE */

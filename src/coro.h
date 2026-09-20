/* Stackless coroutines, protothreads style (SPEC 6.3).
 *
 * The original's front end blocks: it waits for VBlanks, for Delay, for the fire button,
 * for fades.  A browser page cannot block, and from file:// there is no SharedArrayBuffer
 * to block in a worker.  So every routine that can wait becomes a coroutine with a
 * switch-based resume point, and every local that lives across a wait moves into a context
 * struct.  The original's linear control flow is kept line for line; a wait becomes
 * CO_WAIT or CO_CALL.
 *
 * The unit of time is one wof_pass.  The shell calls wof_vblank once per emulated VBlank
 * and wof_pass straight after it (SPEC 6.2), and the headless original delivers a VBlank
 * exactly where the program waits, so one CO_WAIT is one VBlank and the two agree VBlank
 * for VBlank.  wof_init runs the coroutine up to its first wait, which is the work the
 * original does before its first WaitTOF; from then on pass N runs the work the original
 * does after VBlank N.
 *
 * Rules that the switch trick imposes and that this file cannot check:
 *   - a CO_ macro may not appear inside a switch of the routine's own;
 *   - a local that must survive a wait belongs in the context struct, not on the stack;
 *   - every coroutine returns wof_co_t and nothing else.
 */
#ifndef WOF_CORO_H
#define WOF_CORO_H

typedef enum { WOF_CO_WAIT = 0, WOF_CO_DONE = 1 } wof_co_t;

/* A resume point.  0 is "not started", which is what a zeroed context gives. */
#define CO_BEGIN(c)        switch ((c)->line) { case 0:
#define CO_END(c)          } (c)->line = 0; return WOF_CO_DONE

/* Give the pass back; the next one resumes here.  One CO_WAIT is one VBlank. */
#define CO_WAIT(c)         do { (c)->line = __LINE__; return WOF_CO_WAIT;                 \
                                case __LINE__:; } while (0)

/* Resume here until the condition holds.  The condition is tested at once, so a child
 * coroutine runs its first chunk in the same pass its parent reached it in. */
#define CO_WAIT_UNTIL(c, cond)                                                            \
    do { (c)->line = __LINE__; case __LINE__: if (!(cond)) return WOF_CO_WAIT; } while (0)

/* Run a child coroutine to completion.  The child's context is reset first, so a routine
 * can be called again later without carrying its old resume point. */
#define CO_CALL(c, child, call)                                                           \
    do { (child)->line = 0; CO_WAIT_UNTIL(c, (call) == WOF_CO_DONE); } while (0)

/* Leave a coroutine early. */
#define CO_RETURN(c)       do { (c)->line = 0; return WOF_CO_DONE; } while (0)

#endif /* WOF_CORO_H */

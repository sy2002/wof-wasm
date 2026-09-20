/* Motorola fast floating point, the arithmetic the game's own logic computes with.
 *
 * Three routines of the original use it, at 28 call sites, two of them inside the logic
 * tick (`re/notes/ffp.md`).  They reach `mathffp.library` through the C library's glue at
 * 0x021C9C-0x021D2E, which leaves the operands in D0 and D1 and lets the caller branch on
 * the condition codes the library's routine returns.  SPEC 7.1 forbids substituting host
 * floating point: rounding would differ and the simulation would drift.  src/ffp.c is
 * therefore an integer transliteration of mathffp 34.1's own 68000 code, and every result,
 * every register and every condition code bit agrees with the ROM (tests/test_oracle_ffp.py).
 *
 * The format is 32 bits: a 24-bit mantissa in bits 31-8, normalised so that bit 31 is set,
 * then the sign in bit 7 and a 7-bit excess-64 exponent in bits 6-0.  The value is
 * (-1)^sign x mantissa / 2^24 x 2^(exponent - 64).  A number whose exponent byte is zero
 * is zero; there is no infinity and no NaN.
 *
 * The interface M4 uses at the call sites:
 *
 *   uint32_t  y = wof_ffp_mul(a, b);        where only the result is wanted
 *   wof_ffp_t r = wof_ffp_tst_cc(x);        where the original branches on the flags,
 *   if (wof_ffp_ge(r.ccr)) ...              as 0x021A64 does with `jsr ffp_tst; bge`
 */
#ifndef WOF_FFP_H
#define WOF_FFP_H

#include <stdint.h>

/* The 68000's condition codes, in the bit positions of its status register. */
#define WOF_CCR_X 0x10u
#define WOF_CCR_N 0x08u
#define WOF_CCR_Z 0x04u
#define WOF_CCR_V 0x02u
#define WOF_CCR_C 0x01u

typedef struct {
    uint32_t d0;      /* the result, as the mathffp routine leaves D0 */
    uint32_t d1;      /* D1 at the return: only SPCmp and SPTst change it */
    uint8_t  ccr;     /* X N Z V C at the return to the caller */
    uint8_t  trap;    /* 0, or the 68000 exception the original would take here */
} wof_ffp_t;

/* SPDiv reaches `divu.w #0,d0` when the divisor's exponent byte is zero, which on a 68000
 * is the zero divide, exception vector 5.  SPEC 7.1: the port asserts in test builds. */
#define WOF_FFP_TRAP_DIVIDE_BY_ZERO 5

/* The nine operations, each as the glue entry the game calls.  d0 and d1 are the operands
 * in the registers the caller leaves them in; the unary ones take theirs where mathffp
 * does, which for SPTst is D1 and for the rest D0. */
wof_ffp_t wof_ffp_add_cc(uint32_t d0, uint32_t d1);   /* orig 0x021C9C  mathffp SPAdd */
wof_ffp_t wof_ffp_sub_cc(uint32_t d0, uint32_t d1);   /* orig 0x021CCE  mathffp SPSub */
wof_ffp_t wof_ffp_mul_cc(uint32_t d0, uint32_t d1);   /* orig 0x021CEC  mathffp SPMul */
wof_ffp_t wof_ffp_div_cc(uint32_t d0, uint32_t d1);   /* orig 0x021CD8  mathffp SPDiv */
wof_ffp_t wof_ffp_cmp_cc(uint32_t d0, uint32_t d1);   /* orig 0x021CA6  mathffp SPCmp */
wof_ffp_t wof_ffp_tst_cc(uint32_t d1);                /* orig 0x021CBA  mathffp SPTst */
wof_ffp_t wof_ffp_neg_cc(uint32_t d0);                /* orig 0x021CB0  mathffp SPNeg */
wof_ffp_t wof_ffp_fix_cc(uint32_t d0);                /* orig 0x021CC4  mathffp SPFix */
wof_ffp_t wof_ffp_flt_cc(uint32_t d0);                /* orig 0x021CE2  mathffp SPFlt */

/* How many zero divides the core has run into.  Zero in a correct run; the tests read it
 * through tests/shim.c, and a test build stops on the first one. */
extern uint32_t wof_ffp_traps;

/* ------------------------------------------------------------------ what a call site uses */

static inline uint32_t wof_ffp_add(uint32_t a, uint32_t b) { return wof_ffp_add_cc(a, b).d0; }
static inline uint32_t wof_ffp_sub(uint32_t a, uint32_t b) { return wof_ffp_sub_cc(a, b).d0; }
static inline uint32_t wof_ffp_mul(uint32_t a, uint32_t b) { return wof_ffp_mul_cc(a, b).d0; }
static inline uint32_t wof_ffp_div(uint32_t a, uint32_t b) { return wof_ffp_div_cc(a, b).d0; }
static inline uint32_t wof_ffp_neg(uint32_t a)             { return wof_ffp_neg_cc(a).d0; }
static inline uint32_t wof_ffp_fix(uint32_t a)             { return wof_ffp_fix_cc(a).d0; }
static inline uint32_t wof_ffp_flt(uint32_t a)             { return wof_ffp_flt_cc(a).d0; }
static inline int32_t  wof_ffp_cmp(uint32_t a, uint32_t b)
{
    return (int32_t)wof_ffp_cmp_cc(a, b).d0;
}
static inline int32_t  wof_ffp_tst(uint32_t a)             { return (int32_t)wof_ffp_tst_cc(a).d0; }

/* The branches the original makes on the returned condition codes, as the 68000 tests
 * them.  A caller writes `if (wof_ffp_ge(r.ccr))` where the listing has `bge`. */
static inline int wof_ffp_n(uint8_t ccr)  { return (ccr & WOF_CCR_N) != 0; }
static inline int wof_ffp_v(uint8_t ccr)  { return (ccr & WOF_CCR_V) != 0; }
static inline int wof_ffp_eq(uint8_t ccr) { return (ccr & WOF_CCR_Z) != 0; }
static inline int wof_ffp_ne(uint8_t ccr) { return (ccr & WOF_CCR_Z) == 0; }
static inline int wof_ffp_lt(uint8_t ccr) { return wof_ffp_n(ccr) != wof_ffp_v(ccr); }
static inline int wof_ffp_ge(uint8_t ccr) { return wof_ffp_n(ccr) == wof_ffp_v(ccr); }
static inline int wof_ffp_gt(uint8_t ccr) { return wof_ffp_ge(ccr) && wof_ffp_ne(ccr); }
static inline int wof_ffp_le(uint8_t ccr) { return wof_ffp_lt(ccr) || wof_ffp_eq(ccr); }
static inline int wof_ffp_mi(uint8_t ccr) { return wof_ffp_n(ccr); }
static inline int wof_ffp_pl(uint8_t ccr) { return !wof_ffp_n(ccr); }

#endif

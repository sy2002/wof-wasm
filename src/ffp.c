/* Motorola fast floating point in integer code (SPEC 7.1, SPEC 10 point 13).
 *
 * The game computes with mathffp.library, so the port has to give the same 32 bits and the
 * same condition codes for every operand the original can produce; a host float would
 * round differently and the simulation would drift apart from the original within a few
 * ticks.  What follows is therefore a transliteration of mathffp 34.1's own 68000 code,
 * instruction for instruction, with the ROM address of each line in the comment.  The
 * helpers above the routines are the 68000 instructions those routines are made of, each
 * with exactly the condition codes that instruction writes: SPAdd reads the X bit back
 * with `roxr` and SPMul with `addx`, so X cannot simply be recomputed at the end.
 *
 * Two entry conventions come out of the glue at 0x021C9C-0x021D2E (re/notes/ffp.md):
 *
 *   * The operands stay in D0 and D1 as the caller left them.  SPTst takes its one operand
 *     in D1, the other unary ones in D0.  Only SPCmp and SPTst write D1.
 *   * D3, D4 and D5 are saved and restored by the routines that use them, and the bits of
 *     them that mathffp leaves uninitialised never reach a result or a flag, so they start
 *     at zero here.  A test feeds the original random values in those registers and holds
 *     both sides to the same answer.
 *   * X at the entry is the caller's.  Several paths return without writing it - SPNeg's
 *     zero, SPAdd's "the other operand is zero", SPCmp and SPTst throughout - so the
 *     condition codes they return carry it through.  The glue leaves X alone, so it is the
 *     X of the game's own call site; nothing in the original branches on it.  Here it is
 *     zero at the entry, which is what the differential test sets up on the other side.
 */
#include "ffp.h"

uint32_t wof_ffp_traps;

#define FX WOF_CCR_X
#define FN WOF_CCR_N
#define FZ WOF_CCR_Z
#define FV WOF_CCR_V
#define FC WOF_CCR_C

#define M8  0x000000FFu
#define M16 0x0000FFFFu
#define M32 0xFFFFFFFFu
#define B8  0x00000080u
#define B16 0x00008000u
#define B32 0x80000000u

/* ------------------------------------------------------------------ the instructions */

/* move, tst, clr, and, or, eor: N and Z from the operand, V and C cleared, X untouched. */
static uint8_t ins_nz(uint32_t v, uint32_t mask, uint32_t msb, uint8_t cc)
{
    return (uint8_t)((cc & FX) | ((v & mask & msb) ? FN : 0) | ((v & mask) ? 0 : FZ));
}

static uint32_t ins_move(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t r = (dst & ~mask) | (src & mask);

    *cc = ins_nz(r, mask, msb, *cc);
    return r;
}

static uint32_t ins_clr(uint32_t dst, uint32_t mask, uint8_t *cc)
{
    *cc = (uint8_t)((*cc & FX) | FZ);
    return dst & ~mask;
}

static uint32_t ins_eor(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t r = (dst & ~mask) | ((dst ^ src) & mask);

    *cc = ins_nz(r, mask, msb, *cc);
    return r;
}

static uint32_t ins_or(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t r = dst | (src & mask);

    *cc = ins_nz(r, mask, msb, *cc);
    return r;
}

static uint32_t ins_moveq(int32_t imm, uint8_t *cc)
{
    uint32_t r = (uint32_t)imm;

    *cc = ins_nz(r, M32, B32, *cc);
    return r;
}

static uint32_t ins_add(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t a = dst & mask, b = src & mask, r = (a + b) & mask;
    uint8_t f = 0;

    if (r & msb)                    f |= FN;
    if (r == 0)                     f |= FZ;
    if ((~(a ^ b) & (a ^ r)) & msb) f |= FV;
    if (r < a)                      f |= (uint8_t)(FC | FX);
    *cc = f;
    return (dst & ~mask) | r;
}

static uint32_t ins_sub(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t a = dst & mask, b = src & mask, r = (a - b) & mask;
    uint8_t f = 0;

    if (r & msb)                   f |= FN;
    if (r == 0)                    f |= FZ;
    if (((a ^ b) & (a ^ r)) & msb) f |= FV;
    if (b > a)                     f |= (uint8_t)(FC | FX);
    *cc = f;
    return (dst & ~mask) | r;
}

/* cmp is sub without the result and without X. */
static void ins_cmp(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint8_t keep = (uint8_t)(*cc & FX);

    ins_sub(dst, src, mask, msb, cc);
    *cc = (uint8_t)((*cc & ~FX) | keep);
}

/* addx: as add with the X bit, and Z is only ever cleared, never set. */
static uint32_t ins_addx(uint32_t dst, uint32_t src, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t a = dst & mask, b = src & mask, x = (*cc & FX) ? 1u : 0u;
    uint32_t r = (a + b + x) & mask;
    uint8_t f = (uint8_t)(*cc & FZ);

    if (r & msb)                    f |= FN;
    if (r != 0)                     f &= (uint8_t)~FZ;
    if ((~(a ^ b) & (a ^ r)) & msb) f |= FV;
    if ((uint64_t)a + b + x > mask) f |= (uint8_t)(FC | FX);
    *cc = f;
    return (dst & ~mask) | r;
}

static uint32_t ins_neg(uint32_t dst, uint32_t mask, uint32_t msb, uint8_t *cc)
{
    uint32_t a = dst & mask, r = (0u - a) & mask;
    uint8_t f = 0;

    if (r & msb)          f |= FN;
    if (r == 0)           f |= FZ;
    if ((a & r) & msb)    f |= FV;              /* only the most negative value overflows */
    if (a != 0)           f |= (uint8_t)(FC | FX);
    *cc = f;
    return (dst & ~mask) | r;
}

/* swap: the condition codes are those of the whole long afterwards. */
static uint32_t ins_swap(uint32_t d, uint8_t *cc)
{
    uint32_t r = (d >> 16) | (d << 16);

    *cc = ins_nz(r, M32, B32, *cc);
    return r;
}

/* lsr.l with a register or an immediate count.  A count of zero writes no C and no X. */
static uint32_t ins_lsr_l(uint32_t d, uint32_t count, uint8_t *cc)
{
    uint8_t f = (uint8_t)(*cc & FX);
    uint32_t r;

    count &= 63u;
    if (count == 0) {
        *cc = ins_nz(d, M32, B32, *cc);
        return d;
    }
    r = count >= 32 ? 0u : d >> count;
    if (count <= 32 && ((d >> (count - 1)) & 1u))
        f |= (uint8_t)(FC | FX);
    else
        f &= (uint8_t)~(FC | FX);
    if (r == 0)
        f |= FZ;
    *cc = f;                                    /* N is always clear: bit 31 shifts in as 0 */
    return r;
}

static uint32_t ins_lsr_w(uint32_t d, uint8_t *cc)
{
    uint32_t w = d & M16, r = w >> 1;
    uint8_t f = 0;

    if (r == 0)  f |= FZ;
    if (w & 1u)  f |= (uint8_t)(FC | FX);
    *cc = f;
    return (d & ~M16) | r;
}

static uint32_t ins_ror_w(uint32_t d, uint8_t *cc)
{
    uint32_t w = d & M16, r = ((w >> 1) | (w << 15)) & M16;
    uint8_t f = (uint8_t)(*cc & FX);

    if (r & B16) f |= FN;
    if (r == 0)  f |= FZ;
    if (w & 1u)  f |= FC;
    *cc = f;
    return (d & ~M16) | r;
}

static uint32_t ins_ror_l(uint32_t d, uint8_t *cc)
{
    uint32_t r = (d >> 1) | (d << 31);
    uint8_t f = (uint8_t)(*cc & FX);

    if (r & B32) f |= FN;
    if (r == 0)  f |= FZ;
    if (d & 1u)  f |= FC;
    *cc = f;
    return r;
}

static uint32_t ins_roxr_l(uint32_t d, uint8_t *cc)
{
    uint32_t x = (*cc & FX) ? B32 : 0u, r = (d >> 1) | x;
    uint8_t f = 0;

    if (r & B32) f |= FN;
    if (r == 0)  f |= FZ;
    if (d & 1u)  f |= (uint8_t)(FC | FX);
    *cc = f;
    return r;
}

static uint32_t ins_mulu_w(uint32_t dst, uint32_t src, uint8_t *cc)
{
    uint32_t r = (dst & M16) * (src & M16);

    *cc = ins_nz(r, M32, B32, *cc);
    return r;
}

/* divu.w.  A quotient that does not fit in 16 bits sets V and leaves the destination
 * alone; the 68000 leaves N and Z undefined there, and this keeps them as they were.  A
 * zero divisor is the zero divide exception again, which SPDiv reaches for a divisor whose
 * mantissa is below 0x100: after the swap its high word, which is what it divides by, is
 * zero.  An unnormalised operand is the only way to get there. */
static uint32_t ins_divu_w(uint32_t dst, uint32_t src, uint8_t *cc, uint8_t *trap)
{
    uint32_t divisor = src & M16, quotient, remainder;

    if (divisor == 0) {
        *trap = WOF_FFP_TRAP_DIVIDE_BY_ZERO;
        return dst;
    }
    quotient = dst / divisor;
    if (quotient > M16) {
        *cc = (uint8_t)((*cc & (FX | FN | FZ)) | FV);
        return dst;
    }
    remainder = dst % divisor;
    *cc = ins_nz(quotient, M16, B16, *cc);
    return (remainder << 16) | quotient;
}

static wof_ffp_t out(uint32_t d0, uint32_t d1, uint8_t cc, uint8_t trap)
{
    wof_ffp_t r;

    r.d0 = d0;
    r.d1 = d1;
    r.ccr = (uint8_t)(cc & 0x1Fu);
    r.trap = trap;
    return r;
}

/* --------------------------------------------------------- SPFix, orig glue 0x021CC4 */

wof_ffp_t wof_ffp_fix_cc(uint32_t d0, uint32_t d1)
{
    uint8_t cc = 0;

    d1 = ins_move(d1, d0, M8, B8, &cc);                     /* fe3ed4 move.b d0,d1 */
    if (cc & FN) goto negative;                             /* fe3ed6 bmi */
    if (cc & FZ) goto done;                                 /* fe3ed8 beq */
    d0 = ins_clr(d0, M8, &cc);                              /* fe3eda clr.b d0 */
    d1 = ins_sub(d1, 0x41u, M8, B8, &cc);                   /* fe3edc subi.b #$41,d1 */
    if (cc & FN) goto too_small;                            /* fe3ee0 bmi */
    d1 = ins_sub(d1, 0x1Fu, M8, B8, &cc);                   /* fe3ee2 subi.b #$1f,d1 */
    if (!(cc & FN)) goto too_big;                           /* fe3ee6 bpl */
    d1 = ins_neg(d1, M8, B8, &cc);                          /* fe3ee8 neg.b d1 */
    d0 = ins_lsr_l(d0, d1, &cc);                            /* fe3eea lsr.l d1,d0 */
done:
    return out(d0, d1, cc, 0);                              /* fe3eec rts */

too_big:
    d0 = ins_moveq(-1, &cc);                                /* fe3eee moveq #$ff,d0 */
    d0 = ins_lsr_l(d0, 1u, &cc);                            /* fe3ef0 lsr.l #1,d0 */
    cc |= FV;                                               /* fe3ef2 ori.b #$2,ccr */
    return out(d0, d1, cc, 0);                              /* fe3ef6 rts */

too_small:
    d0 = ins_moveq(0, &cc);                                 /* fe3ef8 moveq #0,d0 */
    return out(d0, d1, cc, 0);                              /* fe3efa rts */

negative:
    d0 = ins_clr(d0, M8, &cc);                              /* fe3efc clr.b d0 */
    d1 = ins_sub(d1, 0xC1u, M8, B8, &cc);                   /* fe3efe subi.b #$c1,d1 */
    if (cc & FN) goto too_small;                            /* fe3f02 bmi */
    d1 = ins_sub(d1, 0x1Fu, M8, B8, &cc);                   /* fe3f04 subi.b #$1f,d1 */
    if (!(cc & FN)) {                                       /* fe3f08 bpl */
        if (!(cc & FZ)) goto most_negative;                 /* fe3f12 bne */
        d0 = ins_neg(d0, M32, B32, &cc);                    /* fe3f14 neg.l d0 */
        cc = ins_nz(d0, M32, B32, cc);                      /* fe3f16 tst.l d0 */
        if (cc & FN) goto done;                             /* fe3f18 bmi */
most_negative:
        d0 = ins_moveq(0, &cc);                             /* fe3f1a moveq #0,d0 */
        cc = (uint8_t)((cc & ~FZ) | ((d0 & B32) ? 0 : FZ)); /* fe3f1c bset #31,d0: Z is the */
        d0 |= B32;                                          /*        bit as it was */
        cc |= FV;                                           /* fe3f20 ori.b #$2,ccr */
        return out(d0, d1, cc, 0);                          /* fe3f24 rts */
    }
    d1 = ins_neg(d1, M8, B8, &cc);                          /* fe3f0a neg.b d1 */
    d0 = ins_lsr_l(d0, d1, &cc);                            /* fe3f0c lsr.l d1,d0 */
    d0 = ins_neg(d0, M32, B32, &cc);                        /* fe3f0e neg.l d0 */
    return out(d0, d1, cc, 0);                              /* fe3f10 rts */
}

/* --------------------------------------------------------- SPFlt, orig glue 0x021CE2 */

wof_ffp_t wof_ffp_flt_cc(uint32_t d0, uint32_t d1)
{
    uint8_t cc = 0;

    (void)d1;                                               /* moveq #$5f,d1 overwrites it */

    d1 = ins_moveq(0x5F, &cc);                              /* fe3f28 moveq #$5f,d1 */
    cc = ins_nz(d0, M32, B32, cc);                          /* fe3f2a tst.l d0 */
    if (cc & FZ) goto done;                                 /* fe3f2c beq */
    if (!(cc & FN)) goto positive;                          /* fe3f2e bpl */
    d1 = ins_moveq(-0x20, &cc);                             /* fe3f30 moveq #$e0,d1 */
    d0 = ins_neg(d0, M32, B32, &cc);                        /* fe3f32 neg.l d0 */
    if (cc & FV) goto exponent;                             /* fe3f34 bvs */
    d1 = ins_sub(d1, 1u, M8, B8, &cc);                      /* fe3f36 subq.b #1,d1 */
positive:
    ins_cmp(d0, 0x7FFFu, M32, B32, &cc);                    /* fe3f38 cmpi.l #$7fff,d0 */
    if (!((cc & FC) || (cc & FZ))) goto shift;              /* fe3f3e bhi */
    d0 = ins_swap(d0, &cc);                                 /* fe3f40 swap d0 */
    d1 = ins_sub(d1, 0x10u, M8, B8, &cc);                   /* fe3f42 subi.b #$10,d1 */
shift:
    for (;;) {
        d0 = ins_add(d0, d0, M32, B32, &cc);                /* fe3f46 add.l d0,d0 */
        if (cc & FN) break;                                 /* fe3f48 dbmi d1,fe3f46 */
        d1 = (d1 & ~M16) | ((d1 - 1u) & M16);
        if ((d1 & M16) == M16) break;
    }
    cc = ins_nz(d0, M8, B8, cc);                            /* fe3f4c tst.b d0 */
    if (!(cc & FN)) goto exponent;                          /* fe3f4e bpl */
    d0 = ins_add(d0, 0x100u, M32, B32, &cc);                /* fe3f50 addi.l #$100,d0 */
    if (!(cc & FC)) goto exponent;                          /* fe3f56 bcc */
    d0 = ins_roxr_l(d0, &cc);                               /* fe3f58 roxr.l #1,d0 */
    d1 = ins_add(d1, 1u, M8, B8, &cc);                      /* fe3f5a addq.b #1,d1 */
exponent:
    d0 = ins_move(d0, d1, M8, B8, &cc);                     /* fe3f5c move.b d1,d0 */
done:
    return out(d0, d1, cc, 0);                              /* fe3f5e rts */
}

/* ------------------------------------------- SPCmp and SPTst, orig glue 0x021CA6, 0x021CBA
 *
 * Both compare, capture the condition codes with exec.GetCC because `move sr` is
 * privileged from the 68010 on, turn them into -1, 0 or +1 in D0 and then put them back,
 * so a caller can branch on the comparison itself.  D1 keeps its high word and carries the
 * captured codes in its low word.  SPCmp answers a smaller first operand with +1 and a
 * larger one with -1; SPTst is the other way round.  Neither touches X, so the X the
 * caller had comes back out. */

static wof_ffp_t ffp_getcc_tail(uint32_t d1, uint8_t cc)
{
    uint32_t d0;
    uint8_t captured = (uint8_t)(cc & 0x1Fu);               /* fe3f80 jsr GetCC: sr & 0xff */

    d1 = (d1 & ~M16) | captured;                            /* fe3f86 move.w d0,d1 */
    d0 = 0;                                                 /* fe3f88 moveq #0,d0 */
    cc = captured;                                          /* fe3f8a move.w d1,ccr */
    return out(d0, d1, cc, 0);
}

wof_ffp_t wof_ffp_cmp_cc(uint32_t d0, uint32_t d1)
{
    uint8_t cc = 0;
    wof_ffp_t r;

    cc = ins_nz(d1, M8, B8, cc);                            /* fe3f60 tst.b d1 */
    if (cc & FN) {                                          /* fe3f62 bpl */
        cc = ins_nz(d0, M8, B8, cc);                        /* fe3f64 tst.b d0 */
        if (cc & FN) {                                      /* fe3f66 bpl */
            ins_cmp(d1, d0, M8, B8, &cc);                   /* fe3f68 cmp.b d0,d1 */
            if (cc & FZ)                                    /* fe3f6a bne */
                ins_cmp(d1, d0, M32, B32, &cc);             /* fe3f6c cmp.l d0,d1 */
            goto tail;                                      /* fe3f6e bra */
        }
    }
    ins_cmp(d0, d1, M8, B8, &cc);                           /* fe3f70 cmp.b d1,d0 */
    if (cc & FZ)                                            /* fe3f72 bne */
        ins_cmp(d0, d1, M32, B32, &cc);                     /* fe3f74 cmp.l d1,d0 */
tail:
    r = ffp_getcc_tail(d1, cc);
    if (wof_ffp_lt(r.ccr))      r.d0 = 1u;                  /* fe3f8c blt -> fe3f96 addq.l */
    else if (wof_ffp_gt(r.ccr)) r.d0 = M32;                 /* fe3f8e bgt -> fe3f92 subq.l */
    return r;                                               /* fe3f98 move.w d1,ccr; rts */
}

wof_ffp_t wof_ffp_tst_cc(uint32_t d0, uint32_t d1)
{
    uint8_t cc = 0;
    wof_ffp_t r;

    (void)d0;                                               /* moveq #0,d0 overwrites it */

    cc = ins_nz(d1, M8, B8, cc);                            /* fe3f9c tst.b d1 */
    r = ffp_getcc_tail(d1, cc);
    if (wof_ffp_lt(r.ccr))      r.d0 = M32;                 /* fe3fb4 blt -> fe3fba subq.l */
    else if (wof_ffp_gt(r.ccr)) r.d0 = 1u;                  /* fe3fb6 bgt -> fe3fbe addq.l */
    return r;                                               /* fe3fc0 move.w d1,ccr; rts */
}

/* --------------------------------------------------------- SPNeg, orig glue 0x021CB0 */

wof_ffp_t wof_ffp_neg_cc(uint32_t d0, uint32_t d1)
{
    uint8_t cc = 0;

    cc = ins_nz(d0, M8, B8, cc);                            /* fe3fca tst.b d0 */
    if (!(cc & FZ))                                         /* fe3fcc beq */
        d0 = ins_eor(d0, 0x80u, M8, B8, &cc);               /* fe3fce eori.b #$80,d0 */
    return out(d0, d1, cc, 0);                              /* fe3fd2 rts */
}

/* ------------------------------------------- SPAdd and SPSub, orig glue 0x021C9C, 0x021CCE
 *
 * SPSub flips the sign of the second operand and joins SPAdd; the two entries differ only
 * in the order of the tests that get them there, because a zero exponent byte must be
 * recognised before the flip turns it into a negative zero. */

static wof_ffp_t ffp_addsub(uint32_t d0, uint32_t d1, int subtract)
{
    uint32_t d3 = 0, d4 = 0, d5 = 0;
    uint8_t cc = 0;

    if (subtract) {
        d4 = ins_move(d4, d1, M8, B8, &cc);                 /* fe3fd8 move.b d1,d4 */
        if (cc & FZ) goto result_a;                         /* fe3fda beq */
        d4 = ins_eor(d4, 0x80u, M8, B8, &cc);               /* fe3fdc eori.b #$80,d4 */
        if (cc & FN) goto b_negative;                       /* fe3fe0 bmi */
        d5 = ins_move(d5, d0, M8, B8, &cc);                 /* fe3fe4 move.b d0,d5 */
        if (cc & FN) goto opposite_signs;                   /* fe3fe6 bmi */
        if (cc & FZ) goto result_b;                         /* fe3fea bne / fe3fec bra */
    } else {
        d4 = ins_move(d4, d1, M8, B8, &cc);                 /* fe3ff2 move.b d1,d4 */
        if (cc & FN) goto b_negative;                       /* fe3ff4 bmi */
        if (cc & FZ) goto result_a;                         /* fe3ff6 beq */
        d5 = ins_move(d5, d0, M8, B8, &cc);                 /* fe3ff8 move.b d0,d5 */
        if (cc & FN) goto opposite_signs;                   /* fe3ffa bmi */
        if (cc & FZ) goto result_b;                         /* fe3ffc beq */
    }

same_sign:
    d5 = ins_sub(d5, d4, M8, B8, &cc);                      /* fe3ffe sub.b d4,d5 */
    if (cc & FN) goto b_is_bigger;                          /* fe4000 bmi */
    d4 = ins_move(d4, d0, M8, B8, &cc);                     /* fe4002 move.b d0,d4 */
    ins_cmp(d5, 0x18u, M8, B8, &cc);                        /* fe4004 cmpi.b #$18,d5 */
    if (!(cc & FC)) goto result_a;                          /* fe4008 bcc */
    d3 = ins_move(d3, d1, M32, B32, &cc);                   /* fe400a move.l d1,d3 */
    d3 = ins_clr(d3, M8, &cc);                              /* fe400c clr.b d3 */
    d3 = ins_lsr_l(d3, d5, &cc);                            /* fe400e lsr.l d5,d3 */
    d0 = ins_move(d0, 0x80u, M8, B8, &cc);                  /* fe4010 move.b #$80,d0 */
    d0 = ins_add(d0, d3, M32, B32, &cc);                    /* fe4014 add.l d3,d0 */
    if (cc & FC) goto carried;                              /* fe4016 bcs */
restore_exponent:
    d0 = ins_move(d0, d4, M8, B8, &cc);                     /* fe4018 move.b d4,d0 */
    return out(d0, d1, cc, 0);                              /* fe401e rts */

carried:
    d0 = ins_roxr_l(d0, &cc);                               /* fe4020 roxr.l #1,d0 */
    d4 = ins_add(d4, 1u, M8, B8, &cc);                      /* fe4022 addq.b #1,d4 */
    if (!(cc & FV) && !(cc & FC)) goto restore_exponent;    /* fe4024 bvs / fe4026 bcc */
    d0 = ins_moveq(-1, &cc);                                /* fe4028 moveq #$ff,d0 */
    d4 = ins_sub(d4, 1u, M8, B8, &cc);                      /* fe402a subq.b #1,d4 */
    d0 = ins_move(d0, d4, M8, B8, &cc);                     /* fe402c move.b d4,d0 */
    cc |= FV;                                               /* fe402e ori.b #$2,ccr */
    return out(d0, d1, cc, 0);                              /* fe4036 rts */

result_b:
    d0 = ins_move(d0, d1, M32, B32, &cc);                   /* fe4038 move.l d1,d0 */
    d0 = ins_move(d0, d4, M8, B8, &cc);                     /* fe403a move.b d4,d0 */
    return out(d0, d1, cc, 0);                              /* fe4040 rts */

result_a:
    cc = ins_nz(d0, M8, B8, cc);                            /* fe4042 tst.b d0 */
    return out(d0, d1, cc, 0);                              /* fe4048 rts */

b_is_bigger:
    ins_cmp(d5, 0xE8u, M8, B8, &cc);                        /* fe404a cmpi.b #$e8,d5 */
    if (wof_ffp_le(cc)) goto result_b;                      /* fe404e ble */
    d5 = ins_neg(d5, M8, B8, &cc);                          /* fe4050 neg.b d5 */
    d3 = ins_move(d3, d1, M32, B32, &cc);                   /* fe4052 move.l d1,d3 */
    d0 = ins_clr(d0, M8, &cc);                              /* fe4054 clr.b d0 */
    d0 = ins_lsr_l(d0, d5, &cc);                            /* fe4056 lsr.l d5,d0 */
    d3 = ins_move(d3, 0x80u, M8, B8, &cc);                  /* fe4058 move.b #$80,d3 */
    d0 = ins_add(d0, d3, M32, B32, &cc);                    /* fe405c add.l d3,d0 */
    if (cc & FC) goto carried;                              /* fe405e bcs */
    d0 = ins_move(d0, d4, M8, B8, &cc);                     /* fe4060 move.b d4,d0 */
    return out(d0, d1, cc, 0);                              /* fe4066 rts */

b_negative:
    d5 = ins_move(d5, d0, M8, B8, &cc);                     /* fe4068 move.b d0,d5 */
    if (cc & FN) goto same_sign;                            /* fe406a bmi */
    if (cc & FZ) goto result_b;                             /* fe406c beq */
opposite_signs:
    d3 = ins_moveq(-0x80, &cc);                             /* fe406e moveq #$80,d3 */
    d5 = ins_eor(d5, d3, M8, B8, &cc);                      /* fe4070 eor.b d3,d5 */
    d5 = ins_sub(d5, d4, M8, B8, &cc);                      /* fe4072 sub.b d4,d5 */
    if (cc & FZ) goto equal_exponents;                      /* fe4074 beq */
    if (cc & FN) goto a_is_smaller;                         /* fe4076 bmi */
    ins_cmp(d5, 0x18u, M8, B8, &cc);                        /* fe4078 cmpi.b #$18,d5 */
    if (!(cc & FC)) goto result_a;                          /* fe407c bcc */
    d4 = ins_move(d4, d0, M8, B8, &cc);                     /* fe407e move.b d0,d4 */
    d0 = ins_move(d0, d3, M8, B8, &cc);                     /* fe4080 move.b d3,d0 */
    d3 = ins_move(d3, d1, M32, B32, &cc);                   /* fe4082 move.l d1,d3 */
subtract_aligned:
    d3 = ins_clr(d3, M8, &cc);                              /* fe4084 clr.b d3 */
    d3 = ins_lsr_l(d3, d5, &cc);                            /* fe4086 lsr.l d5,d3 */
    d0 = ins_sub(d0, d3, M32, B32, &cc);                    /* fe4088 sub.l d3,d0 */
    if (cc & FN) goto restore_exponent;                     /* fe408a bmi */
    d5 = ins_move(d5, d4, M8, B8, &cc);                     /* fe408c move.b d4,d5 */
renormalise:
    d0 = ins_clr(d0, M8, &cc);                              /* fe408e clr.b d0 */
    d4 = ins_sub(d4, 1u, M8, B8, &cc);                      /* fe4090 subq.b #1,d4 */
    ins_cmp(d0, 0x7FFFu, M32, B32, &cc);                    /* fe4092 cmpi.l #$7fff,d0 */
    if ((cc & FC) || (cc & FZ)) {                           /* fe4098 bhi */
        d0 = ins_swap(d0, &cc);                             /* fe409a swap d0 */
        d4 = ins_sub(d4, 0x10u, M8, B8, &cc);               /* fe409c subi.b #$10,d4 */
    }
    for (;;) {
        d0 = ins_add(d0, d0, M32, B32, &cc);                /* fe40a0 add.l d0,d0 */
        if (cc & FN) break;                                 /* fe40a2 dbmi d4,fe40a0 */
        d4 = (d4 & ~M16) | ((d4 - 1u) & M16);
        if ((d4 & M16) == M16) break;
    }
    d5 = ins_eor(d5, d4, M8, B8, &cc);                      /* fe40a6 eor.b d4,d5 */
    if (cc & FN) goto zero;                                 /* fe40a8 bmi */
    d0 = ins_move(d0, d4, M8, B8, &cc);                     /* fe40aa move.b d4,d0 */
    if (cc & FZ) goto zero;                                 /* fe40ac beq */
    return out(d0, d1, cc, 0);                              /* fe40b2 rts */

zero:
    d0 = ins_moveq(0, &cc);                                 /* fe40b4 moveq #0,d0 */
    return out(d0, d1, cc, 0);                              /* fe40ba rts */

a_is_smaller:
    ins_cmp(d5, 0xE8u, M8, B8, &cc);                        /* fe40bc cmpi.b #$e8,d5 */
    if (wof_ffp_le(cc)) goto result_b;                      /* fe40c0 ble */
    d5 = ins_neg(d5, M8, B8, &cc);                          /* fe40c4 neg.b d5 */
    d3 = ins_move(d3, d0, M32, B32, &cc);                   /* fe40c6 move.l d0,d3 */
    d0 = ins_move(d0, d1, M32, B32, &cc);                   /* fe40c8 move.l d1,d0 */
    d0 = ins_move(d0, 0x80u, M8, B8, &cc);                  /* fe40ca move.b #$80,d0 */
    goto subtract_aligned;                                  /* fe40ce bra */

equal_exponents:
    d5 = ins_move(d5, d0, M8, B8, &cc);                     /* fe40d0 move.b d0,d5 */
    {                                                       /* fe40d2 exg.l d5,d4 */
        uint32_t t = d5;
        d5 = d4;
        d4 = t;
    }
    d0 = ins_move(d0, d1, M8, B8, &cc);                     /* fe40d4 move.b d1,d0 */
    d0 = ins_sub(d0, d1, M32, B32, &cc);                    /* fe40d6 sub.l d1,d0 */
    if (cc & FZ) goto zero;                                 /* fe40d8 beq */
    if (!(cc & FN)) {                                       /* fe40da bpl */
        d5 = ins_move(d5, d4, M8, B8, &cc);                 /* fe408c move.b d4,d5 */
        goto renormalise;
    }
    d0 = ins_neg(d0, M32, B32, &cc);                        /* fe40dc neg.l d0 */
    d4 = ins_move(d4, d5, M8, B8, &cc);                     /* fe40de move.b d5,d4 */
    goto renormalise;                                       /* fe40e0 bra fe408e */
}

wof_ffp_t wof_ffp_add_cc(uint32_t d0, uint32_t d1) { return ffp_addsub(d0, d1, 0); }
wof_ffp_t wof_ffp_sub_cc(uint32_t d0, uint32_t d1) { return ffp_addsub(d0, d1, 1); }

/* --------------------------------------------------------- SPMul, orig glue 0x021CEC */

wof_ffp_t wof_ffp_mul_cc(uint32_t d0, uint32_t d1)
{
    uint32_t d3 = 0, d4 = 0, d5 = 0;
    uint8_t cc = 0;

    d5 = ins_move(d5, d0, M8, B8, &cc);                     /* fe40e8 move.b d0,d5 */
    if (cc & FZ) return out(d0, d1, cc, 0);                 /* fe40ea beq -> fe413e rts */
    d4 = ins_move(d4, d1, M8, B8, &cc);                     /* fe40ec move.b d1,d4 */
    if (cc & FZ) goto zero;                                 /* fe40ee beq */
    d5 = ins_add(d5, d5, M16, B16, &cc);                    /* fe40f0 add.w d5,d5 */
    d4 = ins_add(d4, d4, M16, B16, &cc);                    /* fe40f2 add.w d4,d4 */
    d3 = ins_moveq(-0x80, &cc);                             /* fe40f4 moveq #$80,d3 */
    d4 = ins_eor(d4, d3, M8, B8, &cc);                      /* fe40f6 eor.b d3,d4 */
    d5 = ins_eor(d5, d3, M8, B8, &cc);                      /* fe40f8 eor.b d3,d5 */
    d5 = ins_add(d5, d4, M8, B8, &cc);                      /* fe40fa add.b d4,d5 */
    if (cc & FV) goto exponent_overflow;                    /* fe40fc bvs */
    d4 = ins_move(d4, d3, M8, B8, &cc);                     /* fe40fe move.b d3,d4 */
    d5 = ins_eor(d5, d4, M16, B16, &cc);                    /* fe4100 eor.w d4,d5 */
    d5 = ins_ror_w(d5, &cc);                                /* fe4102 ror.w #1,d5 */
    d5 = ins_swap(d5, &cc);                                 /* fe4104 swap d5 */
    d5 = ins_move(d5, d1, M16, B16, &cc);                   /* fe4106 move.w d1,d5 */
    d0 = ins_clr(d0, M8, &cc);                              /* fe4108 clr.b d0 */
    d5 = ins_clr(d5, M8, &cc);                              /* fe410a clr.b d5 */
    d4 = ins_move(d4, d5, M16, B16, &cc);                   /* fe410c move.w d5,d4 */
    d4 = ins_mulu_w(d4, d0, &cc);                           /* fe410e mulu.w d0,d4 */
    d4 = ins_swap(d4, &cc);                                 /* fe4110 swap d4 */
    d3 = ins_move(d3, d0, M32, B32, &cc);                   /* fe4112 move.l d0,d3 */
    d3 = ins_swap(d3, &cc);                                 /* fe4114 swap d3 */
    d3 = ins_mulu_w(d3, d5, &cc);                           /* fe4116 mulu.w d5,d3 */
    d4 = ins_add(d4, d3, M32, B32, &cc);                    /* fe4118 add.l d3,d4 */
    d1 = ins_swap(d1, &cc);                                 /* fe411a swap d1 */
    d3 = ins_move(d3, d1, M32, B32, &cc);                   /* fe411c move.l d1,d3 */
    d3 = ins_mulu_w(d3, d0, &cc);                           /* fe411e mulu.w d0,d3 */
    d4 = ins_add(d4, d3, M32, B32, &cc);                    /* fe4120 add.l d3,d4 */
    d4 = ins_clr(d4, M16, &cc);                             /* fe4122 clr.w d4 */
    d4 = ins_addx(d4, d4, M8, B8, &cc);                     /* fe4124 addx.b d4,d4 */
    d4 = ins_swap(d4, &cc);                                 /* fe4126 swap d4 */
    d0 = ins_swap(d0, &cc);                                 /* fe4128 swap d0 */
    d0 = ins_mulu_w(d0, d1, &cc);                           /* fe412a mulu.w d1,d0 */
    d1 = ins_swap(d1, &cc);                                 /* fe412c swap d1 */
    d5 = ins_swap(d5, &cc);                                 /* fe412e swap d5 */
    d0 = ins_add(d0, d4, M32, B32, &cc);                    /* fe4130 add.l d4,d0 */
    if (!(cc & FN)) goto renormalise;                       /* fe4132 bpl */
    d0 = ins_add(d0, 0x80u, M32, B32, &cc);                 /* fe4134 addi.l #$80,d0 */
    d0 = ins_move(d0, d5, M8, B8, &cc);                     /* fe413a move.b d5,d0 */
    if (cc & FZ) goto zero;                                 /* fe413c beq */
    return out(d0, d1, cc, 0);                              /* fe4142 rts */

renormalise:
    d5 = ins_sub(d5, 1u, M8, B8, &cc);                      /* fe4144 subq.b #1,d5 */
    if (cc & FV) goto zero;                                 /* fe4146 bvs */
    if (cc & FC) goto zero;                                 /* fe4148 bcs */
    d4 = ins_moveq(0x40, &cc);                              /* fe414a moveq #$40,d4 */
    d0 = ins_add(d0, d4, M32, B32, &cc);                    /* fe414c add.l d4,d0 */
    d0 = ins_add(d0, d0, M32, B32, &cc);                    /* fe414e add.l d0,d0 */
    if (cc & FC) {                                          /* fe4150 bcc */
        d0 = ins_roxr_l(d0, &cc);                           /* fe4152 roxr.l #1,d0 */
        d5 = ins_add(d5, 1u, M8, B8, &cc);                  /* fe4154 addq.b #1,d5 */
    }
    d0 = ins_move(d0, d5, M8, B8, &cc);                     /* fe4156 move.b d5,d0 */
    if (cc & FZ) goto zero;                                 /* fe4158 beq */
    return out(d0, d1, cc, 0);                              /* fe415e rts */

zero:
    d0 = ins_moveq(0, &cc);                                 /* fe4160 moveq #0,d0 */
    return out(d0, d1, cc, 0);                              /* fe4166 rts */

exponent_overflow:
    if (!(cc & FN)) goto zero;                              /* fe4168 bpl */
    d0 = ins_eor(d0, d1, M8, B8, &cc);                      /* fe416a eor.b d1,d0 */
    d0 = ins_or(d0, 0xFFFFFF7Fu, M32, B32, &cc);            /* fe416c ori.l #$ffffff7f,d0 */
    cc = ins_nz(d0, M8, B8, cc);                            /* fe4172 tst.b d0 */
    cc |= FV;                                               /* fe4174 ori.b #$2,ccr */
    return out(d0, d1, cc, 0);                              /* fe417c rts */
}

/* --------------------------------------------------------- SPDiv, orig glue 0x021CD8 */

wof_ffp_t wof_ffp_div_cc(uint32_t d0, uint32_t d1)
{
    uint32_t d3 = 0, d4 = 0, d5 = 0;
    uint8_t cc = 0, trap = 0;

    d5 = ins_move(d5, d1, M8, B8, &cc);                     /* fe41b0 move.b d1,d5 */
    if (cc & FZ)                                            /* fe41b2 beq -> fe4180 */
        goto divide_by_zero;                                /* fe4180 divu.w #0,d0 */
    d4 = ins_move(d4, d0, M32, B32, &cc);                   /* fe41b4 move.l d0,d4 */
    if (cc & FZ) return out(d0, d1, cc, 0);                 /* fe41b6 beq -> fe4194 rts */
    d3 = ins_moveq(-0x80, &cc);                             /* fe41b8 moveq #$80,d3 */
    d5 = ins_add(d5, d5, M16, B16, &cc);                    /* fe41ba add.w d5,d5 */
    d4 = ins_add(d4, d4, M16, B16, &cc);                    /* fe41bc add.w d4,d4 */
    d5 = ins_eor(d5, d3, M8, B8, &cc);                      /* fe41be eor.b d3,d5 */
    d4 = ins_eor(d4, d3, M8, B8, &cc);                      /* fe41c0 eor.b d3,d4 */
    d4 = ins_sub(d4, d5, M8, B8, &cc);                      /* fe41c2 sub.b d5,d4 */
    if (cc & FV) goto exponent_overflow;                    /* fe41c4 bvs -> fe41a2 */
    d0 = ins_clr(d0, M8, &cc);                              /* fe41c6 clr.b d0 */
    d0 = ins_swap(d0, &cc);                                 /* fe41c8 swap d0 */
    d1 = ins_swap(d1, &cc);                                 /* fe41ca swap d1 */
    ins_cmp(d0, d1, M16, B16, &cc);                         /* fe41cc cmp.w d1,d0 */
    if (!(cc & FN)) {                                       /* fe41ce bmi */
        d4 = ins_add(d4, 2u, M8, B8, &cc);                  /* fe41d0 addq.b #2,d4 */
        if (cc & FV) goto sign_from_words;                  /* fe41d2 bvs -> fe419a */
        d0 = ins_ror_l(d0, &cc);                            /* fe41d4 ror.l #1,d0 */
    }
    d0 = ins_swap(d0, &cc);                                 /* fe41d6 swap d0 */
    d5 = ins_move(d5, d3, M8, B8, &cc);                     /* fe41d8 move.b d3,d5 */
    d4 = ins_eor(d4, d5, M16, B16, &cc);                    /* fe41da eor.w d5,d4 */
    d4 = ins_lsr_w(d4, &cc);                                /* fe41dc lsr.w #1,d4 */
    d3 = ins_move(d3, d0, M32, B32, &cc);                   /* fe41de move.l d0,d3 */
    d3 = ins_divu_w(d3, d1, &cc, &trap);                    /* fe41e0 divu.w d1,d3 */
    if (trap) goto divide_by_zero;
    d5 = ins_move(d5, d3, M16, B16, &cc);                   /* fe41e2 move.w d3,d5 */
    d3 = ins_mulu_w(d3, d1, &cc);                           /* fe41e4 mulu.w d1,d3 */
    d0 = ins_sub(d0, d3, M32, B32, &cc);                    /* fe41e6 sub.l d3,d0 */
    d0 = ins_swap(d0, &cc);                                 /* fe41e8 swap d0 */
    d1 = ins_swap(d1, &cc);                                 /* fe41ea swap d1 */
    d3 = ins_move(d3, d1, M16, B16, &cc);                   /* fe41ec move.w d1,d3 */
    d3 = ins_clr(d3, M8, &cc);                              /* fe41ee clr.b d3 */
    d3 = ins_mulu_w(d3, d5, &cc);                           /* fe41f0 mulu.w d5,d3 */
    d0 = ins_sub(d0, d3, M32, B32, &cc);                    /* fe41f2 sub.l d3,d0 */
    if (cc & FC) {                                          /* fe41f4 bcc */
        do {
            d5 = ins_sub(d5, 1u, M16, B16, &cc);            /* fe41f6 subi.w #1,d5 */
            d0 = ins_add(d0, d1, M32, B32, &cc);            /* fe41fa add.l d1,d0 */
        } while (!(cc & FC));                               /* fe41fc bcc -> fe41f6 */
    }
    d3 = ins_move(d3, d1, M32, B32, &cc);                   /* fe41fe move.l d1,d3 */
    d3 = ins_swap(d3, &cc);                                 /* fe4200 swap d3 */
    d0 = ins_clr(d0, M16, &cc);                             /* fe4202 clr.w d0 */
    d0 = ins_divu_w(d0, d3, &cc, &trap);                    /* fe4204 divu.w d3,d0 */
    if (trap) goto divide_by_zero;
    d5 = ins_swap(d5, &cc);                                 /* fe4206 swap d5 */
    if (!(cc & FN)) {                                       /* fe4208 bmi */
        d5 = ins_move(d5, d0, M16, B16, &cc);               /* fe420a move.w d0,d5 */
        d5 = ins_add(d5, d5, M32, B32, &cc);                /* fe420c add.l d5,d5 */
        d4 = ins_sub(d4, 1u, M8, B8, &cc);                  /* fe420e subq.b #1,d4 */
        d0 = ins_move(d0, d5, M16, B16, &cc);               /* fe4210 move.w d5,d0 */
    }
    d5 = ins_move(d5, d0, M16, B16, &cc);                   /* fe4212 move.w d0,d5 */
    d5 = ins_add(d5, 0x80u, M32, B32, &cc);                 /* fe4214 addi.l #$80,d5 */
    d0 = ins_move(d0, d5, M32, B32, &cc);                   /* fe421a move.l d5,d0 */
    d0 = ins_move(d0, d4, M8, B8, &cc);                     /* fe421c move.b d4,d0 */
    if (cc & FZ) goto zero;                                 /* fe421e beq -> fe41a4 */
    return out(d0, d1, cc, 0);                              /* fe4224 rts */

zero:
    d0 = ins_moveq(0, &cc);                                 /* fe41a4 moveq #0,d0 */
    return out(d0, d1, cc, 0);                              /* fe41aa rts */

divide_by_zero:
    /* The 68000 takes exception vector 5 and never comes back here.  SPEC 7.1 has the port
     * assert in a test build; the counter is what the tests read, and the caller gets a
     * zero it cannot mistake for an answer. */
    wof_ffp_traps++;
    return out(0, d1, 0, WOF_FFP_TRAP_DIVIDE_BY_ZERO);

exponent_overflow:
    if (cc & FN) goto sign_byte;                            /* fe41a2 bmi -> fe419e */
    goto zero;                                              /* fe41a4 */

sign_from_words:
    d1 = ins_swap(d1, &cc);                                 /* fe419a swap d1 */
    d0 = ins_swap(d0, &cc);                                 /* fe419c swap d0 */
sign_byte:
    d0 = ins_eor(d0, d1, M8, B8, &cc);                      /* fe419e eor.b d1,d0 */
    d0 = ins_or(d0, 0xFFFFFF7Fu, M32, B32, &cc);            /* fe4188 ori.l #$ffffff7f,d0 */
    cc = ins_nz(d0, M8, B8, cc);                            /* fe418e tst.b d0 */
    cc |= FV;                                               /* fe4190 ori.b #$2,ccr */
    return out(d0, d1, cc, 0);                              /* fe4198 rts */
}

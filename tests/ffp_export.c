/* src/ffp.c on its own, for the two targets the port has to agree on (SPEC 10 point 13).
 *
 * tests/test_oracle_ffp.py builds this file twice and nothing else ever links it; the core
 * of dist/wof.html never sees it:
 *
 *   * as a stand-alone WebAssembly module, which tests/ffp_wasm.mjs runs in Node, so that
 *     the same corpus goes through the wasm32-freestanding code generator as through the
 *     native one;
 *   * natively with -fsanitize=undefined, as the program below, which reads the same
 *     corpus from a file and writes the same results to another.
 *
 * The corpus is a file of little-endian u32 triples (operation, D0, D1); the results are
 * quadruples (D0, D1, condition codes, trap).
 */
#include "ffp.h"

#define FFP_BATCH 8192

static uint32_t ffp_in[FFP_BATCH * 3];
static uint32_t ffp_out[FFP_BATCH * 4];

#if defined(__wasm__)
#define FFP_EXPORT(name) __attribute__((export_name(#name), used))
#else
#define FFP_EXPORT(name)
#endif

static wof_ffp_t one(uint32_t op, uint32_t d0, uint32_t d1)
{
    switch (op) {
    case 0:  return wof_ffp_add_cc(d0, d1);
    case 1:  return wof_ffp_sub_cc(d0, d1);
    case 2:  return wof_ffp_mul_cc(d0, d1);
    case 3:  return wof_ffp_div_cc(d0, d1);
    case 4:  return wof_ffp_cmp_cc(d0, d1);
    case 5:  return wof_ffp_tst_cc(d0, d1);
    case 6:  return wof_ffp_neg_cc(d0, d1);
    case 7:  return wof_ffp_fix_cc(d0, d1);
    default: return wof_ffp_flt_cc(d0, d1);
    }
}

FFP_EXPORT(ffp_input)  uint32_t *ffp_input(void)  { return ffp_in; }
FFP_EXPORT(ffp_output) uint32_t *ffp_output(void) { return ffp_out; }
FFP_EXPORT(ffp_batch)  uint32_t  ffp_batch(void)  { return FFP_BATCH; }

FFP_EXPORT(ffp_run) void ffp_run(uint32_t n)
{
    uint32_t i;

    for (i = 0; i < n && i < FFP_BATCH; i++) {
        wof_ffp_t r = one(ffp_in[i * 3], ffp_in[i * 3 + 1], ffp_in[i * 3 + 2]);

        ffp_out[i * 4]     = r.d0;
        ffp_out[i * 4 + 1] = r.d1;
        ffp_out[i * 4 + 2] = r.ccr;
        ffp_out[i * 4 + 3] = r.trap;
    }
}

#if !defined(__wasm__)
#include <stdio.h>

int main(int argc, char **argv)
{
    FILE *in, *out;
    size_t got;

    if (argc != 3) {
        fprintf(stderr, "usage: %s CASES RESULTS\n", argv[0]);
        return 2;
    }
    in = fopen(argv[1], "rb");
    out = fopen(argv[2], "wb");
    if (!in || !out) {
        fprintf(stderr, "cannot open the corpus\n");
        return 2;
    }
    while ((got = fread(ffp_in, 3 * sizeof(uint32_t), FFP_BATCH, in)) > 0) {
        ffp_run((uint32_t)got);
        fwrite(ffp_out, 4 * sizeof(uint32_t), got, out);
    }
    fclose(in);
    fclose(out);
    return 0;
}
#endif

# The game's floating point

Game logic computes with **Motorola fast floating point**, the `mathffp.library` of
Kickstart. Three routines use it, at 28 call sites, and two of them are in the call tree of
the logic tick, so the port has to reproduce the nine operations bit-exactly in integer
code (`SPEC.md` sections 7.1 and 10 point 13). This note is what the original does, what
the port does, and how each of the two is known.

Every finding below is marked **observed**, with the run or test that shows it, or **read**,
which means it comes from the listing alone.

```text
src/ffp.c, src/ffp.h        the port: the nine operations and what a call site uses
tests/ffp.py                the reference: the ROM's own routines through the game's glue
tests/ffp_model.py          what the two tick routines compute
tests/test_oracle_ffp.py    the differential test, the models and the controls
tools/ffp_observe.py        the runs that watched the game use it
tools/ffp_soak.py           the long differential run, outside the suite
```

## The format

32 bits, one register:

```text
 31                                8   7   6                 0
+------------------------------------+-----+-------------------+
|            mantissa, 24 bits       | sign|  exponent, 7 bits |
+------------------------------------+-----+-------------------+
```

The value is `(-1)^sign x mantissa / 2^24 x 2^(exponent - 64)`, with the mantissa
normalised so that bit 31 is set. There is no infinity and no NaN.

- **A number whose exponent byte is zero is zero, whatever the mantissa** (observed:
  `SPFix` of `0x12345600` returns `0x12345600` with Z set, and `SPMul` by it returns zero).
  The game's own zero is `0x00000000`.
- `0x00000080`, a zero mantissa with the sign bit set, is **not** a zero: its exponent byte
  is `0x80`, so it is a normal negative number of exponent −64 (observed: `SPNeg` of it
  gives `0x00000000`, and `SPDiv` by it overflows instead of trapping).
- The largest magnitude is `0xFFFFFF7F`, about `9.22e18`; the smallest that is not zero is
  `0x80000001`, about `2.7e-20`.

## How the game reaches it

The C library's glue sits at `0x021C9C`–`0x021D2E`. Each of the nine entries pushes a
library offset and jumps to `ffp_dispatch` (`0x021CF6`), which opens the library on first
use into `MathBase` (`0x027FAE`, `-0x3050(a4)`) and then jumps into it with **the operands
still in D0 and D1 as the caller left them**. On the way back nothing touches the condition
codes, so the caller can branch on what the library's routine left. Five sites do, all of
them inside `format_float` and all after a `tst` or a `cmp`: `bge` at `0x021A68`, `ble` at
`0x021A86`, `bge` at `0x021A94`, `blt` at `0x021AB4` and `blt` at `0x021B32` (read). None
of the fifteen sites the game actually reaches branches on the flags (observed).

| glue | mathffp | offset | operands |
|---|---|---|---|
| `ffp_add` `0x021C9C` | `SPAdd` | −66 | `D0 + D1` |
| `ffp_cmp` `0x021CA6` | `SPCmp` | −42 | `D0` against `D1` |
| `ffp_neg` `0x021CB0` | `SPNeg` | −60 | `D0` |
| `ffp_tst` `0x021CBA` | `SPTst` | −48 | **`D1`** |
| `ffp_fix` `0x021CC4` | `SPFix` | −30 | `D0` |
| `ffp_sub` `0x021CCE` | `SPSub` | −72 | `D0 - D1` |
| `ffp_div` `0x021CD8` | `SPDiv` | −84 | `D0 / D1` |
| `ffp_flt` `0x021CE2` | `SPFlt` | −36 | `D0`, a signed 32-bit integer |
| `ffp_mul` `0x021CEC` | `SPMul` | −78 | `D0 x D1` |

Kickstart 1.3 carries `mathffp 34.1 (18 Aug 1987)`; the harness and the tests find it in
`original/kick.rom` by the resident module's name and never by an address.

**`SPCmp` and `SPTst` call `exec.GetCC`**, because `move sr` is privileged from the 68010
on. It is the only library call mathffp makes, and the tests find it in the ROM by its
instruction, a `move.w sr,D0` followed by a mask and a return. Nothing else in the nine
routines leaves its own registers.

## What each operation does at its edges

All observed, by `tests/test_oracle_ffp.py` against the ROM through the game's glue.

| case | answer | flags |
|---|---|---|
| overflow in add, sub, mul, div | the largest magnitude of the right sign, `0xFFFFFF7F` or `0xFFFFFFFF` | V |
| overflow in `SPFix` above `2^31 - 1` | `0x7FFFFFFF` | X V C |
| `SPFix` of exactly `-2^31` | `0x80000000`, exact, not an overflow | X N |
| underflow in mul and div | a clean `0x00000000` | Z |
| operands of equal magnitude and opposite sign | `0x00000000` | Z |
| exponents 24 or more apart | the larger operand, unchanged | — |
| exponents 23 apart | the smaller one still moves the result | — |
| `SPFix` of anything between −1 and 1 | `0x00000000`: it truncates towards zero | X Z |
| `SPFlt` of `0x7FFFFFFF` | `0x80000060`, which is `2^31`: it rounds to nearest | — |
| `SPFlt` of an integer wider than 24 bits | rounded half away from zero | — |
| `SPDiv` by an operand whose exponent byte is zero | **68000 exception 5**, the zero divide | — |
| `SPDiv` by an operand whose mantissa is below `0x100` | **68000 exception 5** again | — |

The two zero divides are two different instructions: the first is a deliberate
`divu.w #0,d0` that mathffp reaches as soon as it sees a zero divisor; the second is the
real division, whose 16-bit divisor is the divisor's mantissa shifted down by 8 and is zero
for an unnormalised operand. Both are observed. A real machine would take the exception and
never come back; `SPEC.md` 7.1 has the port assert instead, and it counts them in
`wof_ffp_traps`, which a test holds at exactly the number the original took.

Two more results of the original that are worth knowing (observed):

- `SPCmp` answers **`+1` when the first operand is smaller** and `-1` when it is larger,
  which is the other way round from `SPTst`. Both put the comparison's own condition codes
  back before returning, so a caller that branches on the flags is unaffected.
- `SPCmp` and `SPTst` leave `D1` as `(D1 and 0xFFFF0000) or ccr`; `SPFix` writes only the
  low byte of `D1`; `SPFlt` overwrites `D1` entirely; `SPNeg` never touches it.

The X bit at the return is the caller's own where a path writes no flags at all — `SPNeg`
on a zero, `SPAdd` when the other operand is zero, `SPCmp` and `SPTst` throughout. The glue
leaves X alone, so it is the X of the game's call site. Nothing in the original branches on
it, and the port takes it as zero at the entry, which is what the differential test sets up
on the other side.

## The port

`src/ffp.c` is a transliteration of mathffp 34.1's own 68000 code, instruction for
instruction, with the ROM address of each line in the comment. The helpers above the
routines are the 68000 instructions they are made of, each writing exactly the condition
codes that instruction writes, because `SPAdd` reads the X bit back with `roxr` and `SPMul`
with `addx`.

```c
typedef struct {
    uint32_t d0;      /* the result, as the mathffp routine leaves D0 */
    uint32_t d1;      /* D1 at the return */
    uint8_t  ccr;     /* X N Z V C at the return to the caller */
    uint8_t  trap;    /* 0, or the 68000 exception the original would take here */
} wof_ffp_t;

wof_ffp_t wof_ffp_mul_cc(uint32_t d0, uint32_t d1);   /* and eight more */
```

A call site that only wants the result uses `wof_ffp_mul(a, b)`; one that branches uses
`wof_ffp_tst_cc(0, x)` and `wof_ffp_ge(r.ccr)`, which is the shape the 28 sites need — 23
of them want the value alone and five branch on the flags. All nine take both registers,
because what the caller had in the other one comes back out.

**`D3` to `D5` start at zero.** `SPAdd`, `SPSub`, `SPMul` and `SPDiv` save and restore them
and leave parts of them uninitialised; nothing that comes out of the routines depends on
what was in them, which a test shows by running the original twice per case, once with zero
and once with a random value in all three (observed).

### How it is tested

- A corpus of about 22,500 cases through **three builds** of the same file: the native
  library, a stand-alone WebAssembly module the test builds with ziglang and runs in Node,
  and the same file under `-fsanitize=undefined`. Compared are the full 32-bit result, the
  second register and the condition codes.
- The corpus is the named edges above, random operands from a fixed seed shaped so that
  close exponents, mantissas differing in the last bits, the ends of the exponent range and
  both zero divides are frequent, and **every operand pair the game was observed to
  produce**.
- `tools/ffp_soak.py` runs a million operands per operation outside the suite.

## What the game computes with it

### `player_motion` `0x01BDFA`, once per tick from `0x01C70E`

Observed over 2,782 entries in five flights; the model in `tests/ffp_model.py` reproduces
every call and every value it leaves.

Inputs, all words unless said otherwise:

| where | meaning |
|---|---|
| `pitch_angle` `0x025AA2` | the current pitch, in hundredths of a degree |
| `pitch_target` `0x025402` | what it eases towards |
| `0x025AAA` | while it is set and the target stands at 600, the target is −800 instead |
| `pitch_delta` `0x025408` | the tick's own pitch offset |
| `attitude_index` `0x02540E` | 0 to 25, the index into `attitude_factor` |
| `throttle` `0x025414` | 0 to 1000 |
| `0x025F16` | the step the pitch target loses while the throttle is below 1000 |
| `0x026D43` bit 0 | suppresses that loss |
| `0x027DEA` | a counter the across component is taken out of |
| `player_record` `0x027DEC` | long: the record everything below is in |
| record `+0x0C` | zero while the aircraft flies normally |
| record `+0x14` | the facing, `+1` or `-1`, which the horizontal speed is multiplied by |

The arithmetic:

```text
pitch_angle += (pitch_target - pitch_angle) / 4            divs.w, truncated towards zero
angle        = abs(pitch_angle + pitch_delta)              hundredths of a degree
across       = sine_degrees[angle / 100]
along        = sine_degrees[(9000 - angle) / 100]          which is the cosine
if pitch_angle < 0 or pitch_delta < 0:  across = SPNeg(across)

0x027DEA    -= SPFix(across)
if record[+0x14] > 0 and throttle < 1000:  0x027DEA -= 0x027DEA / 10

record[+0x16] = SPFix((attitude_factor[attitude_index] x SPFlt(throttle) x along + 50) / 100)
record[+0x02] += record[+0x16] x record[+0x14]             muls.w, the low word kept

record[+0x18] = SPFix(SPFlt(throttle) x across / 100)
if throttle < 1000 and record[+0x0C] equals 0:
    if not 0x026D43 bit 0:
        pitch_target -= 0x025F16 / 2, floored at -4500
    record[+0x18] -= (1000 - throttle) / 100

record[+0x00] += record[+0x18]
if record[+0x00] > 1100:   record[+0x00] = 1100
                           pitch_target = -pitch_target
                           record[+0x18] = -(record[+0x18] / 2)
elif record[+0x00] < -4:   record[+0x00] = -4
```

So `+0x16` and `+0x18` are the two speed components, `+0x02` and `+0x00` the position, and
the aircraft bounces off a ceiling of 1100 with its climb halved and reversed. The
constants `0xC8000046` and `0xC8000047` in the listing are 50 and 100.

### `aircraft_motion` `0x01D796`, once per tick per enemy aircraft, from `0x01E898`

`0x01E7D6` walks the four records of `aircraft_records` `0x02522A`, `0x34` bytes each, and
calls this for every record whose state word is neither zero nor `0x10`. Observed over
1,671 entries; the model reproduces all of them.

```text
if not state and 0x14 and player_record[+0x0C] is 4, 8 or 6:
    record[+0x1E] = 0x6A4

step          = (int16)((record[+0x1C] / 100) x record[+0x14])     divs.w then muls.w
record[+0x20] += SPFix(attitude_factor[record[+0x16]] x SPFlt(step))

if not state and 0x14 and not record[+0x03] bit 2:
    if player_record[+0x0C] equals 1:  record[+0x24] = 0x46
    if record[+0x24] < 0x21:           record[+0x24] = 0x21
```

The rest of the routine steers `+0x22` and `+0x26` towards `+0x24` and takes values from
the entropy stream through `0x01CAC8`; that belongs to the object system, not here.

### `format_float` `0x021A40` is dead

It is the C library's `%e`, `%f` and `%g` conversion, reached from `0x0218A4` only when the
formatter's conversion letter is `e` or above (`sub.w #0x65,d0` at `0x02187A`). It is the
only user of `SPSub`, `SPCmp` and `SPTst`.

- **Observed:** no entry in six runs, which together cover the whole front end, a take-off,
  level flight, climbing, diving and turning, firing, a roll over the bow and 3,218 ticks of
  a flight with an enemy aircraft. Only `"%d"` ever reached `sprintf` in them.
- **Read:** the executable has seven calls of `sprintf`. Six push a literal — `"%d"` four
  times, `"%-6ld"` and `"%-12s"` — and the seventh is inside the wrapper `0x01F332`, whose
  only caller is the crack's text screen `0x01F41A` with five strings that carry no
  conversion at all. That screen is not part of the game (`SPEC.md` section 8).
- **The control:** the same observer fires at once when `sprintf` is given a floating-point
  conversion under the oracle, and the answers are right: `%f` of 100 gives `100.000000`,
  `%e` gives `1.000000e+02`, `[%8.3f]` of `0xE10000C4` gives `[ -14.062]`.

**The game proper therefore uses six of the nine operations**: add, mul, div, neg, fix and
flt. Sub, cmp and tst exist only for the formatter. The port implements all nine anyway,
because the formatter is reachable from the C library the port replaces and because a wrong
one would be a silent trap for M4.

## The call sites

All 28, with what the runs saw.

| site | operation | calls observed | operands |
|---|---|---|---|
| `0x01BE90` | neg | 251 | the across component |
| `0x01BE9C` | fix | 2,782 | the across component |
| `0x01BEE0` | flt | 2,782 | the throttle, 716 to 1400 |
| `0x01BEE8` | mul | 2,782 | attitude factor by the throttle |
| `0x01BEF0` | mul | 2,782 | that by the along component |
| `0x01BEFA` | add | 2,782 | that plus 50 |
| `0x01BF04` | div | 2,782 | that by 100 |
| `0x01BF08` | fix | 2,782 | the horizontal speed |
| `0x01BF32` | flt | 2,782 | the throttle again |
| `0x01BF3A` | mul | 2,782 | by the across component |
| `0x01BF44` | div | 2,782 | by 100 |
| `0x01BF48` | fix | 2,782 | the vertical speed |
| `0x01D80C` | flt | 1,671 | the aircraft's step, −9 to 13 |
| `0x01D814` | mul | 1,671 | by its attitude factor |
| `0x01D818` | fix | 1,671 | its height change |
| `0x021A64` | tst | not reached | inside `format_float`, see above; `bge` follows |
| `0x021A6E` | neg | not reached | |
| `0x021A82` | tst | not reached | `ble` follows |
| `0x021A90` | cmp | not reached | `bge` follows |
| `0x021A9C` | mul | not reached | |
| `0x021AB0` | cmp | not reached | `blt` follows |
| `0x021ABC` | div | not reached | |
| `0x021B24` | add | not reached | |
| `0x021B2E` | cmp | not reached | `blt` follows |
| `0x021BB4` | fix | not reached | |
| `0x021BD2` | flt | not reached | |
| `0x021BDC` | sub | not reached | |
| `0x021BE2` | mul | not reached | |

The thirteen that no run reached are all inside `format_float`, whose single guard is read
above; they are marked **read**, not observed. All fifteen others were reached by the runs
of `tools/ffp_observe.py`, and every distinct operand pair they produced is in the corpus of
the differential test.

## The two tables of constants

Both are 32-bit FFP numbers in the DATA hunk and both reach the port through
`re/tables.toml` (`SPEC.md` section 5 step 1); a test compares what the core holds with what
the executable holds.

| table | address | entries | contents |
|---|---|---|---|
| `attitude_factor` | `0x025B0C` | 26 | 1, 0.98, 0.95, 0.91, 0.86, 0.81, 0.75, 0.70, 0.60, 0.50, 0.40, 0.30, 0.23, 0.20, 0, 0.05, 0.25, 0.45, 0.60, 0.70, 0.75, 0.81, 0.86, 0.91, 0.95, 0.98 |
| `sine_degrees` | `0x025B74` | 91 | sin of the index in degrees, 0 to 90 |

**Every entry of both is normalised** (observed, a test over all 117). The extent of the
first is 26 because the second begins where it ends, and because the two routines index it
with `attitude_index` and with a record's `+0x16`, which between them stayed inside 0 to 24
in every run (observed). The indices into the second stayed inside 0 to 90, its exact
extent, so neither table was ever read past its end. The last entry of the second table is exactly 1 and the first is 0;
entries 1 to 3 repeat the value of entry 4, `sin 4 degrees`, which puts a floor under the
smallest angle the game can have. Past entry 90 the DATA hunk holds shape names, not
numbers.

## What is open

- The meaning of `0x027DEA`, which `player_motion` takes the across component out of and
  which `0x01C0B2` decrements and floors at 4. It is written by the two routines this note
  covers and read by the dashboard's, which belongs to M4.
- The name of `0x025AAA` and of `0x025F16`, both of which only steer the pitch target.
- `aircraft_records` `0x02522A`: what the state words 1, 2, 4, 8 and `0x10` mean, and the
  rest of the record. That is point 3, the object system.
- The condition codes cannot be read out of the emulator at a hook: Unicorn keeps them
  lazily and hands back whatever was last materialised. Both the oracle and the observers
  read them by running a move from SR inside the emulation, which is exact; anything that
  wants flags out of a run has to go the same way.

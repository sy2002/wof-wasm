# The routine inventory

Every [routine](glossary.md#routine) of the game's program, with its status in the port. The [routine inventory](glossary.md#routine-inventory) is [`re/functions.csv`](repo:re/functions.csv), and [chapter 4](part-1/reading.md#the-inventory) tells what it is for. The same run of the [disassembler](glossary.md#disassembler), [`tools/disasm.py`](repo:tools/disasm.py), that writes the [listing](glossary.md#listing) writes the inventory, from the program and the names kept by hand, and [`tests/test_generated.py`](repo:tests/test%5Fgenerated.py) holds the committed file to that run byte for byte. Every column is worked out again at each run but the [status](glossary.md#status-of-a-routine), which is set by hand at the [working method](glossary.md#working-method)'s fifth step, on the evidence it names ([`SPEC.md`](repo:SPEC.md#74-working-method), 7.4); a routine new to the inventory starts as `todo`. Read the file, which has more columns, with a CSV reader: one of them holds commas.

The rows follow the addresses, as the file does, and a row gives:

| Column | What it holds |
|---|---|
| Address | where the routine begins, `0x` and six hexadecimal digits at the [fixed load layout](glossary.md#fixed-load-layout), so that the address of an `orig` comment finds its row |
| Name | the project's name for it, kept in [`re/names.txt`](repo:re/names.txt); a routine nobody named is `sub_` and its address, as `sub_022f04` |
| Kind | `C` for a routine the compiler made, known by its first instruction, `link a5`; `asm` for one written by hand in assembly |
| Span | its size in bytes, from its start to the next routine's, so that the spans cover the whole code |
| Status | where the port stands with the routine |

The statuses mean:

| Status | What it means |
|---|---|
| `verified` | ported and held to the original by a test of its own: under the [oracle](glossary.md#oracle) for a [pure routine](glossary.md#pure-routine), by other tests for the rest |
| `ported` | ported and held by the comparisons of whole runs of the game |
| `partial` | ported as far as the [scripts](glossary.md#mission-script) run it, the rest marked as [stand-ins](glossary.md#stand-in) or, where the reading was sure, ported from the reading |
| `replace` | the port does the job its own way: the memory, the [copper lists](glossary.md#copper-list), the calls into the floating point |
| `drop` | not needed: the [crack](glossary.md#crack)'s screen, the debug reporters |
| `todo` | no status set; mostly the C library and the system's glue at the end of the code, whose work the port does its own way, or code with no caller in the listing |

The counts and the rows are made from the file by the book's build, which the book's check holds to it: they are the inventory as it stood when the book was last built.

--8<-- "generated/tables/routines.md"

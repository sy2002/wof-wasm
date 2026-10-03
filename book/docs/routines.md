# The routine inventory

Every routine of the game's program, with its status in the port. The [routine inventory](glossary.md#routine-inventory) is [`re/functions.csv`](repo:re/functions.csv), and [chapter 4](part-1/reading.md#the-inventory) tells what it is for. The same run of the disassembler, [`tools/disasm.py`](repo:tools/disasm.py), that writes the [listing](glossary.md#listing) writes the inventory, from the program and the names kept by hand, and [`tests/test_generated.py`](repo:tests/test%5Fgenerated.py) holds the committed file to that run byte for byte. Every column is worked out again at each run but the status, which is kept by hand and carried over; a routine new to the inventory starts as `todo`. The file has more columns than this page shows, the callers and the calls among them; read it with a CSV reader, since one of its columns holds commas.

A row of the table below gives:

| Column | What it holds |
|---|---|
| Address | where the routine begins, at the [fixed load layout](glossary.md#fixed-load-layout): the address in the listing and in the port's `orig` comments |
| Name | the project's name for it, kept in [`re/names.txt`](repo:re/names.txt); a routine nobody named is `sub_` and its address, as `sub_022f04` |
| Kind | `C` for a routine the compiler made, known by its first instruction, `link a5`; `asm` for one written by hand in assembly |
| Span | its size in bytes, from its start to the next routine's, so that the spans cover the whole code |
| Status | where the port stands with the routine |

The statuses mean:

| Status | What it means |
|---|---|
| `verified` | ported and held to the original by a test of its own: under the [oracle](glossary.md#oracle) for a [pure routine](glossary.md#pure-routine), by other tests for the rest |
| `ported` | ported and held by the comparisons of whole runs of the game |
| `partial` | ported as far as the scripts run it, the rest marked as [stand-ins](glossary.md#stand-in) or, where the reading was sure, ported from it |
| `replace` | the port does the job its own way: the memory, the copper lists, the calls into the floating point |
| `drop` | not needed: the crack's screen, the debug reporters |
| `todo` | no status set; mostly the C library and the system's glue at the end of the code, or code nothing calls, on which nothing had to be decided |

The counts and the rows are made from the file every time the site is built, so they are the inventory's as it stands, and the book's check holds the table to the file.

--8<-- "generated/tables/routines.md"

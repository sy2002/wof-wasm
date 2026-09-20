# The high-score file

Answers the first half of point 12 of `SPEC.md` section 10. The save-game layout is not here; of
the save game only what the dialog needs, which is in `re/notes/frontend.md`.

Everything below was run: the original's own reader, sorter and writer run under the headless
original on the disk's own file, with `high_score_table` (`0x027DDA`) pointed at a buffer of the
harness's. The tests are in `tests/test_frontend.py`.

## The file

`highscore`, in the game's own directory, **360 bytes**: ten entries of **36 bytes**, best first.
All values are big-endian.

```text
entry, 36 bytes:
+0   u32   score
+4   u16   the rank the player had reached
+6   30    name, NUL-padded; at most 16 characters are ever entered
```

The disk's own file, decoded (`test_the_file_is_ten_entries_of_thirty_six_bytes`):

| # | Score | Rank | Name |
|---|---|---|---|
| 0 | 2350 | 6 | 16 characters |
| 1 | 1400 | 0 | 13 characters |
| 2 | 1025 | 0 | empty |
| 3 | 775 | 4 | empty |
| 4 | 750 | 0 | empty |
| 5 | 350 | 5 | empty |
| 6 | 200 | 0 | empty |
| 7–9 | 0 | 0 | twelve spaces |

The +4 word is the rank: `high_score_entry` writes `0x0253BE`, the rank the run was played at,
into it, and `high_score_draw` uses it to index `rank_names` (`0x025910`), which has seven
entries. Entries 7 to 9 of the shipped file are exactly what a missing file produces, so the disk
was shipped with a file that had been played into seven times.

## The routines

| Address | Name | What it does |
|---|---|---|
| `0x0193CC` | `high_score_load` | `Open("highscore", MODE_OLDFILE)`, `Read` 360 bytes, `Close`. When the open fails it fills in ten entries of score 0, rank 0 and the twelve-space string at `0x019464` `strncpy`'d to 30 |
| `0x019320` | `high_score_sort` | bubble sort by score, descending, swapping whole 36-byte entries, repeated until a pass swaps nothing |
| `0x019288` | `high_score_save` | `save_file("highscore", table, 360)`: `Open(MODE_NEWFILE)`, `Write`, `Close` |
| `0x0192AE` | `high_score_reset_unused` | ten entries of 5000 with the 15-character name at `0x019310`, then save. **No caller**; a developer's reset |

The table itself is not in DATA: it is a 360-byte local of `high_score_screen` (`0x019856`) and
`high_score_table` (`0x027DDA`) points at it, so it exists only while that screen runs.

## When it is read and written

- `high_score_entry` (`0x019472`), the first thing `high_score_screen` does, **reads** the file
  and **sorts** it.
- It compares the player's score, the long at `0x02534C`, with entry 9's score. If it is not
  greater, the routine returns and **nothing is written**.
- If it is greater, the name entry appears, the score, the name and the rank replace **entry 9**,
  the table is sorted again and **written**.
- Nothing else in the executable writes the file.

Because the write happens inside `high_score_screen`, and that screen is reached only at the end
of the outer loop (`re/notes/frontend.md`), the file is written at most once per game.

## Round trip

`test_reading_the_file_and_writing_it_back_gives_the_same_bytes`: the original's reader followed
by the original's writer reproduces the disk's 360 bytes exactly.

`test_an_inserted_score_lands_where_the_layout_says`: writing 1000 with rank 3 and a name into
entry 9 and running the original's sort puts it at index 3, between 1025 and 775, and the scores
come out `2350 1400 1025 1000 775 750 350 200 0 0`.

## The clear command

Control-C in flight calls `dos.DeleteFile("highscore")` with no further check
(`re/notes/keys.md`, `test_control_c_deletes_the_high_score_file`). The next
`high_score_load` then finds no file and fills in the ten empty entries: score 0, rank 0, a name
of twelve spaces (`test_without_the_file_the_table_is_ten_empty_entries`). The in-memory table is
not touched at the moment of the delete; the clear only takes effect at the next read, which is
the next high-score screen.

The manual says Control-C works only after Control-D has shown the list. **This executable has no
Control-D**, and Control-C is unconditional.

## For the port

- Write the 360 bytes through the virtual file system to `localStorage` under `wof:highscore`
  (`SPEC.md` section 6.2). Nothing else keeps them, so that is what "high scores persist across
  reloads" means in M3's acceptance.
- The names are drawn in the system font, so a name may hold any byte `RawKeyConvert` produced;
  the port stores the bytes, not a decoded string.
- The comparison is `>` against entry 9, so a score equal to the tenth does not get in.

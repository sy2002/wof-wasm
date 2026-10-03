/* src/fs.c, lines 493-539 */
/* The n-th name of the game's directory that begins with `wof.`, in ExNext order.  A file
 * the run has written comes before a file of the disk in the same chain, because it is
 * newer; two written files are ordered newest first for the same reason. */
const char *wof_fs_dir_entry(uint32_t index)
{
    const char *best;
    uint32_t    best_key;
    uint32_t    seen = 0;
    uint32_t    last_key = 0;
    const char *last = 0;

    for (;;) {
        best = 0;
        best_key = 0;
        for (uint32_t i = 0; i < FS_WRITE_MAX; i++) {
            if (!fs_written[i].used || !begins_with_wof(fs_written[i].name))
                continue;

            uint32_t key = ((uint32_t)name_hash(fs_written[i].name) << 24)
                         | (0xFFFFFFu - fs_written[i].written);

            if ((!last || key > last_key) && (!best || key < best_key)) {
                best = fs_written[i].name;
                best_key = key;
            }
        }
        for (uint32_t i = 0; i < fs_files; i++) {
            const char *name = (const char *)entry_of(i);

            if (!begins_with_wof(name) || is_deleted(name) || written_find(name))
                continue;

            uint32_t key = ((uint32_t)name_hash(name) << 24) | 0xFFFFFFu;

            if ((!last || key > last_key) && (!best || key < best_key)) {
                best = name;
                best_key = key;
            }
        }
        if (!best)
            return 0;
        if (seen++ == index)
            return best;
        last = best;
        last_key = best_key;
    }
}

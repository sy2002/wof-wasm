/* src/music.c, lines 681-707, a part of wof_music_start (lines 671-728) */
CO_BEGIN(c);
wof_g.song_number = song;
if (wof_m.songs_seglist[0].set) {
    wof_player_call(6, wof_tbl_music_fade_speed[0], 0);
    if (wof_g.opt_music_off) {
        /* 0x0123FE: with opt_music_off set the original branches to the LoadSeg path at
         * 0x01240E and loads wofsongs and songplay a second time, the first copies
         * leaking.  The new player's command 0, _OpenTimerInt (songplay+0x09BC), ignores
         * what AddICRVector answers, and timer A stays with the first player's timer_node,
         * so every underflow goes on running the first player's SongInt on its DATA hunk,
         * fading under command 6; it saves the vector at 0x70, the first player's
         * SongIntHandler, and puts its own there, so the channels' interrupts reach the
         * second player's DATA hunk.  Two players' DATA are then live, which the port's
         * state, one player's (src/mission.def), cannot hold.  A later music_stop gives
         * command 4 to the second player: RemICRVector takes the first player's node off
         * timer A, and 0x70 gets back the first player's handler, in a segment that
         * leaked but whose code is still there; audio_irq would never be at 0x70 again.
         * Nothing reaches it (re/notes/music.md, "The game's calls"): opt_music_off is set
         * only in flight (0x01CD5A), when the music is unloaded, and cleared at 0x01006A
         * before every rank selection.  The port goes on as with the music off: command 1
         * and no command 2. */
        WOF_STANDIN("M8 STAND-IN: music_start at 0x0123FE, the music loaded and "
                    "opt_music_off set: a second player, which the port's state cannot hold");
    } else {
        while (wof_player_call(5, 0, 0) != 0) {
            for (wof_f.music_spin = SPIN_VBLANKS; wof_f.music_spin; wof_f.music_spin--)
                CO_WAIT(c);

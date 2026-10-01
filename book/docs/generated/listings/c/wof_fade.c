/* src/fade.c, lines 184-201 */
/* The body of all four.  `target1` of 0 is the all-black table the fade_out routines
 * build on their stack; `pair` says whether the second viewport comes along. */
wof_co_t wof_fade(const uint16_t *target1, const uint16_t *target2, int pair)
{
    wof_ctx_t *c = &wof_f.co_fade;

    CO_BEGIN(c);
    fade_begin(target1, target2, pair);
    for (wof_f.fade_step = 0; wof_f.fade_step < 16; wof_f.fade_step++) {
        fade_apply(wof_f.fade_step);
        /* Each step rebuilds and installs the front view's copper list.  What survives of
         * that here is that vblank_flag is cleared, so a wait_vblank after a fade waits. */
        wof_view_show(wof_f.front_view);
        for (wof_f.fade_wait = 0; wof_f.fade_wait < fade_vblanks; wof_f.fade_wait++)
            CO_WAIT(c);
    }
    CO_END(c);
}

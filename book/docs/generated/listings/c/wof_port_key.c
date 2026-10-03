/* src/portkeys.c, lines 44-88 */
/* The shell's entry.  The state that decides what happens here - the line editor, the
 * pause, the briefing - lives in the core, which is why this layer does (SPEC 6.1). */
void wof_port_key(uint8_t code, uint16_t qualifier)
{
    uint16_t with_control = (uint16_t)(qualifier | IEQUALIFIER_CONTROL);

    /* The keyboard assist steps the weapon menu with the stick alone; the cursor keys would
     * reach it a second time through last_key (src/assist.c). */
    if (wof_assist_swallows(code))
        return;
    if (!wof_f.editing) {
        switch (code) {
        case RAW_P:                             /* KeyP pauses and continues */
            wof_key(RAW_ESCAPE, qualifier);
            return;
        case RAW_V:                             /* KeyV flips the vertical control; KeyF is */
            wof_key(RAW_F, with_control);       /* the shell's fullscreen key */
            return;
        case RAW_G:                             /* KeyG saves, on the carrier only */
            wof_key(RAW_G, with_control);
            return;
        case RAW_L:                             /* KeyL loads */
            wof_key(RAW_L, with_control);
            return;
        case RAW_M:                             /* KeyM switches the music: KeyS is the stick */
            wof_key(RAW_S, with_control);
            return;
        case RAW_R:                             /* KeyR restarts, paused or in the briefing */
            if (wof_g.pause_flag || wof_f.briefing) {
                wof_key(RAW_R, with_control);
                return;
            }
            break;
        case RAW_C:                             /* KeyC clears the high scores, paused only */
            if (wof_g.pause_flag) {
                wof_key(RAW_C, with_control);
                return;
            }
            break;
        default:
            break;
        }
    }
    wof_key(code, qualifier);
}

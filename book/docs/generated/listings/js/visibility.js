// web/main.js, lines 371-400
/* A hidden page stops (SPEC 6.2, Pause): no animation frame reaches it, so the clock is
   stopped outright and the sound is held, and a mission comes back from a real absence
   paused.  A page can also be hidden for a few milliseconds only and shown again; a
   pause asked for on the way out then stopped the mission and its sound for an absence
   the player never made.  So the pause is asked for on the way back, and only after an
   absence of HIDDEN_PAUSE_MS or more.  No VBlank runs while the page is hidden, so the
   request reaches the same pass as one made on the way out. */
const HIDDEN_PAUSE_MS = 1000;
let hiddenSince = document.hidden ? performance.now() : -1;
page.hides = document.hidden ? 1 : 0;

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        hiddenSince = performance.now();
        page.hides++;
        clock.stop();
        audio.suspend();
    } else {
        if (hiddenSince >= 0) {
            page.lastHiddenMs = performance.now() - hiddenSince;
            if (page.lastHiddenMs >= HIDDEN_PAUSE_MS) {
                requestPauseFromPage();  /* a mission comes back paused */
            }
        }
        hiddenSince = -1;
        audio.resume();
        video.restartFrames();                   /* the time away is no frame */
        clock.start();
    }
});

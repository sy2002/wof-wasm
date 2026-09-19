/* Instrumentation both page checks install before any page script runs.
 *
 * It records every AudioContext construction and resume, and whether the page had been
 * activated at that moment.  That is the invariant behind a browser's autoplay warning,
 * which WebDriver does not deliver as a log message: a context built without activation is
 * born suspended and never plays, however many keys are pressed afterwards.
 *
 * It also logs the events the page received, so that a test which presses one key can say
 * that the page saw one key.  A driver can produce phantom repeats, and a measurement of
 * what one key press does is worthless if the page in fact got hundreds.
 */
export const AUDIO_WATCH = `() => {
    window.__wofAudio = [];
    window.__wofContexts = [];
    window.__wofEvents = [];
    addEventListener('keydown', (event) => window.__wofEvents.push('keydown:' + event.key), true);
    addEventListener('pointerdown', () => window.__wofEvents.push('pointerdown'), true);
    const Native = window.AudioContext || window.webkitAudioContext;
    if (!Native) {
        return;
    }
    const activated = () => !!(navigator.userActivation && navigator.userActivation.hasBeenActive);
    class Watched extends Native {
        constructor(...args) {
            super(...args);
            window.__wofAudio.push({ call: 'construct', activated: activated() });
            window.__wofContexts.push(this);
        }
        resume() {
            window.__wofAudio.push({ call: 'resume', activated: activated() });
            return super.resume();
        }
    }
    window.AudioContext = Watched;
    if (window.webkitAudioContext) {
        window.webkitAudioContext = Watched;
    }
}`;

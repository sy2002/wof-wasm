// web/audio.js, lines 198-222
    function pumpWorklet() {
        const rate = ctx.sampleRate;
        let queued = sent - consumed;
        for (const block of takeEmulated(rate)) {
            if (fresh) {
                continue;                        /* mixed before the sound started */
            }
            if (queued > HIGH_SECONDS * rate) {
                counts.dropped += block.left.length;
                continue;
            }
            post(block);
            queued += block.left.length;
        }
        if (fresh || queued < LOW_SECONDS * rate) {
            const pad = Math.ceil(TARGET_SECONDS * rate - queued);
            if (pad > 0) {
                if (!fresh) {
                    counts.padded += pad;
                }
                post(silence(pad));
            }
        }
        fresh = false;
    }

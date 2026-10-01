// web/clock.js, lines 60-98
    function frame(now) {
        handle = requestAnimationFrame(frame);
        animationFrames++;

        if (last < 0) {
            last = now;
            measure(now);
            return;
        }

        let elapsed = now - last;
        last = now;
        if (elapsed < 0) {
            elapsed = 0;
        }

        accumulator += elapsed;
        if (accumulator > MAX_CATCHUP * period) {
            accumulator = MAX_CATCHUP * period;
            stalls++;
        }

        let issued = 0;
        while (accumulator >= period) {
            core.vblank(input.consume());
            core.pass();
            accumulator -= period;
            issued++;
        }

        if (issued) {
            video.present();
        }
        audio.pump();
        measure(now);
        if (onFrame) {
            onFrame(now);
        }
    }

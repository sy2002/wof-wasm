// web/video.js, lines 503-548
    /* The box is laid out in whole device pixels and only then converted back to CSS pixels,
       so that the browser has nothing left to resample: the backing store is exactly the CSS
       size times devicePixelRatio, and the picture lands on the physical pixel grid. */
    function fit() {
        const ratio = window.devicePixelRatio || 1;
        const availableWidth = Math.max(1, Math.floor(window.innerWidth * ratio));
        const availableHeight = Math.max(1, Math.floor(window.innerHeight * ratio));
        const aspect = standard.boxWidth / standard.boxHeight;

        let deviceWidth = availableWidth;
        let deviceHeight = Math.round(availableWidth / aspect);
        if (deviceHeight > availableHeight) {
            deviceHeight = availableHeight;
            deviceWidth = Math.round(availableHeight * aspect);
        }
        deviceWidth = Math.max(1, Math.min(deviceWidth, availableWidth));
        deviceHeight = Math.max(1, Math.min(deviceHeight, availableHeight));

        const left = Math.round((availableWidth - deviceWidth) / 2);
        const top = Math.round((availableHeight - deviceHeight) / 2);

        if (ratio === dpr && deviceWidth === box.deviceWidth && deviceHeight === box.deviceHeight
            && left === box.left && top === box.top) {
            return;
        }
        dpr = ratio;
        box = { deviceWidth, deviceHeight, left, top };

        canvas.width = deviceWidth;
        canvas.height = deviceHeight;
        canvas.style.width = (deviceWidth / dpr) + 'px';
        canvas.style.height = (deviceHeight / dpr) + 'px';
        canvas.style.left = (left / dpr) + 'px';
        canvas.style.top = (top / dpr) + 'px';

        placeSign();
        placeHelp();

        /* The smallest whole numbers whose enlargement is at least as large as the box. */
        kx = Math.max(1, Math.ceil(deviceWidth / w));
        ky = Math.max(1, Math.ceil(deviceHeight / h));
        renderer.resize({ width: deviceWidth, height: deviceHeight, kx, ky });

        /* A resized canvas is cleared: the last picture is drawn again at once. */
        renderer.draw();
    }

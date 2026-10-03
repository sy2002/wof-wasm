# tests/picture.py, lines 98-107
def whole_picture_differences(source, screenshot, box):
    """For every framebuffer pixel, how far the screenshot is from it at its block's centre."""
    left, top, width, height = box
    rows, columns = source.shape[:2]
    xs = block_centres(left, width, columns)
    ys = block_centres(top, height, rows)
    assert xs.min() >= 0 and xs.max() < screenshot.shape[1], 'the box is not in the screenshot'
    assert ys.min() >= 0 and ys.max() < screenshot.shape[0], 'the box is not in the screenshot'
    shown = screenshot[np.ix_(ys, xs)].astype(int)
    return np.abs(shown - source.astype(int)).max(axis=2)

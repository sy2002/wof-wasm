"""Comparing what a browser puts on the screen with the framebuffer it was given.

The page tests measure the display box off the DOM; this measures the picture itself, in a
driver screenshot, which is the only thing that sees what the compositor did after the shell
was finished.  Three questions, none of which a sample point in a flat area can answer:

- **Every pixel.** At the centre of the block each framebuffer pixel is shown as, the
  screenshot carries that pixel's colour.  Valid where a block is at least three device
  pixels in each direction, which a Retina-sized window gives.
- **Where the picture lies.** The position of the picture is fitted from its own colour
  edges, to a fraction of a device pixel, and compared with the rectangle the DOM reports.
  This is what catches a picture shifted by one device pixel, or stretched by one, which is
  what happens when a browser puts the canvas on a whole CSS pixel instead of a whole device
  pixel and every pixel is then a blend of two.
- **Whether the edges are hard.** Between the centres of two neighbouring blocks of
  different colour, how many device pixels are neither colour.  Two-step scaling leaves none
  where the enlargement comes out exact and one where the reduction falls between blocks; a
  single smooth step spreads the edge over most of a block, and a compositor that resampled
  the canvas again leaves its own trace.

The sub-pixel fit works on a step between two flat runs.  If the picture has a hard edge at
position `e`, a device pixel `i` shows the fraction `clamp(e - i, 0, 1)` of the colour on the
left, so the fractions summed over the pixels between the two block centres give `e - i0`.
Each step's position is regressed against the framebuffer coordinate it belongs to; the slope
is the picture's real size divided by 640 (or 214) and the intercept its real origin.
"""
import base64
import io

import numpy as np
from PIL import Image

# How far a screenshot pixel may be from the framebuffer pixel it shows.  Measured over all
# 136,960 pixels: the difference is 0 in every browser and at every size checked, so this
# leaves room for one rounding step and nothing else.
WHOLE_PICTURE_TOLERANCE = 2

# How far the fitted position of the picture may be from the rectangle the DOM reports, in
# device pixels.  A browser that puts the canvas on a whole CSS pixel instead of a whole
# device pixel is out by one.
POSITION_TOLERANCE = 0.25

# How far one fitted edge may be from the straight line through all of them.  This is the
# residual of the fit, not a property of the shell: a picture that is really a grid of equal
# blocks gives a straight line, and a wandering one means the blocks are not equal.
RESIDUAL_TOLERANCE = 0.35

# Device pixels between two block centres that are neither block's colour.  Measured at the
# sizes these checks run at: 1, in both directions, in every browser.  A single smooth step
# spreads an edge over most of a block instead, which at these sizes is three or more.
SOFTNESS_LIMIT = 1

# Two colours count as a step worth fitting when they differ by this much in one channel, and
# as the same colour when they differ by less than the tolerance.
STEP_HEIGHT = 64
COLOUR_TOLERANCE = 8

# The smallest block, in device pixels, at which any of this means anything.  Below it a
# framebuffer pixel is not a block of its own colour at all: the centre pixel of a block
# carries its neighbours, the softness of an edge is most of what there is between two block
# centres, and the fit of the position starts to wander.  Three device pixels in each
# direction is what a window on a Retina screen gives; a window of ordinary density has to be
# made large for it, which is what the headless runs do.
SMALLEST_BLOCK = 3.0


def _bytes(encoded):
    return base64.b64decode(encoded.split(',', 1)[1] if encoded.startswith('data:') else encoded)


def decode(encoded):
    """A PNG, from a data: URL or bare base64, as (height, width, 3) of uint8."""
    return np.asarray(Image.open(io.BytesIO(_bytes(encoded))).convert('RGB'))


def box_in_screenshot(geometry, screenshot):
    """The display box as the DOM reports it, in the screenshot's own pixels.

    The screenshot need not be in device pixels - what it is in is decided by comparing its
    width with the viewport it shows, rather than assumed from devicePixelRatio."""
    scale = screenshot.shape[1] / geometry['window']['width']
    rect = geometry['rect']
    return (rect['left'] * scale, rect['top'] * scale,
            rect['width'] * scale, rect['height'] * scale)


def block_size(box, shape=(214, 640)):
    """How many screenshot pixels one framebuffer pixel is shown as, across and down."""
    _, _, width, height = box
    return width / shape[1], height / shape[0]


def block_centres(origin, size, count):
    """The screenshot pixel at the centre of each block."""
    return np.floor(origin + (np.arange(count) + 0.5) * size / count).astype(int)


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


def _steps(source, along, limit):
    """Framebuffer positions where a flat run meets another flat run of a different colour.

    Three pixels of each colour, so that no other edge can fall inside the stretch of
    screenshot the fit looks at, and a difference large enough to project onto reliably."""
    pixels = source.astype(np.int16)
    lo, hi = 2, along - 3
    left = pixels[:, lo:hi]
    right = pixels[:, lo + 1:hi + 1]
    flat = ((pixels[:, lo - 2:hi - 2] == left).all(-1) & (pixels[:, lo - 1:hi - 1] == left).all(-1)
            & (pixels[:, lo + 2:hi + 2] == right).all(-1)
            & (pixels[:, lo + 3:hi + 3] == right).all(-1))
    height = np.abs(left - right).max(-1)
    rows, columns = np.nonzero(flat & (height >= STEP_HEIGHT))
    if len(columns) > limit:
        keep = np.unique(np.linspace(0, len(columns) - 1, limit).astype(int))
        rows, columns = rows[keep], columns[keep]
    return rows, columns + lo


def _fit_along(source, screenshot, origin, size, across_origin, across_size, limit=400):
    """The picture's origin and size along the second axis of the arrays given.

    Both arrays are laid out so that axis 1 is the direction being fitted; the caller
    transposes them to fit the other one."""
    rows, columns = source.shape[:2]
    at_rows, at_columns = _steps(source, columns, limit)

    fitted, coordinates, softest = [], [], 0
    for row, column in zip(at_rows, at_columns):
        first = source[row, column].astype(float)
        second = source[row, column + 1].astype(float)
        centre_first = origin + (column + 0.5) * size / columns
        centre_second = origin + (column + 1.5) * size / columns
        start = int(np.ceil(centre_first))
        stop = int(np.floor(centre_second))
        line = int(np.floor(across_origin + (row + 0.5) * across_size / rows))
        if stop <= start or line < 0 or line >= screenshot.shape[0]:
            continue
        if start < 0 or stop >= screenshot.shape[1]:
            continue

        between = screenshot[line, start:stop + 1].astype(float)
        direction = first - second
        fraction = np.clip(((between - second) @ direction) / (direction @ direction), 0, 1)
        fitted.append(start + fraction.sum())
        coordinates.append(column + 1)

        neither = ((np.abs(between - first).max(1) > COLOUR_TOLERANCE)
                   & (np.abs(between - second).max(1) > COLOUR_TOLERANCE))
        softest = max(softest, int(neither.sum()))

    assert len(fitted) >= 20, 'only %d colour steps to fit the picture with' % len(fitted)
    coordinates = np.array(coordinates, dtype=float)
    fitted = np.array(fitted)
    slope, intercept = np.polyfit(coordinates, fitted, 1)
    residual = np.abs(fitted - (intercept + slope * coordinates)).max()
    return {'origin': intercept, 'size': slope * columns, 'residual': residual,
            'steps': len(fitted), 'softness': softest}


def fit_picture(source, screenshot, box):
    """Where the picture really lies in the screenshot, fitted from its own colour edges."""
    left, top, width, height = box
    return {
        'x': _fit_along(source, screenshot, left, width, top, height),
        'y': _fit_along(source.transpose(1, 0, 2), screenshot.transpose(1, 0, 2),
                        top, height, left, width),
    }


# ------------------------------------------------------------------------------ assertions

def _measured(geometry, box, note):
    return ('%s: window %s at dpr %s, the DOM box %s, in the screenshot %s'
            % (note, geometry['window'], geometry['dpr'], geometry['rect'],
               tuple(round(value, 2) for value in box)))


def big_enough_blocks(geometry, screenshot_png):
    """Whether these checks mean anything at the size this screenshot was taken at."""
    width, height = Image.open(io.BytesIO(_bytes(screenshot_png))).size
    across, down = block_size(box_in_screenshot(geometry, np.empty((height, width, 3))))
    return across >= SMALLEST_BLOCK and down >= SMALLEST_BLOCK


def _require_big_blocks(box, note):
    across, down = block_size(box)
    assert across >= SMALLEST_BLOCK and down >= SMALLEST_BLOCK, (
        '%s: a framebuffer pixel is shown as %.2f x %.2f device pixels, too small to judge '
        'the picture by' % (note, across, down))


def assert_the_screenshot_is_the_picture(source_png, screenshot_png, geometry, note=''):
    """Every framebuffer pixel, at the centre of the block it is shown as."""
    source, screenshot = decode(source_png), decode(screenshot_png)
    box = box_in_screenshot(geometry, screenshot)
    _require_big_blocks(box, note)

    differences = whole_picture_differences(source, screenshot, box)
    worst = int(differences.max())
    if worst > WHOLE_PICTURE_TOLERANCE:
        y, x = np.unravel_index(differences.argmax(), differences.shape)
        left, top, width, height = box
        shown = screenshot[block_centres(top, height, 214)[y], block_centres(left, width, 640)[x]]
        raise AssertionError(
            '%s: %d of %d pixels are wrong; at framebuffer (%d, %d) the screenshot shows %s '
            'where the framebuffer has %s - %s'
            % (note, int((differences > WHOLE_PICTURE_TOLERANCE).sum()), differences.size,
               x, y, list(shown), list(source[y, x]), _measured(geometry, box, note)))
    return worst


def assert_the_picture_lies_where_the_dom_says(source_png, screenshot_png, geometry, note=''):
    """The picture's own edges say where it is, to a fraction of a device pixel."""
    source, screenshot = decode(source_png), decode(screenshot_png)
    box = box_in_screenshot(geometry, screenshot)
    left, top, width, height = box
    _require_big_blocks(box, note)
    fit = fit_picture(source, screenshot, box)

    for axis, origin, size, names in (('x', left, width, ('left', 'width')),
                                      ('y', top, height, ('top', 'height'))):
        found = fit[axis]
        assert found['residual'] <= RESIDUAL_TOLERANCE, (
            '%s: the %s edges do not lie on one straight line, worst residual %.2f device '
            'pixels over %d steps - %s'
            % (note, axis, found['residual'], found['steps'], _measured(geometry, box, note)))
        assert abs(found['origin'] - origin) <= POSITION_TOLERANCE, (
            '%s: the picture starts at %s %.2f, the DOM says %.2f - %s'
            % (note, names[0], found['origin'], origin, _measured(geometry, box, note)))
        assert abs(found['size'] - size) <= POSITION_TOLERANCE, (
            '%s: the picture is %.2f wide in %s, the DOM says %.2f - %s'
            % (note, found['size'], names[1], size, _measured(geometry, box, note)))
    return fit


def assert_the_blocks_have_hard_edges(source_png, screenshot_png, geometry, note=''):
    """Nothing blurred the picture: between two block centres of different colour there is
    almost nothing that is neither colour."""
    source, screenshot = decode(source_png), decode(screenshot_png)
    box = box_in_screenshot(geometry, screenshot)
    _require_big_blocks(box, note)
    fit = fit_picture(source, screenshot, box)
    for axis in ('x', 'y'):
        assert fit[axis]['softness'] <= SOFTNESS_LIMIT, (
            '%s: %d device pixels between two %s block centres are neither block\'s colour, '
            'which is what a single smooth step or a compositor resample leaves behind - %s'
            % (note, fit[axis]['softness'], axis, _measured(geometry, box, note)))
    return fit

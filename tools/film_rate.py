"""How often the picture changes in a slow-motion film of the real machine.

The owner films the Amiga's monitor with a phone at 240 fps; the exported file plays the
slowed section at 30 fps, so inside it one video frame is 1/240 s and a 50 Hz refresh is
4.8 frames.  The picture changes once per pass, so the interval between changes, in
refreshes, is the number of VBlanks a pass takes (SPEC.md section 3.3; re/notes/passes.md,
"What the film of the real machine shows").

    .venv/bin/python tools/film_rate.py FILM.mov [--crop X0 Y0 X1 Y1] [--start S --end S]

The crop is in the 480 x 270 frame the film is scaled to; pick a region of the game's
picture that changes every pass (the sea band below the ship worked), and leave the
dashboard and reflections out.  The start and end cut the normal-speed head and tail of the
export off; without them the slowed section is found from the frame differences.  Needs
ffmpeg on the path, and numpy from the project environment.

The calibration that makes the method trustworthy: the story scroller changes the picture
every 2 VBlanks in the port, whose drawing is held to the original VBlank by VBlank, and a
film of the scroller must therefore show intervals of 9.6 frames.  Run it on such a film
first; if the intervals come out otherwise, the capture chain is not resolving every refresh.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np

W, H = 480, 270


def decode(path, start=None, end=None):
    out = tempfile.NamedTemporaryFile(suffix='.gray', delete=False).name
    cmd = ['ffmpeg', '-v', 'error', '-y']
    if start is not None:
        cmd += ['-ss', str(start)]
    if end is not None:
        cmd += ['-to', str(end)]
    cmd += ['-i', path, '-vf', 'scale=%d:%d' % (W, H), '-pix_fmt', 'gray', '-f', 'rawvideo', out]
    subprocess.run(cmd, check=True)
    a = np.fromfile(out, dtype=np.uint8).reshape(-1, H, W)
    os.unlink(out)
    return a


def slowed_section(d):
    """The slowed section of an export: where the frame difference is small.  Returns the
    frame range between the first and the last second whose mean is below twice the
    smallest second's mean."""
    per = np.array([d[i:i + 30].mean() for i in range(0, len(d) - 30, 30)])
    low = per.min() * 2
    inside = np.where(per < low)[0]
    return inside[0] * 30, (inside[-1] + 1) * 30


def intervals(d, factor=1.3):
    base = np.convolve(d, np.ones(15) / 15, mode='same')
    peaks = [i for i in range(2, len(d) - 2)
             if d[i] > factor * base[i] and d[i] >= max(d[i - 2:i + 3])]
    return np.diff(peaks)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('film')
    p.add_argument('--crop', nargs=4, type=int, metavar=('X0', 'Y0', 'X1', 'Y1'),
                   default=(125, 148, 380, 162))
    p.add_argument('--start', type=float)
    p.add_argument('--end', type=float)
    p.add_argument('--fps', type=float, default=240.0, help='the capture rate')
    p.add_argument('--hz', type=float, default=50.0, help='the machine\'s refresh rate')
    args = p.parse_args()
    frames = decode(args.film, args.start, args.end)
    x0, y0, x1, y1 = args.crop
    c = frames[:, y0:y1, x0:x1].astype(np.int16)
    d = np.abs(np.diff(c, axis=0)).mean(axis=(1, 2))
    if args.start is None and args.end is None:
        lo, hi = slowed_section(d)
        d = d[lo:hi]
        print('slowed section: frames %d to %d of %d' % (lo, hi, len(frames)))
    iv = intervals(d)
    per_refresh = args.fps / args.hz
    hist = np.bincount(iv)
    print('%d picture changes; interval histogram (frames: count), %.1f frames per refresh:'
          % (len(iv) + 1, per_refresh))
    print('  ' + ' '.join('%d:%d' % (k, hist[k]) for k in range(3, min(len(hist), 40)) if hist[k] >= 2))
    in_refreshes = np.round(iv / per_refresh).astype(int)
    counts = np.bincount(in_refreshes)
    print('in refreshes: ' + ', '.join('%d: %d' % (k, counts[k]) for k in range(1, len(counts)) if counts[k]))
    mode = counts[1:].argmax() + 1
    print('most common interval: %d refreshes, that is %d VBlanks per picture change' % (mode, mode))
    return 0


if __name__ == '__main__':
    sys.exit(main())

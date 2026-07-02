"""Track the horizontal action position in each extracted segment.

For every frame: downscale, diff against the previous frame, remove the
uniform component (camera pan), and take the centroid of localized motion —
that's where the players/ball are. Two-pass exponential smoothing gives a
stable virtual-camera pan. Writes build/tracks.json: clip id -> list of
x centers in [0,1] per frame.
"""
import json
import os

import numpy as np
from PIL import Image

SEG = json.load(open("build/segments.json"))
DW, DH = 160, 90

tracks = {}
for cid in SEG:
    fdir = f"build/frames/{cid}"
    files = sorted(os.listdir(fdir))
    small = []
    for f in files:
        im = Image.open(f"{fdir}/{f}").convert("L").resize((DW, DH), Image.BILINEAR)
        small.append(np.asarray(im).astype(np.float32))
    xs = []
    prev_x = 0.5
    for i in range(len(small)):
        if i == 0:
            xs.append(0.5)
            continue
        d = np.abs(small[i] - small[i - 1])
        col = d.sum(axis=0)
        base = np.median(col)          # camera pan lights up all columns evenly
        act = np.clip(col - base, 0, None)
        tot = act.sum()
        if tot < 1e-3 or d.mean() < 0.5:   # static frame: hold position
            xs.append(prev_x)
        else:
            x = float((act * np.arange(DW)).sum() / tot) / DW
            xs.append(x)
            prev_x = x
    xs = np.array(xs)
    # two-pass EMA (forward + backward) => smooth, zero-lag-ish pan
    for _ in range(2):
        for i in range(1, len(xs)):
            xs[i] = 0.92 * xs[i - 1] + 0.08 * xs[i]
        xs = xs[::-1].copy()
    tracks[cid] = [round(float(x), 4) for x in xs]
    print(f"{cid}: {len(xs)} frames, x range [{xs.min():.2f}, {xs.max():.2f}]")

json.dump(tracks, open("build/tracks.json", "w"))
print("wrote build/tracks.json")

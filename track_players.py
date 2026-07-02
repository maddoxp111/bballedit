"""Track players per frame with YOLO person detection -> build/tracks.json.

For each extracted frame: detect people, keep court-sized boxes (filters out
crowd), and center on the weighted mean of the biggest cluster. Velocity-
clamped smoothing turns the raw centers into a steady virtual-camera pan.
Replaces track_motion.py (motion centroid was too noisy to keep players
in a tight crop).
"""
import json
import os

import numpy as np
from PIL import Image
from ultralytics import YOLO

SEG = json.load(open("build/segments.json"))
model = YOLO("yolov8n.pt")

IMGSZ = 640


def frame_centers(fdir, files):
    """Raw action x-center in [0,1] per frame."""
    xs = []
    for i in range(0, len(files)):
        img = Image.open(f"{fdir}/{files[i]}")
        sw, sh = img.size
        r = model.predict(img, imgsz=IMGSZ, classes=[0], conf=0.25, verbose=False)[0]
        boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else np.zeros((0, 4))
        best = None
        cands = []
        for x0, y0, x1, y1 in boxes:
            h = (y1 - y0) / sh
            cy = (y0 + y1) / 2 / sh
            if h < 0.10 or cy < 0.22:      # too small or too high = crowd
                continue
            cands.append(((x0 + x1) / 2 / sw, h * h))   # weight ~ size^2
        if cands:
            arr = np.array(cands)
            # weighted mean, then re-weight toward boxes near that mean to
            # lock onto the main cluster instead of stragglers
            m = np.average(arr[:, 0], weights=arr[:, 1])
            d = np.exp(-((arr[:, 0] - m) ** 2) / 0.08)
            best = float(np.average(arr[:, 0], weights=arr[:, 1] * d))
        xs.append(best)
    return xs


tracks = {}
for cid in SEG:
    fdir = f"build/frames/{cid}"
    files = sorted(os.listdir(fdir))
    raw = frame_centers(fdir, files)
    # fill gaps (no detections) by carrying the last known center
    last = next((v for v in raw if v is not None), 0.5)
    filled = []
    for v in raw:
        if v is not None:
            last = v
        filled.append(last)
    xs = np.array(filled)
    # velocity-clamped follow: camera chases the target but can't jerk
    out = np.empty_like(xs)
    out[0] = xs[0]
    max_v = 0.018                      # max pan speed per frame (~55%/s)
    for i in range(1, len(xs)):
        target = xs[max(0, i - 2): i + 3].mean()   # small look-around window
        step = np.clip(target - out[i - 1], -max_v, max_v)
        out[i] = out[i - 1] + step
    # gentle final smooth
    k = np.hanning(9); k /= k.sum()
    pad = np.pad(out, 4, mode="edge")
    out = np.convolve(pad, k, mode="same")[4:-4]
    tracks[cid] = [round(float(v), 4) for v in out]
    print(f"{cid}: {len(out)} frames, x [{out.min():.2f}, {out.max():.2f}]")

json.dump(tracks, open("build/tracks.json", "w"))
print("wrote build/tracks.json")

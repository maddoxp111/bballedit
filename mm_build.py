"""Extract + track segments for the Malik Messina-Moore commitment mixtape.

The timeline is laid out on the song's beat grid; each segment is anchored so
its money frame (verified by hand, frame by frame) lands on a chosen beat.
Frames go to build/mm/<idx>/, action tracks + meta to build/mm_meta.json.
"""
import json
import os
import re
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np
from ultralytics import YOLO

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
A = json.load(open("build/mm_analysis.json"))
P, DROP = A["period"], A["drop"]
SONG_START = DROP - 6 * P          # timeline t=0 maps here; drop lands on beat 6

# (slot_start_beat, slot_end_beat, clip, money_src_seconds, money_beat, speed)
SEGMENTS = [
    (5,  12, "47131767",  8.30,  6.0,  1.00),   # fast-break slam (on the drop)
    (12, 18, "39688928",  6.75, 13.0,  1.00),   # three vs San Diego
    (18, 23, "35318773", 11.30, 19.0,  1.00),   # dime in transition
    (26, 31, "38858052", 10.50, 27.0,  1.00),   # dish for the basket
    (31, 36, "38858052", 12.40, 32.0,  0.80),   # hero run-back
    (36, 41, "39688928", 16.30, 37.0,  0.85),   # three, replay angle
    (41, 46, "47131767", 20.20, 42.0,  1.00),   # second slam
    (46, 50, "35318773", 12.10, 47.0,  0.75),   # close-up
    (50, 57, "47131767",  8.30, 52.5,  0.42),   # slam again, slow-mo
]
CARD_SLOTS = [(0, 5), (23, 26), (57, 64)]       # intro / transition / outro

model = YOLO("yolov8n.pt")


def duration(path):
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def action_x(rgb):
    """Where the play is: weighted centre of the biggest on-court bodies.

    Broadcast cameras keep the action centred and the involved players are
    the largest boxes, so the top few (after dropping crowd, foreground
    bodies hugging the bottom edge, and half-cut edge boxes) point at the
    play. An orange-blob ball detector is useless here — the camera pan
    makes static signage register as "moving orange".
    Returns (x, max_box_height).
    """
    r = model.predict(rgb, imgsz=960, classes=[0], conf=0.20, verbose=False)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None, 0.0
    sh, sw = r.orig_shape
    cands = []
    for x0, y0, x1, y1 in r.boxes.xyxy.cpu().numpy():
        h = (y1 - y0) / sh
        cy = (y0 + y1) / 2 / sh
        cx = (x0 + x1) / 2 / sw
        if h < 0.08 or not (0.20 <= cy <= 0.80) or not (0.06 <= cx <= 0.94):
            continue
        cands.append((cx, h))
    if not cands:
        return None, 0.0
    cands.sort(key=lambda c: -c[1])
    top = cands[:3]
    xs = np.array([c[0] for c in top])
    ws = np.array([c[1] for c in top]) ** 2
    return float(np.average(xs, weights=ws)), float(cands[0][1])


def ball_and_rim(bgr, prev_gray):
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(hsv, (3, 95, 80), (24, 255, 255))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ball = rim = None
    if prev_gray is not None:
        motion = cv2.threshold(cv2.absdiff(gray, prev_gray), 14, 255, cv2.THRESH_BINARY)[1]
        motion = cv2.dilate(motion, np.ones((7, 7), np.uint8))
        m = cv2.morphologyEx(cv2.bitwise_and(orange, motion), cv2.MORPH_OPEN,
                             np.ones((3, 3), np.uint8))
        n, _, stats, cents = cv2.connectedComponentsWithStats(m)
        best = None
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if not (25 <= area <= 900) or not (0.45 <= bw / max(bh, 1) <= 2.2):
                continue
            if cents[i][1] > 0.9 * h:
                continue
            if best is None or area > best[1]:
                best = (cents[i], area)
        if best is not None:
            ball = best[0][0] / w
        s = cv2.bitwise_and(orange, cv2.bitwise_not(motion))
        n, _, stats, cents = cv2.connectedComponentsWithStats(s)
        best = None
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if not (60 <= area <= 2500) or cents[i][1] > 0.65 * h:
                continue
            if bw / max(bh, 1) < 1.6:
                continue
            if best is None or area > best[1]:
                best = (cents[i], area)
        if best is not None:
            rim = best[0][0] / w
    return ball, rim, gray


def players_x(rgb):
    r = model.predict(rgb, imgsz=640, classes=[0], conf=0.25, verbose=False)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None
    sh, sw = r.orig_shape
    xs, ws_ = [], []
    for x0, y0, x1, y1 in r.boxes.xyxy.cpu().numpy():
        hh = (y1 - y0) / sh
        if hh < 0.10 or (y0 + y1) / 2 / sh < 0.22:
            continue
        xs.append((x0 + x1) / 2 / sw)
        ws_.append(hh * hh)
    if not xs:
        return None
    xs, ws_ = np.array(xs), np.array(ws_)
    m = np.average(xs, weights=ws_)
    d = np.exp(-((xs - m) ** 2) / 0.08)
    return float(np.average(xs, weights=ws_ * d))


def smooth(raw):
    """Light, responsive smoothing.

    Heavy smoothing averages the ball across a whole fast break and leaves
    the crop nowhere near the action, so keep it short: reject outlier
    jumps, then a 7-frame centered mean plus a mild zero-phase EMA.
    """
    idx = np.arange(len(raw))
    known = np.array([i for i, v in enumerate(raw) if v is not None])
    if len(known) == 0:
        return np.full(len(raw), 0.5)
    xs = np.interp(idx, known, np.array([raw[i] for i in known], float))
    # median-ish outlier rejection against a 5-frame neighbourhood
    med = np.array([np.median(xs[max(0, i - 2): i + 3]) for i in range(len(xs))])
    xs = np.where(np.abs(xs - med) > 0.16, med, xs)
    k = np.ones(7) / 7.0
    xs = np.convolve(np.pad(xs, 3, mode="edge"), k, "same")[3:-3]
    for _ in range(2):
        for i in range(1, len(xs)):
            xs[i] = 0.65 * xs[i - 1] + 0.35 * xs[i]
        xs = xs[::-1].copy()
    return np.clip(xs, 0, 1)


meta = {"song_start": round(SONG_START, 4), "period": P, "cards": CARD_SLOTS,
        "segments": []}
for i, (b0, b1, cid, msrc, mbeat, speed) in enumerate(SEGMENTS):
    path = f"build/clips/{cid}.mp4"
    dur = duration(path)
    t0, t1 = b0 * P, b1 * P
    mt = mbeat * P
    src_start = msrc - (mt - t0) * speed
    src_len = (t1 - t0) * speed + 0.25
    src_start = max(0.0, min(src_start, dur - src_len - 0.05))
    fdir = f"build/mm/{i:02d}"
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(f"{fdir}/{f}")
    subprocess.run([FFMPEG, "-y", "-ss", f"{src_start:.3f}", "-i", path,
                    "-t", f"{src_len:.3f}", "-vf", f"fps={FPS}", "-q:v", "3",
                    f"{fdir}/%04d.jpg"], check=True, capture_output=True)
    files = sorted(os.listdir(fdir))
    raw, heights, nd = [], [], 0
    for f in files:
        bgr = cv2.imread(f"{fdir}/{f}")
        x, mh = action_x(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        raw.append(x)
        heights.append(mh)
        nd += x is not None
    track = smooth(raw)
    # a shot where bodies fill the frame is already tight: don't zoom further
    hk = np.ones(9) / 9.0
    hsm = np.convolve(np.pad(np.array(heights), 4, mode="edge"), hk, "same")[4:-4]
    meta["segments"].append(dict(i=i, b0=b0, b1=b1, t0=round(t0, 3), t1=round(t1, 3),
                                 cid=cid, speed=speed, frames=len(files),
                                 money_t=round(mt, 3),
                                 track=[round(float(v), 4) for v in track],
                                 bodyh=[round(float(v), 3) for v in hsm]))
    print(f"seg {i:02d} {cid} beats {b0}-{b1} src {src_start:.2f} speed {speed} "
          f"{len(files)}f det {nd}/{len(files)} maxbody {max(heights):.2f}")

json.dump(meta, open("build/mm_meta.json", "w"))
print("wrote build/mm_meta.json")

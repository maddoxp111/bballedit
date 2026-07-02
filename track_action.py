"""Ball + basket action tracker -> build/tracks.json.

Per frame, three signals are fused into one x target:
  1. ball  — orange, saturated, MOVING blob of ball-ish size (color ∩ motion)
  2. rim   — orange, mostly STATIC, wide flat blob in the upper half
  3. players — YOLO person cluster (fallback/stabilizer)
Ball wins when found, else rim, else players; gaps are interpolated, then the
whole track gets zero-phase (forward+backward) smoothing so the virtual
camera pans smoothly with no frame-to-frame jitter.
"""
import json
import os

import cv2
import numpy as np
from ultralytics import YOLO

SEG = json.load(open("build/segments.json"))
model = YOLO("yolov8n.pt")


def ball_and_rim(bgr, prev_gray):
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(hsv, (3, 95, 80), (24, 255, 255))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ball = rim = None
    if prev_gray is not None:
        motion = cv2.absdiff(gray, prev_gray)
        motion = cv2.threshold(motion, 14, 255, cv2.THRESH_BINARY)[1]
        motion = cv2.dilate(motion, np.ones((7, 7), np.uint8))
        # ---- ball: orange AND moving, small round-ish blob
        m = cv2.bitwise_and(orange, motion)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, _, stats, cents = cv2.connectedComponentsWithStats(m)
        best = None
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if not (30 <= area <= 900):
                continue
            if not (0.45 <= bw / max(bh, 1) <= 2.2):
                continue
            if cents[i][1] > 0.9 * h:      # bottom edge junk
                continue
            if best is None or area > best[1]:
                best = (cents[i], area)
        if best is not None:
            ball = (best[0][0] / w, best[0][1] / h)
        # ---- rim: orange AND static, wide flat blob, upper 65%
        s = cv2.bitwise_and(orange, cv2.bitwise_not(motion))
        n, _, stats, cents = cv2.connectedComponentsWithStats(s)
        best = None
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if not (60 <= area <= 2500) or cents[i][1] > 0.65 * h:
                continue
            if bw / max(bh, 1) < 1.6:      # rims read as wide bars
                continue
            if best is None or area > best[1]:
                best = (cents[i], area)
        if best is not None:
            rim = (best[0][0] / w, best[0][1] / h)
    return ball, rim, gray


def players_x(img_rgb):
    r = model.predict(img_rgb, imgsz=640, classes=[0], conf=0.25, verbose=False)[0]
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


def smooth_track(raw):
    """Interpolate gaps then zero-phase smooth: no jitter, no lag spikes."""
    idx = np.arange(len(raw))
    known = np.array([i for i, v in enumerate(raw) if v is not None])
    if len(known) == 0:
        return np.full(len(raw), 0.5)
    vals = np.array([raw[i] for i in known], dtype=float)
    xs = np.interp(idx, known, vals)
    for _ in range(3):                     # forward-backward EMA x3 (zero phase)
        for _ in range(2):
            for i in range(1, len(xs)):
                xs[i] = 0.85 * xs[i - 1] + 0.15 * xs[i]
            xs = xs[::-1].copy()
    return np.clip(xs, 0.0, 1.0)


tracks = {}
for cid in SEG:
    fdir = f"build/frames/{cid}"
    files = sorted(os.listdir(fdir))
    raw, prev_gray = [], None
    nb = nr = 0
    for f in files:
        bgr = cv2.imread(f"{fdir}/{f}")
        ball, rim, prev_gray = ball_and_rim(bgr, prev_gray)
        if ball is not None:
            raw.append(ball[0]); nb += 1
        elif rim is not None:
            raw.append(rim[0]); nr += 1
        else:
            raw.append(players_x(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
    xs = smooth_track(raw)
    tracks[cid] = [round(float(v), 4) for v in xs]
    print(f"{cid}: ball {nb}/{len(files)}, rim {nr}, x [{xs.min():.2f}, {xs.max():.2f}]")

json.dump(tracks, open("build/tracks.json", "w"))
print("wrote build/tracks.json")

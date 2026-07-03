"""Pick each ESPN clip's money moment and pre-extract frames for the renderer.

The make + crowd roar is the loudest sustained stretch of broadcast audio, so
each clip's window is centered just before its smoothed-RMS peak. Frames land
in build/frames/<id>/ as 1080-wide JPEGs at 30fps; window times go to
build/segments.json.
"""
import json
import os
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30

# clip id -> (pre, post) seconds around the roar peak
SEGMENTS = {
    "47474610": (1.7, 0.9),   # Kinziger dunk (opener)
    "47041854": (1.7, 2.6),   # Klabo dunk (long tail: opens the highlight run)
    "48001037": (1.7, 0.9),   # Klabo and-1
    "47614013": (1.7, 0.9),   # Klabo three
    "47195895": (1.7, 0.9),   # Klabo bucket
    "47042256": (1.7, 0.9),   # Klabo dish
    "47383232": (2.3, 0.3),   # Walker flush (buildup -> flush at the end)
    "47614227": (1.7, 0.9),   # Walker and-1
    "48244171": (1.7, 0.9),   # Walker hoop+harm (NIT)
    "47762098": (1.7, 0.9),   # Walker and-1
    "48282177": (2.3, 0.3),   # Walker and-1 (NIT), flush at the end
    "48282097": (1.7, 0.9),   # Kinziger range 3
    "48037850": (1.7, 0.9),   # Kinziger 3 vs UNI
    "47613943": (1.7, 0.9),   # Kinziger shot vs Indiana St
    "48382384": (2.2, 0.4),   # Kinziger runner, make near the end
    "48282239": (5.0, 5.0),   # Kinziger GAME WINNER (finale, long)
    "48038210": (1.7, 0.9),   # Kinziger nice bucket (bonus)
    "47716449": (1.7, 0.9),   # Walker fights for and-1 (bonus)
}

# clips where roar detection misses; explicit [t0, t1] in clip time
FIXED = {"48282239": (13.4, 23.4)}  # drive -> release ~18s -> splash ~19.3s -> celebration


def roar_peak(path):
    subprocess.run([FFMPEG, "-y", "-i", path, "-ac", "1", "-ar", "8000",
                    "build/_probe.wav"], check=True, capture_output=True)
    with wave.open("build/_probe.wav") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    hop = 800  # 0.1s
    n = len(a) // hop
    rms = np.sqrt(np.mean(a[: n * hop].reshape(n, hop) ** 2, axis=1))
    k = np.hanning(21); k /= k.sum()  # ~2s smoothing
    sm = np.convolve(rms, k, mode="same")
    return float(np.argmax(sm)) / 10.0, n / 10.0


def probe_duration(path):
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


out = {}
for cid, (pre, post) in SEGMENTS.items():
    path = f"build/clips/{cid}.mp4"
    if not os.path.exists(path):
        print(f"MISSING {cid}"); continue
    dur = probe_duration(path)
    peak, _ = roar_peak(path)
    if cid in FIXED:
        t0, t1 = FIXED[cid]
        t1 = min(t1, dur)
    else:
        t0 = max(0.0, min(peak - pre, dur - (pre + post) - 0.1))
        t1 = min(dur, t0 + pre + post)
    fdir = f"build/frames/{cid}"
    os.makedirs(fdir, exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-ss", f"{t0:.3f}", "-i", path, "-t", f"{t1 - t0:.3f}",
                    "-vf", f"fps={FPS}", "-q:v", "3",
                    f"{fdir}/%04d.jpg"], check=True, capture_output=True)
    nf = len(os.listdir(fdir))
    out[cid] = {"t0": round(t0, 3), "t1": round(t1, 3), "peak": round(peak, 2),
                "dur": round(dur, 2), "frames": nf}
    print(f"{cid}: dur {dur:.1f}s peak {peak:.1f}s -> [{t0:.1f}, {t1:.1f}] {nf} frames")

json.dump(out, open("build/segments.json", "w"), indent=1)
print("wrote build/segments.json")

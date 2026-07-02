"""Extract per-segment frames for the Coen Carr edit -> build/carr/<idx>/.

The timeline mirrors the reference edit exactly; each gameplay segment is a
different dunk. Windows are anchored to each clip's crowd-roar peak (the
flush) with a per-segment offset, and slow-mo segments pull proportionally
less source time.
"""
import json
import os
import re
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30

# (t0, t1, clip, speed, anchor)  anchor = window start relative to roar peak
TIMELINE = [
    (0.0,  2.0,  "48201030", 1.0, -1.6),   # posterizes two defenders
    (2.0,  4.1,  "47554482", 1.0, -1.7),   # massive windmill
    (4.1,  5.0,  "47053282", 1.0, -0.6),   # ferocious alley-oop
    (5.0,  7.0,  "42611187", 0.6, -1.1),   # half-court lob (ATTENTION moment)
    (7.0,  12.0, "48076071", 0.45, 0.1),   # and-1 oop aftermath, slow celebration
    (12.0, 14.5, "42197680", 0.7, -1.4),   # foul-line lefty windmill
    (14.5, 16.0, "47294356", 0.5, -0.2),   # rim impact closeup
    (16.0, 18.5, "44082477", 0.6, -1.2),   # reverse alley-oop
    (18.5, 20.5, "43561998", 1.0, -1.5),   # thunderous one-hander
    (20.5, 21.0, "46958285", 1.0, -0.2),   # quick rim impact
    (21.0, 23.5, "38657377", 1.0, -1.9),   # double-clutch foul-line jam
    (23.5, 24.5, "44251756", 0.6, -0.3),   # flush impact vs Oregon
    (24.5, 28.0, "48201030", 0.45, 4.1),   # closeup reaction after the posterizer
    (28.0, 30.0, "39243391", 0.8, -1.2),   # emphatic alley-oop
    (30.0, 32.5, "43561575", 0.5, 0.3),    # teammates mob him after the slam
    (32.5, 36.5, "47715879", 0.4, -0.8),   # cinematic slow-mo oop
]
OUTRO_T = 36.5
DUR = 40.70


def roar_peak(path):
    subprocess.run([FFMPEG, "-y", "-i", path, "-ac", "1", "-ar", "8000",
                    "build/_probe.wav"], check=True, capture_output=True)
    with wave.open("build/_probe.wav") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    hop = 800
    n = len(a) // hop
    rms = np.sqrt(np.mean(a[: n * hop].reshape(n, hop) ** 2, axis=1))
    k = np.hanning(21); k /= k.sum()
    return float(np.argmax(np.convolve(rms, k, "same"))) / 10.0


def duration(path):
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


meta = []
peaks = {}
for i, (t0, t1, cid, speed, anchor) in enumerate(TIMELINE):
    path = f"build/clips/{cid}.mp4"
    if cid not in peaks:
        peaks[cid] = roar_peak(path)
    dur = duration(path)
    src_len = (t1 - t0) * speed + 0.2
    w0 = max(0.0, min(peaks[cid] + anchor, dur - src_len - 0.05))
    fdir = f"build/carr/{i:02d}"
    os.makedirs(fdir, exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-ss", f"{w0:.3f}", "-i", path, "-t", f"{src_len:.3f}",
                    "-vf", f"fps={FPS}", "-q:v", "3", f"{fdir}/%04d.jpg"],
                   check=True, capture_output=True)
    nf = len(os.listdir(fdir))
    meta.append({"i": i, "t0": t0, "t1": t1, "cid": cid, "speed": speed,
                 "w0": round(w0, 3), "frames": nf})
    print(f"seg {i:02d} {cid} peak {peaks[cid]:5.1f}s window [{w0:.1f}, {w0+src_len:.1f}] {nf} frames")

json.dump(meta, open("build/carr_meta.json", "w"), indent=1)
print("wrote build/carr_meta.json")

"""Build the Coen Carr edit timeline: a different dunk flush on every bass hit.

Bass hits are detected from the reference audio (25-130Hz spectral flux,
strongest-first with a min gap). Flush times below were verified frame by
frame for each clip. Each segment plays so its flush lands exactly on its
hit; the intro clip's flush lands on the beat drop at ~6.91s while the
captions run. Frames go to build/carr/<idx>/, meta to build/carr_meta.json.
"""
import json
import os
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
OUTRO_T = 36.5

# clip id -> hand-verified flush time (ball hits the rim/net), seconds
FLUSH = {
    "42611187": 24.60, "48201030": 8.05, "47554482": 12.40, "47053282": 14.80,
    "48076071": 8.40, "42197680": 6.60, "47294356": 23.05, "44082477": 25.25,
    "43561998": 6.70, "46958285": 24.70, "38657377": 12.80, "44251756": 21.50,
    "39243391": 7.70, "43561575": 6.45, "47715879": 6.90, "42784103": 12.50,
    "42785385": 14.55, "42433548": 8.40, "42432663": 21.20, "42433496": 17.30,
    "42354863": 12.95, "42257177": 12.80, "38899217": 7.50, "43431174": 5.20,
}

# dunk order on the bass hits (hit 1 = the intro clip's flush on the drop)
INTRO_CLIP = "42611187"          # half-court lob, slow buildup under the captions
HIT_CLIPS = ["48201030", "47554482", "43561998", "47053282", "42197680",
             "38657377", "44082477", "42354863", "39243391", "46958285",
             "42784103", "48076071", "44251756", "42433496", "42785385",
             "38899217"]
OUTRO_CELEB = ("42652563", 9.30)  # Carr walks into the camera, slow-mo


def bass_hits():
    subprocess.run([FFMPEG, "-y", "-i", "assets/audio/carr_ref_audio.m4a", "-ac", "1",
                    "-ar", "22050", "build/carr_audio.wav"], check=True, capture_output=True)
    with wave.open("build/carr_audio.wav") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    SR, hop = 22050, 256
    n = (len(a) - 1024) // hop
    idx = np.arange(1024)[None, :] + hop * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(a[idx] * np.hanning(1024).astype(np.float32), axis=1))
    freqs = np.fft.rfftfreq(1024, 1 / SR)
    bass = spec[:, (freqs >= 25) & (freqs <= 130)].sum(axis=1)
    k = np.hanning(5); k /= k.sum()
    flux = np.clip(np.diff(np.convolve(bass, k, "same"), prepend=0), 0, None)
    fps = SR / hop
    cands = []
    i = 0
    thr = np.percentile(flux, 97)
    while i < len(flux):
        if flux[i] > thr:
            j = i + int(np.argmax(flux[i:i + int(0.1 * fps)]))
            cands.append((j / fps, flux[j]))
            i = j + int(0.25 * fps)
        else:
            i += 1
    # strongest-first with min gap, inside the beat section
    picked = []
    for t, s in sorted(cands, key=lambda x: -x[1]):
        if s < 95 or not (6.5 <= t <= 34.0):
            continue
        if all(abs(t - p) >= 1.15 for p in picked):
            picked.append(t)
    return sorted(round(t, 2) for t in picked)


def duration(path):
    import re
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


# strong-accent bass hits, hand-selected from the detector's raw output
# (bass_hits() kept for reference; the curated grid below is what we sync to)
hits = [6.91, 8.99, 10.15, 11.30, 12.68, 13.84, 14.99, 17.53, 19.38,
        21.22, 23.07, 24.92, 27.45, 28.61, 29.76, 31.14, 32.30]
print(f"{len(hits)} bass hits: {hits}")
assert len(hits) == len(HIT_CLIPS) + 1, f"need {len(hits)-1} hit clips, have {len(HIT_CLIPS)}"

POST = 0.35   # seconds a flush lingers before the cut
segments = []
# intro: buildup under the captions, flush exactly on the drop (hits[0])
segments.append(dict(t0=0.0, t1=hits[0] + POST, cid=INTRO_CLIP, speed=0.55,
                     flush_t=hits[0]))
for k, cid in enumerate(HIT_CLIPS):
    h = hits[k + 1]
    t0 = hits[k] + POST
    t1 = (hits[k + 2] + POST) if k + 2 <= len(HIT_CLIPS) else OUTRO_T - 1.55
    # slight slow-mo when there's room, full speed for quick cuts
    speed = 0.75 if h - t0 > 2.0 else 1.0
    segments.append(dict(t0=round(t0, 2), t1=round(min(t1, h + POST + 2), 2),
                         cid=cid, speed=speed, flush_t=h))
# fix each segment end to the next segment start
for i in range(len(segments) - 1):
    segments[i]["t1"] = segments[i + 1]["t0"]
# outro celebration: last hit + POST -> 36.5
segments.append(dict(t0=segments[-1]["t1"], t1=OUTRO_T, cid=OUTRO_CELEB[0],
                     speed=0.45, flush_t=None))

meta = []
for i, s in enumerate(segments):
    path = f"build/clips/{s['cid']}.mp4"
    dur = duration(path)
    seg_len = s["t1"] - s["t0"]
    src_len = seg_len * s["speed"] + 0.2
    if s["flush_t"] is not None:
        src_start = FLUSH[s["cid"]] - (s["flush_t"] - s["t0"]) * s["speed"]
        if src_start < 0:   # not enough buildup: stretch it
            s["speed"] = round(FLUSH[s["cid"]] / (s["flush_t"] - s["t0"]) * 0.98, 3)
            src_start = FLUSH[s["cid"]] - (s["flush_t"] - s["t0"]) * s["speed"]
            src_len = seg_len * s["speed"] + 0.2
    else:
        src_start = OUTRO_CELEB[1]
    src_start = max(0.0, min(src_start, dur - src_len - 0.05))
    fdir = f"build/carr/{i:02d}"
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(f"{fdir}/{f}")
    subprocess.run([FFMPEG, "-y", "-ss", f"{src_start:.3f}", "-i", path,
                    "-t", f"{src_len:.3f}", "-vf", f"fps={FPS}", "-q:v", "3",
                    f"{fdir}/%04d.jpg"], check=True, capture_output=True)
    nf = len(os.listdir(fdir))
    meta.append(dict(i=i, t0=s["t0"], t1=s["t1"], cid=s["cid"], speed=s["speed"],
                     frames=nf))
    ft = f"{s['flush_t']:.2f}" if s["flush_t"] else "  -  "
    print(f"seg {i:02d} {s['cid']} [{s['t0']:5.2f},{s['t1']:5.2f}] flush@{ft} "
          f"speed {s['speed']:.2f} src {src_start:.2f} {nf}f")

json.dump(meta, open("build/carr_meta.json", "w"), indent=1)
print("wrote build/carr_meta.json")

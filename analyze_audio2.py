"""Analysis for the footage edit: song plays from 0:00.

Finds the beat grid over [0, 60s] and the first big drop (sustained energy jump),
snapped to the beat grid. Writes build/analysis2.json.
"""
import json
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SONG = "assets/audio/40_Nights.mp3"
SR = 22050
DUR = 60.0

subprocess.run([FFMPEG, "-y", "-i", SONG, "-ac", "1", "-ar", str(SR), "-t", "90",
                "build/song_head.wav"], check=True, capture_output=True)
with wave.open("build/song_head.wav") as w:
    audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

# onset envelope (spectral flux), same as analyze_audio.py
hop, nfft = 512, 1024
frames = 1 + (len(audio) - nfft) // hop
win = np.hanning(nfft).astype(np.float32)
idx = np.arange(nfft)[None, :] + hop * np.arange(frames)[:, None]
spec = np.abs(np.fft.rfft(audio[idx] * win, axis=1))
flux = np.maximum(spec[1:] - spec[:-1], 0).sum(axis=1)
flux = np.concatenate([[0], flux])
kernel = np.hanning(9); kernel /= kernel.sum()
env = np.convolve(flux, kernel, mode="same")
env = (env - env.min()) / (env.max() - env.min() + 1e-9)
fps_env = SR / hop

# tempo
seg = env - env.mean()
ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
lags = np.arange(int(fps_env * 60 / 180), int(fps_env * 60 / 60))
best_lag = lags[np.argmax(ac[lags])]
bpm = 60.0 * fps_env / best_lag
period = 60.0 / bpm

# beat phase over [0, 60]
n_test = 64
phases = np.linspace(0, period, n_test, endpoint=False)
scores = []
for ph in phases:
    ts = ph + period * np.arange(int(DUR / period))
    fr = (ts * fps_env).astype(int)
    fr = fr[fr < len(env)]
    scores.append(env[fr].sum())
beat_offset = float(phases[int(np.argmax(scores))])

# drop detection: RMS per 0.25s, smoothed; drop = biggest jump between
# consecutive 4s blocks, i.e. where the track suddenly gets loud and stays loud
hop_rms = SR // 4
n_rms = len(audio) // hop_rms
rms = np.sqrt(np.mean(audio[: n_rms * hop_rms].reshape(n_rms, hop_rms) ** 2, axis=1))
blk = 16  # 4s blocks
jumps = []
for i in range(blk, min(n_rms - blk, int(45 * 4))):
    before = rms[i - blk:i].mean()
    after = rms[i:i + blk].mean()
    jumps.append((after - before, i / 4.0))
jump, drop_t = max(jumps)
# snap drop to the nearest beat
k = round((drop_t - beat_offset) / period)
drop = beat_offset + k * period
print(f"bpm {bpm:.2f}  offset {beat_offset:.3f}  drop ~{drop_t:.2f}s -> beat {k} at {drop:.3f}s (jump {jump:.3f})")

# window-local energy per 0.5s
n2 = int(DUR * 2)
rms2 = rms[: n2 * 2].reshape(n2, 2).mean(axis=1)
rms2 = (rms2 - rms2.min()) / (rms2.max() - rms2.min() + 1e-9)

json.dump({"bpm": round(bpm, 3), "period": round(period, 5),
           "beat_offset": round(beat_offset, 4), "drop": round(drop, 3),
           "drop_beat": int(k),
           "energy": [round(float(x), 4) for x in rms2]},
          open("build/analysis2.json", "w"), indent=1)
print("wrote build/analysis2.json")

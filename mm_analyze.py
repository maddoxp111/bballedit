"""Beat grid + drop detection for the Messina-Moore mixtape song.

Writes build/mm_analysis.json: bpm, period, beat_offset (phase of the beat
grid) and drop (first beat of the hard section, snapped to the grid).
"""
import json
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SONG = "assets/audio/2_hard_4_the_radio.mp3"
SR = 22050

subprocess.run([FFMPEG, "-y", "-i", SONG, "-ac", "1", "-ar", str(SR), "-t", "90",
                "build/mm_head.wav"], check=True, capture_output=True)
with wave.open("build/mm_head.wav") as w:
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

hop, nfft = 512, 1024
n = (len(a) - nfft) // hop
idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
spec = np.abs(np.fft.rfft(a[idx] * np.hanning(nfft).astype(np.float32), axis=1))
flux = np.concatenate([[0], np.clip(np.diff(spec, axis=0), 0, None).sum(axis=1)])
k = np.hanning(9); k /= k.sum()
env = np.convolve(flux, k, "same")
env = (env - env.min()) / (env.max() - env.min() + 1e-9)
fps = SR / hop

seg = env - env.mean()
ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
lags = np.arange(int(fps * 60 / 180), int(fps * 60 / 60))
bpm = 60.0 * fps / lags[np.argmax(ac[lags])]
period = 60.0 / bpm

# beat phase: maximize onset energy landing on grid points
phases = np.linspace(0, period, 96, endpoint=False)
best, off = -1, 0.0
for ph in phases:
    ts = ph + period * np.arange(int(60 / period))
    fr = (ts * fps).astype(int)
    fr = fr[fr < len(env)]
    s = env[fr].sum()
    if s > best:
        best, off = s, float(ph)

# drop: biggest sustained RMS jump between adjacent 3s blocks
hop_r = SR // 4
nr = len(a) // hop_r
rms = np.sqrt(np.mean(a[: nr * hop_r].reshape(nr, hop_r) ** 2, axis=1))
blk = 12
jumps = [(rms[i:i + blk].mean() - rms[i - blk:i].mean(), i / 4.0)
         for i in range(blk, min(nr - blk, 4 * 60))]
_, drop_t = max(jumps)
drop = off + round((drop_t - off) / period) * period

json.dump({"bpm": round(bpm, 3), "period": round(period, 5),
           "beat_offset": round(off, 4), "drop": round(drop, 3)},
          open("build/mm_analysis.json", "w"), indent=1)
print(f"bpm {bpm:.2f}  period {period:.4f}  offset {off:.3f}  drop {drop:.3f} (raw {drop_t:.2f})")

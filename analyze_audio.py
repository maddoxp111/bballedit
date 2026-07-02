"""Analyze the song: find BPM, beat grid, and the best 60s window for the edit.

Outputs build/analysis.json with:
  - start: chosen window start (seconds into the song)
  - bpm, beat_offset: beat grid (beats at beat_offset + k * 60/bpm, in window-local time)
  - beats: beat times within the 60s window (window-local seconds)
  - energy: per-0.5s normalized RMS energy inside the window (for intensity-driven visuals)
"""
import json
import subprocess
import sys
import wave

import numpy as np

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SONG = "assets/audio/40_Nights.mp3"
SR = 22050
DUR = 60.0

wav_path = "build/song_mono.wav"
subprocess.run([FFMPEG, "-y", "-i", SONG, "-ac", "1", "-ar", str(SR), wav_path],
               check=True, capture_output=True)

with wave.open(wav_path) as w:
    n = w.getnframes()
    audio = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0

total_dur = len(audio) / SR
print(f"decoded {total_dur:.1f}s @ {SR}Hz")

# --- onset envelope via spectral flux ---
hop, nfft = 512, 1024
frames = 1 + (len(audio) - nfft) // hop
win = np.hanning(nfft).astype(np.float32)
idx = np.arange(nfft)[None, :] + hop * np.arange(frames)[:, None]
spec = np.abs(np.fft.rfft(audio[idx] * win, axis=1))
flux = np.maximum(spec[1:] - spec[:-1], 0).sum(axis=1)
flux = np.concatenate([[0], flux])
# smooth + normalize
kernel = np.hanning(9); kernel /= kernel.sum()
env = np.convolve(flux, kernel, mode="same")
env = (env - env.min()) / (env.max() - env.min() + 1e-9)
fps_env = SR / hop  # envelope frames per second

# --- tempo via autocorrelation of onset envelope ---
seg = env[: int(fps_env * min(total_dur, 180))]
seg = seg - seg.mean()
ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
# search lags for 60-180 BPM
lags = np.arange(int(fps_env * 60 / 180), int(fps_env * 60 / 60))
best_lag = lags[np.argmax(ac[lags])]
bpm = 60.0 * fps_env / best_lag
print(f"tempo: {bpm:.2f} BPM (lag {best_lag})")

# --- RMS energy profile to pick the loudest 60s window, aligned near a big onset ---
hop_rms = SR // 2  # 0.5s
n_rms = len(audio) // hop_rms
rms = np.sqrt(np.mean(audio[: n_rms * hop_rms].reshape(n_rms, hop_rms) ** 2, axis=1))
win_len = int(DUR * 2)  # windows of 60s in 0.5s steps
sums = np.convolve(rms, np.ones(win_len), "valid")
best = int(np.argmax(sums))
start = best / 2.0
# don't start mid-song at an awkward point: snap to the strongest onset within +-2s
lo = max(0, int((start - 2) * fps_env)); hi = int((start + 2) * fps_env)
start = (lo + int(np.argmax(env[lo:hi]))) / fps_env
start = max(0.0, min(start, total_dur - DUR - 1))
print(f"window: {start:.2f}s - {start + DUR:.2f}s")

# --- beat phase: align grid to maximize onset energy at beat times ---
period = 60.0 / bpm
n_test = 64
phases = np.linspace(0, period, n_test, endpoint=False)
scores = []
for ph in phases:
    ts = start + ph + period * np.arange(int(DUR / period))
    fr = (ts * fps_env).astype(int)
    fr = fr[fr < len(env)]
    scores.append(env[fr].sum())
beat_offset = float(phases[int(np.argmax(scores))])
beats = [round(float(beat_offset + k * period), 4)
         for k in range(int((DUR - beat_offset) / period) + 1)]
print(f"beat offset {beat_offset:.3f}s, {len(beats)} beats in window")

# window-local energy per 0.5s, normalized
w0 = int(start * 2)
wen = rms[w0: w0 + win_len]
wen = (wen - wen.min()) / (wen.max() - wen.min() + 1e-9)

json.dump({
    "bpm": round(bpm, 3), "start": round(start, 3), "beat_offset": round(beat_offset, 4),
    "period": round(period, 5), "beats": beats,
    "energy": [round(float(x), 4) for x in wen],
}, open("build/analysis.json", "w"), indent=1)
print("wrote build/analysis.json")

"""Build the 60s soundtrack: song from 0:00 + synthesized SFX.

- riser into the drop
- sub-bass boom at the drop and each section slam
- whoosh on every clip cut
Writes build/mix.wav (48kHz stereo).
"""
import json
import subprocess

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
DUR = 60.0

A = json.load(open("build/analysis2.json"))
P, OFF = A["period"], A["beat_offset"]
bt = lambda b: OFF + b * P

# timeline (must match render_edit2.py)
DROP = 9
BLOCKS = [13, 33, 53]          # klabo / walker / kinziger name slams
ROSTER, FINALE = 69, 77
CUTS = [b for b in range(DROP, ROSTER, 4)] + [ROSTER, FINALE] + list(range(ROSTER + 2, FINALE, 2))

subprocess.run([FFMPEG, "-y", "-i", "assets/audio/40_Nights.mp3", "-ac", "2",
                "-ar", str(SR), "-t", str(DUR), "build/song60.wav"],
               check=True, capture_output=True)
import wave
with wave.open("build/song60.wav") as w:
    song = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
song = song.reshape(-1, 2).astype(np.float32) / 32768.0
mix = np.zeros((int(DUR * SR), 2), np.float32)
mix[: len(song)] = song * 0.92

rng = np.random.default_rng(7)


def add(sig, t, gain):
    i0 = int(t * SR)
    n = min(len(sig), len(mix) - i0)
    if n > 0:
        mix[i0:i0 + n] += sig[:n, None] * gain


def boom(dur=0.9):
    t = np.linspace(0, dur, int(SR * dur), False)
    f = 110 * np.exp(-t * 3.5) + 42
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 4.0)
    x += rng.normal(0, 1, len(t)) * np.exp(-t * 60) * 0.6  # attack click
    return np.tanh(x * 1.8)


def whoosh(dur=0.38):
    n = int(SR * dur)
    x = rng.normal(0, 1, n).astype(np.float32)
    # crude bandpass via cascaded diff/cumsum, then swell-and-die envelope
    x = np.diff(np.concatenate([[0], x]))
    k = np.hanning(64); k /= k.sum()
    x = np.convolve(x, k, mode="same")
    t = np.linspace(0, 1, n)
    return x / (np.abs(x).max() + 1e-9) * np.sin(np.pi * t) ** 2


def riser(dur=3.0):
    n = int(SR * dur)
    x = rng.normal(0, 1, n).astype(np.float32)
    win = 512
    out = np.zeros(n, np.float32)
    for i in range(0, n - win, win // 2):  # narrowing smoother -> rising brightness
        w = max(8, int(400 * (1 - i / n) + 8))
        k = np.hanning(w); k /= k.sum()
        seg = np.convolve(x[i:i + win], k, mode="same")
        out[i:i + win] += seg * np.hanning(win)
    t = np.linspace(0, 1, n)
    return out / (np.abs(out).max() + 1e-9) * t ** 2.2


add(riser(3.0), bt(DROP) - 3.0, 0.5)
add(boom(1.2), bt(DROP) - 0.02, 0.85)
for b in BLOCKS:
    add(boom(), bt(b) - 0.02, 0.7)
add(boom(), bt(ROSTER) - 0.02, 0.6)
add(boom(1.4), bt(FINALE) - 0.02, 0.85)
for b in CUTS:
    add(whoosh(), bt(b) - 0.30, 0.4)

# fade out
n_f = int(2.5 * SR)
mix[-n_f:] *= np.linspace(1, 0, n_f)[:, None]
mix = np.clip(mix, -0.99, 0.99)

with wave.open("build/mix.wav", "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote build/mix.wav")

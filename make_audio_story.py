"""Soundtrack for the storytelling edit -> build/story_mix.wav (48k stereo).

Arc: Pedon's "fight together" speech (dry, no music) -> silence + title card
-> the song STARTS under the NIT broadcast (its beat drop lands on the
game-winner's splash) -> song pauses for the locker room "WE ARE STILL HERE"
-> a riser runs from the first highlight's tip-off and the song slams back
in the instant the dunk goes down -> fade, with one quiet reprise of
"we'll always be there for each other" at the end.
"""
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
DUR = 90.2

FT = "build/tt/7635009865773092110.mp4"      # "fight together" speech
LOCKER = "build/tt/7621387281575775519.mp4"  # "we are still here"
GW = "build/clips/48282239.mp4"              # game-winner broadcast
SONG = "assets/audio/40_Nights.mp3"
HIT_T = 47.7                                  # the opening dunk lands here
RESUME_SRC = 9.7815                           # beat 15 of the song (continuity)


def load(path, t0=None, dur=None):
    args = [FFMPEG, "-y"]
    if t0 is not None:
        args += ["-ss", f"{t0:.3f}"]
    args += ["-i", path]
    if dur is not None:
        args += ["-t", f"{dur:.3f}"]
    args += ["-ac", "2", "-ar", str(SR), "build/_seg.wav"]
    subprocess.run(args, check=True, capture_output=True)
    with wave.open("build/_seg.wav") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return a.reshape(-1, 2).astype(np.float32) / 32768.0


def lowpass(x, fc):
    a = 1.0 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = np.zeros(2, np.float32)
    for i in range(len(x)):          # one-pole, fine for pads
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def env(x, fade_in=0.0, fade_out=0.0):
    n = len(x)
    e = np.ones(n, np.float32)
    if fade_in > 0:
        k = int(fade_in * SR); e[:k] = np.linspace(0, 1, k)
    if fade_out > 0:
        k = int(fade_out * SR); e[-k:] = np.linspace(1, 0, k)
    return x * e[:, None]


mix = np.zeros((int(DUR * SR), 2), np.float32)


def add(x, t, gain=1.0):
    i = int(t * SR)
    n = min(len(x), len(mix) - i)
    mix[i:i + n] += x[:n] * gain


rng = np.random.default_rng(3)

# --- act 1: dry speech, no music
add(env(load(FT, 0.0, 7.92), 0.05, 0.08), 0.0, 1.2)
add(env(load(FT, 26.72, 10.08), 0.08, 0.10), 7.92, 1.2)

# --- act 2: song begins under the broadcast; its drop (src 5.88) lands at
# timeline 25.78 — the exact moment the game-winner splashes
add(env(load(GW, 13.4, 10.0), 0.15, 1.0), 19.9, 1.0)
add(env(load(SONG, 0, 10.0), 0.4, 0.5), 19.9, 0.55)

# --- act 3: locker room, song paused
add(env(load(LOCKER, 16.0, 16.1), 0.2, 1.4), 29.9, 1.15)

# --- riser: starts with the first highlight, ends the instant the dunk lands
rl = HIT_T - 46.0
n = int(rl * SR)
x = rng.normal(0, 1, n).astype(np.float32)
t = np.linspace(0, 1, n)
riser = np.cumsum(x) / 200.0
riser = (riser - riser.mean())
riser /= np.abs(riser).max() + 1e-9
add(np.stack([riser, riser], 1) * (t ** 2.2)[:, None], 46.0, 0.55)
bt = np.linspace(0, 1.1, int(1.1 * SR), False)
f = 105 * np.exp(-bt * 3.4) + 40
boom = np.tanh(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-bt * 3.6) * 1.9)
add(np.stack([boom, boom], 1), HIT_T - 0.02, 0.75)

# --- act 4 into act 5: the song slams back in on the dunk (beat-aligned),
# then ducks under the coach's reprise and keeps playing to the end
seg = load(SONG, RESUME_SRC, DUR - HIT_T)
e = np.ones(len(seg), np.float32)
k0 = int((73.7 - HIT_T) * SR)            # ease down as act 5 begins
k1 = min(k0 + int(3.0 * SR), len(seg))
e[k0:k1] = np.linspace(1, 0.38, k1 - k0)
e[k1:] = 0.38
add(env(seg * e[:, None], 0.015, 1.5), HIT_T, 0.95)

# --- act 5: quiet reprise
add(env(lowpass(load(FT, 26.72, 4.2), 2400), 0.3, 0.9), 81.2, 0.95)

# master fade + clip
k = int(2.0 * SR)
mix[-k:] *= np.linspace(1, 0, k)[:, None]
mix = np.clip(mix, -0.99, 0.99)
with wave.open("build/story_mix.wav", "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote build/story_mix.wav")

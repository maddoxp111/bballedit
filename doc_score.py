"""Cinematic underscore for the Redbirds documentary trailer -> build/doc_music.wav.

A synthesised trailer score built to the voiceover's emotional arc: a low
drone and sparse piano under the cold open, strings swelling as the NIT run
builds, a hit and a drop on the game-winner, a stripped-back reflective
passage on "the roster leaves", then a full build that resolves under
"2026, 2027". Everything is generated (no samples), 48k stereo.
"""
import wave

import numpy as np

SR = 48000
DUR = 109.0
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(17)

# --- timeline anchors (video seconds; VO starts at 4.5) ---
T_OPEN, T_BUILD, T_RUN = 0.0, 20.0, 32.0
T_SHOT, T_FALL, T_REFLECT = 42.35, 43.6, 49.0
T_RETURN, T_RISE, T_PEAK, T_OUT = 56.0, 69.0, 79.5, 86.2
T_MONTAGE, T_CARD = 86.2, 104.0     # wordless montage, then the season card

A4 = 220.0
def note(semi):
    return A4 * 2 ** (semi / 12.0)

# D minor-ish: D F A C E G
ROOT = note(-7)          # D3
CHORDS = [               # (start, end, [semitones from A4])
    (0.0, 20.0, [-19, -7, 5]),          # D1/D3/A
    (20.0, 32.0, [-19, -7, 3, 8]),      # add C, F
    (32.0, 42.35, [-19, -7, 5, 12]),
    (42.35, 49.0, [-19, -12, 0, 7]),
    (49.0, 56.0, [-19, -7, 3]),
    (56.0, 69.0, [-19, -7, 5, 8]),
    (69.0, 79.5, [-19, -7, 5, 12]),
    (79.5, 86.2, [-19, -7, 5, 12, 17]),
    (86.2, 96.0, [-19, -7, 3, 8, 15]),
    (96.0, 109.0, [-19, -7, 5, 12, 17]),
]


def env(a, times, vals, curve=1.0):
    """Piecewise-linear envelope over the whole track."""
    e = np.interp(a, times, vals)
    return e ** curve


def saw(freq_hz, phase=0.0):
    ph = 2 * np.pi * freq_hz * t + phase
    # band-limited-ish saw via a few harmonics
    out = np.zeros(N, np.float32)
    for h in range(1, 9):
        out += np.sin(ph * h) / h
    return out * 0.5


def pad_layer():
    """Sustained string-ish bed that follows the chord map."""
    out = np.zeros(N, np.float32)
    for c0, c1, semis in CHORDS:
        i0, i1 = int(c0 * SR), int(min(c1, DUR) * SR)
        seg = np.zeros(i1 - i0, np.float32)
        tt = np.arange(i1 - i0) / SR
        for s in semis:
            f = note(s)
            for det in (-0.14, 0.0, 0.15):     # chorus detune
                ph = 2 * np.pi * (f + det) * tt
                v = np.zeros_like(tt)
                for h in range(1, 7):
                    v += np.sin(ph * h + rng.uniform(0, 6)) / (h * 1.35)
                seg += v
        # slow tremolo + edge fades
        seg *= 1.0 + 0.06 * np.sin(2 * np.pi * 0.7 * tt)
        f_in = min(len(seg), int(1.2 * SR))
        f_out = min(len(seg), int(1.6 * SR))
        seg[:f_in] *= np.linspace(0, 1, f_in)
        seg[-f_out:] *= np.linspace(1, 0.35, f_out)
        out[i0:i1] += seg / max(1, len(semis) * 2)
    return out


def sub_drone():
    f = ROOT / 4
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2 * t)
    return x * env(t, [0, 3, 42, 43, 49, 56, 79, 96, 104, 109], [0, .8, 1, .35, .5, .8, 1, 1, .55, 0])


def piano(times_semis, decay=3.2, gain=1.0):
    """Simple struck-string tone: a few detuned partials with fast decay."""
    out = np.zeros(N, np.float32)
    for (t0, semi) in times_semis:
        i0 = int(t0 * SR)
        n = min(int(5.0 * SR), N - i0)
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        f = note(semi)
        v = np.zeros(n, np.float32)
        for h, amp in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.10)):
            v += amp * np.sin(2 * np.pi * f * h * tt + rng.uniform(0, 6))
        v *= np.exp(-tt * decay)
        v[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
        out[i0:i0 + n] += v * gain
    return out


def taiko(times, gain=1.0):
    out = np.zeros(N, np.float32)
    for t0 in times:
        i0 = int(t0 * SR)
        n = min(int(1.4 * SR), N - i0)
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        f = 62 * np.exp(-tt * 9) + 41
        v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4.2)
        v += rng.normal(0, 1, n) * np.exp(-tt * 42) * 0.5
        out[i0:i0 + n] += np.tanh(v * 1.6) * gain
    return out


def riser(t0, dur, gain=1.0):
    out = np.zeros(N, np.float32)
    i0 = int(t0 * SR)
    n = min(int(dur * SR), N - i0)
    if n <= 0:
        return out
    tt = np.linspace(0, 1, n)
    x = rng.normal(0, 1, n).astype(np.float32)
    acc = np.cumsum(x) / 300.0
    acc -= acc.mean()
    acc /= np.abs(acc).max() + 1e-9
    # rising whine on top
    f = 240 * (1 + 6 * tt ** 2)
    whine = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    out[i0:i0 + n] = (acc + whine) * (tt ** 2.2) * gain
    return out


def impact(t0, gain=1.0):
    out = np.zeros(N, np.float32)
    i0 = int(t0 * SR)
    n = min(int(3.5 * SR), N - i0)
    if n <= 0:
        return out
    tt = np.arange(n) / SR
    f = 90 * np.exp(-tt * 2.6) + 33
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.7)
    noise = rng.normal(0, 1, n) * np.exp(-tt * 16) * 0.55
    out[i0:i0 + n] = np.tanh((boom + noise) * 1.7) * gain
    return out


# --- assemble ---
mix = np.zeros(N, np.float32)
mix += pad_layer() * env(t, [0, 6, 20, 32, 42.35, 43.5, 49, 56, 69, 79.5, 86.2, 96, 104, 109],
                         [0, .30, .42, .60, .85, .30, .34, .52, .72, .92, .82, 1.0, .72, 0]) * 0.85
mix += sub_drone() * 0.30

# sparse piano motif: cold open, reflective passage, and the resolve
motif_a = [(2.0, -7), (5.4, 0), (8.6, 3), (12.0, -2), (16.2, 0)]
motif_b = [(49.6, -7), (52.0, 0), (54.4, 3), (57.0, -2), (60.2, 0), (63.4, 3), (66.0, 5)]
motif_c = [(79.8, 12), (81.4, 8), (83.0, 5), (85.0, 0)]
motif_d = [(99.5, 12), (101.2, 8), (103.0, 5), (105.2, 0), (107.0, -7)]
mix += piano(motif_a, gain=0.30)
mix += piano(motif_b, gain=0.26)
mix += piano(motif_c, gain=0.34)
mix += piano(motif_d, gain=0.32)

# percussion: enters on the build, drives the run, drops out after the shot
beat = 60.0 / 84.0                      # ~84 bpm
hits = [20.0 + k * beat * 2 for k in range(int((42.35 - 20.0) / (beat * 2)) + 1)]
gains = np.linspace(0.28, 0.95, len(hits))
for h, g in zip(hits, gains):
    mix += taiko([h], gain=float(g)) * 0.5
# return section rebuild
hits2 = [56.0 + k * beat * 2 for k in range(int((104.0 - 56.0) / (beat * 2)) + 1)]
g2 = np.linspace(0.30, 1.0, len(hits2))
for h, g in zip(hits2, g2):
    mix += taiko([h], gain=float(g)) * 0.55

mix += riser(37.5, 4.8, 0.42)           # into the game-winner
mix += impact(T_SHOT, 0.85)             # the shot lands
mix += riser(74.0, 5.5, 0.34)           # into the resolve
mix += impact(79.5, 0.55)
mix += riser(99.0, 4.6, 0.30)           # into the season card
mix += impact(104.0, 0.70)
mix += taiko([86.2], gain=0.7)

# gentle master shaping
mix *= env(t, [0, 1.5, 107.0, 109], [0, 1, 1, 0])
mix = np.tanh(mix * 0.85)
mix /= np.abs(mix).max() + 1e-9
mix *= 0.72

# stereo: slight haas widening on the pad-heavy mid
left = mix.copy()
right = np.concatenate([np.zeros(int(0.008 * SR), np.float32), mix])[:N] * 0.97 + mix * 0.03
st = np.stack([left, right], 1)
st = np.clip(st, -0.99, 0.99)

with wave.open("build/doc_music.wav", "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("wrote build/doc_music.wav", round(len(st) / SR, 2), "s")

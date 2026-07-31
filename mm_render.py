"""Malik Messina-Moore — COMMITTED mixtape (1080x1920, 30fps, ~38s).

Mixtape grammar: ball-tracked full-screen crops cut on the beat, VHS/tape
grade with scanlines, grain and chromatic fringing, punch-in zooms, big
condensed type, stat tags, and a slow-mo replay of the slam into the
commitment card. Song is "2 Hard 4 The Radio"; the marquee dunk flushes
exactly on the beat drop. SFX are synthesized.

Run after mm_analyze.py and mm_build.py.
Usage: python3 mm_render.py [--preview t1,t2,...]
"""
import json
import math
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
SR = 48000

M = json.load(open("build/mm_meta.json"))
P = M["period"]
SONG_START = M["song_start"]
SEGS = M["segments"]
DUR = 64 * P + 1.25          # outro card runs to the end

SONG = "assets/audio/2_hard_4_the_radio.mp3"
ANTON = "assets/fonts/Anton-Regular.ttf"
OSWALD = "assets/fonts/Oswald.ttf"
LOGO = Image.open("assets/logo/logo_hi.png").convert("RGBA")

RED = (206, 17, 38)
WHITE = (244, 244, 246)
_fonts = {}


def font(path, size, weight=None):
    key = (path, size, weight)
    if key not in _fonts:
        f = ImageFont.truetype(path, size)
        if weight:
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
        _fonts[key] = f
    return _fonts[key]


def bt(b):
    return b * P


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- footage

_cache = {}


def seg_at(t):
    for s in SEGS:
        if s["t0"] <= t < s["t1"]:
            return s
    return None


def load_frame(i, idx):
    key = (i, idx)
    if key not in _cache:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = np.asarray(
            Image.open(f"build/mm/{i:02d}/{idx:04d}.jpg").convert("RGB")).astype(np.float32)
    return _cache[key]


def seg_frame(s, t):
    """Frame-blended lookup + ball-tracked vertical crop."""
    local = t - s["t0"]
    pos = local * s["speed"] * FPS
    n = s["frames"]
    i0 = int(pos)
    frac = pos - i0
    a = max(1, min(n, i0 + 1))
    b = max(1, min(n, i0 + 2))
    fa = load_frame(s["i"], a)
    src = fa
    if b != a and frac > 0.02 and s["speed"] < 1.0:
        fb = load_frame(s["i"], b)
        if fb.shape == fa.shape:
            src = fa * (1 - frac) + fb * frac
    sh, sw = src.shape[:2]
    drift = 1.0 + 0.05 * min(1.0, local / 2.4)
    punch = 1.0 + 0.10 * math.exp(-max(0.0, local) / 0.16)
    # already-tight shots (bodies filling frame) get no extra zoom
    bh = s.get("bodyh") or [0.0]
    body = bh[min(a - 1, len(bh) - 1)]
    base = 0.78 if body < 0.42 else min(1.0, 0.78 + (body - 0.42) * 1.5)
    ch = int(min(sh, sh * base / (drift * punch)))
    cw = int(ch * 9 / 16)
    tr = s["track"]
    x = tr[min(a - 1, len(tr) - 1)]
    cx = max(cw // 2, min(sw - cw // 2, int(x * sw)))
    top = int(sh * 0.035)
    crop = src[top:top + ch, cx - cw // 2: cx - cw // 2 + cw]
    img = Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    return np.asarray(img).astype(np.float32)


def grade(arr):
    """Punchy tape look: contrast, crushed blacks, red push."""
    luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2])[..., None]
    out = luma * 0.18 + arr * 0.82
    out = (out - 18) * 1.16
    out[..., 0] *= 1.05
    out[..., 2] *= 0.97
    return np.clip(out, 0, 255)


# ---------------------------------------------------------------- type

def fit(path, s, max_w, size, weight=None):
    f = font(path, size, weight)
    while f.getbbox(s)[2] - f.getbbox(s)[0] > max_w and size > 18:
        size -= 4
        f = font(path, size, weight)
    return f


def center_text(d, s, fnt, cy, fill=WHITE, alpha=255, shadow=(0, 0, 0), track=0):
    if track:
        ws = [fnt.getbbox(c)[2] - fnt.getbbox(c)[0] for c in s]
        total = sum(ws) + track * (len(s) - 1)
        x = W // 2 - total // 2
        box = fnt.getbbox(s)
        y = cy - (box[3] - box[1]) // 2 - box[1]
        for c, cw_ in zip(s, ws):
            if shadow:
                d.text((x + 4, y + 4), c, font=fnt, fill=(*shadow, alpha))
            d.text((x, y), c, font=fnt, fill=(*fill, alpha))
            x += cw_ + track
        return
    box = fnt.getbbox(s)
    x = W // 2 - (box[2] - box[0]) // 2
    y = cy - (box[3] - box[1]) // 2 - box[1]
    if shadow:
        d.text((x + 4, y + 4), s, font=fnt, fill=(*shadow, alpha))
    d.text((x, y), s, font=fnt, fill=(*fill, alpha))


def stamp(d, s, cy, size, alpha=255, pad=26):
    """Red slab with knocked-out text."""
    fnt = fit(ANTON, s, 920, size)
    box = fnt.getbbox(s)
    tw, th = box[2] - box[0], box[3] - box[1]
    x0, x1 = W // 2 - tw // 2 - pad, W // 2 + tw // 2 + pad
    d.rectangle([x0, cy - th // 2 - pad, x1, cy + th // 2 + pad], fill=(*RED, alpha))
    center_text(d, s, fnt, cy, WHITE, alpha, shadow=None)


# stat tags: (beat_on, beat_off, big, small)
TAGS = [
    (12.5, 17.5, "10.9", "POINTS PER GAME"),
    (26.5, 30.5, "3.8", "ASSISTS PER GAME"),
    (36.5, 40.5, "33", "STARTS AT XAVIER"),
    (41.5, 45.5, "6'4\"", "COMBO GUARD"),
]


def draw_tags(img, t):
    b = t / P
    d = ImageDraw.Draw(img, "RGBA")
    for b0, b1, big, small in TAGS:
        if b0 <= b < b1:
            a = int(255 * min(1.0, (b - b0) / 0.5, max(0.0, (b1 - b) / 0.5)))
            if a <= 0:
                continue
            y = H - 330
            d.rectangle([70, y - 6, 82, y + 150], fill=(*RED, a))
            f1 = font(ANTON, 132)
            box = f1.getbbox(big)
            d.text((110 + 4, y - box[1] + 4), big, font=f1, fill=(0, 0, 0, a))
            d.text((110, y - box[1]), big, font=f1, fill=(*WHITE, a))
            f2 = font(OSWALD, 44, 500)
            d.text((114 + 3, y + 116 + 3), small, font=f2, fill=(0, 0, 0, a))
            d.text((114, y + 116), small, font=f2, fill=(230, 230, 235, a))


def name_bug(img, t):
    """Persistent small name bug during the run."""
    b = t / P
    if not (6.5 <= b < 56.0):
        return
    a = int(230 * min(1.0, (b - 6.5) / 0.6, max(0.0, (56.0 - b) / 0.6)))
    d = ImageDraw.Draw(img, "RGBA")
    f = font(OSWALD, 40, 600)
    s = "MALIK MESSINA-MOORE"
    box = f.getbbox(s)
    tw = box[2] - box[0]
    d.rectangle([70, 150, 70 + tw + 46, 150 + 74], fill=(10, 10, 12, int(a * 0.72)))
    d.rectangle([70, 150, 82, 150 + 74], fill=(*RED, a))
    d.text((96, 150 + 37 - (box[3] - box[1]) // 2 - box[1]), s, font=f, fill=(*WHITE, a))


# ---------------------------------------------------------------- cards

def card_bg(t, seed=0):
    arr = np.full((H, W, 3), 8.0, np.float32)
    yy = np.arange(H)[:, None, None]
    arr += np.sin(yy * 0.035 + t * 5) * 3.0
    return arr


def intro_card(t):
    b = t / P
    arr = card_bg(t)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    if b >= 0.4:
        a = int(255 * ease((b - 0.4) / 1.0))
        f = fit(ANTON, "MALIK", 900, 190)
        center_text(d, "MALIK", f, H // 2 - 250, WHITE, a)
        f2 = fit(ANTON, "MESSINA-MOORE", 980, 150)
        center_text(d, "MESSINA-MOORE", f2, H // 2 - 90, WHITE, a)
    if b >= 2.2:
        a = int(255 * ease((b - 2.2) / 0.6))
        sc = 1.0 + 0.5 * (1 - ease((b - 2.2) / 0.6))
        stamp(d, "COMMITTED", H // 2 + 120, int(120 * sc), a)
    if b >= 3.4:
        a = int(230 * ease((b - 3.4) / 0.5))
        center_text(d, "ILLINOIS STATE", font(OSWALD, 56, 500), H // 2 + 280,
                    (200, 200, 205), a, track=10)
    return np.asarray(img).astype(np.float32)


def transition_card(t):
    b = t / P - 23
    arr = card_bg(t)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * ease(b / 0.4))
    center_text(d, "XAVIER", fit(ANTON, "XAVIER", 900, 150), H // 2 - 190, (150, 150, 155), a)
    f = font(ANTON, 130)
    center_text(d, "↓", f, H // 2 - 20, RED, a)
    center_text(d, "ILLINOIS STATE", fit(ANTON, "ILLINOIS STATE", 960, 150),
                H // 2 + 150, WHITE, a)
    return np.asarray(img).astype(np.float32)


def outro_card(t):
    b = t / P - 57
    arr = card_bg(t)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    lw = int(880 * (1.0 + 0.02 * math.sin(b * 0.9)))
    lg = LOGO.resize((lw, int(LOGO.size[1] * lw / LOGO.size[0])), Image.LANCZOS)
    a = ease(b / 0.5)
    if a > 0:
        tmp = lg.copy()
        tmp.putalpha(lg.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(tmp, (W // 2 - lw // 2, H // 2 - 500))
    d = ImageDraw.Draw(img, "RGBA")
    if b >= 0.8:
        aa = int(255 * ease((b - 0.8) / 0.5))
        sc = 1.0 + 0.4 * (1 - ease((b - 0.8) / 0.5))
        stamp(d, "COMMITTED", H // 2 + 330, int(140 * sc), aa)
    if b >= 1.8:
        aa = int(235 * ease((b - 1.8) / 0.5))
        center_text(d, "2026 — 27", font(OSWALD, 54, 500), H // 2 + 500,
                    (190, 190, 195), aa, track=12)
    if b >= 2.6:
        aa = int(210 * ease((b - 2.6) / 0.5))
        center_text(d, "ROLL BIRDS", font(OSWALD, 44, 500), H // 2 + 590,
                    (140, 140, 146), aa, track=10)
    return np.asarray(img.convert("RGB")).astype(np.float32)


# ---------------------------------------------------------------- fx

MONEY = [s["money_t"] for s in SEGS]
CUTS = sorted({s["t0"] for s in SEGS} | {bt(23), bt(26), bt(57)})
_grain = [np.random.default_rng(s).integers(-11, 11, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.10 - 0.30 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


_scan = None


def scanlines():
    global _scan
    if _scan is None:
        y = np.arange(H)[:, None, None]
        _scan = (1.0 - 0.055 * (np.sin(y * math.pi) ** 2)).astype(np.float32)
        _scan = (1.0 - 0.05 * ((y % 3) == 0)).astype(np.float32)
    return _scan


def render_frame(fi):
    t = fi / FPS
    b = t / P
    s = seg_at(t)
    if s is not None:
        arr = grade(seg_frame(s, t))
    elif b < 5:
        arr = intro_card(t)
    elif 23 <= b < 26:
        arr = transition_card(t)
    else:
        arr = outro_card(t)

    # chromatic fringe + shake + flash on money moments
    for mt in MONEY:
        dt = t - mt
        if 0 <= dt < 0.20:
            sh = int(10 * (1 - dt / 0.20)) + 4
            arr[:, :, 0] = np.roll(arr[:, :, 0], sh, axis=1)
            arr[:, :, 2] = np.roll(arr[:, :, 2], -sh, axis=1)
        if 0 <= dt < 0.10:
            arr = arr + 70 * (1 - dt / 0.10)
        if 0 <= dt < 0.45:
            amp = 13 * math.exp(-dt * 9)
            if amp > 1:
                r = np.random.default_rng(fi * 17)
                arr = np.roll(arr, (int(r.integers(-1, 2) * amp),
                                    int(r.integers(-1, 2) * amp)), (0, 1))
    # tape glitch on cuts
    for ct in CUTS:
        dt = t - ct
        if 0 <= dt < 0.13:
            r = np.random.default_rng(fi * 7)
            for _ in range(3):
                y0 = int(r.integers(0, H - 90))
                hgt = int(r.integers(18, 80))
                arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(r.integers(-70, 70)), axis=1)

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if s is not None:
        name_bug(img, t)
        draw_tags(img, t)
    arr = np.asarray(img).astype(np.float32)

    arr = arr * scanlines() * vignette()
    g = _grain[fi % 8]
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[:H, :W]
    arr = arr + g
    if t < 0.35:
        arr *= t / 0.35
    if t > DUR - 1.0:
        arr *= max(0.0, (DUR - t) / 1.0)
    return np.clip(arr, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- audio

def build_audio():
    mix = np.zeros((int(DUR * SR), 2), np.float32)
    rng = np.random.default_rng(9)

    def add(sig, t, gain=1.0):
        if sig.ndim == 1:
            sig = np.stack([sig, sig], 1)
        i = int(t * SR)
        n = min(len(sig), len(mix) - i)
        if n > 0:
            mix[i:i + n] += sig[:n] * gain

    subprocess.run([FFMPEG, "-y", "-ss", f"{SONG_START:.3f}", "-i", SONG,
                    "-t", f"{DUR:.3f}", "-ac", "2", "-ar", str(SR),
                    "build/mm_song_seg.wav"], check=True, capture_output=True)
    with wave.open("build/mm_song_seg.wav") as w:
        song = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    song = song.reshape(-1, 2).astype(np.float32) / 32768.0
    e = np.ones(len(song), np.float32)
    k = int(0.25 * SR)
    e[:k] = np.linspace(0, 1, k)
    k2 = int(1.6 * SR)
    e[-k2:] = np.linspace(1, 0, k2)
    add(song * e[:, None], 0.0, 0.92)

    def whoosh(dur=0.34):
        n = int(dur * SR)
        x = np.diff(rng.normal(0, 1, n).astype(np.float32), prepend=0)
        kk = np.hanning(70); kk /= kk.sum()
        x = np.convolve(x, kk, "same")
        return x / (np.abs(x).max() + 1e-9) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2

    def boom(dur=0.85):
        tt = np.linspace(0, dur, int(dur * SR), False)
        f = 108 * np.exp(-tt * 3.5) + 40
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.8)
        x += rng.normal(0, 1, len(tt)) * np.exp(-tt * 55) * 0.6
        return np.tanh(x * 1.8)

    # riser through the intro cards into the drop
    n = int(bt(6) * SR)
    tt = np.linspace(0, 1, n)
    ris = np.cumsum(rng.normal(0, 1, n).astype(np.float32)) / 260.0
    ris -= ris.mean()
    ris /= np.abs(ris).max() + 1e-9
    add(ris * (tt ** 2.3), 0.0, 0.5)

    for ct in CUTS:
        add(whoosh(), max(0.0, ct - 0.3), 0.34)
    for mt in MONEY:
        add(boom(), max(0.0, mt - 0.01), 0.62)
    # extra sub on the drop + the slow-mo replay
    for mt in (bt(6), bt(52.5)):
        tt = np.linspace(0, 1.5, int(1.5 * SR), False)
        sub = np.sin(2 * np.pi * np.cumsum(np.linspace(56, 30, len(tt))) / SR)
        add(sub * np.exp(-tt * 2.1), mt, 0.5)
    # stamp hits on the cards
    for cb in (2.2, 57.8):
        add(boom(0.7), bt(cb), 0.5)

    mix = np.clip(mix, -0.99, 0.99)
    with wave.open("build/mm_mix.wav", "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print("wrote build/mm_mix.wav")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render_frame(int(float(ts) * FPS))).save(f"build/pm_{ts}.png")
            print(f"build/pm_{ts}.png")
        return
    build_audio()
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "22", "-pix_fmt", "yuv420p", "build/mm_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 150 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/mm_silent.mp4", "-i", "build/mm_mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", "messina_moore_committed.mp4"],
        check=True, capture_output=True)
    print("wrote messina_moore_committed.mp4")


if __name__ == "__main__":
    main()

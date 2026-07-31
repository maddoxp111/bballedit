"""Malik Messina-Moore — COMMITTED mixtape, horizontal cut (1920x1080, 30fps, ~60s).

Full-frame 16:9 broadcast footage (no crop, no tracking), text only in the
intro, no sound design — just the song. Cuts land on the beat grid and the
marquee dunk flushes exactly on the drop.

  python3 mm_wide.py extract     # pull frames for every segment
  python3 mm_wide.py             # render messina_moore_committed_wide.mp4
  python3 mm_wide.py sheet       # contact sheet of segment midpoints
"""
import json
import math
import os
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, SR = 1920, 1080, 30, 48000

A = json.load(open("build/mm_analysis.json"))
P, DROP = A["period"], A["drop"]
SONG = "assets/audio/2_hard_4_the_radio.mp3"
SONG_START = DROP - 6 * P          # timeline 0 -> here; drop lands on beat 6
END_BEAT = 103
DUR = END_BEAT * P + 0.75

ANTON = "assets/fonts/Anton-Regular.ttf"
OSWALD = "assets/fonts/Oswald.ttf"
RED = (206, 17, 38)
WHITE = (244, 244, 246)
_fonts = {}

# (b0, b1, clip, src_start, speed) — everything runs at real speed.
# Avoided on purpose: 38858052 11.4-14.8 (the camera follows a different
# Pepperdine player there, Malik is #3), 39688928 21-26.5 (broadcast stats
# graphics) and 35318773 14.4-15.5 (whip-pan blur).
CUTS = [
    (5,  12, "47131767",  7.72, 1.00),   # fast-break slam, flush on the drop
    (12, 18, "39688928",  6.17, 1.00),   # three vs San Diego
    (18, 23, "35318773",  9.60, 1.00),   # transition dime, then Malik #3 close-up
    (23, 28, "38858052",  8.40, 1.00),   # dish for the bucket
    (28, 33, "38858052",  3.00, 1.00),
    (33, 39, "47131767", 17.30, 1.00),   # build-up into the second slam
    (39, 45, "39688928", 15.30, 1.00),   # three, replay angle
    (45, 50, "35318773", 16.10, 1.00),
    (50, 56, "47131767",  1.00, 1.00),
    (56, 62, "39688928",  0.80, 1.00),
    (62, 68, "47131767", 11.80, 1.00),
    (68, 74, "35318773",  0.80, 1.00),
    (74, 80, "47131767",  4.20, 1.00),
    (80, 86, "38858052",  5.20, 1.00),
    (86, 92, "39688928", 11.30, 1.00),
    (92, 98, "47131767", 18.90, 1.00),   # second slam again
    (98, 103, "47131767", 6.80, 1.00),   # closing slam
]


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


def extract():
    for i, (b0, b1, cid, src, speed) in enumerate(CUTS):
        need = (b1 - b0) * P * speed + 0.25
        fdir = f"build/mmw/{i:02d}"
        os.makedirs(fdir, exist_ok=True)
        for f in os.listdir(fdir):
            os.remove(f"{fdir}/{f}")
        subprocess.run([FFMPEG, "-y", "-ss", f"{src:.3f}", "-i", f"build/clips/{cid}.mp4",
                        "-t", f"{need:.3f}", "-vf", "fps=30", "-q:v", "2",
                        f"{fdir}/%04d.jpg"], check=True, capture_output=True)
        print(f"seg {i:02d} {cid} b{b0}-{b1} src {src:.2f} x{speed} "
              f"{len(os.listdir(fdir))}f")


_cache = {}


def load(i, idx):
    key = (i, idx)
    if key not in _cache:
        if len(_cache) > 6:
            _cache.clear()
        _cache[key] = np.asarray(
            Image.open(f"build/mmw/{i:02d}/{idx:04d}.jpg").convert("RGB")).astype(np.float32)
    return _cache[key]


def seg_at(t):
    b = t / P
    for i, (b0, b1, cid, src, speed) in enumerate(CUTS):
        if b0 <= b < b1:
            return i, b0, speed, b1
    return None


def footage(t):
    i, b0, speed, _ = seg_at(t)
    n = len(os.listdir(f"build/mmw/{i:02d}"))
    local = t - b0 * P
    pos = local * speed * FPS
    a = max(1, min(n, int(pos) + 1))
    frac = pos - int(pos)
    arr = load(i, a)
    if speed < 1.0 and frac > 0.02:
        b = max(1, min(n, a + 1))
        if b != a:
            fb = load(i, b)
            if fb.shape == arr.shape:
                arr = arr * (1 - frac) + fb * frac
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if img.size != (W, H):
        img = img.resize((W, H), Image.LANCZOS)
    return np.asarray(img).astype(np.float32)


def grade(arr):
    luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2])[..., None]
    out = luma * 0.16 + arr * 0.84
    out = (out - 14) * 1.13
    out[..., 0] *= 1.04
    out[..., 2] *= 0.98
    return np.clip(out, 0, 255)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def center(d, s, fnt, cy, fill=WHITE, alpha=255, track=0, shadow=(0, 0, 0)):
    if track:
        ws = [fnt.getbbox(c)[2] - fnt.getbbox(c)[0] for c in s]
        total = sum(ws) + track * (len(s) - 1)
        x = W // 2 - total // 2
        box = fnt.getbbox(s)
        y = cy - (box[3] - box[1]) // 2 - box[1]
        for c, cw in zip(s, ws):
            if shadow:
                d.text((x + 4, y + 4), c, font=fnt, fill=(*shadow, alpha))
            d.text((x, y), c, font=fnt, fill=(*fill, alpha))
            x += cw + track
        return
    box = fnt.getbbox(s)
    x = W // 2 - (box[2] - box[0]) // 2
    y = cy - (box[3] - box[1]) // 2 - box[1]
    if shadow:
        d.text((x + 4, y + 4), s, font=fnt, fill=(*shadow, alpha))
    d.text((x, y), s, font=fnt, fill=(*fill, alpha))


def intro(t):
    b = t / P
    arr = np.full((H, W, 3), 8.0, np.float32)
    yy = np.arange(H)[:, None, None]
    arr += np.sin(yy * 0.035 + t * 5) * 3.0
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    if b >= 0.35:
        a = int(255 * ease((b - 0.35) / 1.0))
        center(d, "MALIK MESSINA-MOORE", font(ANTON, 150), H // 2 - 120, WHITE, a)
    if b >= 2.1:
        a = int(255 * ease((b - 2.1) / 0.55))
        sc = 1.0 + 0.45 * (1 - ease((b - 2.1) / 0.55))
        s = "COMMITTED"
        fnt = font(ANTON, int(110 * sc))
        box = fnt.getbbox(s)
        tw, th = box[2] - box[0], box[3] - box[1]
        d.rectangle([W // 2 - tw // 2 - 34, H // 2 + 60 - th // 2 - 26,
                     W // 2 + tw // 2 + 34, H // 2 + 60 + th // 2 + 26], fill=(*RED, a))
        center(d, s, fnt, H // 2 + 60, WHITE, a, shadow=None)
    if b >= 3.3:
        a = int(230 * ease((b - 3.3) / 0.5))
        center(d, "ILLINOIS STATE", font(OSWALD, 58, 500), H // 2 + 230,
               (198, 198, 203), a, track=14)
    return np.asarray(img).astype(np.float32)


_grain = [np.random.default_rng(s).integers(-7, 7, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.08 - 0.24 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


def render_frame(fi):
    t = fi / FPS
    arr = grade(footage(t)) if seg_at(t) else intro(t)
    arr = arr * vignette()
    g = _grain[fi % 8]
    arr = arr + np.repeat(np.repeat(g, 2, 0), 2, 1)[:H, :W]
    if t < 0.35:
        arr *= t / 0.35
    if t > DUR - 1.1:
        arr *= max(0.0, (DUR - t) / 1.1)
    return np.clip(arr, 0, 255).astype(np.uint8)


def build_audio():
    subprocess.run([FFMPEG, "-y", "-ss", f"{SONG_START:.3f}", "-i", SONG,
                    "-t", f"{DUR:.3f}", "-ac", "2", "-ar", str(SR),
                    "build/mmw_song.wav"], check=True, capture_output=True)
    with wave.open("build/mmw_song.wav") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    a = a.reshape(-1, 2).astype(np.float32) / 32768.0
    e = np.ones(len(a), np.float32)
    k = int(0.3 * SR)
    e[:k] = np.linspace(0, 1, k)
    k2 = int(1.6 * SR)
    e[-k2:] = np.linspace(1, 0, k2)
    a = np.clip(a * e[:, None] * 0.95, -0.99, 0.99)
    with wave.open("build/mmw_mix.wav", "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())
    print("wrote build/mmw_mix.wav")


def sheet():
    tiles = []
    for i, (b0, b1, cid, src, speed) in enumerate(CUTS):
        t = (b0 + b1) / 2 * P
        im = Image.fromarray(render_frame(int(t * FPS))).resize((480, 270))
        d = ImageDraw.Draw(im)
        d.text((8, 8), f"{i}:{cid} b{b0}-{b1}", fill=(255, 235, 0))
        tiles.append(im)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    s = Image.new("RGB", (480 * cols, 270 * rows), (0, 0, 0))
    for i, im in enumerate(tiles):
        s.paste(im, ((i % cols) * 480, (i // cols) * 270))
    s.save("build/mmw_sheet.jpg", quality=85)
    print("wrote build/mmw_sheet.jpg")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        extract(); return
    if len(sys.argv) > 1 and sys.argv[1] == "sheet":
        sheet(); return
    build_audio()
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "21", "-pix_fmt", "yuv420p", "build/mmw_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 200 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/mmw_silent.mp4", "-i", "build/mmw_mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest",
         "messina_moore_committed_wide.mp4"], check=True, capture_output=True)
    print("wrote messina_moore_committed_wide.mp4")


if __name__ == "__main__":
    main()

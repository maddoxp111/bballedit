"""Coen Carr edit — exact remake of the reference edit's structure.

Letterboxed 16:9 footage centered on black, dark moody grade, serif-italic
lyric captions word by word at the reference timings ("I'M CURIOUS FOR YOU
GOT MY ATTENTION", with CURIOUS typing out), slow-mo segments with frame
blending, and a TikTok-style outro card. Audio comes straight from the
reference video. Every gameplay segment is a different dunk.

Run after: carr_build.py.  Usage: python3 render_carr.py [--preview t1,t2,...]
"""
import json
import math
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
DUR = 40.70
OUTRO_T = 36.5
REF_AUDIO = "assets/audio/carr_ref_audio.m4a"

META = json.load(open("build/carr_meta.json"))

PLAYFAIR = "assets/fonts/PlayfairDisplay-Italic.ttf"
MONT = "assets/fonts/Montserrat.ttf"
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
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


# ---------------------------------------------------------------- captions
# (word, t_on, t_off);  CURIOUS types out letter by letter from 0.5 to 2.0
CAPTIONS = [
    ("I'M", 0.0, 0.45),
    ("CURIOUS", 0.5, 2.15),
    ("FOR", 2.2, 2.75),
    ("YOU", 2.8, 4.15),
    ("GOT", 4.2, 5.05),
    ("MY", 5.1, 5.75),
    ("ATTENTION", 5.8, 6.9),
]
CAP_DX = {"I'M": 60, "CURIOUS": -30, "FOR": 20, "YOU": -30, "GOT": 10,
          "MY": -10, "ATTENTION": 0}


def caption_at(t):
    for word, on, off in CAPTIONS:
        if on <= t < off:
            if word == "CURIOUS":
                n = 3 + int(max(0.0, min(1.0, (t - 0.5) / 1.5)) * 4)  # CUR..CURIOUS
                return word[:n], word
            return word, word
    return None, None


# ---------------------------------------------------------------- footage

_cache = {}


def seg_frame(seg, local_t):
    """Frame-blended slow-mo lookup."""
    fdir = f"build/carr/{seg['i']:02d}"
    pos = local_t * seg["speed"] * FPS
    i0 = int(pos)
    frac = pos - i0
    n = seg["frames"]
    a = max(1, min(n, i0 + 1))
    b = max(1, min(n, i0 + 2))

    def load(idx):
        key = (seg["i"], idx)
        if key not in _cache:
            _cache.clear() if len(_cache) > 6 else None
            _cache[key] = np.asarray(
                Image.open(f"{fdir}/{idx:04d}.jpg").convert("RGB")).astype(np.float32)
        return _cache[key]

    fa = load(a)
    if b != a and frac > 0.02:
        fb = load(b)
        if fb.shape == fa.shape:
            return fa * (1 - frac) + fb * frac
    return fa


def grade(arr):
    """Dark, desaturated, slightly warm — the reference's moody look."""
    luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2])[..., None]
    out = luma * 0.45 + arr * 0.55
    out *= 0.82
    out[..., 0] *= 1.06
    out[..., 2] *= 0.93
    out = 255.0 * (np.clip(out, 0, 255) / 255.0) ** 1.07
    return out


def scene_footage(t):
    seg = next(s for s in META if s["t0"] <= t < s["t1"])
    arr = seg_frame(seg, t - seg["t0"])
    fh = int(round(W * arr.shape[0] / arr.shape[1]))
    img = Image.fromarray(arr.astype(np.uint8)).resize((W, fh), Image.BICUBIC)
    arr = grade(np.asarray(img).astype(np.float32))
    canvas = np.zeros((H, W, 3), np.float32)
    y0 = (H - arr.shape[0]) // 2
    canvas[y0:y0 + arr.shape[0]] = arr
    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    # caption
    shown, full = caption_at(t)
    if shown:
        d = ImageDraw.Draw(img)
        size = 66 if full == "ATTENTION" else 58
        fnt = font(PLAYFAIR, size, 560)
        box = fnt.getbbox(shown)
        tw = box[2] - box[0]
        cx = W // 2 + CAP_DX.get(full, 0)
        cy = H // 2 + (40 if full != "ATTENTION" else -140)
        x, y = cx - tw // 2, cy - (box[3] - box[1]) // 2 - box[1]
        d.text((x + 3, y + 3), shown, font=fnt, fill=(10, 10, 12))
        d.text((x, y), shown, font=fnt, fill=(240, 238, 234))
    return img


# ---------------------------------------------------------------- outro

def chroma_text(d, s, fnt, cx, cy, off=3):
    box = fnt.getbbox(s)
    x = cx - (box[2] - box[0]) // 2
    y = cy - (box[3] - box[1]) // 2 - box[1]
    d.text((x - off, y - 2), s, font=fnt, fill=(37, 244, 238))
    d.text((x + off, y + 2), s, font=fnt, fill=(254, 44, 85))
    d.text((x, y), s, font=fnt, fill=(255, 255, 255))


def scene_outro(t):
    img = Image.new("RGB", (W, H), (16, 16, 30))
    d = ImageDraw.Draw(img)
    lt = t - OUTRO_T
    a = min(1.0, lt / 0.4)
    cy = H // 2 - 160
    note = font(DEJAVU, int(150 * (0.7 + 0.3 * a)))
    chroma_text(d, "♪", note, W // 2, cy - 130)
    chroma_text(d, "TikTok", font(MONT, 110, 700), W // 2, cy + 40)
    if lt > 1.0:
        bw, bh = 620, 92
        bx, by = W // 2 - bw // 2, cy + 180
        d.rounded_rectangle([bx - 5, by - 3, bx + bw + 1, by + bh + 3],
                            radius=18, fill=(37, 244, 238))
        d.rounded_rectangle([bx + 1, by + 3, bx + bw + 7, by + bh + 7],
                            radius=18, fill=(254, 44, 85))
        d.rounded_rectangle([bx - 2, by, bx + bw + 4, by + bh + 4],
                            radius=18, fill=(22, 22, 38), outline=(255, 255, 255), width=3)
        if lt > 1.5:
            # magnifier
            mx, my = bx + 52, by + bh // 2 + 2
            d.ellipse([mx - 16, my - 18, mx + 8, my + 6], outline=(255, 255, 255), width=4)
            d.line([mx + 6, my + 4, mx + 18, my + 16], fill=(255, 255, 255), width=4)
            f = font(MONT, 40, 500)
            d.text((bx + 110, by + bh // 2 - 22), "@bballedit", font=f, fill=(235, 235, 240))
            nf = font(DEJAVU, 44)
            d.text((bx + bw - 64, by + bh // 2 - 26), "♪", font=nf, fill=(255, 255, 255))
    return img


# ---------------------------------------------------------------- post

_grain = [np.random.default_rng(s).integers(-6, 6, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.06 - 0.22 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


def render_frame(fi):
    t = fi / FPS
    img = scene_outro(t) if t >= OUTRO_T else scene_footage(t)
    arr = np.asarray(img).astype(np.float32)
    if t < OUTRO_T:
        g = _grain[fi % 8]
        g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:H, :W]
        arr = (arr + g) * vignette()
    if t > DUR - 0.5:
        arr *= max(0.0, (DUR - t) / 0.5)
    return np.clip(arr, 0, 255).astype(np.uint8)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render_frame(int(float(ts) * FPS))).save(f"build/pc_{ts}.png")
            print(f"build/pc_{ts}.png")
        return
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "23", "-pix_fmt", "yuv420p", "build/carr_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/carr_silent.mp4", "-i", REF_AUDIO,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", "coen_carr_edit.mp4"],
        check=True, capture_output=True)
    print("wrote coen_carr_edit.mp4")


if __name__ == "__main__":
    main()

"""Illinois State — "Still Here", a storytelling edit (1080x1920, 30fps, 88.5s).

Arc: Coach Pedon's "fight together" speech (subtitled, desaturated) -> title
card -> the real broadcast of Kinziger's NIT game-winner -> locker room
"WE ARE STILL HERE" eruption -> the song drops into a ball-tracked highlight
run -> slow-mo eruption under closing cards: "unfinished business."

Run after: make_audio_story.py (and the v3 assets: build/frames + tracks.json).
Usage: python3 render_story.py [--preview t1,t2,...]
"""
import json
import math
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, DUR = 1080, 1920, 30, 88.5

SEG = json.load(open("build/segments.json"))
TRK = json.load(open("build/tracks.json"))
A = json.load(open("build/analysis2.json"))
P = A["period"]

PLAYFAIR = "assets/fonts/PlayfairDisplay-Italic.ttf"
MONT = "assets/fonts/Montserrat.ttf"
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


# ---------------------------------------------------------------- timeline

FT = "build/tt/7635009865773092110.mp4"
LOCKER = "build/tt/7621387281575775519.mp4"
DROP_T = 46.0
CARD1_T, ACT2_T, ACT3_T, ACT5_T = 18.0, 19.9, 29.9, 72.0

HIGHLIGHTS = ["47041854", "48001037", "47383232", "47614227", "48282097",
              "47474610", "48037850", "48244171", "48282177", "48382384"]
SLOT = 4 * P  # 4 beats per highlight

SUBS = [
    (0.1, 2.6, "you gotta fight. you gotta fight together."),
    (2.6, 4.1, "you gotta fight for what you believe in."),
    (4.1, 5.3, "you gotta fight for who you are."),
    (5.3, 7.9, "it's what you gotta do, man."),
    (7.92, 11.3, "we'll always be there for each other —"),
    (11.3, 14.0, "in your greatest moment, your darkest moment,"),
    (14.0, 16.5, "and everything in between."),
    (16.5, 18.0, "for real. be there for your teammates."),
    (29.9, 31.9, "all i know is this, fellas."),
    (31.9, 34.9, "today is march 26th."),
    (34.9, 37.6, "there's four words i've been dying to say."),
    (37.6, 40.5, "dying to say."),
    (40.5, 44.5, "WE ARE STILL HERE."),
    (79.6, 83.4, "we'll always be there for each other."),
]
RUN_CAPS = [
    (46.6, 49.2, "they could have left."),
    (56.9, 59.5, "they ran it back."),
]

# ---------------------------------------------------------------- sources

_tt_cache = {}


def tt_frame(path, src_t, crop=None):
    """Frame from a TikTok video at src_t, optionally (top_frac, h_frac) crop."""
    key = (path, round(src_t * FPS))
    if key not in _tt_cache:
        if len(_tt_cache) > 4:
            _tt_cache.clear()
        r = subprocess.run([FFMPEG, "-ss", f"{src_t:.3f}", "-i", path, "-frames:v", "1",
                            "-f", "image2pipe", "-vcodec", "png", "-"],
                           capture_output=True)
        import io
        _tt_cache[key] = Image.open(io.BytesIO(r.stdout)).convert("RGB")
    img = _tt_cache[key]
    sw, sh = img.size
    if crop:
        top = int(crop[0] * sh)
        ch = int(crop[1] * sh)
        cw = int(ch * 9 / 16)
        cx = sw // 2
        img = img.crop((cx - cw // 2, top, cx - cw // 2 + cw, top + ch))
    return np.asarray(img.resize((W, H), Image.BICUBIC)).astype(np.float32)


_es_cache = {"key": None, "img": None}


def espn_frame(cid, local_t, punch_t):
    """Full-screen ball-tracked crop of an extracted ESPN segment (v3 style)."""
    n = SEG[cid]["frames"]
    idx = max(1, min(n, int(local_t * FPS) + 1))
    key = (cid, idx)
    if _es_cache["key"] != key:
        _es_cache["img"] = Image.open(f"build/frames/{cid}/{idx:04d}.jpg").convert("RGB")
        _es_cache["key"] = key
    src = _es_cache["img"]
    sw, sh = src.size
    drift = 1.0 + 0.05 * min(1.0, local_t / 2.6)
    punch = 1.0 + 0.04 * math.exp(-max(0.0, punch_t) / 0.12)
    ch = int(sh * 0.78 / (drift * punch))
    cw = int(ch * 9 / 16)
    xs = TRK[cid]
    x = xs[min(idx - 1, len(xs) - 1)]
    cx = max(cw // 2, min(sw - cw // 2, int(x * sw)))
    top = int(sh * 0.035)
    crop = src.crop((cx - cw // 2, top, cx - cw // 2 + cw, top + ch))
    return np.asarray(crop.resize((W, H), Image.BICUBIC)).astype(np.float32)


# ---------------------------------------------------------------- grading

def grade(arr, sat, gain, warm=0.0, gamma=1.05):
    luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2])[..., None]
    out = luma * (1 - sat) + arr * sat
    out *= gain
    if warm:
        out[..., 0] *= 1 + 0.06 * warm
        out[..., 2] *= 1 - 0.07 * warm
    return 255.0 * (np.clip(out, 0, 255) / 255.0) ** gamma


# ---------------------------------------------------------------- text

def draw_sub(img, s, y_frac=0.74, size=44, alpha=255, fnt_path=PLAYFAIR):
    d = ImageDraw.Draw(img, "RGBA")
    size_ = size
    fnt = font(fnt_path, size_, 560)
    while fnt.getbbox(s)[2] - fnt.getbbox(s)[0] > 960 and size_ > 24:
        size_ -= 3
        fnt = font(fnt_path, size_, 560)
    box = fnt.getbbox(s)
    x = W // 2 - (box[2] - box[0]) // 2
    y = int(H * y_frac)
    d.text((x + 2, y + 2), s, font=fnt, fill=(0, 0, 0, alpha))
    d.text((x, y), s, font=fnt, fill=(242, 240, 236, alpha))


def card(lines, t_rel, spacing=110, size=54):
    img = Image.new("RGB", (W, H), (6, 6, 8))
    d = ImageDraw.Draw(img, "RGBA")
    y0 = H // 2 - spacing * (len(lines) - 1) // 2
    for i, s in enumerate(lines):
        a = max(0.0, min(1.0, (t_rel - 0.25 * i) / 0.5))
        if a <= 0:
            continue
        fnt = font(PLAYFAIR, size, 560)
        while fnt.getbbox(s)[2] - fnt.getbbox(s)[0] > 940:
            size -= 3
            fnt = font(PLAYFAIR, size, 560)
        box = fnt.getbbox(s)
        d.text((W // 2 - (box[2] - box[0]) // 2, y0 + i * spacing - (box[3] - box[1]) // 2),
               s, font=fnt, fill=(238, 236, 232, int(255 * a)))
    return np.asarray(img).astype(np.float32)


# ---------------------------------------------------------------- scenes

def scene(t):
    if t < CARD1_T:                                   # act 1: the speech
        src = t if t < 7.92 else 26.72 + (t - 7.92)
        arr = tt_frame(FT, src, crop=(0.01, 0.66))
        return grade(arr, 0.3, 0.8, warm=0.3)
    if t < ACT2_T:                                    # title card
        return card(["march 22, 2026.", "nit second round — tied at 75.",
                     "1.7 seconds left."], t - CARD1_T)
    if t < ACT3_T:                                    # act 2: the shot (broadcast)
        arr = espn_frame("48282239", t - ACT2_T, t - ACT2_T)
        g = grade(arr, 0.85, 0.92)
        if 0 <= t - (ACT2_T + 5.9) < 0.1:             # single flash on the splash
            g = g + 70
        return g
    if t < DROP_T:                                    # act 3: locker room
        arr = tt_frame(LOCKER, 16.0 + (t - ACT3_T))
        return grade(arr, 0.55, 0.85, warm=0.35)
    if t < ACT5_T:                                    # act 4: the run
        k = min(int((t - DROP_T) / SLOT), len(HIGHLIGHTS) - 1)
        cid = HIGHLIGHTS[k]
        local = t - (DROP_T + k * SLOT)
        arr = espn_frame(cid, local, local)
        g = grade(arr, 1.0, 0.95, gamma=1.03)
        if 0 <= t - DROP_T < 0.1:
            g = g + 70
        return g
    # act 5: slow-mo eruption + cards
    lt = t - ACT5_T
    if lt < 13.0:
        arr = tt_frame(LOCKER, 32.5 + lt * 0.45)
        g = grade(arr, 0.4, 0.42, warm=0.4)
    else:
        g = np.full((H, W, 3), 6.0, np.float32)
    return g


_grain = [np.random.default_rng(s).integers(-7, 7, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.07 - 0.24 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


def render_frame(fi):
    t = fi / FPS
    arr = scene(t)
    g = _grain[fi % 8]
    g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:H, :W]
    arr = (arr + g) * vignette()
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    for t0, t1, s in SUBS:
        if t0 <= t < t1:
            a = int(255 * min(1.0, (t - t0) / 0.25, max(0.0, (t1 - t) / 0.25)))
            big = s.isupper()
            draw_sub(img, s, size=58 if big else 44, alpha=a)
    for t0, t1, s in RUN_CAPS:
        if t0 <= t < t1:
            a = int(235 * min(1.0, (t - t0) / 0.3, max(0.0, (t1 - t) / 0.3)))
            draw_sub(img, s, y_frac=0.5, size=48, alpha=a, fnt_path=MONT)
    # closing cards over the dimmed slow-mo
    if ACT5_T + 2.5 <= t < ACT5_T + 7.5:
        a = int(255 * min(1.0, (t - ACT5_T - 2.5) / 0.6, max(0.0, (ACT5_T + 7.5 - t) / 0.6)))
        draw_sub(img, "unfinished business.", y_frac=0.47, size=72, alpha=a)
    if ACT5_T + 8.5 <= t < DUR - 1.5:
        a = int(255 * min(1.0, (t - ACT5_T - 8.5) / 0.6))
        draw_sub(img, "illinois state basketball", y_frac=0.45, size=58, alpha=a)
        draw_sub(img, "2026 — 27", y_frac=0.52, size=44, alpha=a)
    arr = np.asarray(img).astype(np.float32)
    if t > DUR - 1.5:
        arr *= max(0.0, (DUR - t) / 1.5)
    return np.clip(arr, 0, 255).astype(np.uint8)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render_frame(int(float(ts) * FPS))).save(f"build/ps_{ts}.png")
            print(f"build/ps_{ts}.png")
        return
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "22", "-pix_fmt", "yuv420p", "build/story_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/story_silent.mp4", "-i", "build/story_mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", "still_here_edit.mp4"],
        check=True, capture_output=True)
    print("wrote still_here_edit.mp4")


if __name__ == "__main__":
    main()

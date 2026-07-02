"""Illinois State "IS BACK" edit v3 — reference style: full-screen footage.

Full 9:16 crop of the broadcast frame, virtual camera pans with the motion
track so the action stays centered, punch-in settle on cuts + slow drift zoom
(no beat pulsing), dip-to-black between player blocks, and almost no text:
one cold-open line, a tiny lowercase name per player, one closer.

Run after: analyze_audio2.py, build_segments.py, track_motion.py, make_audio.py.
Usage: python3 render_edit3.py [--preview t1,t2,...]
"""
import json
import math
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, DUR = 1080, 1920, 30, 60.0

A = json.load(open("build/analysis2.json"))
SEG = json.load(open("build/segments.json"))
TRK = json.load(open("build/tracks.json"))
P, OFF = A["period"], A["beat_offset"]

WHITE = (245, 245, 245)

MONT = "assets/fonts/Montserrat.ttf"
_fonts = {}


def font(size, weight=600):
    key = (size, weight)
    if key not in _fonts:
        f = ImageFont.truetype(MONT, size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        _fonts[key] = f
    return _fonts[key]


def bt(b):
    return OFF + b * P


def beat_at(t):
    return (t - OFF) / P


# ---------------------------------------------------------------- timeline

DROP = 9
PLAYLIST = [  # (start_beat, clip id)
    (9, "47474610"),
    (13, "47041854"), (17, "48001037"), (21, "47614013"), (25, "47195895"), (29, "47042256"),
    (33, "47383232"), (37, "47614227"), (41, "48244171"), (45, "47762098"), (49, "48282177"),
    (53, "48282097"), (57, "48037850"), (61, "47613943"), (65, "48382384"),
    (69, "48038210"), (73, "47716449"),
    (77, "48282239"),
]
BLOCK_STARTS = [13, 33, 53, 69, 77]     # dip-to-black boundaries
NAME_TAGS = {13: "mason klabo", 33: "chase walker", 53: "johnny kinziger"}
FINALE_B = 77
MAKE_B = 86.3                            # game-winner splashes ~beat 86.3


def clip_at(b):
    cur = PLAYLIST[0]
    for item in PLAYLIST:
        if b >= item[0]:
            cur = item
        else:
            break
    return cur


_cache = {"key": None, "img": None}


def clip_frame(cid, local_t):
    n = SEG[cid]["frames"]
    idx = max(1, min(n, int(local_t * FPS) + 1))
    key = (cid, idx)
    if _cache["key"] != key:
        _cache["img"] = Image.open(f"build/frames/{cid}/{idx:04d}.jpg").convert("RGB")
        _cache["key"] = key
    return _cache["img"], idx - 1


def footage_full(t, b):
    """Full-screen 9:16 crop, panned to the motion track, punch-in on cuts."""
    b0, cid = clip_at(b)
    local_t = t - bt(b0)
    src, fidx = clip_frame(cid, local_t)
    sw, sh = src.size
    seg_len = SEG[cid]["frames"] / FPS
    drift = 1.0 + 0.05 * min(1.0, local_t / max(seg_len, 0.1))
    punch = 1.0 + 0.04 * math.exp(-max(0.0, local_t) / 0.12)
    zoom = drift * punch
    # 80% height, anchored near the top: keeps the broadcast scorebug
    # (bottom ~15%) out of frame at every zoom level
    ch = int(sh * 0.78 / zoom)
    cw = int(ch * 9 / 16)
    top = int(sh * 0.035)
    xs = TRK[cid]
    x = xs[min(fidx, len(xs) - 1)]
    cx = int(x * sw)
    cx = max(cw // 2, min(sw - cw // 2, cx))
    crop = src.crop((cx - cw // 2, top, cx - cw // 2 + cw, top + ch))
    return crop.resize((W, H), Image.BICUBIC)


# ---------------------------------------------------------------- text

def draw_center(d, s, fnt, cy, fill=WHITE, tracking=0, alpha=255):
    if tracking:
        widths = [fnt.getbbox(ch)[2] - fnt.getbbox(ch)[0] for ch in s]
        total = sum(widths) + tracking * (len(s) - 1)
        x = W // 2 - total // 2
        box = fnt.getbbox(s)
        y = cy - (box[3] - box[1]) // 2 - box[1]
        for ch, cw_ in zip(s, widths):
            d.text((x + 2, y + 2), ch, font=fnt, fill=(0, 0, 0, alpha // 2))
            d.text((x, y), ch, font=fnt, fill=(*fill, alpha))
            x += cw_ + tracking
    else:
        box = fnt.getbbox(s)
        x = W // 2 - (box[2] - box[0]) // 2
        y = cy - (box[3] - box[1]) // 2 - box[1]
        d.text((x + 2, y + 2), s, font=fnt, fill=(0, 0, 0, alpha // 2))
        d.text((x, y), s, font=fnt, fill=(*fill, alpha))


def fade(x):
    return max(0.0, min(1.0, x))


def scene_intro(t, b):
    img = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(img, "RGBA")
    if b < 4:
        a = fade(b / 0.8) * (1.0 if b < 3.4 else fade((4 - b) / 0.6))
        draw_center(d, "illinois state basketball", font(46), H // 2 - 20,
                    tracking=6, alpha=int(255 * a))
    else:
        a = fade((b - 4) / 0.8)
        draw_center(d, "is back.", font(78), H // 2 - 30, tracking=4, alpha=int(255 * a))
        draw_center(d, "2026 — 27", font(34, 500), H // 2 + 90, (150, 150, 154),
                    tracking=10, alpha=int(220 * a))
    return img


def scene_footage(t, b):
    img = footage_full(t, b)
    d = ImageDraw.Draw(img, "RGBA")
    for nb, name in NAME_TAGS.items():
        lb = b - nb
        if 0 <= lb < 4:
            a = fade(lb / 0.7) * fade((4 - lb) / 0.7)
            draw_center(d, name, font(44), H - 260, tracking=8, alpha=int(235 * a))
    if b >= MAKE_B + 0.6:
        a = fade((b - MAKE_B - 0.6) / 0.8)
        draw_center(d, "illinois state is back.", font(52), H // 2,
                    tracking=6, alpha=int(245 * a))
    return img


# ---------------------------------------------------------------- post

_grain = [np.random.default_rng(s).integers(-8, 8, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.08 - 0.26 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


def post(img, t, b, fi):
    arr = np.asarray(img).astype(np.float32)
    # dip-to-black at block boundaries
    for bb in BLOCK_STARTS:
        dt = abs(t - bt(bb))
        if dt < 0.09:
            arr *= dt / 0.09
    # single white flash at the drop and the game-winner
    for hb in (DROP, MAKE_B):
        if 0 <= b - hb < 0.10:
            arr = arr + 70
    g = _grain[fi % 8]
    g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:H, :W]
    arr = (arr + g) * vignette()
    if t > DUR - 2.2:
        arr *= max(0.0, (DUR - t) / 2.2)
    return np.clip(arr, 0, 255).astype(np.uint8)


def render_frame(fi):
    t = fi / FPS
    b = beat_at(t)
    img = scene_intro(t, b) if b < DROP else scene_footage(t, b)
    return post(img, t, b, fi)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render_frame(int(float(ts) * FPS))).save(f"build/p3_{ts}.png")
            print(f"build/p3_{ts}.png")
        return
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "23", "-pix_fmt", "yuv420p", "build/video3_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/video3_silent.mp4", "-i", "build/mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", "illinois_state_is_back.mp4"],
        check=True, capture_output=True)
    print("wrote illinois_state_is_back.mp4")


if __name__ == "__main__":
    main()

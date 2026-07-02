"""Illinois State Basketball "IS BACK" edit — 2026-27 roster hype video.

Renders a 60s vertical (1080x1920, 30fps) typography edit beat-synced to the
attached song, then muxes the chosen 60s audio window with a fade-out.

Usage: python3 render_edit.py [--preview t1,t2,...]   (preview dumps PNGs instead)
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import os

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"
SONG = "assets/audio/40_Nights.mp3"
if not os.path.exists(SONG):
    sys.exit("missing assets/audio/40_Nights.mp3")
W, H, FPS, DUR = 1080, 1920, 30, 60.0

A = json.load(open("build/analysis.json"))
PERIOD = A["period"]
OFFSET = A["beat_offset"]
ENERGY = A["energy"]

RED = (206, 17, 38)
DARKRED = (122, 8, 20)
WHITE = (245, 245, 245)
BLACK = (10, 10, 12)

ANTON = "assets/fonts/Anton-Regular.ttf"
OSWALD = "assets/fonts/Oswald.ttf"
_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def beat_at(t):
    """Continuous beat position at time t (window-local seconds)."""
    return (t - OFFSET) / PERIOD


def pulse(t, decay=6.0):
    """1.0 right on a beat, exponential decay after."""
    b = beat_at(t)
    frac = b - math.floor(b)
    return math.exp(-decay * frac * PERIOD) if b >= 0 else 0.0


def energy(t):
    i = min(int(t * 2), len(ENERGY) - 1)
    return ENERGY[max(0, i)]


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- drawing utils

def text_size(fnt, s):
    box = fnt.getbbox(s)
    return box[2] - box[0], box[3] - box[1], box


def draw_center(draw, s, fnt, cy, fill, cx=W // 2, tracking=0, shadow=None):
    """Draw string centered at (cx, cy) measuring actual glyph bbox."""
    w, h, box = text_size(fnt, s)
    if tracking:
        w += tracking * (len(s) - 1)
    x, y = cx - w // 2, cy - h // 2 - box[1]
    if shadow:
        off = max(2, fnt.size // 28)
        _draw_tracked(draw, s, fnt, x + off, y + off, shadow, tracking)
    _draw_tracked(draw, s, fnt, x, y, fill, tracking)


def _draw_tracked(draw, s, fnt, x, y, fill, tracking):
    if not tracking:
        draw.text((x, y), s, font=fnt, fill=fill)
        return
    for ch in s:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getbbox(ch)[2] - fnt.getbbox(ch)[0] + tracking


def fit_font(path, s, max_w, start_size):
    size = start_size
    while size > 20:
        f = font(path, size)
        if text_size(f, s)[0] <= max_w:
            return f
        size -= 8
    return font(path, size)


def base_bg(t, tone="black"):
    """Dark bg with slow-moving diagonal red streaks."""
    img = Image.new("RGB", (W, H), BLACK if tone == "black" else tone)
    d = ImageDraw.Draw(img, "RGBA")
    ph = t * 90
    for i in range(6):
        x0 = (i * 340 + ph) % (W + 900) - 450
        alpha = 14 + int(10 * energy(t))
        d.polygon([(x0, H), (x0 + 130, H), (x0 + 130 + 520, 0), (x0 + 520, 0)],
                  fill=(RED[0], RED[1], RED[2], alpha))
    return img


def stamp_watermark(img, s, size, cy, alpha, cx=W // 2, dx=0):
    """Alpha-composite a giant faint glyph onto img (returns new RGB image)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fnt = font(ANTON, size)
    w, h, box = text_size(fnt, s)
    ImageDraw.Draw(layer).text((cx - w // 2 + dx, cy - h // 2 - box[1]), s,
                               font=fnt, fill=(255, 255, 255, alpha))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def chip(d, s, cx, cy, fnt, fg=WHITE, bg=RED):
    w, h, _ = text_size(fnt, s)
    pad_x, pad_y = 28, 16
    d.rounded_rectangle([cx - w // 2 - pad_x, cy - h // 2 - pad_y,
                         cx + w // 2 + pad_x, cy + h // 2 + pad_y],
                        radius=8, fill=bg)
    draw_center(d, s, fnt, cy, fg)


# ---------------------------------------------------------------- content data

BIG3 = [
    dict(num="3", first="MASON", last="KLABO", pos="GUARD", cls="SOPHOMORE",
         home="FARGO, N.D.", tag="BACK FOR MORE"),
    dict(num="35", first="CHASE", last="WALKER", pos="FORWARD", cls="SENIOR",
         home="COLUMBUS, OHIO", tag="STILL HERE"),
    dict(num="11", first="JOHNNY", last="KINZIGER", pos="GUARD", cls="SENIOR",
         home="DE PERE, WIS.", tag="LIGHTS OUT"),
]

FLOCK = [  # rest of the official 2026-27 roster (goredbirds.com)
    ("0", "NOAH", "CLEVELAND", "F"),
    ("1", "DENG", "GARANG", "G"),
    ("2", "ISAAC", "ERICKSEN", "G/F"),
    ("4", "LEYTON", "WOLF", "F"),
    ("5", "DEMARION", "BURCH", "G"),
    ("12", "MATTHEW", "SZAFONI", "F"),
    ("13", "TY", "BLAKE", "G"),
    ("15", "NICK", "ALLEN", "F"),
    ("24", "ZAXTON", "KING", "G"),
    ("25", "JORDAN", "WILLIAMS", "G"),
    ("33", "LOUIE", "SEMONA", "F"),
]

INTRO_LINES = ["BLOOMINGTON-NORMAL", "THEY COUNTED US OUT",
               "THE NEST WENT QUIET", "NOT ANYMORE."]


# ---------------------------------------------------------------- scenes
# All scenes get (t, b) with t = window seconds, b = continuous beat position.

def scene_intro(t, b):
    img = base_bg(t)
    d = ImageDraw.Draw(img)
    idx = max(0, min(int(b // 2), 3))
    line = INTRO_LINES[idx]
    appear = (b - idx * 2) / 0.4  # snap in over 0.4 beats
    col = RED if idx == 3 else WHITE
    f = fit_font(ANTON, line, 940, 130)
    if appear > 0:
        a = ease_out(appear)
        fnt = font(ANTON, max(24, int(f.size * (1.6 - 0.6 * a))))
        draw_center(d, line, fnt, H // 2, col, shadow=(0, 0, 0))
    # previous lines linger faint above
    fy = H // 2 - 260
    for j in range(idx):
        draw_center(d, INTRO_LINES[j], font(ANTON, 54), fy - (idx - 1 - j) * 90, (70, 70, 74))
    draw_center(d, "2026 — 27", font(OSWALD, 44), H - 180, (120, 120, 125), tracking=14)
    return img


def scene_title(t, b):
    img = base_bg(t)
    d = ImageDraw.Draw(img)
    words = [("ILLINOIS", 8), ("STATE", 10), ("BASKETBALL", 12)]
    ys = [H // 2 - 330, H // 2 - 90, H // 2 + 130]
    for (wd, hit), y in zip(words, ys):
        if b >= hit:
            a = ease_out((b - hit) / 0.5)
            f = fit_font(ANTON, wd, 960, 200 if wd != "BASKETBALL" else 170)
            fnt = font(ANTON, max(24, int(f.size * (0.4 + 0.6 * a))))
            draw_center(d, wd, fnt, y, WHITE, shadow=(0, 0, 0))
    if b >= 14:
        a = ease_out((b - 14) / 0.5)
        base = fit_font(ANTON, "IS BACK.", 980, 260).size
        fnt = font(ANTON, max(24, int(base * (1.8 - 0.8 * a))))
        # red slab behind
        d.rectangle([0, H // 2 + 300, W, H // 2 + 640], fill=(*RED, ))
        draw_center(d, "IS BACK.", fnt, H // 2 + 470, WHITE, shadow=(60, 4, 10))
    return img


def scene_isback_hold(t, b):
    img = base_bg(t, tone=(16, 3, 6))
    d = ImageDraw.Draw(img)
    p = pulse(t)
    d.rectangle([0, 0, W, H], fill=None)
    draw_center(d, "ILLINOIS STATE", font(ANTON, 96), H // 2 - 420, WHITE, tracking=4)
    draw_center(d, "BASKETBALL", font(ANTON, 96), H // 2 - 280, WHITE, tracking=10)
    fnt = font(ANTON, int(330 + 26 * p))
    draw_center(d, "IS", fnt, H // 2 - 20, RED, shadow=(0, 0, 0))
    draw_center(d, "BACK", fnt, H // 2 + 330, RED, shadow=(0, 0, 0))
    draw_center(d, "THE NEST NEVER LEFT", font(OSWALD, 46), H - 200, (150, 150, 155), tracking=10)
    return img


def scene_player(t, b, p0, pl):
    """8-beat spotlight card for a returning starter."""
    lb = b - p0  # local beats 0..8
    img = base_bg(t)
    # giant watermark number sliding subtly
    img = stamp_watermark(img, pl["num"], 1150, H // 2 - 160, 18, dx=-int(lb * 6))
    d = ImageDraw.Draw(img, "RGBA")
    # RETURNING chip slams first
    if lb >= 0:
        chip(d, "R E T U R N I N G", W // 2, 300, font(OSWALD, 46))
    # first name on beat 1
    if lb >= 1:
        a = ease_out((lb - 1) / 0.5)
        draw_center(d, pl["first"], font(ANTON, max(24, int(120 * (0.5 + 0.5 * a)))),
                    H // 2 - 250, WHITE)
    # last name slam on beat 2
    if lb >= 2:
        a = ease_out((lb - 2) / 0.5)
        f = fit_font(ANTON, pl["last"], 980, 250)
        draw_center(d, pl["last"], font(ANTON, max(24, int(f.size * (1.8 - 0.8 * a)))),
                    H // 2 - 40, RED, shadow=(0, 0, 0))
    # number + info on beat 3
    if lb >= 3:
        draw_center(d, f'#{pl["num"]}', font(ANTON, 170), H // 2 + 220, WHITE)
        draw_center(d, f'{pl["pos"]}  •  {pl["cls"]}', font(OSWALD, 52), H // 2 + 400,
                    (200, 200, 205), tracking=6)
        draw_center(d, pl["home"], font(OSWALD, 44), H // 2 + 480, (140, 140, 146), tracking=8)
    # tagline slab on beat 5
    if lb >= 5:
        a = ease_out((lb - 5) / 0.5)
        y = H - 340
        d.rectangle([0, y - 90, W, y + 90], fill=(*RED, int(235 * a)))
        draw_center(d, pl["tag"], font(ANTON, 110), y, WHITE)
    return img


def scene_flock_intro(t, b):
    img = Image.new("RGB", (W, H), RED)
    d = ImageDraw.Draw(img)
    draw_center(d, "AND THE NEST", font(ANTON, 150), H // 2 - 170, WHITE, shadow=DARKRED)
    draw_center(d, "IS LOADED", font(ANTON, 210), H // 2 + 90, BLACK, shadow=DARKRED)
    return img


def scene_flock(t, b, f0):
    lb = b - f0
    i = min(int(lb // 2), len(FLOCK) - 1)
    num, first, last, pos = FLOCK[i]
    dark = i % 2 == 0
    img = base_bg(t) if dark else Image.new("RGB", (W, H), RED)
    img = stamp_watermark(img, num, 900, H // 2 - 420, 20)
    d = ImageDraw.Draw(img, "RGBA")
    fg = RED if dark else WHITE
    sub = WHITE if dark else (255, 220, 224)
    a = ease_out((lb - i * 2) / 0.45)
    draw_center(d, first, font(ANTON, 92), H // 2 - 210, sub)
    f = fit_font(ANTON, last, 980, 230)
    draw_center(d, last, font(ANTON, max(24, int(f.size * (1.5 - 0.5 * a)))),
                H // 2, fg if dark else BLACK, shadow=(0, 0, 0) if dark else DARKRED)
    draw_center(d, f"#{num}  •  {pos}", font(OSWALD, 56), H // 2 + 220, sub, tracking=6)
    draw_center(d, "2026-27 REDBIRDS", font(OSWALD, 40), H - 180,
                (130, 130, 135) if dark else (250, 200, 205), tracking=12)
    return img


def scene_coach(t, b):
    img = base_bg(t)
    d = ImageDraw.Draw(img)
    chip(d, "T H E  A R C H I T E C T", W // 2, 420, font(OSWALD, 46))
    draw_center(d, "HEAD COACH", font(OSWALD, 60), H // 2 - 260, (190, 190, 195), tracking=16)
    draw_center(d, "RYAN", font(ANTON, 190), H // 2 - 60, WHITE)
    draw_center(d, "PEDON", font(ANTON, 250), H // 2 + 190, RED, shadow=(0, 0, 0))
    draw_center(d, "SAME NEST. NEW HEIGHTS.", font(OSWALD, 46), H // 2 + 430,
                (150, 150, 155), tracking=8)
    return img


def scene_year_slam(t, b):
    img = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(img)
    if b >= 72:
        a = ease_out((b - 72) / 0.5)
        draw_center(d, "2026", font(ANTON, max(24, int(400 * (1.7 - 0.7 * a)))),
                    H // 2 - 300, WHITE, shadow=(40, 40, 44))
    if b >= 74:
        a = ease_out((b - 74) / 0.5)
        draw_center(d, "2027", font(ANTON, max(24, int(400 * (1.7 - 0.7 * a)))),
                    H // 2 + 120, RED, shadow=(0, 0, 0))
    if b >= 76:
        d.rectangle([0, H - 480, W, H - 260], fill=RED)
        draw_center(d, "REDBIRD BASKETBALL", font(ANTON, 96), H - 370, WHITE)
    return img


def scene_finale(t, b):
    img = base_bg(t, tone=(14, 2, 5))
    d = ImageDraw.Draw(img)
    p = pulse(t)
    draw_center(d, "ILLINOIS STATE", font(ANTON, int(130 + 8 * p)), H // 2 - 480, WHITE)
    draw_center(d, "BASKETBALL", font(ANTON, int(130 + 8 * p)), H // 2 - 300, WHITE)
    fnt = font(ANTON, int(380 + 24 * p))
    draw_center(d, "IS", fnt, H // 2 + 10, RED, shadow=(0, 0, 0))
    draw_center(d, "BACK.", fnt, H // 2 + 420, RED, shadow=(0, 0, 0))
    draw_center(d, "SEE YOU AT CEFCU ARENA", font(OSWALD, 50), H - 240,
                (170, 170, 175), tracking=10)
    draw_center(d, "GO BIRDS", font(OSWALD, 42), H - 160, (120, 120, 125), tracking=16)
    return img


SECTIONS = [
    (0, 8, scene_intro),
    (8, 16, scene_title),
    (16, 20, scene_isback_hold),
    (20, 28, lambda t, b: scene_player(t, b, 20, BIG3[0])),
    (28, 36, lambda t, b: scene_player(t, b, 28, BIG3[1])),
    (36, 44, lambda t, b: scene_player(t, b, 36, BIG3[2])),
    (44, 46, scene_flock_intro),
    (46, 68, lambda t, b: scene_flock(t, b, 46)),
    (68, 72, scene_coach),
    (72, 80, scene_year_slam),
    (80, 999, scene_finale),
]

# section boundaries in beats -> big hits (flash + glitch)
HITS = [8, 14, 16, 20, 22, 28, 30, 36, 38, 44, 46, 68, 72, 74, 76, 80]


# ---------------------------------------------------------------- post effects

_grain = [np.random.default_rng(s).integers(-14, 14, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]

_vig = None
def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.15 - 0.42 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


def post(img, t, b, fi):
    p = pulse(t)
    en = energy(t)
    # zoom pulse on beat
    z = 1.0 + 0.045 * p * (0.5 + 0.7 * en)
    if z > 1.001:
        nw, nh = int(W * z), int(H * z)
        img = img.resize((nw, nh), Image.BILINEAR).crop(
            ((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))
    arr = np.asarray(img).astype(np.int16)
    # beats since nearest hit
    hit_d = min((abs(b - h) for h in HITS), default=9)
    just_hit = any(0 <= b - h < 0.22 for h in HITS)
    if just_hit:
        # rgb split glitch
        sh = 6 + int(8 * en)
        arr[:, :, 0] = np.roll(arr[:, :, 0], sh, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -sh, axis=1)
        # slice displacement
        rng = np.random.default_rng(fi)
        for _ in range(4):
            y0 = int(rng.integers(0, H - 80))
            hgt = int(rng.integers(20, 80))
            arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(rng.integers(-90, 90)), axis=1)
        # white flash
        flash = any(0 <= b - h < 0.14 for h in HITS)
        if flash:
            arr = arr + 90
    # shake decays after hits
    shk = math.exp(-3.0 * max(0.0, hit_d) * PERIOD)
    if shk > 0.05:
        rng = np.random.default_rng(fi * 7)
        arr = np.roll(arr, (int(rng.integers(-1, 2) * 14 * shk),
                            int(rng.integers(-1, 2) * 14 * shk)), axis=(0, 1))
    # grain + vignette
    g = _grain[fi % 8]
    g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:H, :W]
    arr = (arr + g).astype(np.float32) * vignette()
    # end fade
    if t > DUR - 2.2:
        arr *= max(0.0, (DUR - t) / 2.2)
    return np.clip(arr, 0, 255).astype(np.uint8)


def render_frame(fi):
    t = fi / FPS
    b = beat_at(t)
    for b0, b1, fn in SECTIONS:
        if b < b1:
            img = fn(t, b)
            break
    return post(img, t, b, fi)


# ---------------------------------------------------------------- main

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            fi = int(float(ts) * FPS)
            Image.fromarray(render_frame(fi)).save(f"build/preview_{ts}.png")
            print(f"build/preview_{ts}.png")
        return

    total = int(DUR * FPS)
    vid = "build/video_silent.mp4"
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", vid],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()

    out = "illinois_state_is_back.mp4"
    subprocess.run(
        [FFMPEG, "-y", "-i", vid, "-ss", str(A["start"]), "-t", str(DUR), "-i", SONG,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-af", f"afade=t=in:st=0:d=0.5,afade=t=out:st={DUR-2.5}:d=2.5",
         "-shortest", out], check=True, capture_output=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

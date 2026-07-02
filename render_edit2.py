"""Illinois State "IS BACK" footage edit — TikTok-style, 1080x1920 @ 30fps, 60s.

Song runs from 0:00; typography cold open until the beat drop (~5.9s), then
ESPN game footage cut on the beat grid: opener slam, Klabo / Walker / Kinziger
blocks, rapid roster cards, and Kinziger's NIT game-winner as the finale.

Run after: analyze_audio2.py, build_segments.py, make_audio.py.
Usage: python3 render_edit2.py [--preview t1,t2,...]
"""
import json
import math
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, DUR = 1080, 1920, 30, 60.0

A = json.load(open("build/analysis2.json"))
SEG = json.load(open("build/segments.json"))
P, OFF = A["period"], A["beat_offset"]
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


def bt(b):
    return OFF + b * P


def beat_at(t):
    return (t - OFF) / P


def pulse(t, decay=6.0):
    b = beat_at(t)
    frac = b - math.floor(b)
    return math.exp(-decay * frac * P) if b >= 0 else 0.0


def energy(t):
    i = min(int(t * 2), len(ENERGY) - 1)
    return ENERGY[max(0, i)]


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def text_size(fnt, s):
    box = fnt.getbbox(s)
    return box[2] - box[0], box[3] - box[1], box


def draw_center(draw, s, fnt, cy, fill, cx=W // 2, tracking=0, shadow=None):
    w, h, box = text_size(fnt, s)
    if tracking:
        w += tracking * (len(s) - 1)
    x, y = cx - w // 2, cy - h // 2 - box[1]
    if shadow:
        off = max(2, fnt.size // 26)
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


def chip(d, s, cx, cy, fnt, fg=WHITE, bg=RED):
    w, h, _ = text_size(fnt, s)
    d.rounded_rectangle([cx - w // 2 - 28, cy - h // 2 - 16,
                         cx + w // 2 + 28, cy + h // 2 + 16], radius=8, fill=bg)
    draw_center(d, s, fnt, cy, fg)


# ---------------------------------------------------------------- timeline

DROP = 9
OPENER = ("47474610", 9)
BLOCKS = [
    dict(b0=13, num="3", first="MASON", last="KLABO", pos="G", cls="SO",
         clips=["47041854", "48001037", "47614013", "47195895", "47042256"]),
    dict(b0=33, num="35", first="CHASE", last="WALKER", pos="F", cls="SR",
         clips=["47383232", "47614227", "48244171", "47762098", "48282177"]),
    dict(b0=53, num="11", first="JOHNNY", last="KINZIGER", pos="G", cls="SR",
         clips=["48282097", "48037850", "47613943", "48382384"]),
]
ROSTER_B, FINALE_B = 69, 77
FINALE_CLIP = "48282239"

ROSTER_CARDS = [
    [("0", "CLEVELAND"), ("1", "GARANG"), ("2", "ERICKSEN")],
    [("4", "WOLF"), ("5", "BURCH"), ("12", "SZAFONI")],
    [("13", "BLAKE"), ("15", "ALLEN"), ("24", "KING")],
    [("25", "WILLIAMS"), ("33", "SEMONA"), ("HC", "PEDON")],
]

INTRO_LINES = ["BLOOMINGTON-NORMAL", "THEY COUNTED US OUT",
               "THE NEST WENT QUIET", "NOT ANYMORE."]

CUT_BEATS = sorted({DROP, ROSTER_B, FINALE_B, FINALE_B + 8}
                   | {b for blk in BLOCKS for b in range(blk["b0"], blk["b0"] + 4 * len(blk["clips"]), 4)}
                   | set(range(ROSTER_B, FINALE_B, 2)))

_frame_cache = {"cid": None, "idx": None, "img": None}


def clip_frame(cid, local_t):
    n = SEG[cid]["frames"]
    idx = max(1, min(n, int(local_t * FPS) + 1))
    if _frame_cache["cid"] == cid and _frame_cache["idx"] == idx:
        return _frame_cache["img"]
    img = Image.open(f"build/frames/{cid}/{idx:04d}.jpg").convert("RGB")
    _frame_cache.update(cid=cid, idx=idx, img=img)
    return img


def footage_canvas(cid, local_t, zoom=1.0):
    """Blurred-fill background + sharp 16:9 footage band, TikTok style."""
    fg = clip_frame(cid, local_t)
    fw, fh = fg.size  # 1080 x ~608
    if zoom > 1.001:
        zw, zh = int(fw * zoom), int(fh * zoom)
        fg = fg.resize((zw, zh), Image.BILINEAR).crop(
            ((zw - fw) // 2, (zh - fh) // 2, (zw - fw) // 2 + fw, (zh - fh) // 2 + fh))
    bg = fg.resize((135, 240), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
    bg = bg.resize((W, H), Image.BILINEAR)
    bg = Image.eval(bg, lambda v: int(v * 0.42))
    y0 = 820 - fh // 2
    bg.paste(fg, (0, y0))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, y0 - 8, W, y0], fill=RED)
    d.rectangle([0, y0 + fh, W, y0 + fh + 8], fill=RED)
    return bg, y0, fh


# ---------------------------------------------------------------- scenes

def base_bg(t):
    img = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(img, "RGBA")
    ph = t * 90
    for i in range(6):
        x0 = (i * 340 + ph) % (W + 900) - 450
        d.polygon([(x0, H), (x0 + 130, H), (x0 + 650, 0), (x0 + 520, 0)],
                  fill=(*RED, 14 + int(10 * energy(t))))
    return img


def scene_intro(t, b):
    img = base_bg(t)
    d = ImageDraw.Draw(img)
    idx = max(0, min(int(b // 2), 3))
    line = INTRO_LINES[idx]
    appear = (b - idx * 2) / 0.4
    col = RED if idx == 3 else WHITE
    f = fit_font(ANTON, line, 940, 130)
    if appear > 0:
        a = ease_out(appear)
        fnt = font(ANTON, max(24, int(f.size * (1.6 - 0.6 * a))))
        draw_center(d, line, fnt, H // 2, col, shadow=(0, 0, 0))
    fy = H // 2 - 260
    for j in range(idx):
        draw_center(d, INTRO_LINES[j], font(ANTON, 54), fy - (idx - 1 - j) * 90, (70, 70, 74))
    draw_center(d, "2026 — 27", font(OSWALD, 44), H - 180, (120, 120, 125), tracking=14)
    # tension: shrink-in vignette ring as riser builds
    if b > 6:
        a = (b - 6) / 3.0
        d.rectangle([0, 0, W, int(120 * a)], fill=BLACK)
        d.rectangle([0, H - int(120 * a), W, H], fill=BLACK)
    return img


def scene_opener(t, b):
    lb = b - DROP
    img, y0, fh = footage_canvas(OPENER[0], t - bt(DROP), zoom=1.0 + 0.05 * pulse(t))
    d = ImageDraw.Draw(img)
    a = ease_out(lb / 0.6)
    fnt = font(ANTON, max(24, int(170 * (1.7 - 0.7 * a))))
    draw_center(d, "ILLINOIS STATE", fnt, 300, WHITE, shadow=(0, 0, 0))
    if lb >= 1:
        a2 = ease_out((lb - 1) / 0.6)
        f2 = font(ANTON, max(24, int(230 * (1.7 - 0.7 * a2))))
        d.rectangle([0, H - 500, W, H - 190], fill=RED)
        draw_center(d, "IS BACK.", f2, H - 345, WHITE, shadow=(60, 4, 10))
    return img


def scene_block(t, b, blk):
    lb = b - blk["b0"]
    ci = min(int(lb // 4), len(blk["clips"]) - 1)
    cid = blk["clips"][ci]
    local = t - bt(blk["b0"] + ci * 4)
    img, y0, fh = footage_canvas(cid, local, zoom=1.0 + 0.05 * pulse(t) * (0.4 + 0.6 * energy(t)))
    d = ImageDraw.Draw(img, "RGBA")
    name = f'{blk["first"]} {blk["last"]}'
    if lb < 3:  # big name slam over first clip
        a = ease_out(lb / 0.7)
        chip(d, "R E T U R N I N G", W // 2, 240, font(OSWALD, 42))
        f = fit_font(ANTON, blk["last"], 980, 240)
        fnt = font(ANTON, max(24, int(f.size * (1.8 - 0.8 * a))))
        draw_center(d, blk["first"], font(ANTON, 100), 400, WHITE, shadow=(0, 0, 0))
        draw_center(d, blk["last"], fnt, 580, RED, shadow=(0, 0, 0))
    else:  # compact tag, bottom left
        tag = f'#{blk["num"]}  {name}'
        fnt = font(ANTON, 56)
        tw, th, _ = text_size(fnt, tag)
        ty = y0 + fh + 60
        d.rectangle([40, ty, 40 + tw + 48, ty + th + 36], fill=(*RED, 235))
        d.text((64, ty + 14), tag, font=fnt, fill=WHITE)
        d.text((64, ty + th + 52), f'{blk["pos"]} • {blk["cls"]} • 2026-27',
               font=font(OSWALD, 36), fill=(220, 220, 224))
    # watermark number top-right
    wm = font(ANTON, 260)
    d.text((W - text_size(wm, blk["num"])[0] - 50, 120), blk["num"],
           font=wm, fill=(255, 255, 255, 60))
    return img


def scene_roster(t, b):
    lb = b - ROSTER_B
    ci = min(int(lb // 2), 3)
    img = base_bg(t) if ci % 2 == 0 else Image.new("RGB", (W, H), RED)
    dark = ci % 2 == 0
    d = ImageDraw.Draw(img)
    draw_center(d, "THE NEST IS LOADED", font(ANTON, 84), 280,
                RED if dark else BLACK, shadow=(0, 0, 0) if dark else DARKRED)
    a = ease_out((lb - ci * 2) / 0.5)
    ys = [H // 2 - 260, H // 2 + 40, H // 2 + 340]
    for (num, last), y in zip(ROSTER_CARDS[ci], ys):
        f = fit_font(ANTON, last, 860, 170)
        fnt = font(ANTON, max(24, int(f.size * (1.4 - 0.4 * a))))
        draw_center(d, last, fnt, y, WHITE if dark else BLACK,
                    shadow=(0, 0, 0) if dark else DARKRED)
        draw_center(d, f"#{num}" if num != "HC" else "HEAD COACH",
                    font(OSWALD, 46), y + 118, RED if dark else (255, 220, 224), tracking=6)
    draw_center(d, "2026-27 REDBIRDS", font(OSWALD, 40), H - 140,
                (130, 130, 135) if dark else (250, 200, 205), tracking=12)
    return img


def scene_finale(t, b):
    lb = b - FINALE_B
    img, y0, fh = footage_canvas(FINALE_CLIP, t - bt(FINALE_B),
                                 zoom=1.0 + 0.04 * pulse(t))
    d = ImageDraw.Draw(img, "RGBA")
    if lb < 8:
        tag = "JOHNNY KINZIGER — FOR THE WIN"
        fnt = fit_font(ANTON, tag, 960, 64)
        tw, th, _ = text_size(fnt, tag)
        ty = y0 + fh + 70
        d.rectangle([W // 2 - tw // 2 - 30, ty, W // 2 + tw // 2 + 30, ty + th + 34],
                    fill=(*RED, 235))
        draw_center(d, tag, fnt, ty + th // 2 + 20, WHITE)
        chip(d, "N I T  •  0 3 . 2 2 . 2 6", W // 2, 250, font(OSWALD, 40))
    else:  # after the shot falls: the message
        a = ease_out((lb - 8) / 0.8)
        fnt = font(ANTON, max(24, int(150 * (1.6 - 0.6 * a))))
        draw_center(d, "ILLINOIS STATE", fnt, 320, WHITE, shadow=(0, 0, 0))
        d.rectangle([0, H - 520, W, H - 180], fill=(*RED, int(240 * a)))
        f2 = font(ANTON, max(24, int(210 * (1.6 - 0.6 * a))))
        draw_center(d, "BASKETBALL", f2, H - 430, WHITE)
        draw_center(d, "IS BACK.", f2, H - 260, WHITE, shadow=(60, 4, 10))
    return img


def scene_for(t, b):
    if b < DROP:
        return scene_intro(t, b)
    if b < BLOCKS[0]["b0"]:
        return scene_opener(t, b)
    for blk in reversed(BLOCKS):
        if b >= blk["b0"]:
            end = blk["b0"] + 4 * len(blk["clips"])
            if b < end:
                return scene_block(t, b, blk)
            break
    if b < FINALE_B:
        if b >= ROSTER_B:
            return scene_roster(t, b)
        return scene_block(t, b, BLOCKS[-1])
    return scene_finale(t, b)


# ---------------------------------------------------------------- post fx

_grain = [np.random.default_rng(s).integers(-13, 13, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _vig = np.clip(1.12 - 0.38 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


HITS = sorted(set(CUT_BEATS) | {FINALE_B + 8})


def post(img, t, b, fi):
    arr = np.asarray(img).astype(np.int16)
    hit_d = min((b - h for h in HITS if b >= h), key=abs, default=9.0)
    if 0 <= hit_d < 0.22:
        sh = 6 + int(8 * energy(t))
        arr[:, :, 0] = np.roll(arr[:, :, 0], sh, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -sh, axis=1)
        rng = np.random.default_rng(fi)
        for _ in range(4):
            y0 = int(rng.integers(0, H - 80))
            hgt = int(rng.integers(20, 80))
            arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(rng.integers(-90, 90)), axis=1)
        if hit_d < 0.14:
            arr = arr + 85
    shk = math.exp(-3.0 * max(0.0, hit_d) * P) if hit_d >= 0 else 0.0
    if shk > 0.05:
        rng = np.random.default_rng(fi * 7)
        arr = np.roll(arr, (int(rng.integers(-1, 2) * 13 * shk),
                            int(rng.integers(-1, 2) * 13 * shk)), axis=(0, 1))
    g = _grain[fi % 8]
    g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:H, :W]
    arr = (arr + g).astype(np.float32) * vignette()
    if t > DUR - 2.2:
        arr *= max(0.0, (DUR - t) / 2.2)
    return np.clip(arr, 0, 255).astype(np.uint8)


def render_frame(fi):
    t = fi / FPS
    return post(scene_for(t, beat_at(t)), t, beat_at(t), fi)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render_frame(int(float(ts) * FPS))).save(f"build/p2_{ts}.png")
            print(f"build/p2_{ts}.png")
        return
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "23", "-pix_fmt", "yuv420p", "build/video2_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/video2_silent.mp4", "-i", "build/mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", "illinois_state_is_back.mp4"],
        check=True, capture_output=True)
    print("wrote illinois_state_is_back.mp4")


if __name__ == "__main__":
    main()

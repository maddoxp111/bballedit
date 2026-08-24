"""Illinois State Redbirds — documentary-trailer (1920x1080, 30fps, 90s).

Cinemascope-letterboxed cinematic cut in the style of the reference film:
drone-quiet establishing shots with a lower-left location title, a build
through the NIT run, the game-winner on the music impact, a reflective
passage, and a resolve into the season card. Voiceover is a two-host
ElevenLabs podcast; score is synthesised (doc_score.py).

  python3 doc_trailer.py extract   # pull frames for every shot
  python3 doc_trailer.py sheet     # contact sheet of shot midpoints
  python3 doc_trailer.py           # render redbirds_documentary.mp4
"""
import os
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, SR = 1920, 1080, 30, 48000
DUR = 90.0
SCOPE_H = int(W / 2.39)                 # 803 -> cinemascope image band
BAR = (H - SCOPE_H) // 2
VO_START = 4.5
DISSOLVE = 0.40                          # default cross-dissolve

SUM = "build/tt/7652790943145299230.mp4"   # summer work, CEFCU Arena
PRA = "build/tt/7613596617618328863.mp4"   # Arch Madness shootaround
LOC = "build/tt/7621387281575775519.mp4"   # locker room after the win
WAKE = "build/clips/48282295.mp4"          # NIT vs Wake Forest
GW = "build/clips/48282239.mp4"            # the game-winner
KZ = "build/clips/48282097.mp4"            # Kinziger three
CW = "build/clips/47383232.mp4"            # Walker flush
DUNK = "build/clips/47041854.mp4"          # Klabo slam
# stills (Wikimedia Commons) get a slow push instead of motion
DUSK = "still:assets/stills/dusk.jpg"      # campus skyline at dusk
TOWERS = "still:assets/stills/towers.jpg"  # Watterson Towers
MARQUEE = "still:assets/stills/normal.jpg" # the NORMAL marquee, uptown
UPTOWN = "still:assets/stills/uptown.jpg"  # uptown Normal

# (t0, t1, src, src_start, speed, ycenter, zoom0, hardcut_in)
# Cut points are locked to the voiceover: "Normal, Illinois" lands on the
# marquee, "the Redbirds" on the CEFCU Arena board, "1.7 seconds" on the live
# wide, and the game-winner drops through the net on the score's impact at
# 42.35, exactly as the hosts say "Kinziger".
SHOTS = [
    (0.0,  5.0,  DUSK,    0.0,  1.00, 0.52, 1.00, False),
    (5.0,  10.5, TOWERS,  0.0,  1.00, 0.46, 1.00, False),
    (10.5, 16.2, MARQUEE, 0.0,  1.00, 0.50, 1.00, False),
    (16.2, 20.3, UPTOWN,  0.0,  1.00, 0.52, 1.00, False),
    (20.3, 24.5, SUM,    46.8,  1.00, 0.44, 1.02, False),
    (24.5, 28.0, SUM,    10.5,  1.00, 0.46, 1.00, False),
    (28.0, 32.0, SUM,     0.30, 1.00, 0.38, 1.03, False),
    (32.0, 35.5, PRA,     0.60, 1.00, 0.46, 1.00, False),
    (35.5, 39.6, WAKE,    6.0,  1.00, 0.52, 1.00, False),
    (39.6, 41.4, GW,      9.50, 1.00, 0.52, 1.00, True),
    (41.4, 42.35, GW,    17.00, 1.00, 0.42, 1.00, True),
    (42.35, 46.0, WAKE,  63.2,  1.00, 0.52, 1.00, True),
    (46.0, 51.0, WAKE,   59.5,  1.00, 0.52, 1.00, False),
    (51.0, 55.0, PRA,    26.5,  1.00, 0.46, 1.02, False),
    (55.0, 58.6, PRA,    20.5,  1.00, 0.46, 1.00, False),
    (58.6, 62.1, KZ,     18.30, 1.00, 0.50, 1.00, False),
    (62.1, 65.0, CW,      4.20, 1.00, 0.50, 1.00, False),
    (65.0, 69.0, PRA,    44.5,  1.00, 0.46, 1.02, False),
    (69.0, 73.5, SUM,    26.5,  1.00, 0.46, 1.00, False),
    (73.5, 77.0, SUM,    20.5,  1.00, 0.46, 1.02, False),
    (77.0, 80.9, SUM,    44.5,  1.00, 0.44, 1.00, False),
    (80.9, 84.7, DUNK,    8.00, 1.00, 0.50, 1.00, True),
    (84.7, 87.2, WAKE,   65.5,  1.00, 0.52, 1.00, False),
]
CARD_T = 87.2                            # end title card

# lower-left location titles: (t0, t1, text)
LOCATIONS = [
    (2.2, 7.0, "NORMAL, ILLINOIS"),
    (20.9, 24.2, "CEFCU ARENA"),
]

ANTON = "assets/fonts/Anton-Regular.ttf"
OSWALD = "assets/fonts/Oswald.ttf"
_fonts = {}


def font(path, size, weight=None):
    k = (path, size, weight)
    if k not in _fonts:
        f = ImageFont.truetype(path, size)
        if weight:
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
        _fonts[k] = f
    return _fonts[k]


def extract():
    for i, (t0, t1, src, s0, sp, yc, z0, hard) in enumerate(SHOTS):
        if src.startswith("still:"):
            print(f"shot {i:02d} still {os.path.basename(src)}")
            continue
        need = (t1 - t0) * sp + DISSOLVE + 0.4
        d = f"build/doc/{i:02d}"
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(f"{d}/{f}")
        subprocess.run([FFMPEG, "-y", "-ss", f"{max(0,s0):.3f}", "-i", src,
                        "-t", f"{need:.3f}", "-vf", f"fps={FPS}", "-q:v", "2",
                        f"{d}/%04d.jpg"], check=True, capture_output=True)
        print(f"shot {i:02d} {os.path.basename(src)[:14]:16s} {t0:5.1f}-{t1:5.1f} "
              f"src {s0:5.1f} {len(os.listdir(d))}f")


_cache = {}


def frame(i, idx):
    k = (i, idx)
    if k not in _cache:
        if len(_cache) > 8:
            _cache.clear()
        p = f"build/doc/{i:02d}/{idx:04d}.jpg"
        _cache[k] = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    return _cache[k]


_stills = {}


def still(path):
    if path not in _stills:
        _stills[path] = np.asarray(
            Image.open(path).convert("RGB")).astype(np.float32)
    return _stills[path]


def shot_image(i, local_t):
    """Scope-band crop of shot i at local time, with a slow push-in."""
    t0, t1, src, s0, sp, yc, z0, hard = SHOTS[i]
    if src.startswith("still:"):
        a = still(src[6:])
    else:
        n = len(os.listdir(f"build/doc/{i:02d}"))
        idx = max(1, min(n, int(local_t * sp * FPS) + 1))
        a = frame(i, idx)
    sh, sw = a.shape[:2]
    prog = max(0.0, min(1.0, local_t / max(0.1, t1 - t0)))
    push = 0.10 if src.startswith('still:') else 0.045
    zoom = z0 * (1.0 + push * prog)          # gentle cinematic drift
    cw = sw / zoom
    ch = cw / 2.39
    if ch > sh:                                # vertical source: fit width
        ch = sh / zoom
        cw = ch * 2.39
        if cw > sw:
            cw = sw / zoom
            ch = cw / 2.39
    cx = sw / 2
    cy = min(max(yc * sh, ch / 2), sh - ch / 2)
    box = (int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).crop(box)
    return np.asarray(im.resize((W, SCOPE_H), Image.LANCZOS)).astype(np.float32)


def grade(a):
    """Filmic: slight desaturation, lifted blacks, cool shadows/warm highs."""
    luma = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
    o = luma * 0.22 + a * 0.78
    o = (o - 8) * 1.10 + 10                    # contrast with a lifted floor
    n = np.clip(o / 255.0, 0, 1)
    o[..., 0] = 255 * (n[..., 0] ** 0.98)      # warm highlights
    o[..., 2] = 255 * (n[..., 2] ** 1.04)      # cool shadows
    return np.clip(o, 0, 255)


def band_at(t):
    """Composite the scope band at time t, with cross-dissolves."""
    cur = None
    for i, (t0, t1, *_rest) in enumerate(SHOTS):
        if t0 <= t < t1:
            cur = i
            break
    if cur is None:
        return None
    t0, t1, src, s0, sp, yc, z0, hard = SHOTS[cur]
    img = shot_image(cur, t - t0)
    dt = t - t0
    if not hard and cur > 0 and dt < DISSOLVE:
        pt0 = SHOTS[cur - 1][0]
        prev = shot_image(cur - 1, t - pt0)
        k = dt / DISSOLVE
        img = prev * (1 - k) + img * k
    return grade(img)


_grain = [np.random.default_rng(s).integers(-6, 6, (H // 2, W // 2, 1), dtype=np.int16)
          for s in range(8)]
_vig = None


def vignette():
    global _vig
    if _vig is None:
        y, x = np.ogrid[:SCOPE_H, :W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - SCOPE_H / 2) / (SCOPE_H / 2)) ** 2)
        _vig = np.clip(1.06 - 0.20 * r ** 2, 0, 1).astype(np.float32)[..., None]
    return _vig


def draw_location(canvas, t):
    d = ImageDraw.Draw(canvas, "RGBA")
    for t0, t1, text in LOCATIONS:
        if t0 <= t < t1:
            a = int(235 * min(1.0, (t - t0) / 0.8, max(0.0, (t1 - t) / 0.8)))
            if a <= 0:
                continue
            f = font(OSWALD, 34, 500)
            x, y = 92, BAR + SCOPE_H - 92
            tr = 7
            for ch in text:
                d.text((x + 2, y + 2), ch, font=f, fill=(0, 0, 0, int(a * 0.7)))
                d.text((x, y), ch, font=f, fill=(238, 238, 240, a))
                x += f.getbbox(ch)[2] - f.getbbox(ch)[0] + tr


def end_card(t):
    lt = t - CARD_T
    img = Image.new("RGB", (W, H), (5, 5, 6))
    d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * min(1.0, lt / 0.8))
    f1 = font(ANTON, 96)
    s = "ILLINOIS STATE"
    box = f1.getbbox(s)
    d.text((W // 2 - (box[2] - box[0]) // 2, H // 2 - 96 - box[1]), s,
           font=f1, fill=(240, 240, 242, a))
    if lt > 0.7:
        a2 = int(230 * min(1.0, (lt - 0.7) / 0.7))
        f2 = font(OSWALD, 40, 500)
        s2 = "2026 — 27"
        x = W // 2 - sum(f2.getbbox(c)[2] - f2.getbbox(c)[0] + 12 for c in s2) // 2
        y = H // 2 + 40
        for c in s2:
            d.text((x, y), c, font=f2, fill=(196, 42, 58, a2))
            x += f2.getbbox(c)[2] - f2.getbbox(c)[0] + 12
    return np.asarray(img).astype(np.float32)


def render_frame(fi):
    t = fi / FPS
    if t >= CARD_T:
        arr = end_card(t)
        canvas = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    else:
        band = band_at(t)
        canvas = Image.new("RGB", (W, H), (0, 0, 0))
        if band is not None:
            band = band * vignette()
            canvas.paste(Image.fromarray(np.clip(band, 0, 255).astype(np.uint8)), (0, BAR))
        draw_location(canvas, t)
    arr = np.asarray(canvas).astype(np.float32)
    g = _grain[fi % 8]
    arr = arr + np.repeat(np.repeat(g, 2, 0), 2, 1)[:H, :W]
    if t < 1.2:                                # fade up from black
        arr *= t / 1.2
    if t > DUR - 1.6:
        arr *= max(0.0, (DUR - t) / 1.6)
    return np.clip(arr, 0, 255).astype(np.uint8)


def build_audio():
    subprocess.run([FFMPEG, "-y", "-i", "build/vo_full.mp3", "-ac", "2", "-ar", str(SR),
                    "build/vo_st.wav"], check=True, capture_output=True)
    with wave.open("build/vo_st.wav") as w:
        vo = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    vo = vo.reshape(-1, 2).astype(np.float32) / 32768.0
    with wave.open("build/doc_music.wav") as w:
        mu = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    mu = mu.reshape(-1, 2).astype(np.float32) / 32768.0

    n = int(DUR * SR)
    out = np.zeros((n, 2), np.float32)
    m = min(len(mu), n)
    out[:m] += mu[:m]

    i0 = int(VO_START * SR)
    k = min(len(vo), n - i0)
    voice = np.zeros((n, 2), np.float32)
    voice[i0:i0 + k] = vo[:k] * 1.18

    # duck the score under the voice
    env = np.abs(voice).max(axis=1)
    win = int(0.05 * SR)
    env = np.convolve(env, np.ones(win) / win, "same")
    env = env / (env.max() + 1e-9)
    rel = int(0.35 * SR)
    env = np.convolve(env, np.hanning(rel) / np.hanning(rel).sum(), "same")
    duck = 1.0 - 0.62 * np.clip(env * 2.4, 0, 1)
    out *= duck[:, None]
    out += voice

    out = np.tanh(out * 0.95)
    out = np.clip(out, -0.99, 0.99)
    with wave.open("build/doc_mix.wav", "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    print("wrote build/doc_mix.wav")


def sheet():
    tiles = []
    for i, (t0, t1, *_r) in enumerate(SHOTS):
        arr = render_frame(int(((t0 + t1) / 2) * FPS))
        im = Image.fromarray(arr).resize((480, 270))
        d = ImageDraw.Draw(im)
        d.text((8, 8), f"{i}  {t0:.0f}-{t1:.0f}s", fill=(255, 220, 0))
        tiles.append(im)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    s = Image.new("RGB", (480 * cols, 270 * rows), (0, 0, 0))
    for i, im in enumerate(tiles):
        s.paste(im, ((i % cols) * 480, (i // cols) * 270))
    s.save("build/doc_sheet.jpg", quality=86)
    print("wrote build/doc_sheet.jpg")


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
         "-crf", "20", "-pix_fmt", "yuv420p", "build/doc_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 200 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/doc_silent.mp4", "-i", "build/doc_mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", "redbirds_documentary.mp4"],
        check=True, capture_output=True)
    print("wrote redbirds_documentary.mp4")


if __name__ == "__main__":
    main()

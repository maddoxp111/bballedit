"""Arcade bootup intro — EA-Sports-style 3D logo assembly (1920x1080, 30fps, 10.5s).

The Redbirds lockup splits into four pieces (ILLINOIS / STATE / REDBIRDS /
bird head). Each tumbles in from off-screen in 3D perspective with motion
blur and a whoosh, slams into its slot with a flash + shake + metallic hit,
the head lands last with a spark burst. The assembled logo gets a light
sweep and a slow parallax wobble over a faint hex-grid backdrop, then the
camera pushes through it as everything dims smoothly to pure black.
All sound effects are synthesized. Output: arcade_bootup.mp4.
"""
import math
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, DUR = 1920, 1080, 30, 10.5
SR = 48000

LOGO = Image.open("assets/logo/logo_hi.png").convert("RGBA")  # 1600x1143

# ---------------------------------------------------------------- pieces
# partition the logo with feathered rect masks (union == full logo)
REGIONS = {  # (x0, y0, x1, y1) in logo pixels
    "illinois": (300, 415, 1035, 605),
    "state":    (450, 605, 1035, 700),
    "redbirds": (450, 700, 1035, 800),
}


def make_pieces():
    w, h = LOGO.size
    arr = np.asarray(LOGO).astype(np.float32)
    used = np.zeros((h, w), np.float32)
    pieces = {}
    for name, (x0, y0, x1, y1) in REGIONS.items():
        m = np.zeros((h, w), np.float32)
        m[y0:y1, x0:x1] = 1.0
        mm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(3))).astype(np.float32) / 255.0
        mm = np.clip(mm - used, 0, 1)
        used = np.clip(used + mm, 0, 1)
        pa = arr.copy()
        pa[..., 3] *= mm
        pieces[name] = pa
    pa = arr.copy()
    pa[..., 3] *= (1.0 - used)          # head = everything not yet claimed
    pieces["head"] = pa
    out = {}
    for name, pa in pieces.items():
        a = pa[..., 3]
        ys, xs = np.where(a > 8)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        img = Image.fromarray(np.clip(pa[y0:y1, x0:x1], 0, 255).astype(np.uint8))
        out[name] = {"img": img, "off": (x0, y0)}
    return out


PIECES = make_pieces()

# final layout: logo 1150px wide, centered
LSCALE = 1150 / LOGO.size[0]
LOFF = (W / 2 - 1150 / 2, H / 2 - LOGO.size[1] * LSCALE / 2)


def final_center(name):
    img = PIECES[name]["img"]
    ox, oy = PIECES[name]["off"]
    cx = LOFF[0] + (ox + img.size[0] / 2) * LSCALE
    cy = LOFF[1] + (oy + img.size[1] / 2) * LSCALE
    return cx, cy


# ---------------------------------------------------------------- 3d paths
# keyframes: (t, x, y, z, yaw, pitch, roll) — z>0 is away from camera,
# z<0 toward it; angles in degrees. Ends locked at the final slot.
def keys_for(name, land, cx, cy):
    e = {
        "illinois": [(-2.2, -1900, cy - 500, -700, -70, 18, -24),
                     (-1.0, W * 0.30, cy - 160, -260, -30, 10, -10),
                     (-0.35, cx + 180, cy + 30, 60, 14, -5, 5)],
        "state":    [(-2.2, W + 1900, cy + 420, -650, 65, -14, 20),
                     (-1.0, W * 0.66, cy + 150, -240, 28, -8, 9),
                     (-0.35, cx - 160, cy - 30, 55, -12, 4, -4)],
        "redbirds": [(-1.8, cx - 300, H + 900, -520, -18, -55, 12),
                     (-0.8, cx + 90, H * 0.68, -180, -8, -24, 6),
                     (-0.3, cx - 60, cy + 40, 45, 4, 10, -3)],
        "head":     [(-2.4, W * 0.75, -1000, -800, 40, 55, -30),
                     (-1.1, W * 0.62, H * 0.25, -300, 18, 24, -14),
                     (-0.4, cx - 70, cy - 60, 70, -8, -10, 6)],
    }[name]
    ks = [(land + dt, x, y, z, ya, pi, ro) for dt, x, y, z, ya, pi, ro in e]
    ks.append((land, cx, cy, 0.0, 0.0, 0.0, 0.0))
    ks.append((land + 0.12, cx, cy, -14.0, 0.0, 0.0, 0.0))   # tiny settle pop
    ks.append((land + 0.30, cx, cy, 0.0, 0.0, 0.0, 0.0))
    return ks


LANDS = {"illinois": 2.6, "state": 3.7, "redbirds": 4.6, "head": 5.7}
PATHS = {n: keys_for(n, LANDS[n], *final_center(n)) for n in PIECES}


def ease(a):
    return a * a * (3 - 2 * a)


def pose(name, t):
    ks = PATHS[name]
    if t <= ks[0][0]:
        return None
    if t >= ks[-1][0]:
        return ks[-1][1:]
    for i in range(len(ks) - 1):
        if ks[i][0] <= t < ks[i + 1][0]:
            a = ease((t - ks[i][0]) / (ks[i + 1][0] - ks[i][0]))
            return tuple(ks[i][j + 1] + a * (ks[i + 1][j + 1] - ks[i][j + 1])
                         for j in range(6))
    return ks[-1][1:]


def find_coeffs(dst, src):
    A, B = [], []
    for (X, Y), (x, y) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
        B += [X, Y]
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


FOV = 1150.0


def piece_quad(name, p):
    """Project the piece's 3D plane corners to screen."""
    x, y, z, yaw, pitch, roll = p
    img = PIECES[name]["img"]
    hw = img.size[0] * LSCALE / 2
    hh = img.size[1] * LSCALE / 2
    ya, pi, ro = (math.radians(v) for v in (yaw, pitch, roll))
    cy_, sy_ = math.cos(ya), math.sin(ya)
    cp, sp = math.cos(pi), math.sin(pi)
    cr, sr = math.cos(ro), math.sin(ro)
    quad = []
    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        rx = dx * cr - dy * sr
        ry = dx * sr + dy * cr
        X = rx * cy_
        Z1 = -rx * sy_
        Y = ry * cp - Z1 * sp
        Z = ry * sp + Z1 * cp
        zz = z + Z + FOV
        s = FOV / max(zz, 80.0)
        quad.append((x + X * s, y + Y * s))
    return quad


def draw_piece(canvas, name, p, alpha=1.0):
    quad = piece_quad(name, p)
    xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
    x0, x1 = int(min(xs)) - 2, int(max(xs)) + 2
    y0, y1 = int(min(ys)) - 2, int(max(ys)) + 2
    if x1 < 0 or y1 < 0 or x0 > W or y0 > H or (x1 - x0) < 4 or (y1 - y0) < 4:
        return
    if (x1 - x0) > 4 * W or (y1 - y0) > 4 * H:
        return
    img = PIECES[name]["img"]
    sw, sh = img.size
    local = [(q[0] - x0, q[1] - y0) for q in quad]
    try:
        co = find_coeffs(local, [(0, 0), (sw, 0), (sw, sh), (0, sh)])
        co = find_coeffs([(0, 0), (sw, 0), (sw, sh), (0, sh)], local)
    except np.linalg.LinAlgError:
        return
    warped = img.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, co,
                           Image.BICUBIC)
    if alpha < 1.0:
        a = warped.getchannel("A").point(lambda v: int(v * alpha))
        warped.putalpha(a)
    canvas.alpha_composite(warped, (x0, y0))


# ---------------------------------------------------------------- backdrop

_hex = None


def hex_bg(t, level):
    """Very dark radial gradient + faint drifting hex grid."""
    global _hex
    if _hex is None:
        tile = Image.new("L", (96, 84), 0)
        d = ImageDraw.Draw(tile)
        for cx, cy in ((24, 21), (72, 63), (72, -21), (-24, 63), (24, 105)):
            d.regular_polygon((cx, cy, 26), 6, rotation=30, outline=28)
        _hex = tile
    reps = (W // 96 + 3, H // 84 + 2)
    grid = Image.new("L", (reps[0] * 96, reps[1] * 84))
    for i in range(reps[0]):
        for j in range(reps[1]):
            grid.paste(_hex, (i * 96, j * 84))
    dx = int(t * 6) % 96
    g = np.asarray(grid.crop((dx, 0, dx + W, H))).astype(np.float32)
    yy, xx = np.ogrid[:H, :W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    rad = np.clip(1.0 - 0.75 * r, 0, 1) * 26
    base = rad + g * 0.55
    out = np.stack([base * 1.05, base * 0.55, base * 0.6], -1)
    return out * level


# ---------------------------------------------------------------- particles

RNG = np.random.default_rng(11)
SPARKS = []
for name, land in LANDS.items():
    cx, cy = final_center(name)
    n = 90 if name == "head" else 36
    ang = RNG.uniform(0, 2 * np.pi, n)
    spd = RNG.uniform(180, 950, n) * (1.4 if name == "head" else 1.0)
    SPARKS.append((land, cx, cy, ang, spd, RNG.uniform(0.4, 1.1, n)))


def draw_sparks(d, t):
    for land, cx, cy, ang, spd, life in SPARKS:
        dt = t - land
        if dt < 0:
            continue
        alive = dt < life
        if not alive.any():
            continue
        x = cx + np.cos(ang) * spd * dt
        y = cy + np.sin(ang) * spd * dt + 260 * dt * dt
        a = np.clip(1 - dt / life, 0, 1) ** 1.4
        for xi, yi, ai in zip(x[alive], y[alive], a[alive]):
            v = int(255 * ai)
            d.ellipse([xi - 2, yi - 2, xi + 2, yi + 2], fill=(255, 235 - int(70 * ai), 180, v))


# ---------------------------------------------------------------- frame

ORDER = ["illinois", "state", "redbirds", "head"]


def render_frame(fi):
    t = fi / FPS
    # global levels: build to full, then dim through the exit push
    if t < 8.2:
        level = 1.0 if t > 0.8 else t / 0.8
    else:
        level = max(0.0, 1.0 - (t - 8.2) / 1.9)
    bg = hex_bg(t, min(level, 1.0) * min(1.0, max(0.0, (t - 0.6) / 1.2)))
    canvas = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")

    # exit push: everything scales up slightly and drifts as it dims
    push = 1.0 + max(0.0, (t - 8.2)) * 0.16
    wobble_y = 3.5 * math.sin(t * 0.9) * (1 if t > 5.9 else 0)

    for name in ORDER:
        p = pose(name, t)
        if p is None:
            continue
        x, y, z, ya, pi, ro = p
        if t > 5.9:  # assembled: shared slow parallax wobble
            ya += wobble_y
            pi += 2.0 * math.sin(t * 0.7 + 1.3)
        if push > 1.0:
            x = W / 2 + (x - W / 2) * push
            y = H / 2 + (y - H / 2) * push
            z -= (push - 1.0) * 160
        # motion blur ghosts while flying fast
        prev = pose(name, t - 1 / 45)
        if prev is not None and t < LANDS[name]:
            v = math.hypot(x - prev[0], y - prev[1])
            if v > 26:
                draw_piece(canvas, name, prev, alpha=0.32)
        draw_piece(canvas, name, (x, y, z, ya, pi, ro))

    d = ImageDraw.Draw(canvas, "RGBA")
    draw_sparks(d, t)
    arr = np.asarray(canvas.convert("RGB")).astype(np.float32)

    # light sweep across the assembled logo
    if 6.2 <= t < 7.2:
        a = (t - 6.2) / 1.0
        sx = -400 + (W + 800) * a
        xx = np.arange(W, dtype=np.float32)
        band = np.exp(-((xx - sx) / 130.0) ** 2)
        arr += band[None, :, None] * 70 * math.sin(a * math.pi)

    # impact flashes + shake
    for name, land in LANDS.items():
        dt = t - land
        if 0 <= dt < 0.12:
            arr += (60 if name != "head" else 105) * (1 - dt / 0.12)
        if 0 <= dt < 0.4:
            amp = (14 if name == "head" else 8) * math.exp(-dt * 11)
            if amp > 0.8:
                r = np.random.default_rng(fi * 13)
                arr = np.roll(arr, (int(r.integers(-1, 2) * amp),
                                    int(r.integers(-1, 2) * amp)), (0, 1))

    arr *= level if t >= 8.2 else 1.0
    # gentle grain, and absolute black by the end
    g = np.random.default_rng(fi % 8).integers(-5, 5, (H // 2, W // 2, 1)).astype(np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[:H, :W]
    arr = arr + g * (level if t > 0.4 else 0.4)
    if t > 10.1:
        arr[:] = 0
    return np.clip(arr, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- audio

def build_audio():
    mix = np.zeros((int(DUR * SR), 2), np.float32)
    rng = np.random.default_rng(5)

    def add(sig, t, gain=1.0, pan=0.0):
        if sig.ndim == 1:
            l = math.sqrt(max(0.0, (1 - pan) / 2)); r = math.sqrt((1 + pan) / 2)
            sig = np.stack([sig * l * 1.41, sig * r * 1.41], 1)
        i = int(t * SR)
        n = min(len(sig), len(mix) - i)
        mix[i:i + n] += sig[:n] * gain

    # boot rumble riser (0 -> first impact)
    n = int(2.6 * SR)
    tt = np.linspace(0, 1, n)
    rum = np.sin(2 * np.pi * np.cumsum(38 + 20 * tt) / SR)
    rum += rng.normal(0, 0.28, n)
    k = np.hanning(257); k /= k.sum()
    rum = np.convolve(rum, k, "same")
    add(rum * (tt ** 1.7), 0.0, 0.5)

    def whoosh(dur, f0=1.0):
        n = int(dur * SR)
        x = rng.normal(0, 1, n).astype(np.float32)
        x = np.diff(x, prepend=0)
        kk = np.hanning(int(90 / f0) | 1); kk /= kk.sum()
        x = np.convolve(x, kk, "same")
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.6
        return x / (np.abs(x).max() + 1e-9) * e

    def clank():
        n = int(0.6 * SR)
        tt = np.linspace(0, 0.6, n, False)
        s = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) *
                np.exp(-tt * dmp) for f, dmp in
                ((760, 12), (1290, 16), (2140, 22), (3320, 30)))
        s += rng.normal(0, 1, n) * np.exp(-tt * 60) * 1.6
        return s / (np.abs(s).max() + 1e-9)

    def boom(dur=1.0, f_hi=110):
        n = int(dur * SR)
        tt = np.linspace(0, dur, n, False)
        f = f_hi * np.exp(-tt * 3.2) + 38
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.4)
        s += rng.normal(0, 1, n) * np.exp(-tt * 45) * 0.7
        return np.tanh(s * 1.9)

    pans = {"illinois": -0.6, "state": 0.6, "redbirds": 0.0, "head": 0.2}
    for name, land in LANDS.items():
        add(whoosh(1.5), land - 1.5, 0.55, pan=-pans[name])
        add(boom(0.9), land - 0.01, 0.62 if name != "head" else 0.95, pan=pans[name] * 0.4)
        add(clank(), land, 0.4 if name != "head" else 0.6, pan=pans[name] * 0.5)
    # head lands: spark shimmer + sub drop
    n = int(1.6 * SR)
    tt = np.linspace(0, 1, n)
    shim = rng.normal(0, 1, n) * np.exp(-tt * 3.2)
    shim = shim - np.convolve(shim, np.hanning(129) / np.hanning(129).sum(), "same")
    add(shim, LANDS["head"], 0.30)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(58, 30, int(1.8 * SR))) / SR)
    add(sub * np.exp(-np.linspace(0, 1.8, int(1.8 * SR)) * 2.0), LANDS["head"], 0.6)

    # hold pad under the assembled logo, gliding down + dying through the exit
    n = int((DUR - 5.7) * SR)
    tt = np.linspace(0, n / SR, n, False)
    glide = np.where(tt < 2.5, 52.0, 52.0 * np.exp(-(tt - 2.5) * 0.09))
    pad = np.sin(2 * np.pi * np.cumsum(glide) / SR)
    pad += 0.6 * np.sin(2 * np.pi * np.cumsum(glide * 1.007) / SR)
    e = np.minimum(tt / 0.8, 1.0) * np.exp(-np.maximum(0.0, tt - 2.5) * 0.9)
    add(pad * e, 5.7, 0.34)

    # glint sweep shimmer
    n = int(1.1 * SR)
    x = rng.normal(0, 1, n)
    x = x - np.convolve(x, np.hanning(65) / np.hanning(65).sum(), "same")
    add(x * np.sin(np.pi * np.linspace(0, 1, n)) ** 2, 6.2, 0.16)

    k = int(0.8 * SR)
    mix[-k:] *= np.linspace(1, 0, k)[:, None]
    mix = np.clip(mix, -0.99, 0.99)
    with wave.open("build/boot_mix.wav", "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print("wrote build/boot_mix.wav")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render_frame(int(float(ts) * FPS))).save(f"build/pb_{ts}.png")
            print(f"build/pb_{ts}.png")
        return
    build_audio()
    total = int(DUR * FPS)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", "build/boot_silent.mp4"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 60 == 0:
            print(f"frame {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        [FFMPEG, "-y", "-i", "build/boot_silent.mp4", "-i", "build/boot_mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", "arcade_bootup.mp4"],
        check=True, capture_output=True)
    print("wrote arcade_bootup.mp4")


if __name__ == "__main__":
    main()

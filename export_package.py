"""Export the documentary trailer as editable parts.

Rather than one flattened MP4, this writes each shot as its own frame-accurate
clip cut from the ORIGINAL source (speed applied, no crop and no grade, so the
full frame stays available for reframing), plus the voiceover and score as
separate stems, plus a cut sheet giving each clip's exact place on the
timeline. Drop the clips in order, lay the two stems underneath at 0:00, and
you have the edit — fully rearrangeable.

Quality: clips are re-encoded once at near-lossless CRF 14 because
frame-accurate trims cannot be stream-copied (cuts would snap to keyframes).
The stems are byte-for-byte copies. For a strictly zero-re-encode route, use
the ORIGINAL files listed in the cut sheet and set the in/out points by hand.
"""
import csv
import os
import shutil
import subprocess

import imageio_ffmpeg

import doc_trailer as dt

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = "capcut_package"
os.makedirs(f"{OUT}/clips", exist_ok=True)
os.makedirs(f"{OUT}/audio", exist_ok=True)

LABEL = {
    "build/aerial/drone.mp4": "drone",
    "build/user/u1.mov": "celebration_court",
    "build/user/u2.mov": "bench_eruption",
    "build/user/u3.mov": "handshake_lockerroom",
    "build/user/u4.mov": "cefcu_workout",
    "build/user/u5.mov": "huddle",
    "build/tt/7652790943145299230.mp4": "summer_cefcu",
    "build/clips/48282239.mp4": "gamewinner_ball",
}

rows = []
for i, (t0, t1, src, s0, sp, yc, z0, hard) in enumerate(dt.SHOTS):
    if src.startswith("still:"):
        continue
    name = f"{i:02d}_{LABEL.get(src, os.path.basename(src).split('.')[0])}.mp4"
    dur_out = t1 - t0
    src_len = dur_out * sp
    vf = f"setpts={1/sp:.6f}*PTS" if abs(sp - 1.0) > 1e-3 else None
    cmd = [FFMPEG, "-y", "-ss", f"{s0:.3f}", "-i", src, "-t", f"{src_len:.3f}"]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-an", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
            "-pix_fmt", "yuv420p", f"{OUT}/clips/{name}"]
    subprocess.run(cmd, check=True, capture_output=True)
    rows.append(dict(order=i, file=f"clips/{name}",
                     timeline_in=f"{t0:.2f}", timeline_out=f"{t1:.2f}",
                     duration=f"{dur_out:.2f}", speed=f"{sp:.2f}",
                     source=src, source_in=f"{s0:.2f}",
                     crop_center_y=f"{yc:.2f}", hard_cut="yes" if hard else "no"))
    print(f"  {name}  {t0:6.2f}-{t1:6.2f}  x{sp}")

shutil.copy("build/vo_full.mp3", f"{OUT}/audio/voiceover.mp3")
shutil.copy("build/doc_music.wav", f"{OUT}/audio/score.wav")

with open(f"{OUT}/cuts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

with open(f"{OUT}/CUT_SHEET.md", "w") as f:
    f.write("# Redbirds documentary - cut sheet\n\n")
    f.write("Timeline is 1920x1080, 30fps, 109s total.\n\n")
    f.write("## Audio (lay both at 0:00, full length)\n\n")
    f.write("- `audio/voiceover.mp3` - two-host VO, starts at 4.5s of its own\n"
            "  file's timeline; place at 0:00 and it lines up.\n")
    f.write("- `audio/score.wav` - the score, already ducked-free (mix it under\n"
            "  the VO to taste; the delivered MP4 ducks it ~62% under speech).\n\n")
    f.write("## Video\n\n")
    f.write("Drop clips in filename order. Each is already trimmed and speed-\n"
            "adjusted, so no retiming is needed.\n\n")
    f.write("| # | clip | in | out | dur | speed | source | src in |\n")
    f.write("|---|------|----|-----|-----|-------|--------|--------|\n")
    for r in rows:
        f.write(f"| {r['order']} | `{r['file']}` | {r['timeline_in']} | "
                f"{r['timeline_out']} | {r['duration']} | {r['speed']}x | "
                f"`{r['source']}` | {r['source_in']} |\n")
    f.write("\n## Look\n\n")
    f.write("The delivered MP4 crops each shot to a 2.39:1 letterbox band "
            "centred at the\n`crop_center_y` fraction in `cuts.csv`, then "
            "applies a filmic grade (slight\ndesaturation, lifted blacks, warm "
            "highlights) plus grain and a vignette.\nThese clips are exported "
            "FULL FRAME and ungraded so you can reframe freely.\n\n")
    f.write("## Titles\n\n")
    f.write('- "NORMAL, ILLINOIS" - lower left, 2.2s to 7.0s\n')
    f.write('- "CEFCU ARENA" - lower left, 16.8s to 20.2s\n')
    f.write('- End card "ILLINOIS STATE" / "2026 - 27" - 104s to 109s\n')

print(f"\nwrote {OUT}/ ({len(rows)} clips + 2 stems + cut sheet)")

# Illinois State Basketball — "IS BACK" Edit (2026–27)

A 60-second vertical (1080×1920, 30fps) TikTok-style hype edit for Illinois
State men's basketball, built from real ESPN game footage and beat-synced to
"40 Nights". Theme: **Illinois State basketball is back** — spotlighting the
returning core (Mason Klabo, Chase Walker, Johnny Kinziger) plus the rest of
the official 2026–27 roster.

Roster source: [goredbirds.com 2026-27 men's basketball roster](https://goredbirds.com/sports/mens-basketball/roster)
— current players only, nobody who left.

## Structure

The song plays from 0:00. Typography cold open until the beat drop (~5.9s),
then footage cut on the ~92 BPM beat grid:

| Beats | Section |
|---|---|
| 0–9 | Cold open — flickering intro lines, riser building into the drop |
| 9–13 | DROP: Kinziger dunk + "ILLINOIS STATE IS BACK." slam |
| 13–33 | MASON KLABO block — 5 clips (dunk, and-1, three, bucket, dime) |
| 33–53 | CHASE WALKER block — 5 clips (flush + a parade of and-1s) |
| 53–69 | JOHNNY KINZIGER block — 4 clips (threes, runner, stuff) |
| 69–77 | Rapid roster cards — the other 11 Redbirds + HC Ryan Pedon |
| 77–end | FINALE: Kinziger's NIT game-winning triple vs Wake Forest (03.22.26), "BASKETBALL IS BACK." slams as the ball flies |

## Pipeline

```bash
pip install numpy pillow imageio-ffmpeg yt-dlp
python3 analyze_audio2.py    # beat grid + drop detection -> build/analysis2.json
# download ESPN clips (ids in build_segments.py) into build/clips/<id>.mp4
python3 build_segments.py    # finds each clip's money moment, extracts frames
python3 track_action.py      # ball + rim + player tracking for the virtual camera
python3 make_audio.py        # song + synthesized SFX (riser/booms/whooshes)
python3 render_edit3.py      # renders illinois_state_is_back.mp4
```

The final look (`render_edit3.py`, modeled on a reference TikTok edit): footage
fills the whole 9:16 frame and a virtual camera pans left/right with the play.
`track_action.py` finds the ball each frame (orange ∩ moving blob), falls back
to the rim (orange static bar) then the YOLO player cluster, interpolates
gaps, and zero-phase smooths the result so the pan is steady with no jitter.
Punch-in settles + slow drift zoom instead of beat pulsing, dip-to-black
between player blocks, and almost no text — one lowercase cold-open line, a
tiny name per player, one closer (Montserrat).
`render_edit2.py` (blurred-fill layout, heavy typography) is kept for
reference.

Details:

- **Footage**: ESPN highlight clips (`espn.com/video/clip?id=...`), found via
  ESPN's search API, downloaded with yt-dlp. Every featured player is on the
  2026–27 roster.
- **Money-moment detection**: the make + crowd roar is the loudest sustained
  stretch of broadcast audio, so each clip window is centered just before its
  smoothed-RMS peak (with a manual override for the finale).
- **Look**: blurred-fill vertical layout, name slams, beat-pulse zoom, shake,
  RGB-split glitch and flash on every cut, grain + vignette.
- **Sound design**: synthesized riser into the drop, sub-bass booms on section
  slams, whooshes on cuts, mixed under the song.
- `analyze_audio.py` / `render_edit.py` are the earlier pure-typography
  version (no footage), kept for reference.

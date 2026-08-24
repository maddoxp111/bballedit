# Build this documentary trailer in CapCut

Paste this whole file to a Claude Code session running LOCALLY on the machine
where CapCut and the CapCut MCP server (plus its VectCutAPI backend on
http://localhost:9001) are installed. Everything below is exact.

---

## 1. What we are building

A 1:49 cinematic documentary trailer for Illinois State Redbirds men's
basketball, in the style of a streaming-doc teaser: aerial establishing shots
of Normal, Illinois, a two-host podcast voiceover telling the story of the
2026 NIT run and the players who chose to come back, and a wordless montage to
close.

**Sequence settings**
- Resolution: 1920 x 1080
- Frame rate: 30 fps
- Duration: 109.0 s
- Background: black

---

## 2. Assets

All paths are relative to this folder.

**Video sources** (full, untrimmed - set in/out per the table in section 4)

| file | what it is | duration |
|---|---|---|
| `source/drone_uptown_isu.mp4` | Aerial tour of Uptown Normal + ISU campus | 3:17 |
| `source/u1.mov` | On-court celebration after a win | 10.3 s |
| `source/u2.mov` | Bench eruption, arms raised | 3.4 s |
| `source/u3.mov` | Handshake line, then locker room | 2.1 s |
| `source/u4.mov` | CEFCU Arena summer workouts | 35.5 s |
| `source/u5.mov` | Team huddle from behind | 4.4 s |
| `source/summer_cefcu.mp4` | More CEFCU Arena workout footage | 53.2 s |
| `source/gamewinner_wake_forest.mp4` | NIT game-winner vs Wake Forest | 23.5 s |

**Audio**

| file | what it is |
|---|---|
| `audio/voiceover.mp3` | Two-host podcast voiceover, 81.7 s |
| `audio/score.wav` | Original cinematic score, 109 s (`score.flac` = same, smaller) |

**Fonts** - both free from Google Fonts, install before building:
- **Anton** (Regular) - the end card headline
- **Oswald** (Medium / weight 500) - location titles and the year line

---

## 3. The look (apply to every video clip)

**Letterbox to 2.39:1 cinemascope.** The image band is **1920 x 803**,
centred, with solid black bars **138 px tall** at top and bottom. In CapCut:
scale each clip so its visible area fills 1920 x 803 and mask/crop the rest,
or place black bars on a track above.

**Framing.** Each clip is cropped to that 2.39:1 band. The `crop centre Y`
column in section 4 is where the band sits vertically in the source frame,
as a fraction of source height (0.42 = the band is centred 42% down). This
keeps the action framed and, on the drone shots, crops out the source video's
own burned-in building captions.

**Slow push-in.** Every clip scales from 100% to about **104.5%** across its
own duration - a slow, constant Ken Burns move. A couple of shots start at
102-103% instead of 100% (the `start zoom` column).

**Colour grade** (mild, filmic):
- Saturation: **-22%**
- Contrast: **+10%**, with blacks lifted slightly (do not crush)
- Highlights slightly warm, shadows slightly cool

**Grain:** very light film grain.
**Vignette:** subtle, about -20% at the corners.

**Transitions:** **0.40 s cross-dissolve** between clips, EXCEPT the two
marked `HARD CUT` in the table, which are straight cuts with no dissolve.

---

## 4. Timeline - video

Place clips in this order. `in`/`out` are positions on the sequence timeline;
`src in` is the in-point inside the source file; `speed` is the playback rate
(values below 1.0 are slow motion).

| # | in | out | dur | source | src in | speed | crop centre Y | start zoom | cut | shot |
|---|----|-----|-----|--------|--------|-------|---------------|-----------|-----|------|
| 0 | 0.00 | 5.50 | 5.50 | `source/drone_uptown_isu.mp4` | 8.50 | 1.00x | 0.42 | 1.00 | dissolve | Aerial over Uptown Normal rooftops |
| 1 | 5.50 | 10.50 | 5.00 | `source/drone_uptown_isu.mp4` | 29.50 | 1.00x | 0.42 | 1.00 | dissolve | Aerial straight down on the Uptown Circle |
| 2 | 10.50 | 16.20 | 5.70 | `source/drone_uptown_isu.mp4` | 95.50 | 1.00x | 0.42 | 1.00 | dissolve | Aerial across ISU campus |
| 3 | 16.20 | 20.50 | 4.30 | `source/drone_uptown_isu.mp4` | 116.80 | 1.00x | 0.42 | 1.00 | dissolve | Aerial over CEFCU Arena (the white dome) |
| 4 | 20.50 | 25.00 | 4.50 | `source/u4.mov` | 0.20 | 1.00x | 0.50 | 1.00 | dissolve | Inside CEFCU Arena - players on the empty floor |
| 5 | 25.00 | 29.00 | 4.00 | `source/summer_cefcu.mp4` | 0.30 | 1.00x | 0.38 | 1.03 | dissolve | Rim and ball close-up, empty arena |
| 6 | 29.00 | 33.00 | 4.00 | `source/u4.mov` | 16.50 | 1.00x | 0.46 | 1.00 | dissolve | Scrimmage, green vs red |
| 7 | 33.00 | 37.40 | 4.40 | `source/u4.mov` | 20.80 | 1.00x | 0.46 | 1.00 | dissolve | Shooting / finishing at the rim |
| 8 | 37.40 | 41.40 | 4.00 | `source/summer_cefcu.mp4` | 10.50 | 1.00x | 0.46 | 1.00 | dissolve | Full-court drill, empty red seats |
| 9 | 41.40 | 42.35 | 0.95 | `source/gamewinner_wake_forest.mp4` | 17.00 | 1.00x | 0.42 | 1.00 | HARD CUT | The ball in flight (game-winner) |
| 10 | 42.35 | 46.50 | 4.15 | `source/u2.mov` | 0.00 | 0.66x | 0.50 | 1.00 | HARD CUT | Bench erupts, arms up |
| 11 | 46.50 | 51.00 | 4.50 | `source/u1.mov` | 0.00 | 0.76x | 0.48 | 1.00 | dissolve | Team celebrating on court |
| 12 | 51.00 | 55.00 | 4.00 | `source/u1.mov` | 3.60 | 0.78x | 0.48 | 1.00 | dissolve | Applause on court, coaches |
| 13 | 55.00 | 58.60 | 3.60 | `source/u5.mov` | 0.00 | 0.78x | 0.52 | 1.00 | dissolve | Huddle from behind, #12 and #14 |
| 14 | 58.60 | 62.10 | 3.50 | `source/u1.mov` | 6.90 | 0.78x | 0.48 | 1.00 | dissolve | Players celebrating - #10, #11, #3 |
| 15 | 62.10 | 63.90 | 1.80 | `source/u3.mov` | 0.86 | 0.36x | 0.50 | 1.00 | dissolve | Locker room, players embracing |
| 16 | 63.90 | 69.00 | 5.10 | `source/u5.mov` | 1.40 | 0.46x | 0.52 | 1.00 | dissolve | Huddle, arms around each other |
| 17 | 69.00 | 73.50 | 4.50 | `source/u4.mov` | 4.80 | 1.00x | 0.50 | 1.00 | dissolve | Workout on the CEFCU floor |
| 18 | 73.50 | 77.50 | 4.00 | `source/u4.mov` | 25.50 | 1.00x | 0.48 | 1.00 | dissolve | Scrimmage action |
| 19 | 77.50 | 81.50 | 4.00 | `source/u4.mov` | 29.80 | 1.00x | 0.46 | 1.00 | dissolve | Team gathering at centre court |
| 20 | 81.50 | 86.20 | 4.70 | `source/summer_cefcu.mp4` | 26.50 | 1.00x | 0.46 | 1.00 | dissolve | Ball handling close-up |
| 21 | 86.20 | 89.80 | 3.60 | `source/u2.mov` | 0.60 | 0.60x | 0.50 | 1.00 | dissolve | Bench celebration |
| 22 | 89.80 | 95.50 | 5.70 | `source/u1.mov` | 0.00 | 0.68x | 0.48 | 1.00 | dissolve | Court celebration, applause |
| 23 | 95.50 | 100.00 | 4.50 | `source/u4.mov` | 13.80 | 1.00x | 0.48 | 1.00 | dissolve | Workout, ball in hands |
| 24 | 100.00 | 104.00 | 4.00 | `source/u5.mov` | 0.20 | 0.85x | 0.52 | 1.00 | dissolve | Huddle, closing shot |

Shot 9 into shot 10 is the key moment: the ball is in flight, then it cuts on
the beat to the bench erupting at **42.35 s**. Keep that cut frame-exact - the
voiceover says "Kinziger" and the score lands an impact at the same instant.

Video ends at **104.00 s**; the end card runs 104.00 - 109.00 s.

---

## 5. Timeline - audio

**Voiceover** - `audio/voiceover.mp3`
- Place its start at **4.50 s** on the timeline (silence before that)
- Runs to about 86.2 s
- Gain: **+1.5 dB**

**Score** - `audio/score.wav`
- Place its start at **0.00 s**, full length to 109 s
- **Duck it under the voiceover**: whenever the VO is speaking, drop the score
  by about **-8 dB** (roughly 62% down), with a ~0.35 s release so it breathes
  back up between lines. If CapCut has auto-ducking, enable it against the VO
  track; otherwise use volume keyframes.
- The score is already built to the edit: it swells into the game-winner at
  42.35 s, pulls back for the reflective section, then builds again from 56 s
  and resolves under the end card.

No other sound effects. No music from the source clips - **mute all video
clips' audio.**

---

## 6. Titles

Three text elements only. Keep them sparse - this is the reference style.

**A. "NORMAL, ILLINOIS"**
- Font: Oswald Medium (weight 500), **34 px**, letter-spacing **+7 px**
- Colour: near-white `#EEEEF0`, with a soft black drop shadow offset 2 px
- Position: **lower left** of the image band - x = 92 px from the left edge,
  baseline y = **849 px** from the top of the 1080 frame
- Timing: fades in at **2.20 s**, out by **7.00 s** (0.8 s fades)

**B. "CEFCU ARENA"**
- Identical styling and position to A
- Timing: **16.80 s** to **20.20 s** (0.8 s fades)

**C. End card** - black background `#050506`, 104.00 - 109.00 s
- Line 1: **"ILLINOIS STATE"** - Anton Regular, **96 px**, colour `#F0F0F2`,
  centred horizontally, sitting just above centre (baseline around y = 444).
  Fades in over 0.8 s from 104.00 s.
- Line 2: **"2026 — 27"** - Oswald Medium, **40 px**, letter-spacing **+12 px**,
  colour Redbird red `#C42A3A`, centred, about 130 px below line 1
  (around y = 580). Fades in from **104.70 s**.
- Whole card fades to black over the final 1.6 s.

---

## 7. Export

- 1920 x 1080, 30 fps, H.264, high bitrate (40-50 Mbps or CapCut's highest)
- Audio: AAC 192 kbps or better
- Export **once** - the source clips are untouched originals, so this is the
  only re-encode in the chain.

---

## 8. If you are driving the CapCut MCP server

The tool sequence maps directly onto the tables above:

1. `capcut_create_draft` - 1920x1080, 30 fps
2. For each row in section 4: `capcut_add_video` with the source path,
   `src in` as the start, the duration, the speed, and the crop/scale for the
   2.39:1 band at that `crop centre Y`
3. `capcut_add_audio` twice - voiceover at 4.50 s, score at 0.00 s
4. `capcut_add_text` three times per section 6
5. `capcut_add_keyframe` for the push-in on each clip and for the score ducking
6. `capcut_save_draft`

Use `capcut_get_duration` on each source first to confirm the in-points land
where this document says they do.

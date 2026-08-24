# Redbirds documentary - cut sheet

Timeline is 1920x1080, 30fps, 109s total.

## Audio (lay both at 0:00, full length)

- `audio/voiceover.mp3` - two-host VO, starts at 4.5s of its own
  file's timeline; place at 0:00 and it lines up.
- `audio/score.wav` - the score, already ducked-free (mix it under
  the VO to taste; the delivered MP4 ducks it ~62% under speech).

## Video

Drop clips in filename order. Each is already trimmed and speed-
adjusted, so no retiming is needed.

| # | clip | in | out | dur | speed | source | src in |
|---|------|----|-----|-----|-------|--------|--------|
| 0 | `clips/00_drone.mp4` | 0.00 | 5.50 | 5.50 | 1.00x | `build/aerial/drone.mp4` | 8.50 |
| 1 | `clips/01_drone.mp4` | 5.50 | 10.50 | 5.00 | 1.00x | `build/aerial/drone.mp4` | 29.50 |
| 2 | `clips/02_drone.mp4` | 10.50 | 16.20 | 5.70 | 1.00x | `build/aerial/drone.mp4` | 95.50 |
| 3 | `clips/03_drone.mp4` | 16.20 | 20.50 | 4.30 | 1.00x | `build/aerial/drone.mp4` | 116.80 |
| 4 | `clips/04_cefcu_workout.mp4` | 20.50 | 25.00 | 4.50 | 1.00x | `build/user/u4.mov` | 0.20 |
| 5 | `clips/05_summer_cefcu.mp4` | 25.00 | 29.00 | 4.00 | 1.00x | `build/tt/7652790943145299230.mp4` | 0.30 |
| 6 | `clips/06_cefcu_workout.mp4` | 29.00 | 33.00 | 4.00 | 1.00x | `build/user/u4.mov` | 16.50 |
| 7 | `clips/07_cefcu_workout.mp4` | 33.00 | 37.40 | 4.40 | 1.00x | `build/user/u4.mov` | 20.80 |
| 8 | `clips/08_summer_cefcu.mp4` | 37.40 | 41.40 | 4.00 | 1.00x | `build/tt/7652790943145299230.mp4` | 10.50 |
| 9 | `clips/09_gamewinner_ball.mp4` | 41.40 | 42.35 | 0.95 | 1.00x | `build/clips/48282239.mp4` | 17.00 |
| 10 | `clips/10_bench_eruption.mp4` | 42.35 | 46.50 | 4.15 | 0.66x | `build/user/u2.mov` | 0.00 |
| 11 | `clips/11_celebration_court.mp4` | 46.50 | 51.00 | 4.50 | 0.76x | `build/user/u1.mov` | 0.00 |
| 12 | `clips/12_celebration_court.mp4` | 51.00 | 55.00 | 4.00 | 0.78x | `build/user/u1.mov` | 3.60 |
| 13 | `clips/13_huddle.mp4` | 55.00 | 58.60 | 3.60 | 0.78x | `build/user/u5.mov` | 0.00 |
| 14 | `clips/14_celebration_court.mp4` | 58.60 | 62.10 | 3.50 | 0.78x | `build/user/u1.mov` | 6.90 |
| 15 | `clips/15_handshake_lockerroom.mp4` | 62.10 | 63.90 | 1.80 | 0.36x | `build/user/u3.mov` | 0.86 |
| 16 | `clips/16_huddle.mp4` | 63.90 | 69.00 | 5.10 | 0.46x | `build/user/u5.mov` | 1.40 |
| 17 | `clips/17_cefcu_workout.mp4` | 69.00 | 73.50 | 4.50 | 1.00x | `build/user/u4.mov` | 4.80 |
| 18 | `clips/18_cefcu_workout.mp4` | 73.50 | 77.50 | 4.00 | 1.00x | `build/user/u4.mov` | 25.50 |
| 19 | `clips/19_cefcu_workout.mp4` | 77.50 | 81.50 | 4.00 | 1.00x | `build/user/u4.mov` | 29.80 |
| 20 | `clips/20_summer_cefcu.mp4` | 81.50 | 86.20 | 4.70 | 1.00x | `build/tt/7652790943145299230.mp4` | 26.50 |
| 21 | `clips/21_bench_eruption.mp4` | 86.20 | 89.80 | 3.60 | 0.60x | `build/user/u2.mov` | 0.60 |
| 22 | `clips/22_celebration_court.mp4` | 89.80 | 95.50 | 5.70 | 0.68x | `build/user/u1.mov` | 0.00 |
| 23 | `clips/23_cefcu_workout.mp4` | 95.50 | 100.00 | 4.50 | 1.00x | `build/user/u4.mov` | 13.80 |
| 24 | `clips/24_huddle.mp4` | 100.00 | 104.00 | 4.00 | 0.85x | `build/user/u5.mov` | 0.20 |

## Look

The delivered MP4 crops each shot to a 2.39:1 letterbox band centred at the
`crop_center_y` fraction in `cuts.csv`, then applies a filmic grade (slight
desaturation, lifted blacks, warm highlights) plus grain and a vignette.
These clips are exported FULL FRAME and ungraded so you can reframe freely.

## Titles

- "NORMAL, ILLINOIS" - lower left, 2.2s to 7.0s
- "CEFCU ARENA" - lower left, 16.8s to 20.2s
- End card "ILLINOIS STATE" / "2026 - 27" - 104s to 109s

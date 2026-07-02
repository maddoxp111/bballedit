# Illinois State Basketball — "IS BACK" Edit (2026–27)

A 60-second vertical (1080×1920, 30fps) hype edit for Illinois State men's
basketball, beat-synced to "40 Nights". Theme: **Illinois State basketball is
back** — spotlighting the returning core (Mason Klabo, Chase Walker, Johnny
Kinziger) then running through the rest of the official 2026–27 roster.

Roster source: [goredbirds.com 2026-27 men's basketball roster](https://goredbirds.com/sports/mens-basketball/roster)
— current players only, nobody who left.

## Structure (beat-mapped at ~92 BPM)

| Beats | Section |
|---|---|
| 0–8 | Cold open — flickering intro lines |
| 8–16 | "ILLINOIS STATE BASKETBALL" word slams → "IS BACK." |
| 16–20 | "IS BACK" hold with beat pulse |
| 20–44 | Returning-player spotlights: #3 Klabo, #35 Walker, #11 Kinziger |
| 44–46 | "AND THE NEST IS LOADED" transition |
| 46–68 | Rapid-fire roster: the other 11 Redbirds, 2 beats each |
| 68–72 | Head coach Ryan Pedon |
| 72–80 | 2026 / 2027 year slam |
| 80–end | Finale hold + fade out |

## Build

```bash
pip install numpy pillow imageio-ffmpeg
python3 analyze_audio.py   # BPM + beat grid + best 60s audio window -> build/analysis.json
python3 render_edit.py     # renders illinois_state_is_back.mp4
```

`analyze_audio.py` picks the loudest 60s stretch of the song (spectral-flux
onset envelope + autocorrelation tempo estimate) so the edit rides the drop.
`render_edit.py` draws every frame with Pillow (Anton/Oswald type, Redbird red
`#CE1126`), applies beat-synced zoom pulse, shake, RGB-split glitch, flash,
grain and vignette, pipes raw frames to ffmpeg, and muxes the audio window
with a fade-out.

# Running this locally (and wiring CapCut to Claude)

This repo builds the edits headlessly with Python + ffmpeg. Run it on your own
machine and two things get better at once: local MCP servers (CapCut) become
reachable, and the pipeline reads your original media instead of round-tripping
through uploads, which is where quality was being lost.

## 1. Get the code and media

```bash
git clone <this repo>
cd bballedit
pip install numpy pillow imageio-ffmpeg yt-dlp opencv-python-headless ultralytics
```

`build/` is gitignored, so the working media does not come with a clone. The
pieces that cannot be re-fetched are checked in under `media_seed/`:

```bash
mkdir -p build/user build/aerial
cp media_seed/u*.mov  build/user/       # your five clips
cp media_seed/drone.mp4 build/aerial/   # Uptown Normal / ISU aerial
```

Everything else is reproducible — and downloads work far better from a home IP
than from this container, which YouTube rate-limited:

```bash
python3 doc_score.py        # regenerates the score
ELEVENLABS_API_KEY=... python3 make_vo.py   # regenerates the two-host voiceover
                            # (or use the committed assets/audio/vo_two_host.mp3)
```

ESPN and TikTok b-roll: the clip IDs are listed in `mm_build.py` and
`doc_trailer.py`; `yt-dlp` pulls them into `build/clips/` and `build/tt/`.

## 2. Build the trailer

```bash
python3 doc_trailer.py validate   # confirms no shot outruns its source
python3 doc_trailer.py extract    # pulls frames for every shot
python3 doc_trailer.py            # renders redbirds_documentary.mp4
```

`SHOTS` at the top of `doc_trailer.py` is the entire edit: one row per shot,
`(start, end, source, source_start, speed, vertical_center, zoom, hard_cut)`.

## 3. Wire up CapCut

The CapCut MCP server (github.com/Atx-Guy/capcut-mcp-server) needs the
VectCutAPI backend on `http://localhost:9001`. Both must run on the machine
where CapCut is installed — that is why this only works locally.

Point the CapCut tools at the ORIGINAL files (`build/user/*.mov`,
`build/aerial/drone.mp4`, `build/clips/*.mp4`) rather than at a rendered MP4.
CapCut then trims and speeds non-destructively, and nothing is re-encoded until
you export once at the end.

`doc_trailer.py`'s `SHOTS` table maps directly onto `capcut_add_video` calls:
each row already carries the source path, in-point, speed and duration.

## Why this avoids the quality loss

The headless pipeline decodes to JPEG frames and re-encodes to H.264 — a real
generational hit, plus a second one when compressing to fit a chat upload. A
CapCut draft referencing the untouched sources skips both: full quality until a
single final export.

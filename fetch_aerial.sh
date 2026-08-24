#!/bin/bash
# Patiently retry the aerial downloads: YouTube rate-limits bursts, so make
# one attempt per target per pass and wait between passes.
cd /home/user/bballedit/build/aerial || exit 1
IDS="jHdI3CPl9rs ZJncedcdrUI qI2Ar-w8KJ8 38lnXfCXdl8 kYOTLaricbE SUejhVOkZ5I"
for pass in $(seq 1 14); do
  need=0
  for id in $IDS; do
    [ -s "$id.mp4" ] && continue
    need=1
    timeout 300 yt-dlp -q --extractor-args "youtube:player_client=android" \
      -f "b[height<=720][ext=mp4]/b[height<=720]/b" -o "$id.mp4" \
      "https://www.youtube.com/watch?v=$id" >/dev/null 2>&1
    if [ -s "$id.mp4" ]; then echo "pass $pass: GOT $id"; else rm -f "$id.mp4"; fi
    sleep 20
  done
  [ "$need" = "0" ] && break
  echo "pass $pass done; have: $(ls *.mp4 2>/dev/null | wc -l)"
  sleep 150
done
echo "FETCH_COMPLETE have $(ls *.mp4 2>/dev/null | wc -l)"

"""Generate the two-host podcast voiceover with ElevenLabs -> build/vo_full.mp3.

Reads the dialogue from vo_script.json and the API key from the
ELEVENLABS_API_KEY environment variable (never stored in the repo):

    ELEVENLABS_API_KEY=... python3 make_vo.py

Uses the text-to-dialogue endpoint so the two speakers trade lines with
natural turn-taking; the fillers ("uh", "um", trailing "...") are written
into the script itself rather than added as tags.
"""
import json
import os
import subprocess
import sys

API = "https://api.elevenlabs.io/v1/text-to-dialogue"
key = os.environ.get("ELEVENLABS_API_KEY")
if not key:
    sys.exit("set ELEVENLABS_API_KEY")

d = json.load(open("vo_script.json"))
voices = d["voices"]
payload = {
    "inputs": [{"text": text, "voice_id": voices[spk]} for spk, text in d["lines"]],
    "model_id": "eleven_v3",
    "settings": {"stability": 0.4, "use_speaker_boost": True},
}
open("build/_vo_payload.json", "w").write(json.dumps(payload))
subprocess.run([
    "curl", "-sS", "-X", "POST", API,
    "-H", f"xi-api-key: {key}",
    "-H", "Content-Type: application/json",
    "-d", "@build/_vo_payload.json",
    "-o", "build/vo_full.mp3",
], check=True)
os.remove("build/_vo_payload.json")
size = os.path.getsize("build/vo_full.mp3")
if size < 20000:
    sys.exit(f"generation failed: {open('build/vo_full.mp3').read()[:300]}")
print(f"wrote build/vo_full.mp3 ({size/1024:.0f} KB, {len(payload['inputs'])} lines)")

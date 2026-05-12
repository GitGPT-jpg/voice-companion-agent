import requests, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

KEY = os.getenv("ELEVENLABS_API_KEY")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
TEXT = "嗯…我在呢。别想太多，慢慢来，有我陪着你。"

# vbf1 当前声音
vid = os.getenv("ELEVENLABS_VOICE_ID", "")
print(f"当前 vbf1 ({vid}) ...")
r = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
    headers={"xi-api-key": KEY, "Content-Type": "application/json"},
    json={
        "text": TEXT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    },
)
if r.status_code == 200:
    path = os.path.join(OUT, "eleven_vbf1_当前.mp3")
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"  OK -> {path}")
else:
    print(f"  FAIL {r.status_code}: {r.text[:200]}")

# Bill 温柔设置 (低 stability = 更有感情)
print("Bill 温柔版 (stability=0.35) ...")
bill_id = "pqHfZKP75CvOlQylNhV4"
r = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{bill_id}",
    headers={"xi-api-key": KEY, "Content-Type": "application/json"},
    json={
        "text": TEXT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.35, "similarity_boost": 0.7},
    },
)
if r.status_code == 200:
    path = os.path.join(OUT, "eleven_Bill_温柔版.mp3")
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"  OK -> {path}")
else:
    print(f"  FAIL {r.status_code}: {r.text[:200]}")

print("Done")

import requests, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

KEY = os.getenv("ELEVENLABS_API_KEY")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
os.makedirs(OUT, exist_ok=True)

TEXT = "嗯…我在呢。别想太多，慢慢来，有我陪着你。"

# 先获取 voice 列表，打印原始 ID
r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": KEY})
data = r.json()

print("=== 所有可用 voices ===")
male_voices = []
for v in data.get("voices", []):
    vid = v["voice_id"].strip()
    name = v["name"]
    labels = v.get("labels", {})
    gender = labels.get("gender", "?")
    print(f"  [{len(vid)}] '{vid}' -> {name} ({gender})")
    
    # 收集男声
    if gender == "male":
        male_voices.append((vid, name))

print(f"\n=== 生成 {len(male_voices)} 个男声样本 ===")
for vid, name in male_voices:
    path = os.path.join(OUT, f"eleven_{name.replace(' ','_')}.mp3")
    print(f"  {name} ({vid}) ...")
    r2 = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
        json={
            "text": TEXT,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
    )
    if r2.status_code == 200:
        with open(path, "wb") as f:
            f.write(r2.content)
        print(f"    OK -> {path}")
    else:
        print(f"    FAIL {r2.status_code}: {r2.text[:200]}")
print("Done")

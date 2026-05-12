import requests, json, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
KEY = os.getenv("ELEVENLABS_API_KEY")

# 1. 已添加的 voices
print("=" * 60)
print("你的 ElevenLabs 已添加 voices")
print("=" * 60)
r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": KEY})
for v in r.json().get("voices", []):
    labels = v.get("labels", {})
    print(f"  {v['name']:35s} {v['voice_id']:20s} gender={labels.get('gender','?')} age={labels.get('age','?')}")

# 2. 搜索 Library 里的温柔男声（中文）
print("\n" + "=" * 60)
print("ElevenLabs Voice Library 搜索 'gentle male'")
print("=" * 60)
for search in ["gentle", "soft", "warm", "calm", "boyfriend"]:
    r2 = requests.get(
        f"https://api.elevenlabs.io/v1/voices?search={search}&page_size=20",
        headers={"xi-api-key": KEY}
    )
    for v in r2.json().get("voices", []):
        labels = v.get("labels", {})
        gender = labels.get("gender", "?")
        if gender == "male" or gender == "?":
            preview = v.get("preview_url", "")
            print(f"  [{search}] {v['name']:30s} {v['voice_id'][:20]} gender={gender} age={labels.get('age','?')} desc={labels.get('description','')[:60]}")
            if preview:
                print(f"          preview: {preview}")

"""测试 ElevenLabs 经典 premade voices — 温柔男声"""
import requests, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
KEY = os.getenv("ELEVENLABS_API_KEY")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
os.makedirs(OUT, exist_ok=True)

TEXT = "嗯…我在呢。别想太多，慢慢来，有我陪着你。"

# ElevenLabs 公开 premade voices — 社区广为人知的 ID
# 这些是贴在 ElevenLabs 文档和社区里的标准 voices
PREMIUM_MALE = {
    # 经典 premade（所有账号都有）
    "Adam":    "pNInz6obpgDQGcFmaJgB",    # 深沉/磁性
    "Antoni":  "ErXwobaYiN3P2qO7ZVNo",    # 温暖（如果可用）
    "Arnold":  "VR6AewLTigWG4xSOukaG",    # 成熟
    # 其他可能
    "Josh":    "TxGEqnHWrfWFTfGW9XjX",    # 年轻男声
    "Sam":     "yoZ06aMxZJJ28mfd3POQ",    # 中性偏男
    
    # 你自己已有的
    "Daniel":  "onwK4e9ZLuTAzcXQwTjL",    # 播音员
    "Bill":    "pqHfZKP75CvOlQylNhV4",    # 成熟睿智
}

for name, vid in PREMIUM_MALE.items():
    path = os.path.join(OUT, f"premade_{name}.mp3")
    print(f"{name:10s} ({vid[:16]}...) ...", end=" ")
    
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
        json={
            "text": TEXT,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
        },
    )
    
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"OK -> {path}")
    else:
        print(f"FAIL {r.status_code}")

print("\nDone — 去 tts_cache/ 里听 premade_*.mp3")

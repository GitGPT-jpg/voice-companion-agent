"""用 ElevenLabs Voice Design 生成温柔男声预览"""
import requests, os, json, time
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
KEY = os.getenv("ELEVENLABS_API_KEY")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
os.makedirs(OUT, exist_ok=True)

# Voice Design — 描述我们想要的温柔男声
# 生成 3 个不同的变体
designs = [
    {
        "name": "gentle_boyfriend_1",
        "text": "嗯…我在呢。别想太多，慢慢来，有我陪着你。",
        "voice_description": "A gentle, soft-spoken young Chinese male voice. Warm, tender, caring boyfriend tone. Speaks slowly with emotional depth. Comforting and soothing, like talking to someone you love before sleep."
    },
    {
        "name": "gentle_boyfriend_2", 
        "text": "傻瓜…别急，我哪也不去。",
        "voice_description": "A warm, intimate male voice, mid-20s. Smooth and tender, like a caring partner whispering. Chinese speaker with a gentle, protective tone. Very natural and human-like."
    },
    {
        "name": "gentle_boyfriend_3",
        "text": "有我陪着你呢…闭上眼睛，慢慢呼吸。",
        "voice_description": "A soft, deep but gentle male voice. Late 20s. Soothing ASMR quality. Speaks Chinese with warmth and tenderness. Perfect for comforting and bedtime conversations."
    },
]

print("ElevenLabs Voice Design - 温柔男声生成\n")

for d in designs:
    print(f"设计: {d['name']}")
    print(f"描述: {d['voice_description'][:80]}...")
    
    # 生成预览
    r = requests.post(
        "https://api.elevenlabs.io/v1/text-to-voice/create-previews",
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
        json={
            "voice_description": d["voice_description"],
            "text": d["text"],
        }
    )
    
    if r.status_code == 200:
        previews = r.json().get("previews", [])
        print(f"  生成 {len(previews)} 个预览")
        for i, p in enumerate(previews):
            audio_url = p.get("generated_audio_url") or p.get("audio_base_64")
            if audio_url and audio_url.startswith("http"):
                # 下载预览音频
                ar = requests.get(audio_url)
                if ar.status_code == 200:
                    fname = f"design_{d['name']}_v{i+1}.mp3"
                    fpath = os.path.join(OUT, fname)
                    with open(fpath, "wb") as f:
                        f.write(ar.content)
                    print(f"    variant {i+1}: {fpath}")
    elif r.status_code == 422:
        print(f"  X Validation error: {r.text[:300]}")
    else:
        print(f"  X HTTP {r.status_code}: {r.text[:300]}")
    
    time.sleep(1)

# 额外：尝试获取更多 premade voices
print("\n\n=== 获取更多 premade 声音 ===")
r = requests.get("https://api.elevenlabs.io/v1/voices?show_legacy=true", 
                  headers={"xi-api-key": KEY})
data = r.json()
male = [v for v in data.get("voices", []) 
        if v.get("labels", {}).get("gender") == "male"]
print(f"可用男声: {len(male)} 个")
for v in male:
    print(f"  {v['name']:30s} {v['voice_id'][:20]}  age={v.get('labels',{}).get('age','?')}  desc={v.get('labels',{}).get('description','')[:50]}")
    if v.get('preview_url'):
        print(f"    preview: {v['preview_url']}")

print("\nDone!")

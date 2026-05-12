import requests, os, json, time
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
KEY = os.getenv("ELEVENLABS_API_KEY")

# 尝试访问 ElevenLabs Voice Library 公开 API
# 已知的公开 voice library 搜索
base = "https://api.elevenlabs.io/v1"

# 尝试 shared-voices 端点
print("=== 尝试 /v1/shared-voices ===")
try:
    r = requests.get(f"{base}/shared-voices", headers={"xi-api-key": KEY},
                     params={"page_size": 50, "gender": "male", "language": "zh"})
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        for v in data.get("voices", []):
            print(f"  {v.get('name','?')} | {v.get('voice_id','?')[:20]}")
    else:
        print(r.text[:300])
except Exception as e:
    print(f"Error: {e}")

# 尝试 voice-library 端点  
print("\n=== 尝试 /v1/voice-library ===")
for endpoint in ["/v1/voice-library", "/v1/voices/library", "/v1/library"]:
    try:
        r = requests.get(f"{base}{endpoint}", headers={"xi-api-key": KEY},
                        params={"search": "gentle", "page_size": 10})
        print(f"{endpoint}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"{endpoint}: Error {e}")

# 尝试直接搜公开 library 
print("\n=== try: search with include_public=true ===")
r = requests.get(f"{base}/voices", headers={"xi-api-key": KEY},
                 params={"search": "gentle male soothing calm warm", "page_size": 50})
data = r.json()
voices = data.get("voices", [])
print(f"Total: {len(voices)} voices")

# 分类
male = [v for v in voices if v.get('labels',{}).get('gender')=='male']
unknown = [v for v in voices if v.get('labels',{}).get('gender') not in ('male','female')]

for v in male + unknown:
    l = v.get('labels',{})
    print(f"\n  {v['name']} ({v['voice_id']})")
    for k,v2 in l.items():
        print(f"    {k}: {v2}")
    if v.get('preview_url'):
        print(f"    preview: {v['preview_url']}")

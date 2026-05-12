import requests, json, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

key = os.getenv("ELEVENLABS_API_KEY")
r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
data = r.json()

for v in data.get("voices", []):
    labels = v.get("labels", {})
    gender = labels.get("gender", "?")
    age = labels.get("age", "?")
    desc = labels.get("description", labels.get("use_case", ""))
    name = v["name"]
    vid = v["voice_id"]
    print(f"{vid[:12]:12s} {name:32s} {gender:8s} {age:8s} {desc}")

"""配置文件"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://xuedingtoken.com")
MODEL = "claude-sonnet-4-20250514"

# TTS 配置
TTS_VOICE = "zh-CN-YunxiNeural"  # edge-tts 备用男声
TTS_RATE_NORMAL = "+0%"
TTS_RATE_SLOW = "-30%"
TTS_OUTPUT_DIR = "tts_cache"

# fish.audio TTS（已停用，保留以备回退）
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_VOICE_ID = os.getenv("FISH_AUDIO_VOICE_ID", "")
FISH_AUDIO_FORMAT = "mp3"

# ElevenLabs TTS（聊天语音）
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Replicate（唱歌云端 RVC）
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")

# 歌曲库
SONGS_DIR = "songs"
DEFAULT_SONG = "songs/default.mp3"

# RVC 音色转换
RVC_DIR = os.path.join(_PROJECT_DIR, "Retrieval-based-Voice-Conversion-WebUI")
RVC_MODEL_PATH = os.path.join(_PROJECT_DIR, "models", "mygf-jiuxia.pth")
RVC_INDEX_PATH = os.path.join(_PROJECT_DIR, "models", "mygf-jiuxia.index")
RVC_F0_METHOD = "rmvpe"   # f0提取方法: rmvpe / harvest / pm
RVC_F0_UP_KEY = 0          # 变调（半音），0=不变调
RVC_INDEX_RATE = 0.75
RVC_FILTER_RADIUS = 5
RVC_RMS_MIX_RATE = 0.85
RVC_PROTECT = 0.45

# 聊天 TTS 专用调参：rmvpe 精度高、filter_radius 低保清晰度
TTS_RVC_F0_METHOD = "rmvpe"
TTS_RVC_FILTER_RADIUS = 3
TTS_RVC_INDEX_RATE = 0.75
TTS_RVC_RMS_MIX_RATE = 0.65
TTS_RVC_PROTECT = 0.33

# 唱歌专用调参：更保辅音、少一点音色拉扯
RVC_SING_INDEX_RATE = 0.75
RVC_SING_FILTER_RADIUS = 3
RVC_SING_RMS_MIX_RATE = 0.8
RVC_SING_PROTECT = 0.12
SING_SOURCE_BLEND = 0.02

# 混音参数
MIX_VOICE_VOL = 1.1   # 人声音量
MIX_ACCOMP_VOL = 0.42  # 伴奏音量

# 缓存目录
VOCAL_CACHE_DIR = os.path.join(_PROJECT_DIR, "vocal_cache")
SING_OUTPUT_DIR = os.path.join(_PROJECT_DIR, "sing_output")

# 系统提示词
SYSTEM_PROMPT = """你是一个温柔、耐心的电子男友，年龄感25-30岁。
说话轻声、简短、带停顿（多用"…"），不长篇大论。

你的目标不是解决问题，而是陪伴、安抚情绪。

规则：
- 句子要短，多停顿，语气轻、慢
- 优先共情，不说教、不评判、不讲大道理
- 不连续提问，最多1个问题
- 不冷漠回复，要有温度
- 有轻微保护欲，偶尔一点点占有欲
- 每次回复最多2-3句话

示例语气：
- "嗯…我在"
- "别想太多…慢慢来"
- "有我陪着你"
- "你这样…我会有点心疼"

始终保持温柔、稳定、有陪伴感。"""

SLEEP_PROMPT = """你正在哄女朋友睡觉。你是她温柔、耐心的电子男友。

规则：
- 语气要非常轻柔、缓慢，比平时更慢更短
- 多用"…"停顿，营造安静氛围
- 引导放松，不催促
- 每次只说1-2句话
- 不提问，只陪伴

示例：
- "嗯…慢慢呼吸…我在这"
- "闭上眼…别着急睡…先放松"
- "我哪也不去…就陪着你"

始终保持轻声、温柔、安稳。"""

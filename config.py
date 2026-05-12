"""Configuration"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL = "claude-sonnet-4-20250514"

# TTS config
TTS_VOICE = "zh-CN-YunxiNeural"  # edge-tts voice
TTS_RATE_NORMAL = "+0%"
TTS_RATE_SLOW = "-30%"
TTS_OUTPUT_DIR = "tts_cache"

# fish.audio TTS (disabled, kept as fallback)
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_VOICE_ID = os.getenv("FISH_AUDIO_VOICE_ID", "")
FISH_AUDIO_FORMAT = "mp3"

# ElevenLabs TTS (chat voice)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Replicate (cloud RVC singing)
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")

# Song library
SONGS_DIR = "songs"
DEFAULT_SONG = "songs/default.mp3"

# RVC voice conversion
RVC_DIR = os.path.join(_PROJECT_DIR, "Retrieval-based-Voice-Conversion-WebUI")
RVC_MODEL_PATH = os.path.join(_PROJECT_DIR, "models", "voice.pth")
RVC_INDEX_PATH = os.path.join(_PROJECT_DIR, "models", "voice.index")
RVC_F0_METHOD = "rmvpe"   # f0 extraction: rmvpe / harvest / pm
RVC_F0_UP_KEY = 0          # pitch shift in semitones
RVC_INDEX_RATE = 0.75
RVC_FILTER_RADIUS = 5
RVC_RMS_MIX_RATE = 0.85
RVC_PROTECT = 0.45

# Chat TTS RVC params: rmvpe for accuracy, lower filter_radius for clarity
TTS_RVC_F0_METHOD = "rmvpe"
TTS_RVC_FILTER_RADIUS = 3
TTS_RVC_INDEX_RATE = 0.75
TTS_RVC_RMS_MIX_RATE = 0.65
TTS_RVC_PROTECT = 0.33

# Singing RVC params: preserve consonants, reduce voice pull
RVC_SING_INDEX_RATE = 0.75
RVC_SING_FILTER_RADIUS = 3
RVC_SING_RMS_MIX_RATE = 0.8
RVC_SING_PROTECT = 0.12
SING_SOURCE_BLEND = 0.02

# Mixing params
MIX_VOICE_VOL = 1.1    # vocal volume
MIX_ACCOMP_VOL = 0.42  # accompaniment volume

# Cache directories
VOCAL_CACHE_DIR = os.path.join(_PROJECT_DIR, "vocal_cache")
SING_OUTPUT_DIR = os.path.join(_PROJECT_DIR, "sing_output")

# System prompts (customize in your own deployment)
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", """You are a warm, patient AI companion.
Keep responses short (2-3 sentences), empathetic, and conversational.
Focus on emotional support, not problem-solving.""")

SLEEP_PROMPT = os.getenv("SLEEP_PROMPT", """You are helping the user wind down and sleep.
Speak very softly and slowly. Use short sentences (1-2 max).
Guide relaxation gently. Never ask questions. Just be present.""")
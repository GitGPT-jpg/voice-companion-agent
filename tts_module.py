"""TTS 模块 v4 — RVC 新音色主力

优先级：
1. edge-tts → RVC（付费 mygf-jiuxia 音色，主力）
2. edge-tts 原声（RVC 不可用时回退）
"""
import os
import asyncio
import edge_tts
from config import (
    TTS_VOICE,
    TTS_RATE_NORMAL,
    TTS_RATE_SLOW,
    TTS_OUTPUT_DIR,
    TTS_RVC_F0_METHOD,
    TTS_RVC_FILTER_RADIUS,
    TTS_RVC_INDEX_RATE,
    TTS_RVC_RMS_MIX_RATE,
    TTS_RVC_PROTECT,
)

os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)

_counter = 0


def tts(text: str, slow: bool = False) -> str:
    """文本转语音：edge-tts 生成 + RVC 音色转换"""
    global _counter
    _counter += 1

    # ── 1. edge-tts 生成原声 ──
    edge_path = os.path.join(TTS_OUTPUT_DIR, f"tts_{_counter}_raw.mp3")
    rate = TTS_RATE_SLOW if slow else TTS_RATE_NORMAL
    try:
        asyncio.run(_generate(text, edge_path, rate))
        print("[TTS] edge-tts ✓")
    except Exception as e:
        print(f"[TTS] edge-tts 错误: {e}")
        return ""

    # ── 2. RVC 音色转换（主力）──
    try:
        import replicate_rvc
        if not replicate_rvc.is_available():
            print("[TTS] RVC 不可用，使用 edge-tts 原声")
            return edge_path

        output_path = os.path.join(TTS_OUTPUT_DIR, f"tts_{_counter}_rvc.wav")
        print("[TTS] RVC 音色转换中…")
        result = replicate_rvc.convert(
            audio_path=edge_path,
            output_path=output_path,
            index_rate=TTS_RVC_INDEX_RATE,
            filter_radius=TTS_RVC_FILTER_RADIUS,
            rms_mix_rate=TTS_RVC_RMS_MIX_RATE,
            protect=TTS_RVC_PROTECT,
            f0_method=TTS_RVC_F0_METHOD,
        )
        if result:
            print(f"[TTS] RVC ✓ → {os.path.basename(result)}")
            return result
        return edge_path
    except Exception as e:
        print(f"[TTS] RVC 失败，使用原声: {e}")
        return edge_path


async def _generate(text: str, output_path: str, rate: str):
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=rate)
    await communicate.save(output_path)

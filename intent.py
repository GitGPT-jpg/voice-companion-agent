"""意图识别模块（混合版：LLM + 规则）

改进：优先使用 LLM 做语义判断，回退到关键词规则保证可靠性。
"""

import time
from typing import Optional

# 缓存 LLM 意图结果（短时间内同一用户不再重复调用 LLM）
_intent_cache: dict[str, tuple[float, str]] = {}
_CACHE_TTL_SEC = 30


def detect_intent(text: str) -> str:
    """识别用户意图：chat / sing / sleep / wake
    
    策略：先用关键词快速判断，明显的直接返回；
    模糊的走 LLM 语义判断（带缓存避免频繁调用）。
    """
    text_lower = text.strip().lower()

    # ── 快速规则（高置信度场景直接跳过 LLM）──
    sing_strong = ["唱首歌", "唱一个", "唱首", "唱支歌", "来一首", "唱来听听",
                   "sing a song", "sing me", "唱给我听", "唱首歌吧"]
    sleep_strong = ["晚安", "睡了", "先睡了", "困了", "好困", "我睡了", "哄我睡",
                    "哄我睡觉", "good night", "night night"]
    wake_strong = ["早安", "早上好", "起床了", "醒了", "不睡了"]

    if any(kw in text_lower for kw in sing_strong):
        return "sing"
    if any(kw in text_lower for kw in sleep_strong):
        return "sleep"
    if any(kw in text_lower for kw in wake_strong):
        return "wake"

    # ── 弱关键词：需要进一步判断 ──
    sing_weak = ["唱", "歌", "sing", "song", "听歌", "唱歌", "来段"]
    sleep_weak = ["睡", "困", "累", "sleep", "休息", "好累", "疲惫"]

    has_sing_weak = any(kw in text_lower for kw in sing_weak)
    has_sleep_weak = any(kw in text_lower for kw in sleep_weak)

    if not has_sing_weak and not has_sleep_weak:
        return "chat"  # 跟唱歌、睡眠都无关，直接走聊天

    # ── 模糊地带：用 LLM 判断 ──
    # 检查缓存
    cache_key = text_lower[:60]
    if cache_key in _intent_cache:
        cached_ts, cached_result = _intent_cache[cache_key]
        if time.time() - cached_ts < _CACHE_TTL_SEC:
            return cached_result

    # LLM 分类
    result = _llm_classify(text)
    _intent_cache[cache_key] = (time.time(), result)
    return result


def _llm_classify(text: str) -> str:
    """用 LLM 做意图分类（轻量调用）"""
    try:
        import anthropic
        from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL

        client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
        )
        response = client.messages.create(
            model=MODEL,
            max_tokens=10,
            system="你是一个意图分类器。只输出一个词：chat、sing、sleep 或 wake。不要输出任何其他内容。",
            messages=[{
                "role": "user",
                "content": (
                    "分类规则：\n"
                    "- sing：用户想听唱歌（包括想听某首歌、让唱一个、提到唱歌）\n"
                    "- sleep：用户想被哄睡、说晚安、说困了累了\n"
                    "- wake：用户刚醒、说早安、说起来了\n"
                    "- chat：以上都不是，就是普通聊天\n\n"
                    f"用户说：「{text}」\n"
                    "意图："
                )
            }],
        )
        result = response.content[0].text.strip().lower()
        # 归一化
        if result in ("sing", "sleep", "wake", "chat"):
            return result
        return "chat"
    except Exception as e:
        print(f"[意图 LLM 错误，回退规则] {e}")
        return _rule_fallback(text)


def _rule_fallback(text: str) -> str:
    """纯规则回退（LLM 不可用时）"""
    t = text.lower()
    if any(kw in t for kw in ["唱", "歌", "sing", "song", "听歌"]):
        return "sing"
    if any(kw in t for kw in ["睡", "困", "累", "sleep", "晚安", "休息"]):
        return "sleep"
    if any(kw in t for kw in ["醒了", "早安", "起床", "不睡", "早上好"]):
        return "wake"
    return "chat"

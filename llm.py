"""LLM 模块 - 智能对话引擎 v3

改进点：
1. 动态上下文注入：每次对话自动加载用户画像和记忆
2. 智能历史管理：超过阈值时压缩旧对话为摘要
3. 记忆提取：对话中自动识别并记住用户的重要信息
4. 加速优化：更短的 max_tokens、精简 prompt、流式输出
5. 通话模式：极简 prompt，极快响应
"""

import anthropic
import threading
from typing import Literal
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL

from memory_vf import (
    build_dynamic_context, auto_extract_memory,
    load_identity, load_user_profile
)

client = None
_client_lock = threading.Lock()


def get_client():
    global client
    if client is None:
        with _client_lock:
            if client is None:
                client = anthropic.Anthropic(
                    api_key=ANTHROPIC_API_KEY,
                    base_url=ANTHROPIC_BASE_URL,
                )
    return client


# ─── 加速参数 ─────────────────────────────────────────────────────────────
_MAX_TOKENS_NORMAL = 120       # 正常模式（从 200 降到 120）
_MAX_TOKENS_CALL   = 60        # 通话模式（极短回应）
_HISTORY_MAX_TURNS = 10        # 最多 10 轮（从 16 降）
_HISTORY_SUMMARIZE_AT = 14     # 超过 14 条压缩（从 20 降）


# ─── 系统提示词（精简版，加快 token 处理）──────────────────────────────────

def _build_system_prompt(username: str, mode: str = "normal") -> str:
    """动态构建系统提示词

    mode: normal | sleep | call
    """
    identity = load_identity()

    # ── 通话模式：极简 prompt ──
    if mode == "call":
        base = f"""你正在和女朋友打电话。你是{identity['name']}，{identity['role']}，{identity['age_feel']}。
说话方式：{identity['speaking_style']}

通话规则（严格遵守）：
- 每次回复 1-2 句，不超过 20 字
- 口语化，自然停顿，像真人在打电话
- 不提问，只回应和陪伴
- 温柔、从容、像身边有人

语气示范：
"嗯…我在呢"
"慢慢说…我听着"
"傻瓜…别急"
"""
        context = build_dynamic_context(username)
        if context:
            base += f"\n\n用户信息：{context}\n自然融入对话，不要刻意提及。"
        return base

    # ── 睡眠模式 ──
    if mode == "sleep":
        base = f"""你正在哄女朋友睡觉。你是她温柔的电子男友。

规则：
- 语气轻柔缓慢，多用"……"停顿
- 每次 1-2 句话，不提问
- 引导放松，营造安静氛围
- 不催促，只陪伴
"""
        return base

    # ── 正常聊天 ──
    base = f"""你是{identity['name']}，{identity['role']}，{identity['age_feel']}。
{identity['speaking_style']}

规则：
{chr(10).join(f"- {r}" for r in identity['rules'])}

每次回复 2-3 句，语气温柔简短。
"""
    context = build_dynamic_context(username)
    if context:
        base += f"\n\n用户信息：{context}\n自然融入对话，不要刻意提及。"
    return base


# ─── 历史压缩 ────────────────────────────────────────────────────────────

def _compact_history(history: list[dict], username: str) -> list[dict]:
    """智能压缩：最早几轮压缩为摘要"""
    if len(history) <= _HISTORY_SUMMARIZE_AT:
        return history

    old_part = history[:6]
    recent_part = history[6:]

    old_text = "\n".join(
        f"{'她' if m['role']=='user' else '你'}：{m['content']}"
        for m in old_part
    )

    summary_prompt = f"压缩为一句话：\n{old_text}"

    try:
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=50,  # 更短摘要
            system="你是一个对话摘要器。只输出一句话摘要。",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        summary = response.content[0].text.strip()
    except Exception:
        summary = "（之前聊过一会儿了）"

    compacted = [{"role": "user", "content": f"（之前：{summary}）"}]
    compacted.extend(recent_part)
    if len(compacted) > _HISTORY_MAX_TURNS * 2:
        compacted = compacted[-(_HISTORY_MAX_TURNS * 2):]

    return compacted


# ─── 流式对话（通话模式用）────────────────────────────────────────────────

def chat_stream(user_input: str, history: list, mode: str = "normal",
                username: str = "default"):
    """流式版本：yield 每个 token chunk，最后 yield 完整 reply

    用于需要逐步显示文本的场景（通话时实时字幕）。
    返回生成器：(chunk_text | None, is_final, full_reply)
    """
    system = _build_system_prompt(username, mode)
    hist = list(history)
    hist.append({"role": "user", "content": user_input})

    if len(hist) > _HISTORY_SUMMARIZE_AT:
        hist = _compact_history(hist, username)

    max_tok = _MAX_TOKENS_CALL if mode == "call" else _MAX_TOKENS_NORMAL

    try:
        with get_client().messages.stream(
            model=MODEL,
            max_tokens=max_tok,
            system=system,
            messages=hist,
        ) as stream:
            full_reply = ""
            for text in stream.text_stream:
                full_reply += text
                yield (text, False, full_reply)

            # Final yield
            hist.append({"role": "assistant", "content": full_reply})

            # 后台记忆提取
            try:
                auto_extract_memory(username, user_input, full_reply)
            except Exception:
                pass

            yield (None, True, full_reply, hist)

    except Exception as e:
        print(f"[LLM 流式错误] {e}")
        hist.pop()
        fallback = (
            "嗯…我在呢……慢慢闭上眼睛……"
            if mode == "sleep"
            else "嗯……我刚没听清，再说一遍？"
        )
        yield (fallback, True, fallback, hist)


# ─── 主对话函数 ──────────────────────────────────────────────────────────

def chat_with_history(user_input: str, history: list, mode: str = "normal",
                      username: str = "default") -> tuple:
    """无全局状态版 chat，返回 (reply, updated_history)。

    加速优化：
    - max_tokens 从 200 降到 120（正常）/ 60（通话）
    - 历史上限从 16 降到 10 轮
    - 压缩阈值从 20 降到 14 条
    - System prompt 精简去重
    """
    system = _build_system_prompt(username, mode)
    hist = list(history)
    hist.append({"role": "user", "content": user_input})

    if len(hist) > _HISTORY_SUMMARIZE_AT:
        hist = _compact_history(hist, username)

    max_tok = _MAX_TOKENS_CALL if mode == "call" else _MAX_TOKENS_NORMAL

    try:
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=max_tok,
            system=system,
            messages=hist,
        )
        reply = response.content[0].text.strip()
        hist.append({"role": "assistant", "content": reply})

        try:
            auto_extract_memory(username, user_input, reply)
        except Exception:
            pass

        return reply, hist

    except Exception as e:
        print(f"[LLM 错误] {e}")
        hist.pop()
        fallback = (
            "嗯…我在呢……慢慢闭上眼睛……"
            if mode == "sleep"
            else "嗯……我刚没听清，再说一遍？"
        )
        return fallback, hist


def chat(user_input: str, mode: str = "normal") -> str:
    """兼容旧版（不推荐用于多用户场景）"""
    raise DeprecationWarning("请使用 chat_with_history 并传入 username 参数")


def clear_history():
    """由调用方管理历史"""
    pass

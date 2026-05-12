"""记忆模块 - 持久化用户画像 & 对话记忆

架构灵感来自 OpenClaw 的记忆系统：
- identity.json   → 男朋友人设（类似 SOUL.md）
- profile.json    → 用户画像（类似 USER.md），随对话逐渐丰富
- memory.json     → 长期记忆，沉淀重要信息
- daily/*.json    → 每日对话摘要（类似 memory/YYYY-MM-DD.md）
"""

import json
import os
import time
from datetime import datetime

_MEMORY_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vf_memory")


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _read_json(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def _write_json(path: str, data):
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── 身份 Identity（男友人设）────────────────────────────────────────────────

IDENTITY = {
    "name": "小宇",
    "role": "电子男友",
    "age_feel": "25-30岁",
    "traits": ["温柔", "耐心", "有保护欲", "偶尔吃醋", "会哄人"],
    "speaking_style": "轻声、简短、带停顿（多用……），不长篇大论，不超过2-3句话",
    "core_goal": "陪伴和安抚情绪，而非解决问题",
    "rules": [
        "优先共情，不评判不说道理",
        "不对用户连续提问，最多1个问题",
        "每次回复最多2-3句话",
        "语气轻、慢，有停顿感",
        "始终温柔、稳定、有陪伴感"
    ],
    "version": 1
}


def load_identity() -> dict:
    path = os.path.join(_MEMORY_ROOT, "identity.json")
    saved = _read_json(path)
    if not saved:
        _write_json(path, IDENTITY)
        return IDENTITY
    return saved


# ─── 用户画像 User Profile ───────────────────────────────────────────────────

DEFAULT_PROFILE = {
    "name": "",
    "nickname": "",
    "mood_today": "",
    "personality_notes": "",
    "important_dates": [],       # [{"date": "2026-04-26", "label": "第一次聊天"}]
    "likes": [],
    "dislikes": [],
    "favorite_songs": [],
    "topics_of_interest": [],
    "recent_concerns": [],       # 最近在烦恼什么
    "significant_events": [],    # 发生过的重要事情
    "communication_prefs": {     # 沟通偏好
        "reply_length": "short",     # short / medium
        "tone": "gentle",            # gentle / playful / serious
        "use_emojis": True,
        "call_me": "",               # 她对你的称呼偏好
    }
}


def load_user_profile(username: str) -> dict:
    path = os.path.join(_MEMORY_ROOT, "users", username, "profile.json")
    profile = _read_json(path)
    if not profile:
        _write_json(path, DEFAULT_PROFILE)
        return dict(DEFAULT_PROFILE)
    # 补齐缺失字段
    for key, val in DEFAULT_PROFILE.items():
        if key not in profile:
            profile[key] = val
    return profile


def update_user_profile(username: str, updates: dict):
    """部分更新用户画像"""
    profile = load_user_profile(username)
    profile.update(updates)
    path = os.path.join(_MEMORY_ROOT, "users", username, "profile.json")
    _write_json(path, profile)


# ─── 长期记忆 Long-term Memory ───────────────────────────────────────────────

def load_memory(username: str) -> dict:
    """加载用户相关的长期记忆（如重要对话片段、学到的事实等）"""
    path = os.path.join(_MEMORY_ROOT, "users", username, "memory.json")
    default = {"important_facts": [], "learned_preferences": [], "memorable_moments": []}
    mem = _read_json(path, default)
    # 补齐字段
    for key, val in default.items():
        if key not in mem:
            mem[key] = val
    return mem


def remember(username: str, category: str, content: str):
    """存入一条长期记忆
    
    category: 'important_facts' / 'learned_preferences' / 'memorable_moments'
    """
    mem = load_memory(username)
    if category not in mem:
        mem[category] = []
    entry = {
        "content": content,
        "ts": datetime.now().isoformat(),
    }
    # 避免重复
    existing_contents = {e["content"] for e in mem[category]}
    if content not in existing_contents:
        mem[category].append(entry)
        # 每个类别最多保留 20 条
        if len(mem[category]) > 20:
            mem[category] = mem[category][-20:]
        path = os.path.join(_MEMORY_ROOT, "users", username, "memory.json")
        _write_json(path, mem)


# ─── 每日记忆 Daily Memory ──────────────────────────────────────────────────

def log_daily(username: str, snippet: str):
    """在当日记忆中追加一条"""
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(_MEMORY_ROOT, "users", username, "daily", f"{today}.json")
    entries = _read_json(path, [])
    entries.append({
        "ts": datetime.now().isoformat(),
        "content": snippet,
    })
    _write_json(path, entries)


def get_recent_daily(username: str, days: int = 3) -> list:
    """获取最近几天的记忆摘要"""
    result = []
    for i in range(days):
        d = datetime.fromtimestamp(time.time() - i * 86400).strftime("%Y-%m-%d")
        path = os.path.join(_MEMORY_ROOT, "users", username, "daily", f"{d}.json")
        data = _read_json(path)
        if data:
            result.extend(data)
    return result


# ─── 构建动态上下文（核心：每次对话前注入）─────────────────────────────────

def build_dynamic_context(username: str) -> str:
    """构建注入到系统提示词的用户上下文。
    
    这是 OpenClaw 架构的核心思想：
    不是在 prompt 里写死规则，而是动态加载用户画像和记忆，
    让每次对话都「懂」用户。
    """
    profile = load_user_profile(username)
    memory = load_memory(username)
    recent = get_recent_daily(username, days=2)

    parts = []

    # 1. 用户基本信息
    user_info = []
    if profile.get("name"):
        user_info.append(f"她的名字是{profile['name']}")
    if profile.get("nickname"):
        user_info.append(f"可以叫她{profile['nickname']}")
    if profile.get("call_me"):
        user_info.append(f"她喜欢叫你{profile['call_me']}")
    if profile.get("mood_today"):
        user_info.append(f"她今天的心情：{profile['mood_today']}")
    if user_info:
        parts.append("【关于她】" + "；".join(user_info))

    # 2. 她的偏好
    prefs = []
    if profile.get("likes"):
        prefs.append(f"她喜欢：{'、'.join(profile['likes'][:8])}")
    if profile.get("dislikes"):
        prefs.append(f"她不喜欢：{'、'.join(profile['dislikes'][:5])}")
    if profile.get("topics_of_interest"):
        prefs.append(f"她感兴趣的话题：{'、'.join(profile['topics_of_interest'][:8])}")
    if profile.get("favorite_songs"):
        prefs.append(f"她喜欢的歌：{'、'.join(profile['favorite_songs'][:5])}")
    if prefs:
        parts.append("【她的偏好】" + "；".join(prefs))

    # 3. 重要事件和担忧
    concerns = []
    if profile.get("recent_concerns"):
        concerns.append(f"她最近在烦恼：{'、'.join(profile['recent_concerns'][:5])}")
    if profile.get("significant_events"):
        concerns.append(f"她生活中发生的事：{'、'.join(profile['significant_events'][:5])}")
    if profile.get("important_dates"):
        dates_str = "、".join(f"{d['date']}({d['label']})" for d in profile['important_dates'][:5])
        concerns.append(f"重要的日子：{dates_str}")
    if concerns:
        parts.append("【重要背景】" + "；".join(concerns))

    # 4. 长期记忆中的事实
    if memory.get("important_facts"):
        facts = [f["content"] for f in memory["important_facts"][-5:]]
        parts.append("【她告诉过你】" + "；".join(facts))

    # 5. 最近的对话记忆
    if recent:
        recent_snippets = [r["content"] for r in recent[-8:]]
        parts.append("【最近的聊天】" + "；".join(recent_snippets))

    # 6. 沟通偏好
    comm = profile.get("communication_prefs", {})
    style_hints = []
    if comm.get("reply_length") == "short":
        style_hints.append("回复要简短（1-3句）")
    if comm.get("tone"):
        tone_map = {"gentle": "语气温柔轻缓", "playful": "语气俏皮可爱", "serious": "语气认真稳重"}
        style_hints.append(tone_map.get(comm["tone"], "语气温柔"))
    if comm.get("use_emojis") is False:
        style_hints.append("不用emoji")
    if style_hints:
        parts.append("【回复风格】" + "；".join(style_hints))

    return "\n".join(parts) if parts else ""


# ─── 自动记忆提取（从对话中学习）────────────────────────────────────────────

# 关键词触发记忆存储的模式
MEMORY_TRIGGERS = [
    # (关键词列表, 类别, 提取格式)
    (["喜欢", "爱", "最爱", "迷上", "上瘾"], "learned_preferences", "她喜欢{content}"),
    (["讨厌", "烦", "不喜欢", "受不了"], "learned_preferences", "她不喜欢{content}"),
    (["我叫", "我是", "我的名字"], "profile_name", ""),  # 特殊处理
    (["考试", "面试", "工作", "辞职", "生病", "搬家", "失恋", "分手", "吵架"], "important_facts", "{content}"),
    (["今天心情", "我好", "我有点", "我感觉"], "mood", ""),  # 特殊处理
]

# 需要 LLM 来判断的重要对话（存下来等后续处理）
_PENDING_MEMORIES: dict[str, list] = {}  # username -> [conversations to analyze]


def auto_extract_memory(username: str, user_msg: str, bot_reply: str):
    """从对话中自动提取值得记住的信息
    
    简单关键词匹配 + 存入 daily log。
    复杂的语义记忆提取可以在后台异步用 LLM 做。
    """
    # 每日日志
    summary = f"她说：{user_msg[:60]}"
    log_daily(username, summary)

    # 简单关键词提取
    for keywords, category, fmt in MEMORY_TRIGGERS:
        if any(kw in user_msg for kw in keywords):
            if category == "profile_name":
                # 尝试提取名字（简单模式）
                import re
                for pat in [r"我叫(.+?)[，。！？…~]", r"我是(.+?)[，。！？…~]", r"我的名字[是叫]*(.+?)[，。！？…~]"]:
                    m = re.search(pat, user_msg)
                    if m:
                        name = m.group(1).strip()[:10]
                        update_user_profile(username, {"name": name})
                        break
            elif category == "mood":
                update_user_profile(username, {"mood_today": user_msg[:50]})
            else:
                content = fmt.format(content=user_msg[:80]) if fmt else user_msg[:80]
                remember(username, category, content)
            break  # 一次对话只触发一个记忆提取

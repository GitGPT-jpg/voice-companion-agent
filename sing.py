"""AI 唱歌模块 - Replicate 云端 RVC Pipeline

流程: 歌曲文件 → 上传 Replicate → 云端 RVC (zsxkib/realistic-voice-cloning) → 下载结果
完全云端，不占本地显卡。
"""
import json
import os
import random

from config import (
    RVC_F0_METHOD,
    RVC_SING_INDEX_RATE,
    RVC_SING_FILTER_RADIUS,
    RVC_SING_RMS_MIX_RATE,
    RVC_SING_PROTECT,
    SING_OUTPUT_DIR,
    SONGS_DIR,
)


# ---------- 歌曲库 ----------

def load_songbook() -> list:
    """加载歌曲库"""
    path = os.path.join(SONGS_DIR, "songbook.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_song(text: str) -> dict | None:
    """根据用户输入匹配歌曲（按 keywords → title → artist 顺序匹配）"""
    songs = load_songbook()
    text = text.lower()

    for song in songs:
        for kw in song.get("keywords", []):
            if kw.lower() in text:
                return song

    for song in songs:
        if song.get("title", "").lower() in text:
            return song

    for song in songs:
        if song.get("artist", "").lower() in text:
            return song

    return None


def get_random_song() -> dict | None:
    """随机选一首歌"""
    songs = load_songbook()
    return random.choice(songs) if songs else None


def list_songs() -> list[dict]:
    """列出所有可用歌曲"""
    return [
        {"id": s["id"], "title": s["title"], "artist": s.get("artist", "未知")}
        for s in load_songbook()
    ]


# ---------- Pipeline ----------

def sing(song_data: dict) -> str:
    """
    AI 唱歌 Pipeline（Replicate 云端 RVC）

    Replicate 模型内部完成: 人声分离 → RVC 音色转换 → 混音
    本地只做: 上传歌曲 + 下载结果
    转换结果持久化缓存，重启后同一首歌直接复用。
    """
    song_file = os.path.join(SONGS_DIR, song_data["file"])
    if not os.path.exists(song_file):
        print(f"[唱歌] 歌曲文件不存在: {song_file}")
        return ""

    os.makedirs(SING_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(SING_OUTPUT_DIR, f"{song_data['id']}_final.wav")

    # 缓存命中：直接复用已有结果
    if os.path.exists(output_path):
        print(f"[唱歌] 使用缓存: {song_data.get('title', song_data['id'])}")
        return output_path

    try:
        import replicate_rvc

        f0_method = RVC_F0_METHOD if RVC_F0_METHOD in ("rmvpe", "mangio-crepe") else "rmvpe"

        print("🎤 正在云端 RVC 转换（Replicate）…")
        result = replicate_rvc.convert(
            audio_path=song_file,
            output_path=output_path,
            index_rate=RVC_SING_INDEX_RATE,
            filter_radius=RVC_SING_FILTER_RADIUS,
            rms_mix_rate=RVC_SING_RMS_MIX_RATE,
            protect=RVC_SING_PROTECT,
            f0_method=f0_method,
            mode="sing",
        )

        if result:
            print("✅ 歌曲合成完成（Replicate RVC）")
            return result
        else:
            print("[唱歌] 转换失败")
            return ""

    except Exception as e:
        print(f"[唱歌] Replicate RVC 失败: {e}")
        return ""


def is_available() -> bool:
    """检查唱歌模块是否可用"""
    import replicate_rvc
    return replicate_rvc.is_available()

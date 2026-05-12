"""AI 陪伴 - 主程序"""
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

from config import DEFAULT_SONG, TTS_OUTPUT_DIR, SING_OUTPUT_DIR
from intent import detect_intent
from llm import chat
from tts_module import tts
from audio import play, stop
from sing import (
    is_available as sing_available,
    sing as sing_song,
    match_song,
    get_random_song,
    list_songs,
)


def _extract_song_keyword(user_input: str) -> str:
    """从用户输入中提取歌曲关键词"""
    remove_words = ["唱", "歌", "首", "一", "给我", "来", "个", "sing", "song", "听"]
    keyword = user_input
    for w in remove_words:
        keyword = keyword.replace(w, "")
    return keyword.strip()


def handle_input(user_input: str, state: dict) -> dict:
    """处理一轮用户输入"""
    intent = detect_intent(user_input)

    if intent == "wake":
        state["mode"] = "normal"
        text = chat(user_input, mode="normal")
        print(f"💬 {text}")
        audio = tts(text)
        play(audio)

    elif intent == "sing":
        _handle_sing(user_input)

    elif intent == "sleep":
        state["mode"] = "sleep"
        text = chat(user_input, mode="sleep")
        print(f"🌙 {text}")
        audio = tts(text, slow=True)
        play(audio)

    else:  # chat
        text = chat(user_input, mode=state.get("mode", "normal"))
        emoji = "🌙" if state.get("mode") == "sleep" else "💬"
        print(f"{emoji} {text}")
        slow = state.get("mode") == "sleep"
        audio = tts(text, slow=slow)
        play(audio)

    return state


def _handle_sing(user_input: str):
    """处理唱歌请求"""
    if sing_available():
        # 匹配歌曲
        keyword = _extract_song_keyword(user_input)
        song = match_song(keyword) if keyword else None
        if song is None:
            song = get_random_song()

        if song:
            title = song.get("title", "一首歌")
            print(f"🎤 给你唱《{title}》~")
            tts_path = tts(f"好…给你唱{title}")
            play(tts_path)

            wav_path = sing_song(song)
            if wav_path:
                play(wav_path)
                return
            else:
                text = "嗓子有点不舒服…下次再唱给你听"
                print(f"🎤 {text}")
                audio = tts(text)
                play(audio)
                return

    # 回退：播放预录歌曲
    if os.path.exists(DEFAULT_SONG):
        print("🎵 给你唱首歌~")
        tts_path = tts("好…给你唱首歌")
        play(tts_path)
        play(DEFAULT_SONG)
    else:
        text = "歌曲还没准备好呢…先陪你聊天吧"
        print(f"🎵 {text}")
        audio = tts(text)
        play(audio)


def cleanup():
    """清理缓存（不清理 vocal_cache，保留分离结果加速下次使用）"""
    if os.path.exists(TTS_OUTPUT_DIR):
        shutil.rmtree(TTS_OUTPUT_DIR, ignore_errors=True)
    if os.path.exists(SING_OUTPUT_DIR):
        shutil.rmtree(SING_OUTPUT_DIR, ignore_errors=True)


def main():
    print("=" * 40)
    print("  💕 AI 陪伴系统")
    print("  输入文字开始聊天")
    print("  输入「唱歌」让他唱歌 🎤")
    print("  输入 quit 退出")
    print("=" * 40)

    if sing_available():
        songs = list_songs()
        if songs:
            print(f"  🎵 已加载 {len(songs)} 首歌曲")
    else:
        print("  ⚠️  唱歌模块未就绪")
        print("     运行 python setup_rvc.py 安装")

    state = {"mode": "normal"}

    try:
        while True:
            mode_hint = " [哄睡中🌙]" if state.get("mode") == "sleep" else ""
            user_input = input(f"\n你{mode_hint}> ").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "退出"):
                print("晚安…好梦~ 💤")
                break

            state = handle_input(user_input, state)

    except KeyboardInterrupt:
        print("\n再见~ 💕")
    finally:
        stop()
        cleanup()


if __name__ == "__main__":
    main()

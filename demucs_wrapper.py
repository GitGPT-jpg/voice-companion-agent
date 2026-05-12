"""人声分离模块 - 使用 Demucs

将歌曲分离为人声和伴奏，结果自动缓存。
"""
import os
import sys
import shutil
import subprocess

from config import VOCAL_CACHE_DIR


def separate(song_path: str) -> tuple[str, str]:
    """
    分离歌曲中的人声和伴奏

    参数:
        song_path: 歌曲文件路径

    返回: (人声路径, 伴奏路径)，失败返回 ("", "")
    """
    song_name = os.path.splitext(os.path.basename(song_path))[0]
    cache_dir = os.path.join(VOCAL_CACHE_DIR, song_name)
    vocal_path = os.path.join(cache_dir, "vocals.wav")
    accomp_path = os.path.join(cache_dir, "no_vocals.wav")

    # 缓存命中，跳过分离
    if os.path.exists(vocal_path) and os.path.exists(accomp_path):
        print(f"[Demucs] 使用缓存: {song_name}")
        return vocal_path, accomp_path

    print(f"[Demucs] 正在分离: {song_name}（首次处理需要几分钟）...")
    os.makedirs(VOCAL_CACHE_DIR, exist_ok=True)

    try:
        subprocess.run(
            [
                sys.executable, "-m", "demucs",
                "--two-stems=vocals",
                "-n", "htdemucs",
                "-o", VOCAL_CACHE_DIR,
                os.path.abspath(song_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # demucs 输出到 VOCAL_CACHE_DIR/htdemucs/song_name/
        demucs_dir = os.path.join(VOCAL_CACHE_DIR, "htdemucs", song_name)
        src_vocal = os.path.join(demucs_dir, "vocals.wav")
        src_accomp = os.path.join(demucs_dir, "no_vocals.wav")

        if not os.path.exists(src_vocal):
            print("[Demucs] 分离输出异常")
            return "", ""

        # 移动到缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        shutil.move(src_vocal, vocal_path)
        shutil.move(src_accomp, accomp_path)

        # 清理 demucs 临时目录
        shutil.rmtree(
            os.path.join(VOCAL_CACHE_DIR, "htdemucs"), ignore_errors=True
        )

        print("[Demucs] 分离完成 ✓")
        return vocal_path, accomp_path

    except subprocess.CalledProcessError as e:
        msg = (e.stderr or "")[:300]
        print(f"[Demucs] 分离失败: {msg}")
        return "", ""
    except FileNotFoundError:
        print("[Demucs] 未安装，请运行: pip install demucs")
        return "", ""
    except Exception as e:
        print(f"[Demucs] 错误: {e}")
        return "", ""


def is_available() -> bool:
    """检查 Demucs 是否可用"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "demucs", "--help"],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False

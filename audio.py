"""音频播放模块"""
import os
import time
import pygame


_initialized = False


def init():
    """初始化 pygame mixer"""
    global _initialized
    if not _initialized:
        pygame.mixer.init()
        _initialized = True


def play(audio_path: str):
    """播放音频文件，阻塞直到播放完成"""
    if not audio_path or not os.path.exists(audio_path):
        print(f"[播放] 文件不存在: {audio_path}")
        return

    init()
    try:
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"[播放错误] {e}")


def stop():
    """停止播放"""
    if _initialized:
        pygame.mixer.music.stop()

"""共享 Replicate 云端 RVC 工具

聊天 TTS 和唱歌都调用此模块，使用同一个 boyfriend.pth 音色。
- 聊天：pseudoram/rvc-v2（纯 RVC，~9秒，轻量）
- 唱歌：zsxkib/realistic-voice-cloning（含 Demucs+混音，完整流水线）
"""
import io
import json
import os
import zipfile

import requests

from config import REPLICATE_API_KEY, RVC_MODEL_PATH, RVC_INDEX_PATH

_MODEL_CHAT = "pseudoram/rvc-v2:d18e2e0a6a6d3af183cc09622cebba8555ec9a9e66983261fc64c8b1572b7dce"
_MODEL_SING = "zsxkib/realistic-voice-cloning:a0076ea13a704d9fa6d02535bc8951d3b141c84dc95d2d3f2f5016eabfcb8d94"

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
_URL_CACHE_FILE = os.path.join(_CACHE_DIR, "replicate_model_url.json")

# 内存缓存
_model_url_cache: str | None = None


def _load_url_cache() -> str | None:
    """从磁盘读取已缓存的模型 URL（同时验证 .pth 文件未变动）"""
    if not os.path.exists(_URL_CACHE_FILE):
        return None
    try:
        with open(_URL_CACHE_FILE, "r") as f:
            data = json.load(f)
        # 若 .pth 修改时间变了，缓存失效
        mtime = os.path.getmtime(RVC_MODEL_PATH)
        if data.get("mtime") != mtime:
            return None
        return data.get("url")
    except Exception:
        return None


def _save_url_cache(url: str):
    """将模型 URL 持久化到磁盘"""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_URL_CACHE_FILE, "w") as f:
        json.dump({"url": url, "mtime": os.path.getmtime(RVC_MODEL_PATH)}, f)


def get_model_url() -> str:
    """将 boyfriend.pth (+ index) 打包成 zip 上传到 Replicate，返回公开 URL。
    优先读磁盘缓存，其次内存缓存，都没有才重新上传。"""
    global _model_url_cache

    if _model_url_cache:
        return _model_url_cache

    cached = _load_url_cache()
    if cached:
        _model_url_cache = cached
        print("[Replicate] 使用缓存模型 URL ✓")
        return _model_url_cache

    import replicate
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY
    client = replicate.Client(api_token=REPLICATE_API_KEY)

    print("[Replicate] 首次上传 RVC 模型…")
    # 只上传 .pth（~55MB），.index 可选且太大（115MB）会导致上传超时
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(RVC_MODEL_PATH, os.path.basename(RVC_MODEL_PATH))
    buf.seek(0)

    model_name = os.path.splitext(os.path.basename(RVC_MODEL_PATH))[0]
    file_obj = client.files.create(buf, filename=f"{model_name}.zip")
    _model_url_cache = file_obj.urls["get"]
    _save_url_cache(_model_url_cache)
    print("[Replicate] 模型上传完成 ✓")
    return _model_url_cache


def convert(
    audio_path: str,
    output_path: str,
    *,
    pitch_change: int = 0,
    index_rate: float = 0.75,
    filter_radius: int = 3,
    rms_mix_rate: float = 0.75,
    protect: float = 0.33,
    f0_method: str = "rmvpe",
    mode: str = "chat",
) -> str:
    """云端 RVC 音色转换（带重试）"""
    import replicate
    import time
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY

    model_url = get_model_url()
    f0_method = f0_method if f0_method in ("rmvpe", "mangio-crepe") else "rmvpe"
    model_name = os.path.splitext(os.path.basename(RVC_MODEL_PATH))[0]

    last_err = None
    for attempt in range(3):
        try:
            with open(audio_path, "rb") as f:
                if mode == "sing":
                    pitch_str = "no-change" if pitch_change == 0 else (
                        f"up-{pitch_change}-key" if pitch_change > 0 else f"down-{abs(pitch_change)}-key"
                    )
                    output_url = replicate.run(
                        _MODEL_SING,
                        input={
                            "song_input": f,
                            "rvc_model": "CUSTOM",
                            "custom_rvc_model_download_url": model_url,
                            "custom_rvc_model_download_name": model_name,
                            "pitch_change": pitch_str,
                            "index_rate": index_rate,
                            "filter_radius": filter_radius,
                            "rms_mix_rate": rms_mix_rate,
                            "protect": protect,
                            "pitch_detection_algorithm": f0_method,
                            "output_format": "wav",
                        },
                        use_file_output=False,
                    )
                else:
                    output_url = replicate.run(
                        _MODEL_CHAT,
                        input={
                            "input_audio": f,
                            "rvc_model": "CUSTOM",
                            "custom_rvc_model_download_url": model_url,
                            "pitch_change": pitch_change,
                            "index_rate": index_rate,
                            "filter_radius": filter_radius,
                            "rms_mix_rate": rms_mix_rate,
                            "protect": protect,
                            "f0_method": f0_method,
                            "output_format": "wav",
                        },
                        use_file_output=False,
                    )

            # 下载结果
            resp = requests.get(str(output_url), timeout=120)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path

        except Exception as e:
            last_err = e
            print(f"[Replicate] 尝试 {attempt+1}/3 失败: {e}")
            if attempt < 2:
                time.sleep(3)

    raise last_err


def is_available() -> bool:
    """检查 Replicate RVC 是否可用"""
    if not REPLICATE_API_KEY:
        return False
    if not RVC_MODEL_PATH or not os.path.exists(RVC_MODEL_PATH):
        return False
    return True

"""音色转换模块 - 使用 RVC

将分离出的人声转换为目标音色（电子男友声音）。
支持从本地 RVC 安装导入推理模块。
"""
import os
import json
import sys
import traceback
import numpy as np
import soundfile as sf

from config import (
    RVC_DIR,
    RVC_MODEL_PATH,
    RVC_INDEX_PATH,
    RVC_F0_METHOD,
    RVC_F0_UP_KEY,
    RVC_INDEX_RATE,
    RVC_FILTER_RADIUS,
    RVC_RMS_MIX_RATE,
    RVC_PROTECT,
)

_vc = None
_config = None
_available = None
_last_error = ""
_RVC_CONFIG_FILES = [
    os.path.join("v1", "32k.json"),
    os.path.join("v1", "40k.json"),
    os.path.join("v1", "48k.json"),
    os.path.join("v2", "32k.json"),
    os.path.join("v2", "48k.json"),
]


def _should_force_fp32(cfg) -> bool:
    """4GB 显卡上半精度容易出静音/NaN，统一走 fp32 更稳。"""
    gpu_mem = getattr(cfg, "gpu_mem", None)
    return gpu_mem is not None and gpu_mem <= 4


def _audio_has_content(audio: np.ndarray) -> bool:
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        return False
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))
    return peak > 1e-4 and rms > 1e-5


def _set_last_error(message: str) -> str:
    global _last_error
    _last_error = message
    return message


def get_last_error() -> str:
    """返回最近一次 RVC 就绪/转换失败原因。"""
    return _last_error


def _required_runtime_files() -> list[tuple[str, str]]:
    required = [
        ("Hubert 模型", os.path.join(RVC_DIR, "assets", "hubert", "hubert_base.pt")),
    ]
    if RVC_F0_METHOD == "rmvpe":
        required.append(
            ("RMVPE 模型", os.path.join(RVC_DIR, "assets", "rmvpe", "rmvpe.pt"))
        )
    return required


def _ensure_runtime_configs():
    """修复 RVC configs/inuse 下缺失或损坏的 JSON 配置。"""
    for rel_path in _RVC_CONFIG_FILES:
        src = os.path.join(RVC_DIR, "configs", rel_path)
        dst = os.path.join(RVC_DIR, "configs", "inuse", rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        needs_repair = not os.path.exists(dst)
        if not needs_repair:
            try:
                with open(dst, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                needs_repair = True

        if needs_repair:
            if not os.path.exists(src):
                raise FileNotFoundError(f"RVC 缺少基础配置文件: {src}")
            with open(src, "r", encoding="utf-8") as f:
                content = f.read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[RVC] 已修复配置文件: configs\\inuse\\{rel_path}")


def is_available() -> bool:
    """检查 RVC 是否可用"""
    global _available
    if _available is not None:
        return _available

    if not os.path.exists(RVC_MODEL_PATH):
        print(f"[RVC] 模型文件不存在: {RVC_MODEL_PATH}")
        print("[RVC] 请将 .pth 模型放到 models/ 目录，命名为 boyfriend.pth")
        _set_last_error(f"模型文件不存在: {RVC_MODEL_PATH}")
        _available = False
        return False

    if not os.path.exists(RVC_DIR):
        print(f"[RVC] 未找到 RVC 目录: {RVC_DIR}")
        print("[RVC] 请运行: python setup_rvc.py")
        _set_last_error(f"RVC 目录不存在: {RVC_DIR}")
        _available = False
        return False

    for label, path in _required_runtime_files():
        if not os.path.exists(path):
            print(f"[RVC] 缺少{label}: {path}")
            _set_last_error(f"缺少{label}: {path}")
            _available = False
            return False

    _set_last_error("")
    _available = True
    return True


def _get_vc():
    """懒加载 RVC 推理实例"""
    global _vc, _config
    if _vc is not None:
        return _vc

    if not is_available():
        return None

    # Add RVC to sys.path
    if RVC_DIR not in sys.path:
        sys.path.insert(0, RVC_DIR)

    # Set environment variables RVC expects
    os.environ.setdefault("weight_root", os.path.join(RVC_DIR, "assets", "weights"))
    os.environ.setdefault("index_root", os.path.join(RVC_DIR, "logs"))
    os.environ.setdefault("rmvpe_root", os.path.join(RVC_DIR, "assets", "rmvpe"))

    # Override sys.argv to prevent argparse conflicts
    saved_argv = sys.argv
    sys.argv = ["rvc_infer"]

    original_cwd = os.getcwd()
    try:
        os.chdir(RVC_DIR)

        _ensure_runtime_configs()

        from configs.config import Config
        from infer.modules.vc.modules import VC

        _config = Config()
        if _should_force_fp32(_config) and _config.is_half:
            print("[RVC] 检测到 4GB 显卡，切换到 fp32 提高稳定性")
            _config.is_half = False
            _config.use_fp32_config()
        _vc = VC(_config)

        # get_vc expects model filename relative to weight_root
        # We pass the full path - need to set weight_root to our models dir
        model_dir = os.path.dirname(os.path.abspath(RVC_MODEL_PATH))
        model_name = os.path.basename(RVC_MODEL_PATH)
        os.environ["weight_root"] = model_dir

        print(f"[RVC] 正在加载模型: {model_name}")
        _vc.get_vc(model_name)

        os.chdir(original_cwd)
        sys.argv = saved_argv
        _set_last_error("")
        print("[RVC] 模型加载成功 ✓")
        return _vc

    except ImportError as e:
        message = _set_last_error(f"导入失败，请检查 RVC 安装: {e}")
        print(f"[RVC] {message}")
        traceback.print_exc()
        _available = False
        _try_restore_cwd(original_cwd)
        sys.argv = saved_argv
        return None
    except Exception as e:
        message = _set_last_error(f"模型加载失败: {e}")
        print(f"[RVC] {message}")
        traceback.print_exc()
        _available = False
        _try_restore_cwd(original_cwd)
        sys.argv = saved_argv
        return None


def convert(
    vocal_path: str,
    output_path: str,
    *,
    f0_method: str = RVC_F0_METHOD,
    f0_up_key: int = RVC_F0_UP_KEY,
    index_rate: float = RVC_INDEX_RATE,
    filter_radius: int = RVC_FILTER_RADIUS,
    rms_mix_rate: float = RVC_RMS_MIX_RATE,
    protect: float = RVC_PROTECT,
) -> str:
    """
    将人声转换为目标音色

    参数:
        vocal_path:  原始人声文件路径
        output_path: 输出文件路径

    返回: 输出文件路径，失败返回空字符串
    """
    vc = _get_vc()
    if vc is None:
        return ""

    input_path = os.path.abspath(vocal_path)
    output_path = os.path.abspath(output_path)
    original_cwd = os.getcwd()
    try:
        os.chdir(RVC_DIR)

        index_path = RVC_INDEX_PATH if os.path.exists(RVC_INDEX_PATH) else ""
        if not index_path and index_rate > 0:
            print("[RVC] 未找到 .index 文件，index_rate 将被忽略")

        info, opt = vc.vc_single(
            sid=0,
            input_audio_path=input_path,
            f0_up_key=f0_up_key,
            f0_file=None,           # no external f0 file
            f0_method=f0_method,
            file_index=index_path,
            file_index2="",
            index_rate=index_rate,
            filter_radius=filter_radius,
            resample_sr=0,
            rms_mix_rate=rms_mix_rate,
            protect=protect,
        )

        os.chdir(original_cwd)

        if opt is None or (isinstance(opt, tuple) and opt[0] is None):
            _set_last_error(f"转换失败: {info}")
            print(f"[RVC] 转换失败: {info}")
            return ""

        # 处理返回值
        if isinstance(opt, tuple):
            sr, audio = opt
        else:
            sr = 40000
            audio = opt

        audio = np.asarray(audio)
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
        if not _audio_has_content(audio):
            _set_last_error("转换结果接近静音")
            print("[RVC] 转换结果接近静音，已判定为失败")
            return ""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sf.write(output_path, audio, sr)
        _set_last_error("")
        print(f"[RVC] 转换完成 ✓")
        return output_path

    except Exception as e:
        message = _set_last_error(f"转换失败: {e}")
        print(f"[RVC] {message}")
        traceback.print_exc()
        _try_restore_cwd(original_cwd)
        return ""


def _try_restore_cwd(path: str):
    try:
        os.chdir(path)
    except Exception:
        pass

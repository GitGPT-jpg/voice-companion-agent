"""RVC 唱歌模块安装助手"""
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RVC_DIR = os.path.join(PROJECT_DIR, "Retrieval-based-Voice-Conversion-WebUI")
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
SONGS_DIR = os.path.join(PROJECT_DIR, "songs")


def step(msg: str):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}")


def install_deps():
    step("1. 安装 Python 依赖")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                           os.path.join(PROJECT_DIR, "requirements.txt")])
    print("✅ 依赖安装完成")


def clone_rvc():
    step("2. 克隆 RVC WebUI")
    if os.path.exists(RVC_DIR):
        print(f"✅ RVC 目录已存在: {RVC_DIR}")
        return

    print("正在克隆 RVC 仓库（可能需要几分钟）...")
    subprocess.check_call([
        "git", "clone", "--depth", "1",
        "https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git",
        RVC_DIR,
    ])
    print("✅ RVC 克隆完成")

    # 安装 RVC 自身依赖
    rvc_req = os.path.join(RVC_DIR, "requirements.txt")
    if os.path.exists(rvc_req):
        print("正在安装 RVC 依赖...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", rvc_req])
        print("✅ RVC 依赖安装完成")


def setup_dirs():
    step("3. 创建目录")
    for d in [MODELS_DIR, SONGS_DIR, os.path.join(PROJECT_DIR, "output"),
              os.path.join(PROJECT_DIR, "vocal_cache"),
              os.path.join(PROJECT_DIR, "sing_output")]:
        os.makedirs(d, exist_ok=True)
        print(f"  📁 {d}")
    print("✅ 目录创建完成")


def print_next_steps():
    step("🎉 安装完成！接下来你需要：")
    print("""
  1. 准备 RVC 模型文件：
     - 将 .pth 模型文件放到 models/ 目录
     - 将 .index 索引文件放到 models/ 目录（可选）
     - 在 config.py 中更新 RVC_MODEL_PATH 和 RVC_INDEX_PATH

  2. 准备歌曲 MP3 文件：
     - 将歌曲放到 songs/ 目录
     - 文件名对应 songbook.json 中的 file 字段
     - 已配置的歌曲：
       * guang_nian_zhi_wai.mp3 (光年之外)
       * tian_mi_mi.mp3 (甜蜜蜜)
       * yue_liang_dai_biao.mp3 (月亮代表我的心)

  3. 运行测试：
     python -c "from sing import is_available; print('OK' if is_available() else 'FAIL')"

  4. 启动系统：
     python main.py

  💡 提示：
  - 首次唱歌会比较慢（Demucs 人声分离需要时间）
  - 分离结果会缓存，第二次唱同一首会很快
  - 如果没有 GPU，推理会慢一些但仍然可以运行
""")


def main():
    print("🎤 RVC 唱歌模块安装助手")
    print("=" * 50)

    try:
        install_deps()
        clone_rvc()
        setup_dirs()
        print_next_steps()
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 安装出错: {e}")
        print("请检查网络连接和 Git 是否已安装")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

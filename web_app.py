"""Web 版 - 灵魂伴侣 💕

访问方式（公网）:
    1. python web_app.py
    2. ngrok http 5000
    3. 把 ngrok 给的 https:// 链接发给她
"""
import os
import sys
import sqlite3
import threading

# 强制 stdout/stderr 使用 UTF-8，避免 Windows GBK 控制台编码报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, abort, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash

from config import TTS_OUTPUT_DIR, SING_OUTPUT_DIR
from intent import detect_intent
from llm import chat_with_history
from tts_module import tts
from sing import sing as sing_song, match_song, get_random_song

# ─── App ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0   # 开发模式禁用静态文件缓存
app.secret_key = os.getenv("WEB_SECRET_KEY", "insecure-dev-key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_HTTPONLY=True,
)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

login_manager = LoginManager(app)
login_manager.login_view = "login"

# Jinja2 自定义过滤器
app.jinja_env.filters["basename"] = os.path.basename

# ─── Users (从 .env 读取，两个固定账号) ──────────────────────────────────────
_USERS = {
    os.getenv("WEB_USER", "admin"): {
        "password": generate_password_hash(os.getenv("WEB_PASS", "admin")),
        "role": "owner",
    },
    os.getenv("WEB_GF_USER", "girl"): {
        "password": generate_password_hash(os.getenv("WEB_GF_PASS", "girl")),
        "role": "user",
    },
}


class User(UserMixin):
    def __init__(self, uid: str):
        self.id = uid
        self.role = _USERS[uid]["role"]


@login_manager.user_loader
def load_user(uid):
    if uid in _USERS:
        return User(uid)
    return None


# ─── 每用户对话历史（内存，重启清空） ────────────────────────────────────────
_histories: dict[str, list] = {}
_hist_lock = threading.Lock()


def _chat(username: str, user_input: str, mode: str = "normal") -> str:
    """线程安全的每用户 LLM 调用。"""
    with _hist_lock:
        hist = _histories.get(username, []).copy()
    reply, new_hist = chat_with_history(user_input, hist, mode, username=username)
    with _hist_lock:
        _histories[username] = new_hist
    return reply


def _chat_call(username: str, user_input: str) -> str:
    """通话模式：更快、更短的回应"""
    with _hist_lock:
        hist = _histories.get(username, []).copy()
    reply, new_hist = chat_with_history(user_input, hist, mode="call", username=username)
    with _hist_lock:
        _histories[username] = new_hist
    return reply


# ─── SQLite 对话日志 ──────────────────────────────────────────────────────────
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_LOG_DB  = os.path.join(_LOG_DIR, "conversations.db")


def _init_db():
    os.makedirs(_LOG_DIR, exist_ok=True)
    con = sqlite3.connect(_LOG_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL,
            username   TEXT NOT NULL,
            intent     TEXT,
            user_msg   TEXT,
            bot_reply  TEXT,
            audio_path TEXT
        )
    """)
    con.commit()
    con.close()


def _log(username, intent, user_msg, bot_reply, audio_path=""):
    try:
        con = sqlite3.connect(_LOG_DB)
        con.execute(
            "INSERT INTO conversations (ts,username,intent,user_msg,bot_reply,audio_path) VALUES (?,?,?,?,?,?)",
            (datetime.now().isoformat(), username, intent, user_msg, bot_reply, audio_path),
        )
        con.commit()
        con.close()
    except Exception as e:
        print(f"[日志错误] {e}")


# ─── 唱歌取消控制 ────────────────────────────────────────────────────────────
_cancelled_reqs: set[str] = set()


# ─── 音频路由 ─────────────────────────────────────────────────────────────────
@app.route("/audio/tts/<path:filename>")
@login_required
def audio_tts(filename):
    base = os.path.abspath(TTS_OUTPUT_DIR)
    fp = os.path.normpath(os.path.join(base, filename))
    if not fp.startswith(base):
        abort(403)
    return send_from_directory(base, filename)


@app.route("/audio/sing/<path:filename>")
@login_required
def audio_sing(filename):
    base = os.path.abspath(SING_OUTPUT_DIR)
    fp = os.path.normpath(os.path.join(base, filename))
    if not fp.startswith(base):
        abort(403)
    return send_from_directory(base, filename)


def _tts_url(path: str) -> str:
    if path and os.path.exists(path):
        return f"/audio/tts/{os.path.basename(path)}"
    return ""


def _sing_url(path: str) -> str:
    if path and os.path.exists(path):
        return f"/audio/sing/{os.path.basename(path)}"
    return ""


# ─── 页面路由 ─────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("chat.html", username=current_user.id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if u in _USERS and check_password_hash(_USERS[u]["password"], p):
            login_user(User(u), remember=True)
            return redirect(url_for("index"))
        return render_template("login.html", error="用户名或密码错误 / Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/admin/logs")
@login_required
def admin_logs():
    if current_user.role != "owner":
        abort(403)
    con = sqlite3.connect(_LOG_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM conversations ORDER BY id DESC LIMIT 500"
    ).fetchall()
    total = con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    users = [r[0] for r in con.execute(
        "SELECT DISTINCT username FROM conversations ORDER BY username"
    ).fetchall()]
    sing_count = con.execute(
        "SELECT COUNT(*) FROM conversations WHERE intent='sing'"
    ).fetchone()[0]
    con.close()
    return render_template("logs.html", rows=rows,
                           total=total, users=users, sing_count=sing_count)


# ─── SocketIO ─────────────────────────────────────────────────────────────────
@socketio.on("chat_message")
def handle_chat(data):
    if not current_user.is_authenticated:
        return

    user_input = (data.get("text") or "").strip()
    req_id     = (data.get("req_id") or "").strip()
    if not user_input or not req_id:
        return

    username = current_user.id
    sid      = request.sid

    def send(event, **kw):
        kw["req_id"] = req_id
        socketio.emit(event, kw, to=sid)

    def worker():
        try:
            intent = detect_intent(user_input)
            send("status", text="思考中… / Thinking…", color="#8B7AA0")

            if intent == "sing":
                keyword = user_input
                for w in ["唱", "歌", "首", "一", "给我", "来", "个", "sing", "song", "听"]:
                    keyword = keyword.replace(w, "")
                keyword = keyword.strip()

                song = match_song(keyword) if keyword else None
                if not song:
                    song = get_random_song()

                if not song:
                    reply = "歌曲库还没准备好呢 🥺"
                    audio = tts(reply)
                    send("bot_message", text=reply, audio_url=_tts_url(audio), glow="pink")
                    _log(username, "sing_no_lib", user_input, reply, audio)
                    return

                title     = song.get("title", "一首歌")
                intro_txt = f"好，给你唱《{title}》~"
                intro_aud = tts(intro_txt)
                send("bot_message", text=intro_txt, audio_url=_tts_url(intro_aud), glow="pink")
                send("singing_start", title=title)
                send("status", text=f"演唱《{title}》中…", color="#8B7AA0")

                wav = sing_song(song)

                # 若用户已按停止，丢弃结果
                if req_id in _cancelled_reqs:
                    _cancelled_reqs.discard(req_id)
                    return

                if wav:
                    send("song_ready", audio_url=_sing_url(wav), title=title)
                    _log(username, "sing", user_input, intro_txt, wav)
                else:
                    err     = "嗓子有点不舒服…下次再唱给你听 🥺"
                    err_aud = tts(err)
                    send("singing_end")
                    send("bot_message", text=err, audio_url=_tts_url(err_aud), glow="pink")
                    _log(username, "sing_fail", user_input, err, err_aud)

            else:
                mode  = "sleep" if intent == "sleep" else "normal"
                reply = _chat(username, user_input, mode)
                audio = tts(reply)
                glow  = "purple" if intent == "sleep" else "pink"
                send("bot_message", text=reply, audio_url=_tts_url(audio), glow=glow)
                _log(username, intent, user_input, reply, audio)

        except Exception as e:
            print(f"[Worker 错误] {e}")
        finally:
            send("server_done")

    threading.Thread(target=worker, daemon=True).start()


@socketio.on("call_message")
def handle_call(data):
    """通话模式：极速响应，仅语音"""
    if not current_user.is_authenticated:
        return

    user_input = (data.get("text") or "").strip()
    req_id     = (data.get("req_id") or "").strip()
    if not user_input or not req_id:
        return

    username = current_user.id
    sid      = request.sid

    def send(event, **kw):
        kw["req_id"] = req_id
        socketio.emit(event, kw, to=sid)

    def worker():
        try:
            send("status", text="…", color="#FF6B9D")
            reply = _chat_call(username, user_input)
            audio = tts(reply)
            send("call_reply", text=reply, audio_url=_tts_url(audio))
            _log(username, "call", user_input, reply, audio)
        except Exception as e:
            print(f"[Call 错误] {e}")
        finally:
            send("call_done")

    threading.Thread(target=worker, daemon=True).start()


@socketio.on("stop_singing")
def on_stop(data):
    if not current_user.is_authenticated:
        return
    req_id = (data.get("req_id") or "").strip()
    if req_id:
        _cancelled_reqs.add(req_id)


@socketio.on("singing_stopped")
def on_singing_stopped(data):
    """用户主动停止唱歌后，AI 用关心的语气追问。"""
    if not current_user.is_authenticated:
        return
    req_id = (data.get("req_id") or "").strip()
    if not req_id:
        return

    username = current_user.id
    sid      = request.sid

    def send(event, **kw):
        kw["req_id"] = req_id
        socketio.emit(event, kw, to=sid)

    def worker():
        try:
            with _hist_lock:
                hist = _histories.get(username, []).copy()
            # 注入隐含语境，不保存进历史，保持对话纯净
            prompt = "（你刚才在唱歌，对方把歌停了。请用20字以内、可爱又有一点点委屈的语气问问：是唱得不好听吗？还是想换首歌呀？）"
            reply, _ = chat_with_history(prompt, hist, "normal")
            audio = tts(reply)
            send("bot_message", text=reply, audio_url=_tts_url(audio), glow="pink")
            _log(username, "sing_stopped", "", reply, audio)
        except Exception as e:
            print(f"[singing_stopped 错误] {e}")
        finally:
            send("server_done")

    threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    _init_db()
    port = int(os.getenv("WEB_PORT", "5000"))

    # 后台线程：等 ngrok 就绪后打印公网 URL
    import re, time as _time, socket as _socket

    def _print_startup():
        try:
            lan_ip = _socket.gethostbyname(_socket.gethostname())
        except Exception:
            lan_ip = "<本机IP>"

        print(f"\n💕 灵魂伴侣 Web 版启动")
        print(f"   本机:  http://localhost:{port}")
        print(f"   局域网: http://{lan_ip}:{port}")

        ngrok_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "ngrok.log")
        ngrok_url = None
        for _ in range(20):
            if os.path.exists(ngrok_log):
                try:
                    content = open(ngrok_log, encoding="utf-8", errors="replace").read()
                    m = re.search(r'url=(https://\S+)', content)
                    if m:
                        ngrok_url = m.group(1)
                        break
                except Exception:
                    pass
            _time.sleep(1)

        if ngrok_url:
            print(f"   公网:  {ngrok_url}")
        else:
            print(f"   公网:  （ngrok 未配置）")
        print()

    threading.Thread(target=_print_startup, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=port, debug=False)


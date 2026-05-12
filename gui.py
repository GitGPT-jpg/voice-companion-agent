"""图形界面 - 灵魂伴侣 💕"""
import math
import os
import queue
import threading
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

import audio as audio_module
from config import SING_OUTPUT_DIR
from intent import detect_intent
from llm import chat as llm_chat
from sing import (
    get_random_song,
    is_available as sing_available,
    match_song,
    sing as sing_song,
)
from tts_module import tts

# ─── 颜色主题 ─────────────────────────────────────────────────────────────────
BG_DARK     = "#0F0A1E"
BG_CARD     = "#18102E"
BG_INPUT    = "#140D28"
ACCENT_PINK = "#FF6B9D"
ACCENT_PURP = "#B57BEE"
TEXT_MAIN   = "#F0E6FF"
TEXT_DIM    = "#8B7AA0"
BUBBLE_HIS  = "#211345"
BORDER_DIM  = "#3D2B5A"

AVATAR_SIZE  = 130
GLOW_LAYERS  = 5


# ─── 头像生成 ─────────────────────────────────────────────────────────────────

def _make_avatar(size: int) -> Image.Image:
    """生成默认渐变圆形头像（粉紫渐变 + 爱心）"""
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r    = size // 2
    for i in range(r, 0, -1):
        t = i / r
        draw.ellipse(
            [r - i, r - i, r + i, r + i],
            fill=(
                int(0x8A + (0xFF - 0x8A) * t),
                int(0x2B + (0x6B - 0x2B) * t),
                int(0xBE + (0x9D - 0xBE) * t),
                255,
            ),
        )
    # 爱心
    hs = size // 5
    cx, cy = r, r + size // 14
    draw.ellipse([cx - hs, cy - hs, cx,      cy], fill=(255, 255, 255, 200))
    draw.ellipse([cx,      cy - hs, cx + hs, cy], fill=(255, 255, 255, 200))
    draw.polygon(
        [(cx - hs, cy - 2), (cx + hs, cy - 2), (cx, cy + hs + 4)],
        fill=(255, 255, 255, 200),
    )
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)
    return img


def _rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(c1: tuple, c2: tuple, t: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ─── 头像组件 ─────────────────────────────────────────────────────────────────

class AvatarWidget(tk.Canvas):
    """带发光动画的圆形头像"""

    def __init__(self, parent, size: int = AVATAR_SIZE, **kw):
        pad         = GLOW_LAYERS * 12 + 20
        canvas_size = size + pad * 2
        super().__init__(
            parent,
            width=canvas_size, height=canvas_size,
            bg=BG_DARK, highlightthickness=0,
            **kw,
        )
        self._r    = size // 2
        self._cx   = canvas_size // 2
        self._cy   = canvas_size // 2
        self._glow = False
        self._color = ACCENT_PINK
        self._phase = 0.0
        self._aid   = None

        # 加载头像图片（优先 assets/avatar.png，否则生成默认）
        asset = os.path.join(os.path.dirname(__file__), "assets", "avatar.png")
        if os.path.exists(asset):
            img = Image.open(asset).convert("RGBA").resize((size, size), Image.LANCZOS)
        else:
            img = _make_avatar(size)
        self._tk_img = ImageTk.PhotoImage(img)
        self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        cx, cy, r = self._cx, self._cy, self._r
        self.create_oval(cx-r-3, cy-r-3, cx+r+3, cy+r+3,
                         outline=BORDER_DIM, width=2)
        self.create_image(cx, cy, image=self._tk_img)

    def start_glow(self, color: str = ACCENT_PINK):
        self._glow  = True
        self._color = color
        if not self._aid:
            self._animate()

    def stop_glow(self):
        self._glow = False
        if self._aid:
            self.after_cancel(self._aid)
            self._aid = None
        self._draw_idle()

    def _animate(self):
        if not self._glow:
            self._aid = None
            return
        self._phase = (self._phase + 0.10) % (2 * math.pi)
        pulse = (math.sin(self._phase) + 1) / 2  # 0 ~ 1

        self.delete("all")
        cx, cy, r  = self._cx, self._cy, self._r
        bg_rgb     = _rgb(BG_DARK)
        glow_rgb   = _rgb(self._color)

        # 外层渐变发光圈（从外到内）
        for i in range(GLOW_LAYERS, 0, -1):
            gap   = i * 10 + int(pulse * 8)
            alpha = (1 - i / (GLOW_LAYERS + 1)) * pulse * 0.9
            self.create_oval(
                cx - r - gap, cy - r - gap,
                cx + r + gap, cy + r + gap,
                outline=_lerp(bg_rgb, glow_rgb, alpha), width=2,
            )
        # 紧贴头像的亮圈
        bright = _lerp(bg_rgb, glow_rgb, 0.7 + pulse * 0.3)
        self.create_oval(cx-r-3, cy-r-3, cx+r+3, cy+r+3,
                         outline=bright, width=3)
        self.create_image(cx, cy, image=self._tk_img)
        self._aid = self.after(40, self._animate)  # ~25fps


# ─── 主应用 ───────────────────────────────────────────────────────────────────

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("💕 灵魂伴侣 / Soulmate")
        self.geometry("420x820")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)

        self._queue: queue.Queue = queue.Queue()
        self._singing = False
        self._mode    = "normal"

        self._build_ui()
        self.after(50, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI 布局 ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── 顶部头像区 ────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        top.pack(fill="x", pady=(20, 0))

        self._avatar = AvatarWidget(top, size=AVATAR_SIZE)
        self._avatar.pack()

        ctk.CTkLabel(
            top, text="男友 / Virtual Boyfriend",
            font=ctk.CTkFont(family="微软雅黑", size=18, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(pady=(4, 0))

        self._status_lbl = ctk.CTkLabel(
            top, text="在线 / Online ·",
            font=ctk.CTkFont(family="微软雅黑", size=12),
            text_color=ACCENT_PINK,
        )
        self._status_lbl.pack(pady=(2, 14))

        ctk.CTkFrame(self, height=1, fg_color=BORDER_DIM).pack(fill="x", padx=20)

        # ── 底部区域（先 pack，chat 后 pack 用 expand 填充剩余空间）─────────
        self._bottom = ctk.CTkFrame(self, fg_color=BG_INPUT, corner_radius=0)
        self._bottom.pack(side="bottom", fill="x")

        # 停止按钮（初始不 pack，唱歌时 pack 到 input_row 之前）
        self._stop_btn = ctk.CTkButton(
            self._bottom,
            text="⏹  停止播放 / Stop",
            font=ctk.CTkFont(family="微软雅黑", size=13),
            fg_color="#3D1A2E", hover_color="#5A2040",
            text_color=ACCENT_PINK,
            border_width=1, border_color=ACCENT_PINK,
            corner_radius=20, height=36,
            command=self._on_stop,
        )

        # 输入行
        self._input_row = ctk.CTkFrame(self._bottom, fg_color="transparent")
        self._input_row.pack(fill="x", padx=16, pady=12)

        self._entry = ctk.CTkEntry(
            self._input_row,
            placeholder_text="说点什么… / Say something…",
            font=ctk.CTkFont(family="微软雅黑", size=14),
            fg_color=BG_CARD, border_color=BORDER_DIM,
            text_color=TEXT_MAIN, placeholder_text_color=TEXT_DIM,
            corner_radius=22, height=44,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entry.bind("<Return>", lambda _e: self._on_send())

        self._send_btn = ctk.CTkButton(
            self._input_row,
            text="❤",
            font=ctk.CTkFont(size=20),
            fg_color=ACCENT_PINK, hover_color="#E05580",
            text_color="white", corner_radius=22,
            width=52, height=44,
            command=self._on_send,
        )
        self._send_btn.pack(side="right")

        # ── 聊天滚动区（填充剩余空间）────────────────────────────────────────
        self._chat = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_DARK, corner_radius=0,
            scrollbar_button_color=BORDER_DIM,
            scrollbar_button_hover_color=ACCENT_PURP,
        )
        self._chat.pack(fill="both", expand=True)

        # 欢迎气泡
        self._add_bubble("嗯，我在这儿呢… 有什么想说的吗？💕 / I'm here. Want to talk?", is_user=False)

    # ─── 气泡消息 ─────────────────────────────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool):
        row = ctk.CTkFrame(self._chat, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=3)

        ctk.CTkLabel(
            row, text=text,
            font=ctk.CTkFont(family="微软雅黑", size=13),
            fg_color=ACCENT_PINK if is_user else BUBBLE_HIS,
            text_color="white" if is_user else TEXT_MAIN,
            corner_radius=16,
            wraplength=250,
            anchor="e" if is_user else "w",
            justify="right" if is_user else "left",
            padx=14, pady=10,
        ).pack(side="right" if is_user else "left")

        self.after(80, lambda: self._chat._parent_canvas.yview_moveto(1.0))

    # ─── 状态 & 动画 ──────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = ACCENT_PINK):
        self._status_lbl.configure(text=text, text_color=color)

    def _show_stop(self):
        self._stop_btn.pack(
            fill="x", padx=40, pady=(6, 0),
            before=self._input_row,
        )

    def _hide_stop(self):
        self._stop_btn.pack_forget()

    def _on_stop(self):
        """用户点击停止按钮"""
        self._singing = False
        audio_module.stop()
        self._hide_stop()
        self._avatar.stop_glow()
        self._set_status("在线 / Online ·")
        self._entry.configure(state="normal")
        self._send_btn.configure(state="normal")

    # ─── 输入处理 ─────────────────────────────────────────────────────────────

    def _on_send(self):
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, "end")
        self._add_bubble(text, is_user=True)
        self._entry.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, user_input: str):
        """后台线程：处理 LLM + TTS + 音频播放"""
        def put(*args):
            self._queue.put(args)

        try:
            intent = detect_intent(user_input)

            if intent == "sing":
                put("status", "思考中… / Thinking…", TEXT_DIM)
                keyword = user_input
                for w in ["唱", "歌", "首", "一", "给我", "来", "个", "sing", "song", "听"]:
                    keyword = keyword.replace(w, "")
                keyword = keyword.strip()

                song = match_song(keyword) if keyword else None
                if not song:
                    song = get_random_song()

                if not song:
                    put("bubble", "歌曲库还没准备好呢 🥺 / The song library isn't ready yet.", False)
                    return

                title = song.get("title", "一首歌")
                put("bubble", f"好～给你唱《{title}》♪", False)

                intro = tts(f"好，给你唱{title}")
                put("status", "说话中… / Speaking…", ACCENT_PINK)
                put("glow", ACCENT_PINK)
                audio_module.play(intro)
                put("glow_off")

                put("status", f"准备《{title}》中… / Preparing song…", TEXT_DIM)
                self._singing = True
                wav = sing_song(song)

                if wav and self._singing:
                    put("singing_start")
                    audio_module.play(wav)
                    put("singing_end")
                elif not wav:
                    put("bubble", "嗓子有点不舒服…下次再唱给你听 🥺", False)
                    err_audio = tts("嗓子有点不舒服，下次再唱给你听")
                    put("glow", ACCENT_PINK)
                    audio_module.play(err_audio)
                    put("glow_off")

            elif intent == "sleep":
                put("status", "思考中… / Thinking…", TEXT_DIM)
                self._mode = "sleep"
                text = llm_chat(user_input, mode="sleep")
                put("bubble", text, False)
                audio = tts(text, slow=True)
                put("status", "哄你睡觉 🌙 / Sleep mode", ACCENT_PURP)
                put("glow", ACCENT_PURP)
                audio_module.play(audio)
                put("glow_off")

            elif intent == "wake":
                put("status", "思考中… / Thinking…", TEXT_DIM)
                self._mode = "normal"
                text = llm_chat(user_input, mode="normal")
                put("bubble", text, False)
                audio = tts(text)
                put("status", "说话中… / Speaking…", ACCENT_PINK)
                put("glow", ACCENT_PINK)
                audio_module.play(audio)
                put("glow_off")

            else:  # 普通聊天
                put("status", "思考中… / Thinking…", TEXT_DIM)
                text = llm_chat(user_input, mode=self._mode)
                put("bubble", text, False)
                audio = tts(text)
                color = ACCENT_PURP if self._mode == "sleep" else ACCENT_PINK
                put("status", "说话中… / Speaking…", color)
                put("glow", color)
                audio_module.play(audio)
                put("glow_off")

        except Exception as e:
            print(f"[GUI worker 错误] {e}")
        finally:
            put("idle")

    # ─── 队列轮询 ─────────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                self._dispatch(self._queue.get_nowait())
        except queue.Empty:
            pass
        self.after(50, self._poll)

    def _dispatch(self, ev: tuple):
        tag = ev[0]
        if tag == "status":
            self._set_status(ev[1], ev[2])
        elif tag == "bubble":
            self._add_bubble(ev[1], ev[2])
        elif tag == "glow":
            self._avatar.start_glow(ev[1])
        elif tag == "glow_off":
            self._avatar.stop_glow()
            self._set_status("在线 / Online ·", ACCENT_PINK)
        elif tag == "singing_start":
            self._set_status("唱歌中 🎵 / Singing", ACCENT_PINK)
            self._avatar.start_glow(ACCENT_PINK)
            self._show_stop()
        elif tag == "singing_end":
            self._singing = False
            self._avatar.stop_glow()
            self._hide_stop()
            self._set_status("在线 / Online ·", ACCENT_PINK)
        elif tag == "idle":
            self._singing = False
            self._avatar.stop_glow()
            self._hide_stop()
            self._set_status("在线 / Online ·", ACCENT_PINK)
            self._entry.configure(state="normal")
            self._send_btn.configure(state="normal")
            self._entry.focus()

    # ─── 关闭 ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        audio_module.stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()

/* chat.js v3 — 灵魂伴侣 Web 版客户端
 *
 * v3 新增：
 * - 打电话模式：连续语音对话，自动循环听→说→听
 * - 通话 UI：大号头像、计时器、字幕
 */

const socket = io({ transports: ["websocket"] });

// ─── DOM refs ────────────────────────────────────────────────────────────
const chatArea    = document.getElementById("chatArea");
const inputBox    = document.getElementById("inputBox");
const sendBtn     = document.getElementById("sendBtn");
const stopSingBtn = document.getElementById("stopSingBtn");
const statusText  = document.getElementById("status-text");
const statusDot   = document.getElementById("status-dot");
const quickRow    = document.getElementById("quickRow");
const glowCanvas  = document.getElementById("glowCanvas");
const ctx         = glowCanvas.getContext("2d");
const callBtn     = document.getElementById("callBtn");
const hangUpBtn   = document.getElementById("hangUpBtn");
const callBanner  = document.getElementById("callBanner");
const callTimer   = document.getElementById("callTimer");
const callSubtitle= document.getElementById("callSubtitle");
const avatarWrap  = document.getElementById("avatarWrap");
const avatarCircle= document.getElementById("avatarCircle");
const inputArea   = document.getElementById("inputArea");
const micBtn      = document.getElementById("micBtn");

const UI_TEXT = {
  online: "在线 / Online · 等你说话 / Ready to listen",
  thinking: "思考中… / Thinking…",
  listening: "正在听… / Listening…",
  call: "📞 通话中 / In call",
};

// ─── State ───────────────────────────────────────────────────────────────
let currentReqId    = null;
let audioQueue      = [];
let audioPlaying    = false;
let currentAudio    = null;
let glowAnimId      = null;
let glowPhase       = 0;
let currentGlowColor = null;
let audioUnlocked   = false;
let typingRow       = null;
let lastMsgTime     = 0;

// ── 通话状态 ──
let callMode     = false;    // 是否在通话界面
let callListening = false;   // 通话中是否正在听
let callStartTime = 0;       // 通话开始时间戳
let callTimerId   = null;    // 计时器 interval
let callSilenceTimer = null; // 静音检测定时器
let callRecognition = null;  // 通话专用 SpeechRecognition

// ─── Audio unlock ────────────────────────────────────────────────────────
let _unlockAudio = null;

function unlockAudio() {
  if (audioUnlocked) return;
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (AC) {
      _unlockAudio = _unlockAudio || new AC();
      if (_unlockAudio.state === 'suspended') {
        _unlockAudio.resume();
      }
      const buf = _unlockAudio.createBuffer(1, 1, 22050);
      const src = _unlockAudio.createBufferSource();
      src.buffer = buf;
      src.connect(_unlockAudio.destination);
      src.start(0);
      const silent = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA");
      silent.play().then(() => { silent.pause(); silent.remove(); }).catch(() => {});
    }
  } catch(e) {}
  audioUnlocked = true;
}

// ─── Utils ───────────────────────────────────────────────────────────────
function genReqId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function setStatus(text, color) {
  statusText.textContent = text;
  statusText.style.color = color || "";
}

function setDot(state) {
  statusDot.className = "dot " + state;
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  inputBox.disabled = busy;
  if (callBtn) callBtn.disabled = busy;
}

// ─── Quick replies ───────────────────────────────────────────────────────
const QUICK_POOLS = {
  default: [
    { send: "想你啦", label: "想你啦 / Miss you" },
    { send: "在干嘛呢", label: "在干嘛呢 / What are you doing?" },
    { send: "我今天好累", label: "我今天好累 / I'm tired today" },
    { send: "陪我聊聊", label: "陪我聊聊 / Talk with me" },
    { send: "睡不着…", label: "睡不着… / Can't sleep" },
    { send: "唱首歌吧", label: "唱首歌吧 / Sing for me" },
  ],
  sleep: [
    { send: "嗯…晚安", label: "嗯…晚安 / Good night" },
    { send: "再陪我一会", label: "再陪我一会 / Stay a bit longer" },
    { send: "你也要睡了吗", label: "你也要睡了吗 / Are you sleeping too?" },
  ],
  wake: [
    { send: "早安", label: "早安 / Good morning" },
    { send: "睡醒了", label: "睡醒了 / I'm awake" },
    { send: "做了个梦", label: "做了个梦 / I had a dream" },
  ],
  sing: [
    { send: "换一首", label: "换一首 / Another song" },
    { send: "唱你拿手的", label: "唱你拿手的 / Sing your best one" },
  ],
};

function updateQuickReplies(intent) {
  if (!quickRow) return;
  const pool = QUICK_POOLS[intent] || QUICK_POOLS.default;
  quickRow.innerHTML = pool.map(item => `<button class="quick-reply" data-send="${escAttr(item.send)}">${escHtml(item.label)}</button>`).join("");
  quickRow.querySelectorAll(".quick-reply").forEach(btn => {
    btn.addEventListener("click", () => {
      inputBox.value = btn.dataset.send || btn.textContent;
      sendMessage();
    });
  });
}

// ─── Glow ────────────────────────────────────────────────────────────────
const GLOW_COLORS = {
  pink:   [[255,107,157], [181,123,238]],
  purple: [[181,123,238], [143,83,209]],
  call:   [[255,107,157], [99,102,241]],
};

function startGlow(colorName) {
  if (glowAnimId) cancelAnimationFrame(glowAnimId);
  currentGlowColor = colorName;
  glowPhase = 0;
  animateGlow();
}

function stopGlow() {
  if (glowAnimId) cancelAnimationFrame(glowAnimId);
  glowAnimId = null;
  currentGlowColor = null;
  ctx.clearRect(0, 0, 220, 220);
}

function animateGlow() {
  glowPhase += 0.04;
  const cx = 110, cy = 110;
  ctx.clearRect(0, 0, 220, 220);

  if (currentGlowColor === 'rainbow') {
    const hueBase = (glowPhase * 28) % 360;
    const layers = [88, 78, 68, 58, 48];
    layers.forEach((radius, i) => {
      const alpha = (1 - i / layers.length) * 0.14;
      const hue = (hueBase + i * 30) % 360;
      const grad = ctx.createRadialGradient(cx, cy, radius - 14, cx, cy, radius);
      grad.addColorStop(0, `hsla(${hue},100%,70%,0)`);
      grad.addColorStop(1, `hsla(${hue},100%,70%,${alpha})`);
      ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = grad; ctx.fill();
    });
    glowAnimId = requestAnimationFrame(animateGlow);
    return;
  }

  const t = (Math.sin(glowPhase) + 1) / 2;
  const cols = GLOW_COLORS[currentGlowColor] || GLOW_COLORS.pink;
  const [r1, r2] = cols;
  const interp = (a, b, x) => Math.round(a + (b - a) * x);
  const r = interp(r1[0], r2[0], t), g = interp(r1[1], r2[1], t), b = interp(r1[2], r2[2], t);

  const layers = [80, 70, 60, 50, 40];
  layers.forEach((radius, i) => {
    const alpha = (1 - i / layers.length) * 0.18;
    ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`; ctx.fill();
  });
  glowAnimId = requestAnimationFrame(animateGlow);
}

// ─── Audio queue ─────────────────────────────────────────────────────────
function enqueueAudio(url, onEnded) {
  audioQueue.push({ url, onEnded: onEnded || null });
  if (!audioPlaying) dequeueAudio();
}

function dequeueAudio() {
  if (audioQueue.length === 0) {
    audioPlaying = false;
    currentAudio = null;
    if (currentGlowColor === 'rainbow') stopGlow();
    // 通话模式：播放完后自动开始听
    if (callMode && !callListening) {
      setTimeout(() => startCallRecognition(), 600);
    }
    return;
  }
  audioPlaying = true;
  startGlow('rainbow');
  const item = audioQueue.shift();
  const a = new Audio(item.url);
  currentAudio = a;
  a.onended = () => {
    if (item.onEnded) item.onEnded();
    dequeueAudio();
  };
  a.onerror = () => {
    dequeueAudio();
  };
  a.play().catch(() => {
    if (currentGlowColor === 'rainbow') stopGlow();
    dequeueAudio();
    if (item.onEnded) item.onEnded();
  });
}

function stopAllAudio() {
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  audioQueue = [];
  audioPlaying = false;
}

// ─── Time divider ───────────────────────────────────────────────────────
function maybeAddTimeDivider() {
  const now = Date.now();
  if (now - lastMsgTime > 300000 && chatArea.children.length > 0) {
    const div = document.createElement("div");
    div.className = "time-divider";
    div.innerHTML = `<span>${formatTime(now)}</span>`;
    chatArea.appendChild(div);
  }
  lastMsgTime = now;
}

function formatTime(ts) {
  const d = new Date(ts);
  const h = d.getHours().toString().padStart(2, '0');
  const m = d.getMinutes().toString().padStart(2, '0');
  return `${h}:${m}`;
}

// ─── Typing indicator ────────────────────────────────────────────────────
function showTyping() {
  hideTyping();
  const row = document.createElement("div");
  row.className = "bubble-row bot typing-row";
  row.innerHTML = `
    <img class="bot-avatar" src="/static/avatar.png" alt="">
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  chatArea.appendChild(row);
  scrollBottom();
  typingRow = row;
}

function hideTyping() {
  if (typingRow) {
    typingRow.remove();
    typingRow = null;
  }
}

// ─── Empty state ─────────────────────────────────────────────────────────
function addEmptyHint() {
  if (chatArea.querySelector(".bubble-row")) return;
  const hint = document.createElement("div");
  hint.className = "empty-hint";
  hint.textContent = "💕 和他打声招呼吧… / Say hi to him…";
  chatArea.appendChild(hint);
}

function removeEmptyHint() {
  const h = chatArea.querySelector(".empty-hint");
  if (h) h.remove();
}

// ─── Bubble rendering ────────────────────────────────────────────────────
function addUserBubble(text) {
  removeEmptyHint();
  maybeAddTimeDivider();
  const row = document.createElement("div");
  row.className = "bubble-row user";
  row.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
  chatArea.appendChild(row);
  scrollBottom();
}

function addBotBubble(text) {
  hideTyping();
  removeEmptyHint();
  const row = document.createElement("div");
  row.className = "bubble-row bot";
  row.innerHTML = `<img class="bot-avatar" src="/static/avatar.png" alt=""><div class="bubble">${escHtml(text)}</div>`;
  chatArea.appendChild(row);
  scrollBottom();
  return row.querySelector(".bubble");
}

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escAttr(s) {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

function scrollBottom() {
  requestAnimationFrame(() => {
    chatArea.scrollTop = chatArea.scrollHeight;
  });
}

// ─── Send message (文字模式) ─────────────────────────────────────────────
function sendMessage() {
  const text = inputBox.value.trim();
  if (!text || sendBtn.disabled) return;

  inputBox.value = "";
  addUserBubble(text);
  removeEmptyHint();
  unlockAudio();

  currentReqId = genReqId();
  // 通话模式用 call_message，否则用 chat_message
  const event = callModeActive() ? "call_message" : "chat_message";
  setBusy(true);
  setDot("busy");
  setStatus(UI_TEXT.thinking, "#B57BEE");
  startGlow("pink");
  showTyping();

  socket.emit(event, { text, req_id: currentReqId });
}

sendBtn.addEventListener("click", sendMessage);
inputBox.addEventListener("keydown", e => { if (e.key === "Enter") sendMessage(); });

// ─── Voice input (Web Speech API) — 文字模式 ─────────────────────────────
let recognition = null;
let isListening = false;

function initSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.style.display = "none";
    return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (e) => {
    let final = "";
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) {
        final += t;
      } else {
        interim += t;
      }
    }
    inputBox.value = final || interim;
    inputBox.focus();
  };

  recognition.onend = () => {
    stopListening();
    const text = inputBox.value.trim();
    if (text) sendMessage();
  };

  recognition.onerror = (e) => {
    console.log("[语音] 错误:", e.error);
    stopListening();
    if (e.error === "no-speech") {
      setStatus("没听到声音，再试一次？ / Didn't catch that.", "#FF6B9D");
    } else if (e.error === "not-allowed") {
      setStatus("需要麦克风权限 / Microphone permission needed", "#FF6B9D");
    }
    setTimeout(() => setStatus(UI_TEXT.online, "#8B7AA0"), 2500);
  };
}

function startListening() {
  if (!recognition || isListening || sendBtn.disabled) return;
  isListening = true;
  micBtn.classList.add("listening");
  inputBox.placeholder = "正在听… / Listening…";
  inputBox.value = "";
  setStatus("🎤 我在听… / I'm listening…", "#FF6B9D");
  startGlow("pink");
  recognition.start();
}

function stopListening() {
  if (!isListening) return;
  isListening = false;
  micBtn.classList.remove("listening");
  inputBox.placeholder = "打字或按🎤说话… / Type or tap the mic…";
  try { recognition.stop(); } catch(e) {}
}

micBtn.addEventListener("click", () => {
  if (isListening) {
    stopListening();
    const text = inputBox.value.trim();
    if (text) sendMessage();
  } else {
    startListening();
  }
});

// ═══════════════════════════════════════════════════════════════════════════
//  📞 打电话模式
// ═══════════════════════════════════════════════════════════════════════════

// 挂断关键词（通话中说这些话会触发挂断）
const HANGUP_KEYWORDS = [
  "挂了吧", "先挂了", "挂了", "挂电话", "拜拜", "再见",
  "先不说了", "不说了", "挂断", "就这样吧", "先这样",
  "bye", "bye bye", "goodbye", "拜", "88",
];

function callModeActive() {
  return callMode;
}

function toggleCallMode() {
  if (callMode) {
    hangUpCall();
  } else {
    startCall();
  }
}

function startCall() {
  callMode = true;
  callListening = false;
  callStartTime = Date.now();

  // UI 切换
  document.body.classList.add("call-mode");
  callBanner.classList.remove("hidden");
  hangUpBtn.classList.remove("hidden");
  callBtn.classList.add("active");
  inputArea.classList.add("hidden");

  // 开始计时
  updateCallTimer();
  callTimerId = setInterval(updateCallTimer, 1000);

  // 启动语音识别
  callRecognition = initCallRecognition();
  if (callRecognition) {
    startCallRecognition();
  }

  // 字幕
  callSubtitle.textContent = UI_TEXT.listening;

  // 状态 + 光晕
  setStatus(UI_TEXT.call, "#FF6B9D");
  setDot("busy");
  startGlow("call");

  // 添加一条通话开始的消息气泡
  addBotBubble("📞 我在呢，说吧… / I'm here, go ahead…");
}

function hangUpCall() {
  callMode = false;
  callListening = false;
  callRecognition = null;

  stopCallRecognition();

  // 停止所有音频
  stopAllAudio();

  // UI 恢复
  document.body.classList.remove("call-mode");
  callBanner.classList.add("hidden");
  hangUpBtn.classList.add("hidden");
  callBtn.classList.remove("active");
  inputArea.classList.remove("hidden");

  // 停止计时
  if (callTimerId) { clearInterval(callTimerId); callTimerId = null; }

  // 停止光晕
  stopGlow();
  setStatus(UI_TEXT.online, "#8B7AA0");
  setDot("idle");
  callSubtitle.textContent = "";

  setBusy(false);
  hideTyping();

  // 添加挂断气泡
  addBotBubble("嗯…挂了也没关系，我一直在的 💕 / It's okay, I'm still here.");
}

function updateCallTimer() {
  const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
  const m = Math.floor(elapsed / 60).toString().padStart(2, '0');
  const s = (elapsed % 60).toString().padStart(2, '0');
  callTimer.textContent = `${m}:${s}`;
}

// ── 通话专用语音识别（v2: continuous=false 更稳定）──
function initCallRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("[通话] SpeechRecognition 不支持");
    callBanner.querySelector(".call-banner-text").textContent = "⚠️ 浏览器不支持语音";
    return null;
  }
  
  const rec = new SpeechRecognition();
  rec.lang = "zh-CN";
  rec.interimResults = true;
  rec.continuous = false;   // ← v2: false 更稳定，每次自动重启
  rec.maxAlternatives = 1;

  rec.onstart = () => {
    console.log("[通话] 🎤 开始听");
    callListening = true;
    callSubtitle.textContent = UI_TEXT.listening;
    callSubtitle.classList.remove("listening");
  };

  rec.onresult = (e) => {
    let final = "";
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t;
      else interim += t;
    }
    const display = final || interim;
    console.log("[通话] 识别:", display);
    if (display) {
      callSubtitle.textContent = display;
      callSubtitle.classList.add("listening");
    }
  };

  rec.onerror = (e) => {
    console.log("[通话] 语音错误:", e.error, e.message);
    callListening = false;
    
    if (e.error === "not-allowed") {
      callSubtitle.textContent = "🔇 请允许麦克风权限 / Please allow microphone access";
      return; // 权限被拒，不重试
    }
    if (e.error === "no-speech") {
      callSubtitle.textContent = UI_TEXT.listening;
    } else if (e.error === "network") {
      callSubtitle.textContent = "网络问题，重试中… / Network issue, retrying…";
    } else {
      callSubtitle.textContent = "…";
    }
    
    // 错误后自动重试
    if (callMode && e.error !== "not-allowed") {
      setTimeout(() => {
        if (callMode && !callListening && !audioPlaying) {
          startCallRecognition();
        }
      }, 800);
    }
  };

  rec.onend = () => {
    console.log("[通话] 识别结束");
    callListening = false;
    
    // 检查是否有识别到的文本
    const text = (callSubtitle.textContent || "").trim();
    
    // 检测挂断关键词
    const lower = text.toLowerCase();
    if (HANGUP_KEYWORDS.some(kw => lower.includes(kw.toLowerCase())) && text.length < 10) {
      callSubtitle.textContent = "挂断中…";
      setTimeout(() => hangUpCall(), 300);
      return;
    }
    
    // 有有效文本 → 发送
    if (text && text !== UI_TEXT.listening && text !== "…" && text !== "正在听…" && !text.startsWith("🔇") && !text.startsWith("⚠️")) {
      console.log("[通话] 发送:", text);
      sendCallMessage(text);
      return; // sendCallMessage 会自己重启识别
    }
    
    // 没内容 → 自动重新开始听
    if (callMode && !audioPlaying) {
      setTimeout(() => {
        if (callMode && !callListening && !audioPlaying) {
          startCallRecognition();
        }
      }, 500);
    }
  };

  return rec;
}

function startCallRecognition() {
  if (!callRecognition || callListening || !callMode) {
    console.log("[通话] 跳过启动 rec=", !!callRecognition, "listening=", callListening, "mode=", callMode);
    return;
  }
  console.log("[通话] 启动识别…");
  try {
    callRecognition.start();
  } catch(e) {
    console.log("[通话] start() 异常:", e);
    // 可能已经在运行，先停再启
    try { callRecognition.abort(); } catch(e2) {}
    callListening = false;
    if (callMode) {
      setTimeout(() => startCallRecognition(), 300);
    }
  }
}

function stopCallRecognition() {
  callListening = false;
  if (callRecognition) {
    try { callRecognition.abort(); } catch(e) {}
  }
}

function sendCallMessage(text) {
  if (!text || !callMode) return;

  callListening = false;
  stopCallRecognition();  // 暂停识别，等回复完再继续

  currentReqId = genReqId();
  addUserBubble(text);

  callSubtitle.textContent = "…";
  callSubtitle.classList.remove("listening");
  setDot("busy");
  setStatus("📞 … / Responding…", "#B57BEE");
  showTyping();

  socket.emit("call_message", { text, req_id: currentReqId });
}

// ── 通话按钮事件 ──
callBtn.addEventListener("click", toggleCallMode);
hangUpBtn.addEventListener("click", hangUpCall);

// ═══════════════════════════════════════════════════════════════════════════
//  SocketIO events
// ═══════════════════════════════════════════════════════════════════════════

// ── 通话事件 ──
socket.on("call_reply", data => {
  if (data.req_id !== currentReqId) return;
  hideTyping();
  const bubble = addBotBubble(data.text || "");
  startGlow("call");

  // 更新字幕
  callSubtitle.textContent = data.text || "";
  callSubtitle.classList.remove("listening");

  if (data.audio_url) {
    // 播放语音，结束后自动开始听
    enqueueAudio(data.audio_url);
  }
});

socket.on("call_done", data => {
  if (data.req_id !== currentReqId) return;
  setDot("busy");
  setStatus(UI_TEXT.call, "#FF6B9D");
  // 不要 reset busy - 等待音频播放完再重新开始听
});

socket.on("status", data => {
  if (data.req_id !== currentReqId) return;
  setStatus(data.text || "", data.color);
});

socket.on("bot_message", data => {
  if (data.req_id !== currentReqId) return;
  hideTyping();
  const glow = data.glow || "pink";
  addBotBubble(data.text || "");
  startGlow(glow);
  if (data.audio_url) {
    enqueueAudio(data.audio_url);
  }
});

socket.on("singing_start", data => {
  if (data.req_id !== currentReqId) return;
  stopSingBtn.classList.remove("hidden");
  setDot("singing");
  setStatus(`演唱《${data.title || "歌曲"}》中… / Singing now…`, "#B57BEE");
  startGlow("purple");
});

socket.on("song_ready", data => {
  if (data.req_id !== currentReqId) return;
  const title = data.title || "歌曲";
  hideTyping();
  const bubbles = chatArea.querySelectorAll(".bubble-row.bot .bubble");
  if (bubbles.length) {
    const last = bubbles[bubbles.length - 1];
    const lbl = document.createElement("div");
    lbl.className = "sing-label";
    lbl.textContent = `🎵 《${title}》`;
    last.appendChild(lbl);
  }
  enqueueAudio(data.audio_url, () => {
    stopSingBtn.classList.add("hidden");
    setDot("idle");
    setStatus(UI_TEXT.online, "#8B7AA0");
  });
});

socket.on("singing_end", data => {
  if (data.req_id !== currentReqId) return;
  stopSingBtn.classList.add("hidden");
  setDot("idle");
});

socket.on("server_done", data => {
  if (data.req_id !== currentReqId) return;
  // 通话模式不做 unlock（由 call_done 处理）
  if (callMode) return;
  const unlock = () => {
    setBusy(false);
    if (!audioPlaying && audioQueue.length === 0) {
      stopGlow();
      setDot("idle");
      setStatus(UI_TEXT.online, "#8B7AA0");
      hideTyping();
    }
  };
  setTimeout(unlock, 400);
});

// ── Stop singing ──
stopSingBtn.addEventListener("click", () => {
  if (!currentReqId) return;
  const oldReqId = currentReqId;
  socket.emit("stop_singing", { req_id: oldReqId });

  stopAllAudio();
  stopSingBtn.classList.add("hidden");
  stopGlow();

  currentReqId = genReqId();
  setBusy(true);
  setDot("busy");
  setStatus(UI_TEXT.thinking, "#B57BEE");
  startGlow("pink");
  showTyping();
  socket.emit("singing_stopped", { req_id: currentReqId });
});

socket.on("disconnect", () => {
  setStatus("连接断开…正在重连 / Reconnecting…", "#FF6B9D");
  setDot("idle");
});
socket.on("connect", () => {
  setStatus(UI_TEXT.online, "#8B7AA0");
  setDot("idle");
});

// ─── Init ────────────────────────────────────────────────────────────────
initSpeech();
addEmptyHint();
updateQuickReplies("default");

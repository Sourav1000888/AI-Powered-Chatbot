const API_BASE = "http://localhost:8000";
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const newChatBtn = document.getElementById("new-chat");
const attachBtn = document.getElementById("attach");
const fileInput = document.getElementById("file-input");
const previews = document.getElementById("previews");
const stopBtn = document.getElementById("stop");
let controller = null;

const EMPTY_HTML = '<p class="empty">Tell me, How can I help you.</p>';
const MAX_IMAGES = 4;
const MAX_DIM = 1568; // Claude isse bade resolution ko waise bhi chhota kar deta hai

let pending = []; // [{ dataUrl, data, media_type }]

function loadSessionId() {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}
let sessionId = loadSessionId();


/* ---------- Voice input (Web Speech API) ---------- */
const micBtn = document.getElementById("mic");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const SPEECH_LANG = "en-IN"; // English ke liye "en-IN" kar do

if (!SpeechRecognition) {
  micBtn.disabled = true;
  micBtn.title = "This browser not support audio input. Please try (chrome, edge)";
} else {
  const rec = new SpeechRecognition();
  rec.lang = SPEECH_LANG;
  rec.interimResults = true; // bolte waqt live text
  rec.continuous = true;

  let listening = false;
  let baseText = "";  // bolne se pehle textarea mein jo tha
  let finalText = ""; // jo pakka ho chuka

  function setListening(on) {
    listening = on;
    micBtn.classList.toggle("listening", on);
    micBtn.setAttribute("aria-pressed", String(on));
    const label = on ? "Recording Stop" : "Write from speak";
    micBtn.title = label;
    micBtn.setAttribute("aria-label", label);
  }

  rec.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += t;
      else interim += t;
    }
    input.value = baseText + finalText + interim;
    input.dispatchEvent(new Event("input")); // textarea ki height update
  };

  rec.onerror = (e) => {
    if (e.error === "no-speech" || e.error === "aborted") return;
    const msgs = {
      "not-allowed": "Mic ki permission block hai. Address bar mein mic allow karein.",
      "service-not-allowed": "Mic ki permission block hai. Address bar mein mic allow karein.",
      "audio-capture": "Mic nahi mila. Check karein ki mic laga hai.",
      network: "Voice service ke liye internet chahiye.",
    };
    alert(msgs[e.error] || `Voice input error: ${e.error}`);
  };

  rec.onend = () => setListening(false);

  micBtn.addEventListener("click", () => {
    if (listening) {
      rec.stop();
      return;
    }
    baseText = input.value ? input.value.trimEnd() + " " : "";
    finalText = "";
    try {
      rec.start();
      setListening(true);
    } catch {
      /* pehle se chal raha ho to ignore */
    }
  });

  // Send karte hi sunna band, taaki baad mein aaya text input mein na ghuse
  form.addEventListener("submit", () => {
    if (listening) rec.abort();
  });
}

/* ---------- Messages ---------- */

function addMessage(role, text = "", images = []) {
  chat.querySelector(".empty")?.remove();
  const el = document.createElement("div");
  el.className = `msg ${role}`;

  if (images.length) {
    const wrap = document.createElement("div");
    wrap.className = "thumbs";
    for (const img of images) {
      const t = document.createElement("img");
      t.src = img.dataUrl;
      t.alt = "sent image";
      wrap.appendChild(t);
    }
    el.appendChild(wrap);
  }
  if (text) el.appendChild(document.createTextNode(text));

  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
  return el;
}

async function restoreHistory() {
  try {
    const res = await fetch(`/history/${sessionId}`);
    if (!res.ok) return;
    const { messages } = await res.json();
    for (const m of messages) {
      const note = m.image_count ? `[${m.image_count} image send]\n` : "";
      addMessage(m.role === "assistant" ? "bot" : "user", note + m.text);
    }
  } catch {
    /* history na mile to khali chat se shuru */
  }
}

/* ---------- Images ---------- */

async function fileToImage(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DIM / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale);
  const h = Math.round(bitmap.height * scale);

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff"; // transparent PNG ke liye safed background
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close?.();

  const dataUrl = canvas.toDataURL("image/jpeg", 0.88);
  return { dataUrl, data: dataUrl.split(",")[1], media_type: "image/jpeg" };
}

async function addFiles(files) {
  for (const file of files) {
    if (!file.type.startsWith("image/")) continue;
    if (pending.length >= MAX_IMAGES) {
      alert(`One message has max ${MAX_IMAGES} images.`);
      break;
    }
    try {
      pending.push(await fileToImage(file));
    } catch {
      alert("This image is not supported try any others.");
    }
  }
  renderPreviews();
}

function renderPreviews() {
  previews.innerHTML = "";
  previews.classList.toggle("has", pending.length > 0);
  pending.forEach((img, i) => {
    const box = document.createElement("div");
    box.className = "thumb";
    const el = document.createElement("img");
    el.src = img.dataUrl;
    el.alt = "Preview";
    const rm = document.createElement("button");
    rm.type = "button";
    rm.textContent = "×";
    rm.setAttribute("aria-label", "Remove image");
    rm.addEventListener("click", () => {
      pending.splice(i, 1);
      renderPreviews();
    });
    box.append(el, rm);
    previews.appendChild(box);
  });
}

attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", async () => {
  await addFiles([...fileInput.files]);
  fileInput.value = "";
});

input.addEventListener("paste", (e) => {
  const files = [...(e.clipboardData?.files || [])].filter((f) => f.type.startsWith("image/"));
  if (files.length) {
    e.preventDefault();
    addFiles(files);
  }
});

chat.addEventListener("dragover", (e) => {
  e.preventDefault();
  chat.classList.add("dragging");
});
chat.addEventListener("dragleave", () => chat.classList.remove("dragging"));
chat.addEventListener("drop", (e) => {
  e.preventDefault();
  chat.classList.remove("dragging");
  addFiles([...e.dataTransfer.files]);
});



function renderSources(el, sources) {
  el.innerHTML = "";
  sources.forEach((s, i) => {
    let url;
    try { url = new URL(s.url); } catch { return; }
    if (!["http:", "https:"].includes(url.protocol)) return; // sirf safe links
    const a = document.createElement("a");
    a.href = url.href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = `${i + 1}. ${s.title || url.hostname}`;
    el.appendChild(a);
  });
}


/* ---------- Send ---------- */

async function send(text, images) {
  addMessage("user", text, images);
  const bot = addMessage("bot");

  const statusEl = document.createElement("div");
  statusEl.className = "status";
  statusEl.textContent = "Thinking...";
  const textEl = document.createElement("span");
  const srcEl = document.createElement("div");
  srcEl.className = "sources";
  bot.append(statusEl, textEl, srcEl);

  controller = new AbortController();
  sendBtn.hidden = true;
  stopBtn.hidden = false;
  let full = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        images: images.map(({ media_type, data }) => ({ media_type, data })),
      }),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop();

      for (const ev of events) {
        if (!ev.startsWith("data: ")) continue;
        const payload = JSON.parse(ev.slice(6));
        if (payload.error) throw new Error(payload.error);

        if (payload.status === "searching") {
          statusEl.hidden = false;
          statusEl.textContent = `Web searching... "${payload.query}"`;
        } else if (payload.status === "answering") {
          statusEl.hidden = false;
          statusEl.textContent = "Responsing...";
        }
        if (payload.text) {
          statusEl.hidden = true;
          full += payload.text;
          textEl.textContent = full;
        }
        if (payload.sources) renderSources(srcEl, payload.sources);
        chat.scrollTop = chat.scrollHeight;
      }
    }
  } catch (err) {
    if (err.name === "AbortError") {
      textEl.textContent = full ? full + "\n\n[STOP]" : "[STOP]";
    } else {
      bot.classList.add("error");
      textEl.textContent = full
        ? full + `\n\n[Stop in the middle: ${err.message}]`
        : `Do not getting answer: ${err.message}. try again.`;
    }
  } finally {
    statusEl.hidden = true;
    stopBtn.hidden = true;
    sendBtn.hidden = false;
    sendBtn.disabled = false;
    controller = null;
    input.focus();
  }
}



stopBtn.addEventListener("click", () => controller?.abort());
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") controller?.abort();
});
newChatBtn.addEventListener("click", () => {
  controller?.abort();
  fetch(`/session/${sessionId}`, { method: "DELETE" }).catch(() => {});
  sessionId = crypto.randomUUID();
  localStorage.setItem("session_id", sessionId);
  pending = [];
  renderPreviews();
  chat.innerHTML = EMPTY_HTML;
  input.focus();
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if ((!text && !pending.length) || sendBtn.disabled) return;
  const images = pending;
  pending = [];
  renderPreviews();
  input.value = "";
  input.style.height = "auto";
  send(text, images);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

restoreHistory();
const body = document.body;
const kind = body.dataset.kind;
const key = body.dataset.key || "";
let cfg = {
  alert_volume: Number(body.dataset.volume || 80) / 100,
  tts_volume: Number(body.dataset.ttsVolume || 85) / 100,
  duration: 8,
  tts: false,
  sound_enabled: true,
  gif: "",
  sound: "",
  alert_style: body.dataset.style || "glass",
  list_style: body.dataset.style || "cards",
  goal_style: body.dataset.style || "bar",
  list_size: 8,
};
let queue = [];
let playing = false;
let playGen = 0;
let hideTimer = 0;
let lastId = null;
const seenIds = new Set();
const audio = new Audio();
let overlaySocket = null;
let waitingReveal = null;
let waitingSleep = null;
const revealedIds = new Set();
const mediaCache = new Map();

function formatToman(value) {
  return Number(value || 0).toLocaleString("en-US");
}

function applyConfig(data) {
  cfg = { ...cfg, ...data };
  const alert = document.getElementById("alert");
  const list = document.getElementById("list");
  const goal = document.getElementById("goal");
  if (alert && cfg.alert_style) {
    const shown = alert.classList.contains("show");
    alert.className = `alert style-${cfg.alert_style}`;
    if (shown) alert.classList.add("show");
  }
  if (list && cfg.list_style) list.className = `list-box style-${cfg.list_style}`;
  if (goal && cfg.goal_style) goal.className = `goal-box style-${cfg.goal_style}`;
  audio.volume = Math.max(0, Math.min(1, cfg.alert_volume || 0));
  applyWidgetTheme();
  if (data.goal && kind === "goal") renderGoal(data.goal);
  if (kind === "gif" && Array.isArray(cfg.gifs)) {
    cfg.gifs.forEach((url) => preloadMedia(url));
  }
  if (kind === "gif" && cfg.gif) preloadMedia(cfg.gif);
}

function paint(el, name, value) {
  if (el && value) el.style.setProperty(name, value);
}

const LEGACY_FILL = new Set([
  "#a78bfa", "#7c4dff", "#7c5cff", "#7c3aed", "#a855f7", "#8b5cf6",
  "#c4b5fd", "#6d28d9", "#4c1d95", "#5b21b6",
  "#c9a227", "#e8c547", "#fde68a", "#fbbf24", "#e8b86d",
]);

function iceFill(value, fallback = "#7dd3fc") {
  const v = String(value || "").toLowerCase();
  if (!v || LEGACY_FILL.has(v)) return fallback;
  return value;
}

function darkIfLight(value, dark) {
  const v = String(value || "").toLowerCase();
  if (!v || v === "#ffffff" || v === "#fff" || v === "#fffffff2" || v === "#fffffff0") return dark;
  if (v === "#2e1065" || v === "#3b0764" || v === "#1e1b4b") return dark;
  if (v === "#e9e1ff" || v === "#2a2438") return "#1c1c20";
  return value;
}

function applyWidgetTheme() {
  const g = cfg.goal || {};
  const goal = document.getElementById("goal");
  if (goal) {
    paint(goal, "--fill", iceFill(g.fill));
    paint(goal, "--track", darkIfLight(g.track, "#1c1c20"));
    paint(goal, "--widget-text", darkIfLight(g.text, "#eef6fb"));
    paint(goal, "--widget-bg", darkIfLight(g.bg, "#121218"));
    paint(goal, "--widget-radius", `${g.radius ?? 20}px`);
    paint(goal, "--widget-font", `${g.font_size ?? 18}px`);
    paint(goal, "--bar-h", `${g.bar_height ?? 14}px`);
    goal.style.display = g.active === false ? "none" : "";
  }
  const list = document.getElementById("list");
  if (list) {
    paint(list, "--widget-bg", darkIfLight(cfg.list_bg, "#121218"));
    paint(list, "--widget-text", darkIfLight(cfg.list_text, "#eef6fb"));
  }
  const tops = document.querySelectorAll(".top-box, .timer-box");
  tops.forEach((el) => {
    paint(el, "--widget-bg", darkIfLight(cfg.list_bg || g.bg, "#121218"));
    paint(el, "--widget-text", darkIfLight(cfg.list_text || g.text, "#eef6fb"));
    paint(el, "--fill", iceFill(g.fill));
  });
  const alert = document.getElementById("alert");
  if (alert) {
    paint(alert, "--alert-text", "#fff");
    paint(alert, "--name-size", "14px");
  }
}

let wsLive = false;

function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${proto}//${location.host}/ws/overlay/?key=${encodeURIComponent(key)}`);
  overlaySocket = socket;
  socket.addEventListener("open", () => {
    wsLive = true;
    if (kind === "alert" || kind === "gif") {
      socket.send(JSON.stringify({ type: "hello", role: kind }));
    }
  });
  socket.addEventListener("message", (event) => onPayload(JSON.parse(event.data)));
  socket.addEventListener("close", () => {
    wsLive = false;
    overlaySocket = null;
    setTimeout(connect, 1500);
  });
}

async function poll() {
  try {
    const res = await fetch(`/overlay/snapshot/?key=${encodeURIComponent(key)}`);
    if (res.ok) onPayload(await res.json());
  } catch (err) {
    /* ignore */
  }
}

const mode = body.dataset.mode || "last";
const period = body.dataset.period || "all";
let rotate = [];
let rotateIndex = 0;

function onPayload(data) {
  if (data.type === "reveal") {
    const rid = String(data.id || "");
    if (rid) revealedIds.add(rid);
    if (waitingReveal && String(waitingReveal.id) === rid) {
      waitingReveal.finish();
    }
    return;
  }
  if (data.type === "skip") {
    skipAlert();
    return;
  }
  if (data.type === "timer" && kind === "timer") {
    applyTimerCommand(data);
    return;
  }
  if (data.type === "settings" || data.type === "snapshot") applyConfig(data);
  if (data.type === "snapshot") {
    if (kind === "list") renderList(listItems(data));
    if (kind === "goal") renderGoal(data.goal);
    if (kind === "top" || kind === "label") renderLabel(data);
    if (kind === "total") renderTotal(data);
    if (kind === "queue") startQueue(data.donors || []);
    if (!wsLive && data.latest && lastId && data.latest.id !== lastId && (kind === "alert" || kind === "gif") && !data.latest.skip_stream) {
      enqueue({ ...data, ...data.latest });
    }
    if (data.latest) lastId = data.latest.id;
  }
  if (data.type === "donation") {
    lastId = data.id;
    if (data.skip_stream) return;
    if (kind === "alert" || kind === "gif") enqueue(data);
    if (kind === "list") {
      if (mode === "last" && Array.isArray(data.ranked)) renderList(data.ranked, data.id);
      else if (data.show_in_list !== false) prependDonor(data);
    }
    if (kind === "goal") renderGoal(data.goal);
    if (kind === "top" || kind === "label") renderLabel(data);
    if (kind === "total") renderTotal(data);
    if (kind === "queue" && data.show_in_list !== false) {
      rotate.unshift(data);
      showQueueItem(data);
    }
  }
}

function skipAlert() {
  playGen += 1;
  queue = [];
  clearTimeout(hideTimer);
  if (waitingReveal) waitingReveal.finish();
  if (waitingSleep) waitingSleep.finish();
  const box = document.getElementById("alert");
  if (box) box.className = `alert style-${cfg.alert_style || "glass"}`;
  const media = document.getElementById("media");
  if (media) media.classList.remove("show");
  try {
    speechSynthesis.cancel();
  } catch (err) {
    /* ignore */
  }
  audio.pause();
  audio.removeAttribute("src");
  hideAlertMedia();
}

function listItems(data) {
  if (mode === "biggest") {
    return [...(data.donors || [])].sort((a, b) => b.amount - a.amount);
  }
  if (mode === "donors") {
    const map = {};
    (data.donors || []).forEach((d) => {
      map[d.name] = (map[d.name] || 0) + d.amount;
    });
    return Object.entries(map)
      .map(([name, amount]) => ({ name, amount, emoji: "👑" }))
      .sort((a, b) => b.amount - a.amount);
  }
  return Array.isArray(data.ranked) ? data.ranked : (data.donors || []);
}

function renderLabel(data) {
  const titles = { latest: "آخرین حمایت", biggest: "بزرگ‌ترین حمایت", donor: "بزرگ‌ترین حمایت‌کننده" };
  const title = document.getElementById("label-title");
  if (title) title.textContent = titles[mode] || titles.biggest;
  if (mode === "latest") renderTop(data.latest || data);
  else if (mode === "donor") renderTop(data.biggest_donor || data);
  else renderTop(data.biggest || data.top || data);
}

function renderTotal(data) {
  const labels = { day: "امروز", week: "هفته", month: "ماه", all: "کل" };
  const title = document.getElementById("total-title");
  const amount = document.getElementById("total-amount");
  if (title) title.textContent = `جمع حمایت‌ها (${labels[period] || "کل"})`;
  if (amount) amount.textContent = formatToman((data.totals || {})[period] || 0);
}

let queueTimer;
function startQueue(donors) {
  rotate = donors.slice();
  if (!rotate.length) return;
  showQueueItem(rotate[0]);
  if (queueTimer) return;
  queueTimer = setInterval(() => {
    if (!rotate.length) return;
    rotateIndex = (rotateIndex + 1) % rotate.length;
    showQueueItem(rotate[rotateIndex]);
  }, 5000);
}

function showQueueItem(item) {
  const li = document.getElementById("q-row");
  const name = document.getElementById("q-name");
  const amount = document.getElementById("q-amount");
  const label = [item.name, item.message].filter(Boolean).join(" · ");
  if (name) name.textContent = label || "—";
  if (amount) amount.textContent = formatToman(item.amount);
  if (li) {
    li.className = `${amountTier(item.amount)}${label.length > 22 ? " has-clip" : ""}`;
  }
}

function renderList(donors, freshId) {
  const root = document.getElementById("donors");
  if (!root) return;
  const titles = { last: "آخرین حمایت‌ها", biggest: "بزرگ‌ترین حمایت‌ها", donors: "بزرگ‌ترین حمایت‌کننده‌ها" };
  const heading = document.querySelector("#list h2");
  if (heading) heading.textContent = titles[mode] || titles.last;
  root.innerHTML = (donors || []).map((d, i) => itemHtml(d, i)).join("");
  if (freshId) {
    const el = root.querySelector(`[data-id="${freshId}"]`);
    if (el) el.classList.add("fresh");
  }
}

function prependDonor(data) {
  if (data.show_in_list === false) return;
  const root = document.getElementById("donors");
  if (!root) return;
  root.insertAdjacentHTML("afterbegin", itemHtml(data));
  while (root.children.length > (cfg.list_size || 8)) root.lastElementChild.remove();
}

function amountTier(amount) {
  const n = Number(amount || 0);
  if (n >= 1_000_000) return "tier-hot";
  if (n >= 200_000) return "tier-ice";
  return "tier-ash";
}

function itemHtml(d, index = 0) {
  const name = String(d.name || "").trim();
  const msg = String(d.message || "").trim();
  const label = mode === "last" ? name : (msg ? (name ? `${name} · ${msg}` : msg) : name);
  const clip = label.length > 14 ? " has-clip" : "";
  const rank = index < 6 ? String(index + 1) : "";
  const id = d.id != null ? String(d.id) : "";
  return `<li class="${amountTier(d.amount)} rank-${index + 1}${clip}" data-id="${escapeHtml(id)}"><span class="lead"><span class="rank">${rank}</span><span class="who">${escapeHtml(label)}</span></span><span class="amt">${formatToman(d.amount)}</span></li>`;
}

function renderGoal(goal) {
  if (!goal) return;
  const title = document.getElementById("goal-title");
  const fill = document.getElementById("goal-fill");
  const meta = document.getElementById("goal-meta");
  const ring = document.getElementById("goal-ring");
  const pct = document.getElementById("goal-pct");
  const ringPct = document.getElementById("goal-ring-pct");
  const currentEl = document.getElementById("goal-current");
  const targetEl = document.getElementById("goal-target");
  const details = `${formatToman(goal.current)} از ${formatToman(goal.target)}`;
  if (title) {
    title.textContent = goal.title || "هدف";
    title.style.display = goal.show_title === false ? "none" : "";
  }
  if (fill) {
    fill.style.width = `${goal.percent || 0}%`;
    fill.style.minWidth = (goal.percent || 0) > 0 ? "10px" : "0";
  }
  if (ring) ring.style.setProperty("--p", goal.percent || 0);
  const box = document.getElementById("goal");
  if (box) {
    box.style.setProperty("--p", goal.percent || 0);
    box.style.display = goal.active === false ? "none" : "";
  }
  if (pct) pct.textContent = `${goal.percent || 0} ٪`;
  if (ringPct) ringPct.textContent = `${goal.percent || 0}٪`;
  if (meta) {
    meta.textContent = details;
    meta.style.display = goal.show_details === false ? "none" : "";
  }
  if (currentEl) currentEl.textContent = formatToman(goal.current);
  if (targetEl) targetEl.textContent = formatToman(goal.target);
}

function renderTop(top) {
  if (!top) return;
  const name = document.getElementById("top-name");
  const amount = document.getElementById("top-amount");
  const emoji = document.getElementById("top-emoji");
  const label = String(top.name || "");
  if (name) name.textContent = label;
  if (amount) amount.textContent = formatToman(top.amount);
  if (emoji) emoji.textContent = top.emoji || "👑";
  const row = document.getElementById("top-row");
  if (row) row.className = `${amountTier(top.amount)}${label.length > 22 ? " has-clip" : ""}`;
}

function rememberId(id) {
  if (id == null || id === "") return false;
  const sid = String(id);
  if (seenIds.has(sid)) return true;
  seenIds.add(sid);
  if (seenIds.size > 250) {
    const oldest = seenIds.values().next().value;
    seenIds.delete(oldest);
  }
  return false;
}

function enqueue(data) {
  if (!data) return;
  if (rememberId(data.id)) return;
  queue.push(data);
  const url = data.gif || cfg.gif;
  if (url && kind === "gif") preloadMedia(url);
  pump();
}

function pump() {
  if (playing) return;
  playing = true;
  runLoop();
}

function waitMs(ms) {
  return new Promise((resolve) => {
    const wrapped = () => {
      clearTimeout(hideTimer);
      if (waitingSleep && waitingSleep.finish === wrapped) waitingSleep = null;
      resolve();
    };
    hideTimer = setTimeout(wrapped, Math.max(0, ms));
    waitingSleep = { finish: wrapped };
  });
}

function aborted(gen) {
  return gen !== playGen;
}

function isVideoUrl(url) {
  return /\.(webm|mp4|ogg)(\?|$)/i.test(url || "");
}

function mediaKey(url) {
  try {
    return new URL(url, location.origin).href.split("?")[0];
  } catch (err) {
    return url;
  }
}

function warmupVideo(src) {
  return new Promise((resolve) => {
    const v = document.createElement("video");
    let done = false;
    v.preload = "auto";
    v.muted = true;
    v.playsInline = true;
    v.src = src;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      v.oncanplaythrough = null;
      v.onerror = null;
      v.pause();
      resolve();
    };
    const timer = setTimeout(finish, 20000);
    v.oncanplaythrough = finish;
    v.onerror = finish;
    v.load();
  });
}

function warmupImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      img.onload = null;
      img.onerror = null;
      resolve();
    };
    const timer = setTimeout(finish, 20000);
    img.onload = finish;
    img.onerror = finish;
    img.src = src;
  });
}

function looksLikeVideo(url, blob) {
  if (blob && blob.type) {
    if (blob.type.startsWith("video/")) return true;
    if (blob.type.startsWith("image/")) return false;
  }
  return isVideoUrl(url) && !/\.(gif|png|webp|jpe?g)(\?|$)/i.test(url || "");
}

async function preloadMedia(url) {
  if (!url) return { src: "", video: false };
  if (url.startsWith("blob:")) return { src: url, video: isVideoUrl(url) };
  const key = mediaKey(url);
  if (mediaCache.has(key)) return mediaCache.get(key);
  const pending = (async () => {
    try {
      const ctrl = new AbortController();
      const abortTimer = setTimeout(() => ctrl.abort(), 45000);
      const res = await fetch(url, { cache: "default", credentials: "same-origin", signal: ctrl.signal });
      clearTimeout(abortTimer);
      if (!res.ok) throw new Error("fetch");
      const blob = await res.blob();
      if (!blob || blob.size < 32) throw new Error("empty");
      const obj = URL.createObjectURL(blob);
      const video = looksLikeVideo(url, blob);
      if (video) await warmupVideo(obj);
      else await warmupImage(obj);
      return { src: obj, video };
    } catch (err) {
      return { src: url, video: looksLikeVideo(url) };
    }
  })();
  mediaCache.set(key, pending);
  const ready = await pending;
  mediaCache.set(key, ready);
  return ready;
}

function notifyReady(id) {
  if (!id || !overlaySocket || overlaySocket.readyState !== 1) return;
  overlaySocket.send(JSON.stringify({ type: "media_ready", id, role: kind }));
}

function waitForReveal(id) {
  if (!id) return Promise.resolve();
  const sid = String(id);
  if (revealedIds.has(sid)) {
    revealedIds.delete(sid);
    return Promise.resolve();
  }
  if (!overlaySocket || overlaySocket.readyState !== 1) {
    notifyReady(id);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const wrapped = () => {
      clearTimeout(timer);
      if (waitingReveal && waitingReveal.finish === wrapped) waitingReveal = null;
      revealedIds.delete(sid);
      resolve();
    };
    const timer = setTimeout(wrapped, 45000);
    waitingReveal = { id: sid, finish: wrapped };
    if (revealedIds.has(sid)) {
      wrapped();
      return;
    }
    notifyReady(id);
    if (revealedIds.has(sid)) wrapped();
  });
}

function hideAlertMedia() {
  const img = document.getElementById("gif");
  const vid = document.getElementById("clip");
  if (img) {
    img.removeAttribute("src");
    img.style.display = "none";
  }
  if (vid) {
    vid.pause();
    vid.removeAttribute("src");
    vid.load();
    vid.style.display = "none";
  }
}

function waitClipReady(vid, src) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      vid.oncanplaythrough = null;
      vid.onerror = null;
      resolve();
    };
    const timer = setTimeout(finish, 8000);
    vid.oncanplaythrough = finish;
    vid.onerror = finish;
    vid.muted = false;
    vid.loop = false;
    vid.preload = "auto";
    vid.src = src;
    vid.style.display = "block";
    vid.load();
  });
}

async function armMedia(src, video) {
  if (kind !== "gif") return;
  const img = document.getElementById("gif");
  const vid = document.getElementById("clip");
  if (!src) {
    hideAlertMedia();
    return;
  }
  if (video) {
    if (img) {
      img.removeAttribute("src");
      img.style.display = "none";
    }
    if (vid) await waitClipReady(vid, src);
    return;
  }
  if (vid) {
    vid.pause();
    vid.removeAttribute("src");
    vid.style.display = "none";
  }
  if (img) {
    img.src = src;
    img.style.display = "block";
    await warmupImage(src);
  }
}

async function startArmedMedia() {
  if (kind !== "gif") return;
  const vid = document.getElementById("clip");
  if (!vid || vid.style.display === "none" || !vid.src) return;
  await vid.play().catch(() => {
    vid.muted = true;
    return vid.play().then(() => {
      vid.muted = false;
    }).catch(() => {});
  });
}

function clearRevealNoise(currentId) {
  const keep = currentId != null ? String(currentId) : "";
  for (const id of [...revealedIds]) {
    if (id !== keep) revealedIds.delete(id);
  }
}

async function playOne(data, gen) {
  const ms = Math.max(3, Number(data.duration || cfg.duration || 8)) * 1000;
  const url = data.gif || cfg.gif || "";
  clearRevealNoise(data.id);
  let ready = { src: "", video: looksLikeVideo(url) };
  if (url && kind === "gif") {
    ready = await preloadMedia(url);
    if (aborted(gen)) return;
    await armMedia(ready.src || url, ready.video);
  }
  if (aborted(gen)) return;
  await waitForReveal(data.id);
  if (aborted(gen)) return;

  if (kind === "gif") {
    const src = ready.src || url;
    await startArmedMedia();
    if (aborted(gen)) return;
    const media = document.getElementById("media");
    if (media) media.classList.toggle("show", Boolean(src));
    await waitMs(ms);
    if (aborted(gen)) return;
    if (media) media.classList.remove("show");
    hideAlertMedia();
    await waitMs(280);
    return;
  }

  const box = document.getElementById("alert");
  if (!box) return;
  document.getElementById("who").textContent = data.name;
  document.getElementById("amount").textContent = `مبلغ ${formatToman(data.amount)} تومان حمایت کرد`;
  document.getElementById("msg").textContent = data.message || "";
  const emo = document.getElementById("emoji");
  if (emo) emo.textContent = data.emoji || "";
  const style = data.alert_style || cfg.alert_style || "glass";
  box.className = `alert style-${style} show`;
  playSound(data);
  if (data.tts ?? cfg.tts) speak(`${data.name} ${formatToman(data.amount)} تومان. ${data.message || ""}`);
  await waitMs(ms);
  if (aborted(gen)) return;
  box.classList.remove("show");
  try {
    speechSynthesis.cancel();
  } catch (err) {
    /* ignore */
  }
  audio.pause();
  await waitMs(320);
}

async function runLoop() {
  try {
    while (queue.length) {
      const gen = playGen;
      const data = queue.shift();
      if (!data) break;
      await playOne(data, gen);
      if (aborted(gen)) break;
    }
  } finally {
    playing = false;
    if (queue.length) pump();
  }
}

function playSound(data) {
  if (kind !== "alert") return;
  if ((data.sound_enabled ?? cfg.sound_enabled) === false) return;
  const src = data.sound || cfg.sound;
  if (!src) return;
  audio.volume = Math.max(0, Math.min(1, data.alert_volume ?? cfg.alert_volume ?? 0.8));
  audio.src = `${src}?t=${Date.now()}`;
  audio.play().catch(() => {});
}

function playChime(volume) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "triangle";
    o.frequency.setValueAtTime(660, ctx.currentTime);
    o.frequency.exponentialRampToValueAtTime(990, ctx.currentTime + 0.12);
    g.gain.setValueAtTime(volume * 0.2, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
    o.connect(g);
    g.connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + 0.45);
  } catch (err) {
    /* ignore */
  }
}

function speak(text) {
  try {
    const utter = new SpeechSynthesisUtterance(text);
    const voices = speechSynthesis.getVoices();
    const fa = voices.find((v) => (v.lang || "").toLowerCase().startsWith("fa"));
    if (fa) utter.voice = fa;
    utter.lang = fa?.lang || "fa-IR";
    utter.volume = Math.max(0, Math.min(1, cfg.tts_volume || 0.85));
    utter.rate = Number(cfg.tts_rate || 1);
    utter.pitch = Number(cfg.tts_pitch || 1);
    speechSynthesis.cancel();
    speechSynthesis.speak(utter);
  } catch (err) {
    /* ignore */
  }
}

if (typeof speechSynthesis !== "undefined") {
  speechSynthesis.getVoices();
  speechSynthesis.addEventListener("voiceschanged", () => speechSynthesis.getVoices());
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

let timerMode = body.dataset.mode || "countdown";
let timerRemain = Number(body.dataset.seconds || 3600);
let timerElapsed = 0;
let timerRunning = timerMode === "stopwatch";
let lastTick = Date.now();

function pad(n) {
  return String(Math.floor(n)).padStart(2, "0");
}

function renderTimer() {
  const el = document.getElementById("timer-digits");
  if (!el) return;
  const total = timerMode === "stopwatch" ? timerElapsed : Math.max(0, timerRemain);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = Math.floor(total % 60);
  el.textContent = `${pad(h)} : ${pad(m)} : ${pad(s)}`;
  const box = document.querySelector(".donathon");
  if (box) {
    const initial = Number(body.dataset.seconds || 3600) || 3600;
    const elapsed = timerMode === "stopwatch" ? timerElapsed : Math.max(0, initial - timerRemain);
    const pct = timerMode === "stopwatch" ? Math.min(100, (timerElapsed / 3600) * 100) : Math.min(100, (elapsed / initial) * 100);
    box.style.setProperty("--sand", `${pct}%`);
  }
}

function applyTimerCommand(data) {
  if (data.action === "reset") {
    timerElapsed = 0;
    timerRemain = Number(data.seconds || body.dataset.seconds || 3600);
    timerRunning = false;
  } else if (data.action === "start") {
    if (data.seconds) timerRemain = Number(data.seconds);
    timerRunning = true;
    lastTick = Date.now();
  } else if (data.action === "pause") {
    timerRunning = false;
  }
  renderTimer();
}

if (kind === "timer") {
  renderTimer();
  setInterval(() => {
    if (!timerRunning) return;
    const now = Date.now();
    const dt = (now - lastTick) / 1000;
    lastTick = now;
    if (timerMode === "stopwatch") timerElapsed += dt;
    else timerRemain = Math.max(0, timerRemain - dt);
    renderTimer();
  }, 250);
}

connect();
setInterval(poll, 4000);
if (kind !== "timer") poll();

if (kind === "alert" && new URLSearchParams(location.search).has("demo")) {
  enqueue({
    name: "MOMD",
    amount: 20000000,
    message: "",
    duration: 600,
    sound_enabled: false,
    tts: false,
  });
}

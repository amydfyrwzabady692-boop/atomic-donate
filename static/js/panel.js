document.querySelectorAll(".copy").forEach((button) => {
  button.addEventListener("click", async () => {
    const input = button.parentElement.querySelector("input");
    const text = button.dataset.copy || input?.value;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    const prev = button.textContent;
    button.textContent = "کپی شد";
    setTimeout(() => {
      button.textContent = prev;
    }, 1200);
  });
});

document.querySelectorAll("input[data-output]").forEach((input) => {
  const target = document.getElementById(input.dataset.output);
  input.addEventListener("input", () => {
    if (target) target.textContent = input.value;
  });
});

const volumeState = {
  alert: document.querySelector('[data-live-volume="alert"]')?.value,
  tts: document.querySelector('[data-live-volume="tts"]')?.value,
};

async function pushVolume() {
  const body = new FormData();
  body.set("alert_volume", volumeState.alert || "80");
  body.set("tts_volume", volumeState.tts || "85");
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]");
  const headers = {};
  if (csrf) headers["X-CSRFToken"] = csrf.value;
  const dockKey = new URLSearchParams(location.search).get("key");
  const url = dockKey ? `/overlay/dock-volume/?key=${encodeURIComponent(dockKey)}` : "/panel/live-volume/";
  if (dockKey) body.set("key", dockKey);
  await fetch(url, { method: "POST", body, headers, credentials: "same-origin" });
}

let volumeTimer;
document.querySelectorAll("[data-live-volume]").forEach((input) => {
  input.addEventListener("input", () => {
    volumeState[input.dataset.liveVolume] = input.value;
    clearTimeout(volumeTimer);
    volumeTimer = setTimeout(pushVolume, 250);
  });
});

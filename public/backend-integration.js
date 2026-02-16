// ===================================
// BACKEND INTEGRATION MODULE
// ===================================

// Determine API base URL - works locally and on Render
const API_BASE = window.location.origin; // This will use the current domain

let stream = null;
let sendTimer = null;
let sending = false;

const state = {
  isLiveMode: false,
  detectionMode: "gesture",
  isMonitoring: true,
  eventCount: 0,
  events: [],
  startTime: Date.now(),
  isRender: window.location.hostname.includes('onrender.com') // Detect if on Render
};

// --- API CALLS ---

async function clearCanvas() {
  try {
    const res = await fetch(`${API_BASE}/api/clear_canvas`, { method: "POST" });
    const data = await res.json();
    if (data.ok) console.log("Canvas cleared");
  } catch (e) {
    console.error("Failed to clear canvas", e);
  }
}

async function setDetectionMode(mode) {
  state.detectionMode = mode;
  
  // Update UI buttons
  document.getElementById("motionModeBtn").classList.toggle("active", mode === "motion");
  document.getElementById("gestureModeBtn").classList.toggle("active", mode === "gesture");

  try {
    await fetch(`${API_BASE}/api/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode })
    });
  } catch (e) {
    console.error("Error setting mode", e);
  }
}

async function toggleMonitoring() {
  state.isMonitoring = !state.isMonitoring;
  updateUI();

  try {
    await fetch(`${API_BASE}/api/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd: "monitoring", enabled: state.isMonitoring })
    });
  } catch (e) {
    console.error("Error toggling monitoring", e);
  }
}

// --- VIEW SWITCHING (Live vs Demo) ---

async function switchView(view) {
  const goingLive = (view === "live");
  state.isLiveMode = goingLive;

  const canvas = document.getElementById("videoCanvas");
  const img = document.getElementById("videoImg");
  const demoBtn = document.getElementById("demoModeBtn");
  const liveBtn = document.getElementById("liveModeBtn");

  // Prevent double-start / double-stop
  if (goingLive && state._startingLive) return;
  if (!goingLive && state._stoppingLive) return;

  if (goingLive) {
    state._startingLive = true;

    try {
      // UI: Live uses browser camera -> show canvas, hide img
      canvas.style.display = "block";
      img.style.display = "none";
      img.src = "";

      demoBtn.classList.remove("active");
      liveBtn.classList.add("active");

      // Close any old SSE connection before starting
      if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
      }

      // Stop any previous loops/camera just in case
      stopSendingFrames();
      stopBrowserCamera();

      // Start browser camera and frame sending
      await startBrowserCamera(canvas);
      startSendingFrames(canvas);

      // Optional: connect SSE (only if your backend supports it + CORS works)
      connectSSE();
    } catch (err) {
      console.error("Failed to start Live mode:", err);

      // If Live fails, fallback to Demo UI state
      state.isLiveMode = false;
      demoBtn.classList.add("active");
      liveBtn.classList.remove("active");

      stopSendingFrames();
      stopBrowserCamera();

      canvas.style.display = "block";
      img.style.display = "none";
      img.src = "";
    } finally {
      state._startingLive = false;
    }

  } else {
    state._stoppingLive = true;

    try {
      // UI: Demo uses canvas drawing too (if you want demo animations),
      // otherwise you can hide canvas here. Keeping it visible is fine.
      canvas.style.display = "block";
      img.style.display = "none";
      img.src = "";

      demoBtn.classList.add("active");
      liveBtn.classList.remove("active");

      // Stop live camera + frame loop
      stopSendingFrames();
      stopBrowserCamera();

      // Stop SSE if used
      if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
      }
    } finally {
      state._stoppingLive = false;
    }
  }
}



// --- SSE HANDLING ---

function connectSSE() {
  if (state.eventSource) state.eventSource.close();

  state.eventSource = new EventSource(`${API_BASE}/events`);

  state.eventSource.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "gesture") {
      addLogEntry(`Gesture: ${data.meta?.status || "detected"}`, "started");
    } else if (data.type === "motion") {
      addLogEntry("Motion Detected", "started");
    }
  };

  state.eventSource.onerror = (err) => {
    console.error("SSE error:", err);
  };
}

// --- UI UPDATES ---

function updateUI() {
  const btn = document.getElementById("monitoringButton");
  const status = document.getElementById("systemStatus");
  
  if (state.isMonitoring) {
    btn.classList.add("monitoring-active");
    document.getElementById("monitoringText").textContent = "Stop Monitoring";
    status.textContent = "Monitoring Active";
  } else {
    btn.classList.remove("monitoring-active");
    document.getElementById("monitoringText").textContent = "Start Monitoring";
    status.textContent = "Paused";
  }
}

function addLogEntry(text, type) {
  const container = document.getElementById("logContainer");
  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.innerHTML = `<div class="log-status-dot ${type}"></div><div>${text}</div>`;
  container.prepend(entry);
}

// --- INIT ---
document.addEventListener("DOMContentLoaded", () => {
  setInterval(() => {
    const ts = document.getElementById("videoTimestamp");
    if (ts) ts.textContent = new Date().toLocaleTimeString();
  }, 1000);
  updateUI();
});

// functions to handle webcam access and sending frames to backend
async function startBrowserCamera(canvas) {
  if (stream) return;

  const video = document.createElement("video");
  video.autoplay = true;
  video.playsInline = true;
  video.muted = true;
  state._video = video;

  stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  video.srcObject = stream;
  await video.play(); // ✅ helps on some browsers

  await new Promise(res => video.onloadedmetadata = res);

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
}

function stopBrowserCamera() {
  if (!stream) return;
  stream.getTracks().forEach(t => t.stop());
  stream = null;
  state._video = null;
}

function startSendingFrames(canvas) {
  if (sendTimer) return;

  const ctx = canvas.getContext("2d");

  if (!canvas.width) canvas.width = 960;
  if (!canvas.height) canvas.height = 540;

  sendTimer = setInterval(async () => {
    if (!state._video) return;
    if (sending) return;
    sending = true;

    try {
      ctx.drawImage(state._video, 0, 0, canvas.width, canvas.height);

      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.7)
      );
      if (!blob) { sending = false; return; }

      const fd = new FormData();
      fd.append("frame", blob, "frame.jpg");

      const res = await fetch(`${API_BASE}/api/detect`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const text = await res.text();
        console.error("detect failed:", res.status, text);
        return;
      }

      const data = await res.json();

      if (Array.isArray(data.events) && data.events.length) {
        const last = data.events[data.events.length - 1];
        addLogEntry(`${last.type || "event"} detected`, "started");
      }
    } catch (e) {
      console.error("detect failed", e);
    } finally {
      sending = false;
    }
  }, 250);
}

function stopSendingFrames() {
  if (sendTimer) clearInterval(sendTimer);
  sendTimer = null;
}


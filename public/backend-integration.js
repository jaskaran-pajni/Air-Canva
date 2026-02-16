// ===================================
// BACKEND INTEGRATION MODULE
// ===================================

const API_BASE = "https://air-motion-canvas.onrender.com"; // Render backend
let stream = null;
let sendTimer = null;


const state = {
  isLiveMode: false,
  detectionMode: "gesture", // 'motion' or 'gesture'
  isMonitoring: true,
  eventCount: 0,
  events: [],
  startTime: Date.now(),
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
  state.isLiveMode = (view === "live");

  const canvas = document.getElementById("videoCanvas");
  const img = document.getElementById("videoImg");
  const demoBtn = document.getElementById("demoModeBtn");
  const liveBtn = document.getElementById("liveModeBtn");

  if (state.isLiveMode) {
    
    canvas.style.display = "block";
    img.style.display = "none";
    img.src = ""; // live img
    demoBtn.classList.remove("active");
    liveBtn.classList.add("active");

    await startBrowserCamera(canvas);
    startSendingFrames(canvas);
  } else {
    // Demo mode = stop camera + stop sending
    demoBtn.classList.add("active");
    liveBtn.classList.remove("active");

    stopSendingFrames();
    stopBrowserCamera();

    
    if (state.eventSource) state.eventSource.close();
  }
}


// --- SSE HANDLING ---

function connectSSE() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = new EventSource(`${API_BASE}/events`);

  state.eventSource.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "gesture") {
      addLogEntry(`Gesture: ${data.meta.status}`, "started");
    } else if (data.type === "motion") {
      addLogEntry("Motion Detected", "started");
    }
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

  sendTimer = setInterval(async () => {
    if (!state._video) return;

    // draw webcam to canvas (so user sees it)
    ctx.drawImage(state._video, 0, 0, canvas.width, canvas.height);

    // send frame to backend
    canvas.toBlob(async (blob) => {
      if (!blob) return;

      const fd = new FormData();
      fd.append("frame", blob, "frame.jpg");

      try {
        const res = await fetch(`${API_BASE}/api/detect`, { method: "POST", body: fd });
        const data = await res.json();

        // show logs quickly
        if (Array.isArray(data.events) && data.events.length) {
          const last = data.events[data.events.length - 1];
          addLogEntry(`${last.type || "event"} detected`, "started");
        }
      } catch (e) {
        console.error("detect failed", e);
      }
    }, "image/jpeg", 0.7);

  }, 250); // 4 fps
}

function stopSendingFrames() {
  if (sendTimer) clearInterval(sendTimer);
  sendTimer = null;
}


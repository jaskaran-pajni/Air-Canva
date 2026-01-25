// // ===================================
// // BACKEND INTEGRATION MODULE (FINAL)
// // ===================================

// const CONFIG = {
//   BACKEND_URL: window.location.origin,   // auto matches current host:port
//   SSE_ENDPOINT: "/events",
//   VIDEO_ENDPOINT: "/video_feed",
//   RECONNECT_DELAY: 3000,
// };

// // State Management
// const state = {
//   isLiveMode: false,
//   backendStatus: "disconnected",
//   eventSource: null,

//   // Monitor (local UI only for now)
//   isMonitoring: true,
//   soundEnabled: true,
//   sensitivity: 30,

//   // Events/UI
//   eventCount: 0,
//   currentStatus: "No Motion",
//   motionActive: false,
//   events: [],

//   // Timing
//   startTime: Date.now(),

//   // Canvas
//   canvas: null,
//   ctx: null,
// };

// // ===================================
// // BACKEND COMMUNICATION (SSE)
// // ===================================

// function connectToBackend() {
//   if (!state.isLiveMode) return;

//   if (state.eventSource) {
//     state.eventSource.close();
//     state.eventSource = null;
//   }

//   updateBackendStatus("connecting");

//   const url = `${CONFIG.BACKEND_URL}${CONFIG.SSE_ENDPOINT}`;
//   console.log("Connecting to backend SSE:", url);

//   state.eventSource = new EventSource(url);

//   state.eventSource.onopen = () => {
//     console.log("Backend connected (SSE open)");
//     updateBackendStatus("connected");
//   };

//   // Your server emits default "message" events:  data: {...}\n\n
//   state.eventSource.onmessage = (e) => {
//     try {
//       const data = JSON.parse(e.data);
//       handleBackendEvent(data);
//       updateBackendStatus("connected");
//     } catch (err) {
//       console.error("Failed to parse SSE JSON:", err, e.data);
//     }
//   };

//   state.eventSource.onerror = (error) => {
//     console.error("SSE connection error:", error);
//     updateBackendStatus("error");

//     if (state.isLiveMode) {
//       setTimeout(() => {
//         if (state.isLiveMode) connectToBackend();
//       }, CONFIG.RECONNECT_DELAY);
//     }
//   };
// }

// function disconnectFromBackend() {
//   if (state.eventSource) {
//     state.eventSource.close();
//     state.eventSource = null;
//   }
//   updateBackendStatus("disconnected");
// }

// // ===================================
// // BACKEND EVENT HANDLING
// // ===================================

// function handleBackendEvent(data) {
//   if (!data || typeof data !== "object") return;

//   // Motion events from your MotionDetector
//   if (data.type === "motion") {
//     if (!state.isMonitoring) return;

//     state.motionActive = true;
//     state.currentStatus = "Motion Detected";
//     state.eventCount++;

//     updateUI();
//     addLogEntry("Motion Detected", "started", data.confidence ?? "");

//     // Auto-clear after short delay so UI doesn't stick forever
//     setTimeout(() => {
//       state.motionActive = false;
//       state.currentStatus = state.isMonitoring ? "No Motion" : "Monitoring Paused";
//       updateUI();
//     }, 900);

//     return;
//   }

//   // Optional: gesture events
//   if (data.type === "gesture") {
//     if (!state.isMonitoring) return;

//     state.motionActive = true;
//     state.currentStatus = "Gesture Detected";
//     state.eventCount++;

//     updateUI();
//     addLogEntry("Gesture Detected", "started", data.meta?.status ?? "");

//     setTimeout(() => {
//       state.motionActive = false;
//       state.currentStatus = state.isMonitoring ? "No Motion" : "Monitoring Paused";
//       updateUI();
//     }, 900);

//     return;
//   }
// }

// // ===================================
// // MODE SWITCHING
// // ===================================

// function switchMode(mode) {
//   const isLive = mode === "live";
//   state.isLiveMode = isLive;

//   const demoBtn = document.getElementById("demoModeBtn");
//   const liveBtn = document.getElementById("liveModeBtn");
//   const backendStatus = document.getElementById("backendStatus");
//   const demoControls = document.getElementById("demoControls");

//   const canvas = document.getElementById("videoCanvas");
//   const img = document.getElementById("videoImg");

//   if (isLive) {
//     demoBtn?.classList.remove("active");
//     liveBtn?.classList.add("active");
//     if (backendStatus) backendStatus.style.display = "flex";
//     demoControls?.classList.remove("visible");

//     // Hide demo canvas
//     if (canvas) canvas.style.display = "none";

//     // Show MJPEG stream
//     if (img) {
//       img.style.display = "block";

//       // Force refresh even if browser caches/sticks
//       const base = `${CONFIG.BACKEND_URL}${CONFIG.VIDEO_ENDPOINT}`;
//       img.src = `${base}?t=${Date.now()}`;
//     }

//     connectToBackend();
//   } else {
//     demoBtn?.classList.add("active");
//     liveBtn?.classList.remove("active");
//     if (backendStatus) backendStatus.style.display = "none";
//     demoControls?.classList.add("visible");

//     // Stop MJPEG
//     if (img) {
//       img.src = "";
//       img.style.display = "none";
//     }

//     // Show demo canvas
//     if (canvas) canvas.style.display = "block";

//     disconnectFromBackend();
//   }
// }

// function updateBackendStatus(status) {
//   state.backendStatus = status;

//   const dot = document.getElementById("backendStatusDot");
//   const text = document.getElementById("backendStatusText");
//   if (!dot || !text) return;

//   dot.className = "backend-status-dot";

//   switch (status) {
//     case "connected":
//       dot.classList.add("connected");
//       text.textContent = "Connected";
//       break;
//     case "connecting":
//       text.textContent = "Connecting...";
//       break;
//     case "error":
//       dot.classList.add("error");
//       text.textContent = "Error";
//       break;
//     default:
//       text.textContent = "Disconnected";
//   }
// }

// // ===================================
// // CONTROL FUNCTIONS (LOCAL UI ONLY)
// // ===================================

// async function toggleMonitoring() {
//   state.isMonitoring = !state.isMonitoring;

//   if (!state.isMonitoring) {
//     state.motionActive = false;
//     state.currentStatus = "Monitoring Paused";
//   } else {
//     state.currentStatus = "No Motion";
//   }

//   updateUI();
// }

// async function updateSensitivity(value) {
//   state.sensitivity = parseInt(value, 10);
//   updateUI();
// }

// async function toggleSound() {
//   state.soundEnabled = !state.soundEnabled;
//   updateUI();
// }

// // ===================================
// // DEMO MODE FUNCTIONS
// // ===================================

// function triggerMotion() {
//   if (state.isLiveMode) {
//     alert("Switch to Demo Mode to use demo controls");
//     return;
//   }

//   if (!state.isMonitoring) {
//     alert("Monitoring is paused! Start monitoring first.");
//     return;
//   }

//   state.motionActive = true;
//   state.currentStatus = "Motion Detected";
//   state.eventCount++;

//   updateUI();
//   addLogEntry("Motion Started", "started");

//   setTimeout(() => {
//     state.motionActive = false;
//     state.currentStatus = "No Motion";
//     updateUI();
//     addLogEntry("Motion Ended", "ended", "2.0s");
//   }, 2000);
// }

// function autoMode() {
//   if (state.isLiveMode) {
//     alert("Switch to Demo Mode to use demo controls");
//     return;
//   }

//   if (!state.isMonitoring) {
//     alert("Please start monitoring first!");
//     return;
//   }

//   let count = 0;
//   const interval = setInterval(() => {
//     if (count >= 5) {
//       clearInterval(interval);
//       return;
//     }
//     triggerMotion();
//     count++;
//   }, 4000);
// }

// function clearLogs() {
//   state.events = [];
//   updateUI();
// }

// function clearAll() {
//   if (!confirm("Clear all events and reset counters?")) return;

//   state.eventCount = 0;
//   state.events = [];
//   updateUI();
// }

// // ===================================
// // LOG MANAGEMENT
// // ===================================

// function addLogEntry(text, type, duration = "") {
//   const now = new Date();
//   const timeStr = now.toLocaleTimeString();
//   const relativeTime = "a few seconds ago";

//   const entry = { text, type, duration, time: timeStr, relativeTime };

//   state.events.unshift(entry);
//   if (state.events.length > 20) state.events = state.events.slice(0, 20);

//   updateLogUI();
// }

// function updateLogUI() {
//   const logContainer = document.getElementById("logContainer");
//   if (!logContainer) return;

//   if (state.events.length === 0) {
//     logContainer.innerHTML = '<div class="log-empty">No recent events</div>';
//     return;
//   }

//   logContainer.innerHTML = state.events
//     .map(
//       (entry) => `
//         <div class="log-entry">
//           <div class="log-entry-header">
//             <div class="log-status-dot ${entry.type}"></div>
//             <div class="log-event-type">${entry.text}</div>
//             ${entry.duration ? `<div class="log-duration">${entry.duration}</div>` : ""}
//           </div>
//           <div class="log-timestamp">${entry.time} · ${entry.relativeTime}</div>
//         </div>
//       `
//     )
//     .join("");
// }

// // ===================================
// // UI UPDATE
// // ===================================

// function updateUI() {
//   const monitoringButton = document.getElementById("monitoringButton");
//   const buttonText = document.getElementById("monitoringText");
//   const buttonIcon = document.getElementById("buttonIcon");
//   const systemStatus = document.getElementById("systemStatus");
//   const headerStatus = document.getElementById("headerStatus");

//   if (state.isMonitoring) {
//     monitoringButton?.classList.add("monitoring-active");
//     if (buttonText) buttonText.textContent = "Stop Monitoring";
//     if (buttonIcon) buttonIcon.textContent = "■";
//     if (systemStatus) systemStatus.textContent = "Monitoring Active";
//     headerStatus?.classList.remove("paused");
//   } else {
//     monitoringButton?.classList.remove("monitoring-active");
//     if (buttonText) buttonText.textContent = "Start Monitoring";
//     if (buttonIcon) buttonIcon.textContent = "▶";
//     if (systemStatus) systemStatus.textContent = "Monitoring Paused";
//     headerStatus?.classList.add("paused");
//   }

//   const recIndicator = document.getElementById("recIndicator");
//   if (state.isMonitoring) recIndicator?.classList.add("recording");
//   else recIndicator?.classList.remove("recording");

//   const motionBadge = document.getElementById("motionBadge");
//   if (state.motionActive) motionBadge?.classList.add("active");
//   else motionBadge?.classList.remove("active");

//   const currentStatusEl = document.getElementById("currentStatus");
//   const eventCountEl = document.getElementById("eventCount");
//   if (currentStatusEl) currentStatusEl.textContent = state.currentStatus;
//   if (eventCountEl) eventCountEl.textContent = state.eventCount;

//   const sensVal = document.getElementById("sensitivityValue");
//   const sensSlider = document.getElementById("sensitivitySlider");
//   if (sensVal) sensVal.textContent = state.sensitivity + "%";
//   if (sensSlider) sensSlider.value = state.sensitivity;

//   const soundToggle = document.getElementById("soundToggle");
//   if (state.soundEnabled) soundToggle?.classList.add("active");
//   else soundToggle?.classList.remove("active");

//   updateLogUI();
// }

// // ===================================
// // VIDEO FEED RENDERING (DEMO CANVAS)
// // ===================================

// function drawVideoFeed() {
//   if (state.isLiveMode) return;
//   if (!state.ctx || !state.canvas) return;

//   const gradient = state.ctx.createLinearGradient(0, 0, state.canvas.width, state.canvas.height);
//   gradient.addColorStop(0, "#2a3f5f");
//   gradient.addColorStop(1, "#1a2332");
//   state.ctx.fillStyle = gradient;
//   state.ctx.fillRect(0, 0, state.canvas.width, state.canvas.height);

//   state.ctx.fillStyle = "rgba(255, 255, 255, 0.05)";
//   state.ctx.fillRect(100, 500, 300, 200);
//   state.ctx.fillRect(900, 400, 250, 300);

//   if (state.motionActive) {
//     state.ctx.strokeStyle = "#10b981";
//     state.ctx.lineWidth = 4;
//     const boxX = 400 + Math.random() * 200;
//     const boxY = 250 + Math.random() * 100;
//     state.ctx.strokeRect(boxX, boxY, 300, 250);
//   }

//   for (let i = 0; i < 50; i++) {
//     state.ctx.fillStyle = `rgba(255, 255, 255, ${Math.random() * 0.02})`;
//     state.ctx.fillRect(Math.random() * state.canvas.width, Math.random() * state.canvas.height, 2, 2);
//   }
// }

// function updateTimestamp() {
//   const now = new Date();
//   const hours = now.getHours() % 12 || 12;
//   const minutes = String(now.getMinutes()).padStart(2, "0");
//   const seconds = String(now.getSeconds()).padStart(2, "0");
//   const ampm = now.getHours() >= 12 ? "PM" : "AM";
//   const ts = document.getElementById("videoTimestamp");
//   if (ts) ts.textContent = `${hours}:${minutes}:${seconds} ${ampm}`;
// }

// function updateUptime() {
//   const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
//   const minutes = Math.floor(elapsed / 60);
//   const seconds = elapsed % 60;
//   const up = document.getElementById("uptime");
//   if (up) up.textContent = `${minutes}:${String(seconds).padStart(2, "0")}`;
// }

// // ===================================
// // INITIALIZATION
// // ===================================

// function init() {
//   state.canvas = document.getElementById("videoCanvas");
//   if (state.canvas) {
//     state.ctx = state.canvas.getContext("2d");
//     state.canvas.width = 1280;
//     state.canvas.height = 720;
//   }

//   // Default to Demo mode
//   document.getElementById("demoModeBtn")?.classList.add("active");

//   setInterval(updateTimestamp, 1000);
//   setInterval(updateUptime, 1000);
//   setInterval(drawVideoFeed, 100);

//   updateUI();

//   console.log("Motion Monitor initialized in Demo mode");
//   console.log("Backend URL:", CONFIG.BACKEND_URL);
// }

// if (document.readyState === "loading") {
//   document.addEventListener("DOMContentLoaded", init);
// } else {
//   init();
// }

// ===================================
// BACKEND INTEGRATION MODULE
// ===================================

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
    const res = await fetch("/api/clear_canvas", { method: "POST" });
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
    await fetch("/api/mode", {
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
    await fetch("/api/mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd: "monitoring", enabled: state.isMonitoring })
    });
  } catch (e) {
    console.error("Error toggling monitoring", e);
  }
}

// --- VIEW SWITCHING (Live vs Demo) ---

function switchView(view) {
  state.isLiveMode = (view === "live");
  
  const canvas = document.getElementById("videoCanvas");
  const img = document.getElementById("videoImg");
  const demoBtn = document.getElementById("demoModeBtn");
  const liveBtn = document.getElementById("liveModeBtn");

  if (state.isLiveMode) {
    canvas.style.display = "none";
    img.style.display = "block";
    img.src = `/video_feed?t=${Date.now()}`;
    demoBtn.classList.remove("active");
    liveBtn.classList.add("active");
    connectSSE();
  } else {
    canvas.style.display = "block";
    img.style.display = "none";
    img.src = "";
    demoBtn.classList.add("active");
    liveBtn.classList.remove("active");
    if (state.eventSource) state.eventSource.close();
  }
}

// --- SSE HANDLING ---

function connectSSE() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = new EventSource("/events");

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

// Force HTTPS for WebRTC on Render
if (window.location.hostname.includes('onrender.com') && window.location.protocol === 'http:') {
    window.location.protocol = 'https:';
}

// WebRTC handler loaded
console.log("%c🎥 WebRTC Handler Loaded", "color: blue; font-size: 16px; font-weight: bold");

// WebRTC variables
let webrtcPC = null;
let localStream = null;
let webrtcActive = false;
let remoteVideo = null;
let localVideoMonitor = null;
let eventCount = 0;

// Socket.IO connection
console.log("🔌 Connecting to Socket.IO server...");
const webrtcSocket = io({
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 20000
});

// ===== LOG FUNCTION FOR UI =====
window.addLogEntry = function(text, type) {
    const container = document.getElementById("logContainer");
    if (!container) return;
    
    const entry = document.createElement("div");
    entry.className = "log-entry";
    
    // Remove the "No recent events" placeholder if it exists
    const emptyMsg = container.querySelector(".log-empty");
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    entry.innerHTML = `<div class="log-status-dot ${type}"></div><div>${text}</div>`;
    container.prepend(entry);
    
    // Limit the number of log entries (keep last 50)
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
};
// ==============================

// Socket.IO event handlers
webrtcSocket.on('connect', () => {
    console.log("%c✅ Connected to WebRTC server", "color: green; font-size: 14px");
    if (window.addLogEntry) {
        window.addLogEntry('Connected to WebRTC server', 'started');
    }
});

webrtcSocket.on('connect_error', (error) => {
    console.error("%c❌ Socket.IO connection error:", "color: red; font-size: 14px", error);
});

webrtcSocket.on('disconnect', (reason) => {
    console.log("%c🔌 Socket.IO disconnected:", "color: orange; font-size: 14px", reason);
});


// Override the switchView function
window.switchView = async function(view) {
    console.log("%c🔄 Switch view called:", "color: purple; font-size: 14px", view);
    
    const canvas = document.getElementById("videoCanvas");
    const remoteVideoEl = document.getElementById("remoteVideo");
    const img = document.getElementById("videoImg");
    const demoBtn = document.getElementById("demoModeBtn");
    const liveBtn = document.getElementById("liveModeBtn");
    
    if (view === "live") {
        try {
            // Show canvas initially for local preview, hide others
            canvas.style.display = "block";
            remoteVideoEl.style.display = "none";
            img.style.display = "none";
            
            demoBtn.classList.remove("active");
            liveBtn.classList.add("active");
            
            stopCamera();
            await startCameraWithWebRTC(canvas);
            
        } catch (err) {
            console.error("%c❌ Failed to start live mode:", "color: red", err);
            if (window.addLogEntry) {
                window.addLogEntry("Camera failed: " + err.message, "ended");
            }
            canvas.style.display = "block";
            remoteVideoEl.style.display = "none";
            img.style.display = "none";
            demoBtn.classList.add("active");
            liveBtn.classList.remove("active");
        }
    } else {
        // Demo mode - show canvas for local preview
        canvas.style.display = "block";
        remoteVideoEl.style.display = "none";
        img.style.display = "none";
        demoBtn.classList.add("active");
        liveBtn.classList.remove("active");
        stopCamera();
    }
};

async function startCameraWithWebRTC(canvas) {
    console.log("%c📷 Starting camera with WebRTC...", "color: cyan; font-size: 14px");
    
    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Browser doesn't support camera access");
        }
        
        console.log("  Requesting camera access...");
        
        // OPTIMIZED: Lower resolution and frame rate for better performance
        localStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 320 },  // Reduced from 640
                height: { ideal: 240 },  // Reduced from 480
                frameRate: { ideal: 15 }  // Reduced from 30
            }, 
            audio: false 
        });
        
        console.log("%c✅ Got local stream", "color: green");
        console.log(`  Tracks: ${localStream.getTracks().length}`);
        
        localStream.getTracks().forEach(track => {
            console.log(`  Track: ${track.kind}`, {
                enabled: track.enabled,
                readyState: track.readyState,
                muted: track.muted,
                label: track.label
            });
        });
        
        // Skip frame monitor for performance (optional)
        // startFrameMonitor(localStream);
        
        const localVideo = document.createElement("video");
        localVideo.srcObject = localStream;
        localVideo.autoplay = true;
        localVideo.playsInline = true;
        localVideo.muted = true;
        
        await localVideo.play();
        console.log("✅ Local video playing");
        
        canvas.width = localVideo.videoWidth || 320;
        canvas.height = localVideo.videoHeight || 240;
        console.log(`📐 Canvas size set to: ${canvas.width} x ${canvas.height}`);
        
        const ctx = canvas.getContext('2d');
        let localFrameCount = 0;
        
        function drawLocal() {
            if (!webrtcActive && localVideo.readyState >= 2) {
                ctx.drawImage(localVideo, 0, 0, canvas.width, canvas.height);
                localFrameCount++;
                
                // Only draw text every few frames to reduce CPU
                if (localFrameCount % 15 === 0) {
                    ctx.fillStyle = 'white';
                    ctx.font = '12px Arial';
                    ctx.fillText(`Local: ${localFrameCount}`, 10, 20);
                    ctx.fillText(`Mode: ${window.currentMode || 'gesture'}`, 10, 40);
                }
                requestAnimationFrame(drawLocal);
            } else {
                requestAnimationFrame(drawLocal);
            }
        }
        drawLocal();
        
        await setupWebRTC(localStream, canvas);
        
    } catch (err) {
        console.error("%c❌ Camera error:", "color: red", err);
        throw err;
    }
}

// Optional: Remove or comment out startFrameMonitor for better performance
/*
function startFrameMonitor(stream) {
    const videoTrack = stream.getVideoTracks()[0];
    if (!videoTrack) {
        console.error("❌ No video track found in stream");
        return;
    }
    
    console.log("🎥 Starting frame monitor for track:", videoTrack.label);
    
    localVideoMonitor = document.createElement('video');
    localVideoMonitor.srcObject = new MediaStream([videoTrack]);
    localVideoMonitor.autoplay = true;
    localVideoMonitor.playsInline = true;
    localVideoMonitor.muted = true;
    localVideoMonitor.style.display = 'none';
    document.body.appendChild(localVideoMonitor);
    
    let frameCheckCount = 0;
    let lastLogTime = Date.now();
    
    localVideoMonitor.onloadeddata = () => {
        console.log("✅ Monitor video loaded, checking frames...");
        
        function checkFrame() {
            if (localVideoMonitor && localVideoMonitor.readyState >= 2) {
                frameCheckCount++;
                if (frameCheckCount % 30 === 0) {
                    const fps = Math.round(30 * 1000 / (Date.now() - lastLogTime));
                    console.log(`📸 Local camera: ${frameCheckCount} frames captured (${fps} fps)`);
                    lastLogTime = Date.now();
                }
            }
            requestAnimationFrame(checkFrame);
        }
        checkFrame();
    };
}
*/

async function setupWebRTC(stream, canvas) {
    console.log("%c🔧 Setting up WebRTC...", "color: orange; font-size: 14px");
    
    try {
        webrtcPC = new RTCPeerConnection({
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        });
        
        console.log("  Created RTCPeerConnection");
        
        stream.getTracks().forEach(track => {
            webrtcPC.addTrack(track, stream);
            console.log("  Added track to WebRTC:", track.kind);
        });
        
        webrtcPC.ontrack = (event) => {
            console.log("%c🔥 Received remote track:", "color: purple", event.track.kind);
            
            if (event.track.kind === 'video') {
                console.log("📹 Connecting remote video element");
                
                // Get the video element from HTML
                const remoteVideoEl = document.getElementById('remoteVideo');
                if (remoteVideoEl) {
                    remoteVideoEl.srcObject = event.streams[0];
                    remoteVideoEl.style.display = 'block';
                    
                    // CRITICAL: Ensure no mirroring
                    remoteVideoEl.style.transform = 'scaleX(1)';
                    remoteVideoEl.style.webkitTransform = 'scaleX(1)';
                    
                    // Hide canvas when remote video is playing
                    const canvas = document.getElementById("videoCanvas");
                    canvas.style.display = 'none';
                    
                    remoteVideoEl.onloadeddata = () => {
                        console.log("%c✅ Remote video playing!", "color: green");
                        webrtcActive = true;
                        
                        if (window.addLogEntry) {
                            window.addLogEntry("WebRTC connected - video playing", "started");
                        }
                    };
                    
                    remoteVideoEl.onerror = (err) => {
                        console.error("❌ Remote video error:", err);
                    };
                }
                
                event.track.onended = () => {
                    console.log("⛔ Remote track ended");
                    webrtcActive = false;
                    const remoteVideoEl = document.getElementById('remoteVideo');
                    if (remoteVideoEl) {
                        remoteVideoEl.style.display = 'none';
                    }
                    const canvas = document.getElementById("videoCanvas");
                    canvas.style.display = 'block';
                };
            }
        };
        
        webrtcPC.onconnectionstatechange = () => {
            if (webrtcPC.connectionState === 'connected') {
                console.log("%c✅✅✅ WebRTC FULLY CONNECTED!", "color: green; font-size: 14px");
                if (window.addLogEntry) {
                    window.addLogEntry('WebRTC fully connected', 'started');
                }
            }
        };
        
        webrtcPC.onicecandidate = (event) => {
            if (event.candidate) {
                webrtcSocket.emit('ice-candidate', event.candidate);
            }
        };
        
        console.log("📤 Creating offer...");
        const offer = await webrtcPC.createOffer({
            offerToReceiveVideo: true,
            offerToReceiveAudio: false
        });
        
        await webrtcPC.setLocalDescription(offer);
        console.log("✅ Local description set, sending offer");
        
        webrtcSocket.emit('offer', {
            sdp: webrtcPC.localDescription.sdp,
            type: webrtcPC.localDescription.type
        });
        
    } catch (err) {
        console.error("❌ WebRTC setup failed:", err);
        webrtcActive = false;
        throw err;
    }
}

function stopCamera() {
    console.log("%c🛑 Stopping camera...", "color: red");
    
    if (localVideoMonitor) {
        localVideoMonitor.srcObject = null;
        localVideoMonitor.remove();
        localVideoMonitor = null;
    }
    
    if (localStream) {
        localStream.getTracks().forEach(t => {
            t.stop();
        });
        localStream = null;
    }
    
    if (webrtcPC) {
        webrtcPC.close();
        webrtcPC = null;
    }
    
    webrtcActive = false;
    
    // Reset UI
    const canvas = document.getElementById("videoCanvas");
    const remoteVideoEl = document.getElementById("remoteVideo");
    if (canvas) canvas.style.display = 'block';
    if (remoteVideoEl) remoteVideoEl.style.display = 'none';
    
    console.log("✅ Camera stopped");
}

window.setDetectionMode = function(mode) {
    webrtcSocket.emit('mode_change', { mode: mode });
    
    document.getElementById("motionModeBtn").classList.toggle("active", mode === "motion");
    document.getElementById("gestureModeBtn").classList.toggle("active", mode === "gesture");
    window.currentMode = mode;
};

window.clearCanvas = function() {
    webrtcSocket.emit('clear_canvas');
};

webrtcSocket.on('answer', async (data) => {
    try {
        if (webrtcPC) {
            await webrtcPC.setRemoteDescription(new RTCSessionDescription(data));
        }
    } catch (err) {
        console.error('❌ Error setting remote description:', err);
    }
});

webrtcSocket.on('ice-candidate', async (candidate) => {
    try {
        if (webrtcPC) {
            await webrtcPC.addIceCandidate(new RTCIceCandidate(candidate));
        }
    } catch (err) {
        console.error('❌ Error adding ICE candidate:', err);
    }
});

webrtcSocket.on('detection_results', (events) => {
    eventCount += events.length;
    
    events.forEach((event) => {
        if (window.addLogEntry) {
            if (event.type === 'gesture') {
                window.addLogEntry(`Gesture: ${event.meta?.status || 'detected'}`, 'started');
            } else if (event.type === 'motion') {
                window.addLogEntry('Motion Detected', 'started');
            }
        }
    });
});

webrtcSocket.on('mode_changed', (data) => {
    if (window.addLogEntry) {
        window.addLogEntry(`Mode changed to: ${data.mode}`, 'ended');
    }
});

webrtcSocket.on('canvas_cleared', () => {
    if (window.addLogEntry) {
        window.addLogEntry('Canvas cleared', 'ended');
    }
});

console.log("%c🎥 WebRTC handler initialization complete", "color: blue");
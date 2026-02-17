// Force HTTPS for WebRTC on Render
if (window.location.hostname.includes('onrender.com') && window.location.protocol === 'http:') {
    window.location.protocol = 'https:';
}

// webrtc-handler.js - FIXED VERSION with camera debugging
console.log("WebRTC handler loaded");

// WebRTC variables
let webrtcPC = null;
let localStream = null;
let webrtcActive = false;
let remoteVideo = null;
let localVideoMonitor = null; // For monitoring local frames
const webrtcSocket = io();

// Override the switchView function
window.switchView = async function(view) {
    console.log("Switch view called:", view);
    
    const canvas = document.getElementById("videoCanvas");
    const img = document.getElementById("videoImg");
    const demoBtn = document.getElementById("demoModeBtn");
    const liveBtn = document.getElementById("liveModeBtn");
    
    if (view === "live") {
        try {
            // Update UI
            canvas.style.display = "block";
            img.style.display = "none";
            demoBtn.classList.remove("active");
            liveBtn.classList.add("active");
            
            // Stop any existing streams
            stopCamera();
            
            // Start camera with WebRTC
            await startCameraWithWebRTC(canvas);
            
        } catch (err) {
            console.error("Failed to start live mode:", err);
            if (window.addLogEntry) {
                window.addLogEntry("Camera failed: " + err.message, "ended");
            }
            
            // Fallback to demo
            canvas.style.display = "block";
            img.style.display = "none";
            demoBtn.classList.add("active");
            liveBtn.classList.remove("active");
        }
    } else {
        // Demo mode
        canvas.style.display = "block";
        img.style.display = "none";
        demoBtn.classList.add("active");
        liveBtn.classList.remove("active");
        stopCamera();
    }
};

async function startCameraWithWebRTC(canvas) {
    console.log("Starting camera with WebRTC...");
    
    try {
        // Check browser support
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Browser doesn't support camera access");
        }
        
        // Get local camera stream
        localStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 },
                frameRate: { ideal: 30 }
            }, 
            audio: false 
        });
        
        console.log("Got local stream, tracks:", localStream.getTracks().length);
        
        // Log detailed track information
        localStream.getTracks().forEach(track => {
            console.log(`  Track kind: ${track.kind}, enabled: ${track.enabled}, readyState: ${track.readyState}, muted: ${track.muted}`);
        });
        
        // Create a monitor to verify frames are actually being captured
        startFrameMonitor(localStream);
        
        // Show local video on canvas as fallback
        const localVideo = document.createElement("video");
        localVideo.srcObject = localStream;
        localVideo.autoplay = true;
        localVideo.playsInline = true;
        localVideo.muted = true;
        
        await localVideo.play();
        console.log("✅ Local video playing");
        
        // Verify video is actually playing
        if (localVideo.readyState < 2) {
            console.warn("⚠️ Local video not ready yet (readyState: " + localVideo.readyState + ")");
        } else {
            console.log("✅ Local video readyState: " + localVideo.readyState);
        }
        
        canvas.width = localVideo.videoWidth || 640;
        canvas.height = localVideo.videoHeight || 480;
        console.log(`📐 Canvas size set to: ${canvas.width} x ${canvas.height}`);
        
        // Draw local video initially with frame counter
        const ctx = canvas.getContext('2d');
        let localFrameCount = 0;
        
        function drawLocal() {
            if (!webrtcActive && localVideo.readyState >= 2) {
                ctx.drawImage(localVideo, 0, 0, canvas.width, canvas.height);
                localFrameCount++;
                
                // Draw frame counter on canvas for visual feedback
                ctx.fillStyle = 'white';
                ctx.font = '12px Arial';
                ctx.fillText(`Local frames: ${localFrameCount}`, 10, 20);
                
                if (localFrameCount % 30 === 0) {
                    console.log(`🎥 Local camera frame ${localFrameCount} drawn to canvas`);
                }
                requestAnimationFrame(drawLocal);
            } else {
                requestAnimationFrame(drawLocal);
            }
        }
        drawLocal();
        
        // Start WebRTC connection
        await setupWebRTC(localStream, canvas);
        
    } catch (err) {
        console.error("Camera error:", err);
        throw err;
    }
}

// New function to monitor local frames
function startFrameMonitor(stream) {
    const videoTrack = stream.getVideoTracks()[0];
    if (!videoTrack) {
        console.error("❌ No video track found in stream");
        return;
    }
    
    console.log("🎥 Starting frame monitor for track:", videoTrack.label);
    
    // Create a hidden video element to monitor frames
    localVideoMonitor = document.createElement('video');
    localVideoMonitor.srcObject = new MediaStream([videoTrack]);
    localVideoMonitor.autoplay = true;
    localVideoMonitor.playsInline = true;
    localVideoMonitor.muted = true;
    localVideoMonitor.style.display = 'none';
    document.body.appendChild(localVideoMonitor);
    
    let frameCheckCount = 0;
    localVideoMonitor.onloadeddata = () => {
        console.log("✅ Monitor video loaded, checking frames...");
        
        function checkFrame() {
            if (localVideoMonitor.readyState >= 2) {
                frameCheckCount++;
                if (frameCheckCount % 30 === 0) {
                    console.log(`📸 Local camera frame ${frameCheckCount} captured (monitor)`);
                }
            }
            requestAnimationFrame(checkFrame);
        }
        checkFrame();
    };
    
    // Also monitor track stats
    setInterval(() => {
        if (videoTrack && typeof videoTrack.getStats === 'function') {
            videoTrack.getStats().then(stats => {
                console.log("📊 Track stats:", stats);
            }).catch(err => {
                // getStats might not be available, ignore
            });
        }
    }, 5000);
}

async function setupWebRTC(stream, canvas) {
    console.log("Setting up WebRTC...");
    
    try {
        // Create peer connection
        webrtcPC = new RTCPeerConnection({
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        });
        
        // Add local stream tracks
        stream.getTracks().forEach(track => {
            webrtcPC.addTrack(track, stream);
            console.log("Added track to WebRTC:", track.kind);
        });
        
        // Add negotiation needed handler
        webrtcPC.onnegotiationneeded = () => {
            console.log("🔄 Negotiation needed");
        };
        
        // Handle incoming processed video
        webrtcPC.ontrack = (event) => {
            console.log("🔥 Received remote track:", event.track.kind);
            
            if (event.track.kind === 'video') {
                console.log("📹 Creating remote video element");
                
                // Create remote video element
                remoteVideo = document.createElement('video');
                remoteVideo.srcObject = new MediaStream([event.track]);
                remoteVideo.autoplay = true;
                remoteVideo.playsInline = true;
                remoteVideo.muted = true;
                
                remoteVideo.onloadedmetadata = () => {
                    console.log("✅ Remote video loaded! Dimensions:", 
                        remoteVideo.videoWidth, "x", remoteVideo.videoHeight);
                    
                    // Start drawing remote video
                    const ctx = canvas.getContext('2d');
                    webrtcActive = true;
                    
                    let frameCount = 0;
                    function drawRemote() {
                        if (webrtcActive && remoteVideo.readyState >= 2) {
                            ctx.drawImage(remoteVideo, 0, 0, canvas.width, canvas.height);
                            frameCount++;
                            if (frameCount % 30 === 0) {
                                console.log("🎨 Drawing remote video frame", frameCount);
                            }
                        }
                        requestAnimationFrame(drawRemote);
                    }
                    drawRemote();
                    
                    if (window.addLogEntry) {
                        window.addLogEntry("WebRTC connected - processing started", "started");
                    }
                };
                
                remoteVideo.onerror = (err) => {
                    console.error("❌ Remote video error:", err);
                };
                
                event.track.onended = () => {
                    console.log("⛔ Remote track ended");
                    webrtcActive = false;
                };
            }
        };
        
        // Handle connection state
        webrtcPC.onconnectionstatechange = () => {
            console.log("🔌 Connection state:", webrtcPC.connectionState);
            if (webrtcPC.connectionState === 'connected') {
                console.log("✅✅✅ WebRTC fully connected! Video should start flowing.");
                if (window.addLogEntry) {
                    window.addLogEntry('WebRTC fully connected', 'started');
                }
            } else if (webrtcPC.connectionState === 'failed') {
                console.error("❌ WebRTC connection failed");
                webrtcActive = false;
            }
        };
        
        // Enhanced ICE connection state monitoring with stats
        webrtcPC.oniceconnectionstatechange = () => {
            console.log("❄️ ICE connection state:", webrtcPC.iceConnectionState);
            
            if (webrtcPC.iceConnectionState === 'connected') {
                console.log("✅ ICE Connected - checking stats...");
                
                // Check stats to see if video is actually sending
                webrtcPC.getStats().then(stats => {
                    stats.forEach(report => {
                        if (report.type === 'outbound-rtp' && report.kind === 'video') {
                            console.log(`📤 Video packets sent: ${report.packetsSent}, bytes: ${report.bytesSent}`);
                        }
                        if (report.type === 'inbound-rtp' && report.kind === 'video') {
                            console.log(`📥 Video packets received: ${report.packetsReceived}, bytes: ${report.bytesReceived}`);
                        }
                    });
                }).catch(err => console.error("Stats error:", err));
            }
        };
        
        // Handle ICE candidates
        webrtcPC.onicecandidate = (event) => {
            if (event.candidate) {
                console.log("Sending ICE candidate");
                webrtcSocket.emit('ice-candidate', event.candidate);
            }
        };
        
        // Create offer
        console.log("Creating offer...");
        const offer = await webrtcPC.createOffer({
            offerToReceiveVideo: true,
            offerToReceiveAudio: false
        });
        
        await webrtcPC.setLocalDescription(offer);
        console.log("Local description set, sending offer");
        
        webrtcSocket.emit('offer', {
            sdp: webrtcPC.localDescription.sdp,
            type: webrtcPC.localDescription.type
        });
        
    } catch (err) {
        console.error("WebRTC setup failed:", err);
        webrtcActive = false;
        throw err;
    }
}

function stopCamera() {
    console.log("Stopping camera...");
    
    // Clean up monitor
    if (localVideoMonitor) {
        localVideoMonitor.srcObject = null;
        localVideoMonitor.remove();
        localVideoMonitor = null;
    }
    
    if (localStream) {
        localStream.getTracks().forEach(t => {
            t.stop();
            console.log("Stopped track:", t.kind);
        });
        localStream = null;
    }
    
    if (webrtcPC) {
        webrtcPC.close();
        webrtcPC = null;
    }
    
    webrtcActive = false;
    remoteVideo = null;
}

// Mode switching
window.setDetectionMode = function(mode) {
    console.log("Setting mode:", mode);
    webrtcSocket.emit('mode_change', { mode: mode });
    
    // Update UI
    document.getElementById("motionModeBtn").classList.toggle("active", mode === "motion");
    document.getElementById("gestureModeBtn").classList.toggle("active", mode === "gesture");
};

window.clearCanvas = function() {
    console.log("Clearing canvas");
    webrtcSocket.emit('clear_canvas');
};

// Socket.io event handlers
webrtcSocket.on('connect', () => {
    console.log('Connected to WebRTC server');
    if (window.addLogEntry) {
        window.addLogEntry('Connected to WebRTC server', 'started');
    }
});

webrtcSocket.on('answer', async (data) => {
    console.log("Received answer from server");
    try {
        if (webrtcPC) {
            await webrtcPC.setRemoteDescription(new RTCSessionDescription(data));
            console.log("Remote description set");
        }
    } catch (err) {
        console.error('Error setting remote description:', err);
    }
});

webrtcSocket.on('ice-candidate', async (candidate) => {
    console.log("Received ICE candidate");
    try {
        if (webrtcPC) {
            await webrtcPC.addIceCandidate(new RTCIceCandidate(candidate));
        }
    } catch (err) {
        console.error('Error adding ICE candidate:', err);
    }
});

webrtcSocket.on('detection_results', (events) => {
    events.forEach(event => {
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
    console.log("Mode changed to:", data.mode);
    if (window.addLogEntry) {
        window.addLogEntry(`Mode changed to: ${data.mode}`, 'ended');
    }
});

webrtcSocket.on('canvas_cleared', () => {
    console.log("Canvas cleared");
    if (window.addLogEntry) {
        window.addLogEntry('Canvas cleared', 'ended');
    }
});

// Add a simple camera test function you can run from console
window.testCamera = async function() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        console.log("✅ Camera test successful!", stream);
        const video = document.createElement('video');
        video.srcObject = stream;
        video.autoplay = true;
        video.controls = true;
        video.width = 320;
        document.body.appendChild(video);
        console.log("📹 Test video added to page - you should see yourself");
        return stream;
    } catch (err) {
        console.error("❌ Camera test failed:", err);
    }
};
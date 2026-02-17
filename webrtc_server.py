# webrtc_server.py
import asyncio
import cv2
import numpy as np
import json
import threading
import time
from fractions import Fraction

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate
from aiortc.rtcrtpparameters import RTCRtpCodecParameters
from aiortc import RTCRtpSender, RTCRtpReceiver
from aiortc.rtcconfiguration import RTCConfiguration, RTCIceServer
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import av
import os
import sys
import traceback

from config import CFG
from detectors.gesture_detector import GestureDetector
from detectors.motion_detector import MotionDetector

print("🚀 Starting WebRTC Server...", flush=True)

app = Flask(
    __name__,
    static_folder="public",
    static_url_path="",
)
app.config['SECRET_KEY'] = 'air-canvas-secret'
CORS(app)

# Socket.IO configuration - disable verbose logging for performance
socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    async_mode='threading',
                    path='/socket.io',
                    ping_timeout=60,
                    ping_interval=25,
                    logger=False,  # Disable for performance
                    engineio_logger=False)  # Disable for performance

# Store peer connections
pcs = set()

# Dictionary to track frame counts per connection
frame_counts = {}

# Global reference to the WebRTC event loop
rtc_loop = None

# Detection engines
IS_RENDER = os.environ.get('RENDER', False)
print(f"Running on Render: {IS_RENDER}", flush=True)

# Initialize detectors
print("Initializing GestureDetector...", flush=True)
gesture_detector = GestureDetector()
print("Initializing MotionDetector...", flush=True)
motion_detector = MotionDetector()
current_mode = "gesture"
print(f"🎮 Initial mode set to: {current_mode}", flush=True)

# Frame monitoring function (simplified for performance)
async def monitor_frame_counts():
    """Monitor frame counts and alert if no frames are being received"""
    while True:
        await asyncio.sleep(10)  # Check less frequently
        if frame_counts:
            for sid, count in list(frame_counts.items()):
                if count == 0:
                    print(f"⚠️ No frames for client {sid[:8]}", flush=True)
            frame_counts.clear()

# Start background monitoring thread
def start_background_loop():
    """Start asyncio event loop in a background thread"""
    global rtc_loop
    rtc_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(rtc_loop)
    rtc_loop.create_task(monitor_frame_counts())
    print("🔁 WebRTC event loop started", flush=True)
    rtc_loop.run_forever()

# Start monitoring in background thread
monitor_thread = threading.Thread(target=start_background_loop, daemon=True)
monitor_thread.start()
print("📊 Frame monitor started", flush=True)

class VideoTransformTrack(VideoStreamTrack):
    """Video track that processes frames with gesture detection"""
    
    def __init__(self, track, sid):
        super().__init__()
        self.track = track
        self.sid = sid
        self.processed_count = 0
        self.skip_counter = 0
        self.skip_every = 2  # Process every 2nd frame (50% reduction)
        self.target_width = 320  # Processing resolution
        self.target_height = 240
        frame_counts[sid] = 0
        print(f"🎥 VideoTransformTrack created for client {sid[:8]}", flush=True)

    async def recv(self):
        """Receive, process, and return the video frame"""
        try:
            # 1. Get the original frame from the user's camera
            frame = await self.track.recv()
            self.processed_count += 1
            self.skip_counter += 1
            frame_counts[self.sid] = self.processed_count

            # 2. Convert to numpy array (OpenCV format - BGR)
            img = frame.to_ndarray(format="bgr24")
            
            # Store original dimensions for later
            original_h, original_w = img.shape[:2]
            
            # 3. Resize for faster processing (320x240 is plenty for gesture detection)
            img_small = cv2.resize(img, (self.target_width, self.target_height))

            # 4. Run the detectors based on current mode (skip frames to reduce CPU)
            global current_mode
            events = []
            processed_img_small = img_small

            # Process only every Nth frame
            if self.skip_counter % self.skip_every == 0:
                if current_mode == "gesture" and gesture_detector and gesture_detector.available:
                    processed_img_small, events = gesture_detector.process(img_small)
                elif current_mode == "motion" and motion_detector:
                    processed_img_small, events = motion_detector.process(img_small)

            # 5. Send events to client via Socket.IO (only if there are events)
            if events:
                socketio.emit('detection_results', events, room=self.sid)

            # 6. Resize back to original size for display
            processed_img = cv2.resize(processed_img_small, (original_w, original_h))

            # 7. Convert BGR to RGB for browser
            rgb_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

            # 8. Rebuild the AV frame to send back to the browser
            new_frame = av.VideoFrame.from_ndarray(rgb_img, format="rgb24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            
            return new_frame

        except Exception as e:
            print(f"❌ Error in recv: {e}", flush=True)
            try:
                return await self.track.recv()
            except:
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                new_frame = av.VideoFrame.from_ndarray(blank, format="rgb24")
                new_frame.pts = 0
                new_frame.time_base = Fraction(1, 30)
                return new_frame

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('public', path)

@app.route('/health')
def health():
    return jsonify({"ok": True, "status": "healthy", "mode": current_mode})

@app.route('/api/clear_canvas', methods=['POST'])
def clear_canvas():
    """Clear the drawing canvas"""
    if gesture_detector and gesture_detector.available:
        gesture_detector.clear()
        socketio.emit('canvas_cleared')
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Gesture detector not available"}), 400

@app.route('/api/mode', methods=['POST'])
def set_mode():
    """Change detection mode"""
    global current_mode
    data = request.json
    mode = data.get('mode')
    if mode in ['gesture', 'motion']:
        current_mode = mode
        print(f"Mode changed to: {mode}", flush=True)
        socketio.emit('mode_changed', {'mode': mode})
        return jsonify({"ok": True, "mode": mode})
    return jsonify({"ok": False, "error": "Invalid mode"}), 400

@socketio.on('connect')
def handle_connect():
    print(f"✅ Client connected: {request.sid[:8]}", flush=True)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid[:8]}", flush=True)
    if request.sid in frame_counts:
        del frame_counts[request.sid]
    for pc in list(pcs):
        if hasattr(pc, 'sid') and pc.sid == request.sid:
            pcs.discard(pc)

@socketio.on('offer')
def handle_offer(data):
    """Handle WebRTC offer"""
    sid = request.sid
    print(f"📞 Received offer from {sid[:8]}", flush=True)

    async def _handle_offer():
        try:
            offer = RTCSessionDescription(sdp=data['sdp'], type=data['type'])
            
            pc = RTCPeerConnection(configuration=RTCConfiguration(
                iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")]
            ))
            pc.sid = sid
            pcs.add(pc)
            
            @pc.on('connectionstatechange')
            async def on_connectionstatechange():
                if pc.connectionState == "failed" or pc.connectionState == "closed":
                    if pc in pcs:
                        pcs.discard(pc)
            
            @pc.on('track')
            def on_track(track):
                if track.kind == 'video':
                    print(f"🎬 Video track received from {sid[:8]}", flush=True)
                    processed_track = VideoTransformTrack(track, sid)
                    pc.addTrack(processed_track)
                    
                    @track.on('ended')
                    async def on_ended():
                        await processed_track.stop()
            
            @pc.on('icecandidate')
            async def on_icecandidate(candidate):
                if candidate:
                    socketio.emit('ice-candidate', {
                        'candidate': candidate.candidate,
                        'sdpMid': candidate.sdpMid,
                        'sdpMLineIndex': candidate.sdpMLineIndex
                    }, room=sid)
            
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            socketio.emit('answer', {
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type
            }, room=sid)
            
            print(f"✅ Answer sent to {sid[:8]}", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling offer: {e}", flush=True)

    if rtc_loop:
        asyncio.run_coroutine_threadsafe(_handle_offer(), rtc_loop)

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    """Handle ICE candidates"""
    sid = request.sid

    async def _add_candidate():
        for pc in pcs:
            if hasattr(pc, 'sid') and pc.sid == sid:
                try:
                    parts = data['candidate'].split()
                    
                    if len(parts) >= 8 and parts[0].startswith('candidate:'):
                        foundation = parts[0].replace('candidate:', '')
                        component = int(parts[1])
                        protocol = parts[2]
                        priority = int(parts[3])
                        ip = parts[4]
                        port = int(parts[5])
                        cand_type = parts[7]
                        
                        candidate = RTCIceCandidate(
                            component=component,
                            foundation=foundation,
                            ip=ip,
                            port=port,
                            priority=priority,
                            protocol=protocol,
                            type=cand_type,
                            sdpMid=data['sdpMid'],
                            sdpMLineIndex=data['sdpMLineIndex']
                        )
                        
                        await pc.addIceCandidate(candidate)
                except Exception as e:
                    print(f"❌ Error adding ICE candidate: {e}", flush=True)

    if rtc_loop:
        asyncio.run_coroutine_threadsafe(_add_candidate(), rtc_loop)

@socketio.on('mode_change')
def handle_mode_change(data):
    """Change detection mode from client"""
    global current_mode
    mode = data.get('mode')
    if mode in ['gesture', 'motion']:
        current_mode = mode
        socketio.emit('mode_changed', {'mode': mode}, room=request.sid)

@socketio.on('clear_canvas')
def handle_clear_canvas():
    """Clear canvas from client"""
    if gesture_detector and gesture_detector.available:
        gesture_detector.clear()
        socketio.emit('canvas_cleared', room=request.sid)

print("✅ All routes registered", flush=True)
print(f"🚀 Server will start on port: {CFG.port}", flush=True)
print("=" * 50, flush=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", CFG.port))
    print(f"🎯 Starting server on port {port}...", flush=True)
    
    # Use eventlet for production (better performance)
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
# webrtc_server.py
import asyncio
import cv2
import numpy as np
import json
import threading
import time

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

# After creating the app, add this
socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    async_mode='threading',
                    path='/socket.io',  # Explicitly set the path
                    ping_timeout=60,
                    ping_interval=25)

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

# Frame monitoring function
async def monitor_frame_counts():
    """Monitor frame counts and alert if no frames are being received"""
    print("🔍 Starting frame monitor...", flush=True)
    while True:
        await asyncio.sleep(5)  # Check every 5 seconds
        if frame_counts:
            for sid, count in list(frame_counts.items()):
                if count == 0:
                    print(f"⚠️ WARNING: No frames received for client {sid}!", flush=True)
                else:
                    print(f"📊 Client {sid[:8]} has received {count} frames", flush=True)
            # Reset counts for next check
            frame_counts.clear()
        else:
            print("📊 No active clients", flush=True)

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
print("📊 Frame monitor started in background thread", flush=True)

class VideoTransformTrack(VideoStreamTrack):
    """Video track that processes frames with gesture detection"""
    
    def __init__(self, track, sid):
        super().__init__()
        self.track = track
        self.sid = sid
        self.frame_count = 0
        self.last_frame = None
        frame_counts[sid] = 0
        print(f"🎥 VideoTransformTrack created for {sid[:8]}", flush=True)
        
        # Start the frame reader task in the RTC loop
        asyncio.run_coroutine_threadsafe(self._read_frames(), rtc_loop)
        
    async def _read_frames(self):
        """Continuously read frames from the incoming track"""
        print(f"📖 Starting frame reader for {self.sid[:8]}", flush=True)
        try:
            while True:
                try:
                    # Read frame from the track
                    frame = await self.track.recv()
                    self.frame_count += 1
                    
                    # Store the last frame for sending back
                    self.last_frame = frame
                    frame_counts[self.sid] = self.frame_count
                    
                    if self.frame_count == 1:
                        print(f"✅✅✅ FIRST FRAME received from {self.sid[:8]}! Video is flowing!", flush=True)
                        print(f"  Frame size: {frame.width} x {frame.height}", flush=True)
                    elif self.frame_count % 30 == 0:
                        print(f"📹 Frame {self.frame_count} received from {self.sid[:8]}", flush=True)
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"❌ Error reading frame: {e}", flush=True)
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            print(f"❌ Frame reader stopped: {e}", flush=True)
    
    async def recv(self):
        """Return the next video frame to send back to the client"""
        try:
            if self.last_frame is not None:
                # Process the frame with gesture detection before sending back
                global current_mode
                
                # Convert to numpy array for OpenCV
                img = self.last_frame.to_ndarray(format="bgr24")
                
                # Process based on mode
                if current_mode == "gesture" and gesture_detector and gesture_detector.available:
                    img, events = gesture_detector.process(img)
                    if events:
                        # Send events to client via socketio
                        socketio.emit('detection_results', events, room=self.sid)
                elif current_mode == "motion" and motion_detector:
                    img, events = motion_detector.process(img)
                    if events:
                        socketio.emit('detection_results', events, room=self.sid)
                
                # Convert back to AV frame
                new_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
                new_frame.pts = self.last_frame.pts
                new_frame.time_base = self.last_frame.time_base
                return new_frame
            else:
                # Return a blank frame with a message
                print(f"⏳ No frames yet for {self.sid[:8]}, sending blank", flush=True)
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for video...", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(blank, f"Client: {self.sid[:8]}", (50, 280),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                frame = av.VideoFrame.from_ndarray(blank, format="bgr24")
                frame.pts = 0
                frame.time_base = 1/30
                return frame
                
        except Exception as e:
            print(f"❌ Error in recv: {e}", flush=True)
            raise

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
    return jsonify({"ok": True, "status": "healthy"})

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
    print(f"✅ Client connected: {request.sid}", flush=True)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid}", flush=True)
    # Clean up frame count
    if request.sid in frame_counts:
        del frame_counts[request.sid]
    # Clean up peer connection
    for pc in list(pcs):
        if hasattr(pc, 'sid') and pc.sid == request.sid:
            pcs.discard(pc)

@socketio.on('offer')
def handle_offer(data):
    """Handle WebRTC offer"""
    sid = request.sid
    print(f"📞 Received offer from {sid}", flush=True)

    async def _handle_offer():
        try:
            offer = RTCSessionDescription(sdp=data['sdp'], type=data['type'])
            
            # Create peer connection with STUN servers
            pc = RTCPeerConnection(configuration=RTCConfiguration(
                iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")]
            ))
            pc.sid = sid  # Store sid for cleanup
            pcs.add(pc)
            
            @pc.on('connectionstatechange')
            async def on_connectionstatechange():
                print(f"🔌 Connection state for {sid}: {pc.connectionState}", flush=True)
                if pc.connectionState == "failed" or pc.connectionState == "closed":
                    if pc in pcs:
                        pcs.discard(pc)
            
            @pc.on('iceconnectionstatechange')
            async def on_iceconnectionstatechange():
                print(f"❄️ ICE connection state for {sid}: {pc.iceConnectionState}", flush=True)
            
            @pc.on('track')
            def on_track(track):
                if track.kind == 'video':
                    print(f"🎬 Video track received from {sid}", flush=True)
                    print(f"  Track settings: {track.kind}", flush=True)
                    # Create processing track
                    processed_track = VideoTransformTrack(track, sid)
                    pc.addTrack(processed_track)
                    print(f"  ✅ Added VideoTransformTrack for {sid}", flush=True)
                    
                    @track.on('ended')
                    async def on_ended():
                        print(f"⛔ Track ended for {sid}", flush=True)
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
            
            print(f"✅ Answer sent to {sid}", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling offer: {e}", flush=True)
            traceback.print_exc()

    # Schedule this on the persistent RTC loop
    if rtc_loop:
        asyncio.run_coroutine_threadsafe(_handle_offer(), rtc_loop)
    else:
        print("❌ RTC loop not available!", flush=True)

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    """Handle ICE candidates"""
    sid = request.sid
    print(f"📨 Received ICE candidate from {sid}", flush=True)

    async def _add_candidate():
        for pc in pcs:
            if hasattr(pc, 'sid') and pc.sid == sid:
                try:
                    # Parse the candidate string
                    parts = data['candidate'].split()
                    
                    if len(parts) >= 8 and parts[0].startswith('candidate:'):
                        foundation = parts[0].replace('candidate:', '')
                        component = int(parts[1])
                        protocol = parts[2]
                        priority = int(parts[3])
                        ip = parts[4]
                        port = int(parts[5])
                        cand_type = parts[7]
                        
                        # Create candidate
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
                        print(f"✅ Added ICE candidate for {sid}", flush=True)
                    else:
                        print(f"⚠️ Unexpected candidate format", flush=True)
                        
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
        print(f"🔄 Mode changed to: {mode} by {request.sid}", flush=True)
        socketio.emit('mode_changed', {'mode': mode}, room=request.sid)

@socketio.on('clear_canvas')
def handle_clear_canvas():
    """Clear canvas from client"""
    if gesture_detector and gesture_detector.available:
        gesture_detector.clear()
        socketio.emit('canvas_cleared', room=request.sid)
        print(f"🧹 Canvas cleared for {request.sid}", flush=True)

print("✅ All routes registered", flush=True)
print(f"🚀 Server will start on port: {CFG.port}", flush=True)
print("=" * 50, flush=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", CFG.port))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
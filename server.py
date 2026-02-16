import numpy as np
import cv2
import os
import json
import time
import sys
import traceback
import builtins  # Add this
from flask_cors import CORS
from flask import Flask, Response, jsonify, request, stream_with_context
from config import CFG
from camera_manager import CameraManager
from event_store import EventStore
from actions import Actions
from pipeline import Pipeline



print("🚀 Starting server.py...", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Current directory: {os.getcwd()}", flush=True)
print(f"Files in directory: {os.listdir('.')}", flush=True)

# Check if running on Render
IS_RENDER = os.environ.get('RENDER', False)
print(f"Running on Render: {IS_RENDER}", flush=True)

try:
    app = Flask(
        __name__,
        template_folder="app/templates",
        static_folder="app/static",
        static_url_path="/app/static",
    )
    print("✅ Flask app created")
    
    CORS(app)
    print("✅ CORS enabled")
    
except Exception as e:
    print(f"❌ Error creating Flask app: {e}")
    traceback.print_exc()
    sys.exit(1)

# Initialize components with error handling
try:
    print("Initializing EventStore...")
    store = EventStore(CFG.log_path, maxlen=CFG.max_events_in_memory)
    print("✅ EventStore initialized")
    
    print("Initializing Actions...")
    actions = Actions(CFG.snapshot_dir)
    print("✅ Actions initialized")
    
    # Only initialize pipeline if NOT on Render, or handle gracefully
    if IS_RENDER:
        print("🚀 Running on Render - Camera features disabled")
        pipeline = None
    else:
        print("Initializing Pipeline...")
        pipeline = Pipeline(store, actions)
        if hasattr(pipeline, "set_mode"):
            pipeline.set_mode("gesture")
        print("✅ Pipeline initialized")
        
except Exception as e:
    print(f"❌ Error initializing components: {e}")
    traceback.print_exc()
    sys.exit(1)

@app.route("/")
def index():
    print("📍 Root endpoint accessed", flush=True)
    return jsonify({
        "ok": True, 
        "service": "air-motion-canvas-backend",
        "status": "running",
        "port": CFG.port
    })

@app.route("/health")
def health():
    """Health check endpoint with detailed info"""
    current_time = time.time()
    return jsonify({
        "ok": True,
        "status": "healthy",
        "timestamp": current_time,
        "port": CFG.port,
        "is_render": IS_RENDER,
        "service": "air-motion-canvas"
    })
    
@app.route("/healthz")
def healthz():
    """Super simple health check for Render's port scanner"""
    return "OK", 200, {'Content-Type': 'text/plain'}    
    
@app.route("/debug/routes")
def list_routes():
    """List all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "path": str(rule)
        })
    return jsonify({
        "routes": routes,
        "count": len(routes)
    })
    
@app.route("/debug")
def debug_info():
    """Debug endpoint to check system status"""
    return jsonify({
        "ok": True,
        "is_render": IS_RENDER,
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "files": os.listdir('.'),
        "env_vars": {k: v for k, v in os.environ.items() if not k.startswith('_')}
    })

@app.route("/video_feed")
def video_feed():
    print("📍 Video feed endpoint accessed")
    # Disable webcam on Render
    if IS_RENDER:
        return jsonify({"ok": False, "error": "Video feed not available on Render - this is a cloud deployment without camera access"}), 400
    
    def gen():
        cam = CameraManager(CFG.camera_index, CFG.width, CFG.height)
        try:
            cam.open()
            print(f"✅ /video_feed opened camera index={CFG.camera_index}")
            while True:
                ok, frame = cam.read()
                if not ok or frame is None:
                    time.sleep(0.03)
                    continue

                if pipeline and getattr(pipeline, "is_monitoring", True):
                    annotated = pipeline.step(frame)
                else:
                    annotated = frame

                ret, buf = cv2.imencode(".jpg", annotated)
                if not ret:
                    continue

                jpg = buf.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
                )
                time.sleep(0.03)
        except Exception as e:
            print("🔥 /video_feed generator crashed:", repr(e))
        finally:
            cam.close()
            print("扫 /video_feed camera closed")

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/detect", methods=["POST"])
def api_detect():
    if IS_RENDER:
        # Return mock data for Render
        return jsonify({
            "ok": True, 
            "mode": "gesture", 
            "events": [{
                "type": "info",
                "timestamp": time.time(),
                "message": "Running in cloud mode - camera simulation"
            }]
        })
    
    if "frame" not in request.files:
        return jsonify({"ok": False, "error": "Missing 'frame'"}), 400

    data = np.frombuffer(request.files["frame"].read(), dtype=np.uint8)
    frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"ok": False, "error": "Bad image"}), 400

    # Process frame (stores events)
    if pipeline:
        pipeline.step(frame)

    # Return recent events
    events = store.latest(5)
    return jsonify({"ok": True, "mode": pipeline.mode if pipeline else "gesture", "events": events})

@app.route("/events")
def events_sse():
    def gen():
        yield "event: hello\ndata: connected\n\n"
        last_seen = None
        last_heartbeat = 0.0
        while True:
            now = time.time()
            if now - last_heartbeat > 2.0:
                yield f"data: {json.dumps({'type': 'heartbeat', 'ts': now})}\n\n"
                last_heartbeat = now
            events = store.latest(1)
            if events:
                cur = json.dumps(events[0], sort_keys=True)
                if cur != last_seen:
                    yield f"data: {cur}\n\n"
                    last_seen = cur
            time.sleep(0.25)

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    return Response(stream_with_context(gen()), mimetype="text/event-stream", headers=headers)

@app.route("/api/mode", methods=["POST"])
def api_mode():
    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd")
    
    if cmd == "monitoring":
        if pipeline:
            pipeline.is_monitoring = bool(data.get("enabled", True))
            return jsonify({"ok": True, "monitoring": pipeline.is_monitoring})
        return jsonify({"ok": False, "error": "Pipeline not initialized"}), 400

    mode = data.get("mode")
    if mode in ["motion", "gesture"]:
        if pipeline:
            pipeline.set_mode(mode)
            return jsonify({"ok": True, "mode": pipeline.mode})
        return jsonify({"ok": False, "error": "Pipeline not initialized"}), 400

    return jsonify({"ok": False, "error": "Invalid command"}), 400

@app.route("/api/clear_canvas", methods=["POST"])
def clear_canvas():
    if pipeline and hasattr(pipeline, "gesture") and pipeline.gesture and pipeline.gesture.available:
        pipeline.gesture.clear()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Gesture system not initialized"}), 400

print("✅ All routes registered")
print(f"🚀 Server will start on port: {CFG.port}")
print("=" * 50)
import numpy as np
import cv2
import os
import json
import time
from flask_cors import CORS
from flask import Flask, Response, jsonify, request, stream_with_context
from config import CFG
from camera_manager import CameraManager
from event_store import EventStore
from actions import Actions
from pipeline import Pipeline

# Check if running on Render
IS_RENDER = os.environ.get('RENDER', False)

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static",
    static_url_path="/app/static",
)
CORS(app)

# Initialize components
store = EventStore(CFG.log_path, maxlen=CFG.max_events_in_memory)
actions = Actions(CFG.snapshot_dir)

# Only initialize pipeline if NOT on Render, or handle gracefully
if IS_RENDER:
    print("🚀 Running on Render - Camera features disabled")
    pipeline = None
else:
    pipeline = Pipeline(store, actions)
    if hasattr(pipeline, "set_mode"):
        pipeline.set_mode("gesture")

# Force Air Canvas (Gesture) as the default mode for testing
if hasattr(pipeline, "set_mode"):
    pipeline.set_mode("gesture")

@app.get("/")
def index():
    return jsonify({"ok": True, "service": "air-motion-canvas-backend"})

@app.route("/video_feed")
def video_feed():
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

@app.route("/health")
def health():
    return {"ok": True}

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
        pipeline.is_monitoring = bool(data.get("enabled", True))
        return jsonify({"ok": True, "monitoring": pipeline.is_monitoring})

    mode = data.get("mode")
    if mode in ["motion", "gesture"]:
        pipeline.set_mode(mode)
        return jsonify({"ok": True, "mode": pipeline.mode})

    return jsonify({"ok": False, "error": "Invalid command"}), 400

@app.route("/api/clear_canvas", methods=["POST"])
def clear_canvas():
    # Looks for the clear() method in your GestureDetector instance inside the pipeline
    if hasattr(pipeline, "gesture") and pipeline.gesture.available:
        pipeline.gesture.clear()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Gesture system not initialized"}), 400

if __name__ == "__main__":
    app.run(host=CFG.host, port=CFG.port, threaded=True)

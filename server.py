import cv2
import json
import time

from flask import Flask, Response, jsonify, request, render_template, stream_with_context

from config import CFG
from camera_manager import CameraManager
from event_store import EventStore
from actions import Actions
from pipeline import Pipeline

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static",
    static_url_path="/app/static",
)

store = EventStore(CFG.log_path, maxlen=CFG.max_events_in_memory)
actions = Actions(CFG.snapshot_dir)
pipeline = Pipeline(store, actions)

# Safe monitoring flag
if not hasattr(pipeline, "is_monitoring"):
    pipeline.is_monitoring = True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    """
    MJPEG stream. We open the camera inside this request (macOS reliable).
    Each frame is optionally processed by pipeline.step().
    """

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

                # If monitoring disabled, stream raw frames (no detection) but keep video alive
                if getattr(pipeline, "is_monitoring", True):
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
            try:
                cam.close()
            except Exception:
                pass
            print("🧹 /video_feed camera closed")

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/events")
def events_sse():
    """
    Server-Sent Events stream:
    - hello event right away
    - heartbeat every 2 seconds
    - newest event when it changes
    """

    def gen():
        yield "event: hello\ndata: connected\n\n"

        last_seen = None
        last_heartbeat = 0.0

        while True:
            now = time.time()

            # heartbeat
            if now - last_heartbeat > 2.0:
                yield f"data: {json.dumps({'type': 'heartbeat', 'ts': now})}\n\n"
                last_heartbeat = now

            # newest event
            events = store.latest(1)
            if events:
                cur = json.dumps(events[0], sort_keys=True)
                if cur != last_seen:
                    yield f"data: {cur}\n\n"
                    last_seen = cur

            time.sleep(0.25)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return Response(stream_with_context(gen()), mimetype="text/event-stream", headers=headers)


@app.route("/api/mode", methods=["POST"])
def api_mode():
    """
    Dashboard commands:
      - { "cmd": "monitoring", "enabled": true/false }
      - { "mode": "motion" } or { "mode": "gesture" }
    """
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


if __name__ == "__main__":
    app.run(host=CFG.host, port=CFG.port, threaded=True)

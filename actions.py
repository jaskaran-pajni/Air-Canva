import os
from datetime import datetime
from typing import Any, Dict, Optional

import cv2
import numpy as np

Event = Dict[str, Any]

class Actions:
    def __init__(self, snapshot_dir: str):
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)

        # Optional: import your existing Discord alert logic if available
        self._discord_available = False
        self._discord_send_fn = None
        try:
            # IMPORTANT:
            # In your vision_test.py, expose a function like:
            #   def send_discord_alert(message: str, image_path: str | None = None): ...
            from vision_test import send_discord_alert  # type: ignore
            self._discord_send_fn = send_discord_alert
            self._discord_available = True
        except Exception:
            self._discord_available = False

    def maybe_snapshot(self, event: Event, frame: np.ndarray) -> Optional[str]:
        """
        Save snapshot only for certain event types.
        """
        event_type = event.get("type", "")
        if event_type in ("motion", "security_alert", "gesture"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{event_type}_{ts}.jpg"
            path = os.path.join(self.snapshot_dir, filename)
            cv2.imwrite(path, frame)
            return path
        return None

    def trigger(self, event: Event, frame: np.ndarray) -> Dict[str, Any]:
        """
        Runs side-effects for an event (snapshot, optional Discord alert, etc.)
        Returns metadata to attach to event.
        """
        meta: Dict[str, Any] = {}

        snap_path = self.maybe_snapshot(event, frame)
        if snap_path:
            meta["snapshot"] = snap_path

        # Example: send Discord alert on motion/security
        if self._discord_available and event.get("type") in ("motion", "security_alert"):
            try:
                msg = f"🚨 Event: {event.get('type')} | conf={event.get('confidence')}"
                self._discord_send_fn(msg, snap_path)  # your function decides what to do
                meta["discord"] = "sent"
            except Exception as e:
                meta["discord"] = f"failed: {e}"

        return meta

import time
from typing import Any, Dict, List, Tuple
import numpy as np

from config import CFG
from event_store import EventStore
from actions import Actions

# Relative imports match your 'detectors' folder structure
from detectors.motion_detector import MotionDetector
from detectors.gesture_detector import GestureDetector

Event = Dict[str, Any]

class _NoOpGestureDetector:
    """Fallback to keep the system running if MediaPipe fails."""
    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Event]]:
        return frame, []

class Pipeline:
    def __init__(self, store: EventStore, actions: Actions):
        self.store = store
        self.actions = actions
        self.mode = CFG.default_mode 
        self.is_monitoring = True 

        self.motion = MotionDetector()
        try:
            self.gesture = GestureDetector()
        except Exception as e:
            print(f"⚠️ GestureDetector disabled: {e}")
            self.gesture = _NoOpGestureDetector()

        self.last_frame = None
        self._last_time = 0.0

    def set_mode(self, mode: str) -> None:
        if mode not in ("motion", "gesture"):
            raise ValueError("mode must be 'motion' or 'gesture'")
        self.mode = mode

    def step(self, frame: np.ndarray) -> np.ndarray:
        # If monitoring is paused, return the raw frame immediately
        if not self.is_monitoring:
            return frame

        # Run the active detector
        if self.mode == "motion":
            annotated, events = self.motion.process(frame)
        else:
            annotated, events = self.gesture.process(frame)

        # Process and store any detected events
        for e in events:
            e.setdefault("type", self.mode)
            e.setdefault("confidence", 0.0) # Ensure confidence exists for the UI
            e["mode"] = self.mode
            
            # Trigger snapshots/alerts
            meta = self.actions.trigger(e, frame)
            if meta: 
                e["meta"] = meta
            
            self.store.add(e)

        return annotated

    def run_forever_generator(self):
        """Throttles the loop based on config FPS."""
        min_dt = 1.0 / max(1, CFG.fps_limit)
        while True:
            now = time.time()
            dt = now - self._last_time
            if dt < min_dt:
                time.sleep(min_dt - dt)
            self._last_time = time.time()
            yield

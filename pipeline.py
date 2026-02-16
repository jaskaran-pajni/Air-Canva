import time
from typing import Any, Dict, List, Tuple
import numpy as np

from config import CFG
from event_store import EventStore
from actions import Actions

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

        # ✅ Lazy init gesture detector
        self.gesture = None
        self._gesture_failed = False

        self.last_frame = None
        self._last_time = 0.0

    def _get_gesture(self):
        """Create the gesture detector only when needed."""
        if self._gesture_failed:
            return _NoOpGestureDetector()

        if self.gesture is None:
            try:
                self.gesture = GestureDetector()
            except Exception as e:
                print(f"⚠️ GestureDetector disabled: {e}")
                self._gesture_failed = True
                return _NoOpGestureDetector()

        return self.gesture

    def set_mode(self, mode: str) -> None:
        if mode not in ("motion", "gesture"):
            raise ValueError("mode must be 'motion' or 'gesture'")
        self.mode = mode

    def step(self, frame: np.ndarray) -> np.ndarray:
        if not self.is_monitoring:
            return frame

        if self.mode == "motion":
            annotated, events = self.motion.process(frame)
        else:
            gesture = self._get_gesture()
            annotated, events = gesture.process(frame)

        for e in events:
            e.setdefault("type", self.mode)
            e.setdefault("confidence", 0.0)
            e["mode"] = self.mode

            meta = self.actions.trigger(e, frame)
            if meta:
                e["meta"] = meta

            self.store.add(e)

        return annotated

    def run_forever_generator(self):
        min_dt = 1.0 / max(1, CFG.fps_limit)
        while True:
            now = time.time()
            dt = now - self._last_time
            if dt < min_dt:
                time.sleep(min_dt - dt)
            self._last_time = time.time()
            yield

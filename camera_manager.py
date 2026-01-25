import sys
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class CameraManager:
    """
    Owns the webcam. Other modules must NEVER call cv2.VideoCapture().

    Notes (macOS):
    - AVFoundation is usually the most reliable backend.
    - Sometimes a camera "opens" but returns bad/empty frames initially.
      We warm up reads and fallback if necessary.
    """

    def __init__(self, index: int, width: int, height: int):
        self.index = index
        self.width = width
        self.height = height
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()

    def _open_capture(self) -> cv2.VideoCapture:
        """
        Open a VideoCapture with platform-appropriate backend + fallback.
        """
        if sys.platform == "darwin":
            # Try AVFoundation first (best for macOS)
            cap = cv2.VideoCapture(self.index, cv2.CAP_AVFOUNDATION)
            if cap.isOpened():
                return cap

            # Fallback to default backend if AVFoundation fails
            cap.release()
            cap = cv2.VideoCapture(self.index)
            return cap

        # Non-mac: default backend
        return cv2.VideoCapture(self.index)

    def open(self) -> None:
        with self._lock:
            if self._cap is not None:
                return

            cap = self._open_capture()

            if not cap.isOpened():
                raise RuntimeError(
                    f"❌ Could not open webcam at index={self.index}. "
                    f"Try camera_index=0 or 1 and close apps using the camera (Zoom/Teams/Discord/Meet)."
                )

            # Set desired properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.width))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.height))
            cap.set(cv2.CAP_PROP_FPS, 30.0)

            # Warm-up reads: ensure we can actually read a real frame
            ok = False
            frame = None
            for _ in range(25):
                ok, frame = cap.read()
                if ok and frame is not None and getattr(frame, "size", 0) > 0:
                    break
                time.sleep(0.05)

            if not (ok and frame is not None and getattr(frame, "size", 0) > 0):
                # If it opened but can't read frames, release and throw a clear error
                cap.release()
                raise RuntimeError(
                    f"❌ Webcam opened at index={self.index} but could not read frames. "
                    f"Common fixes: (1) switch camera_index 0↔1, "
                    f"(2) close apps using camera, "
                    f"(3) macOS Settings → Privacy & Security → Camera → allow Terminal/VSCode."
                )

            self._cap = cap

    def read(self) -> Tuple[bool, np.ndarray]:
        with self._lock:
            if self._cap is None:
                raise RuntimeError("Camera not opened. Call open() first.")
            return self._cap.read()

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

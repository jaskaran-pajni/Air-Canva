import time
from typing import List, Tuple
import numpy as np
import cv2

class GestureDetector:
    """
    Air-canvas gesture detector:
    - Index Finger UP = Draw
    - Fist (All fingers closed) = Hover (No drawing)
    - Mirroring is handled internally for natural interaction.
    """

    def __init__(self):
        self.available = False
        self.reason = ""

        # Persistence state
        self.canvas = None
        self.prev_pt = None
        self.drawing_state = False
        self.last_frame_with_canvas = None

        try:
            import mediapipe as mp  # type: ignore
            self.mp = mp

            if not hasattr(mp, "solutions"):
                self.available = False
                self.reason = "mediapipe installed but mp.solutions missing"
                print(f"⚠️ GestureDetector disabled: {self.reason}")
                return

            self.hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7,
            )
            self.drawer = mp.solutions.drawing_utils
            self.available = True
            print("✅ GestureDetector enabled (MediaPipe Hands).")

        except Exception as e:
            self.available = False
            self.reason = f"MediaPipe init failed: {e}"
            print(f"⚠️ GestureDetector disabled: {self.reason}")

    def clear(self):
        """Clears the persistent drawing canvas."""
        self.canvas = None
        self.prev_pt = None
        self.drawing_state = False
        self.last_frame_with_canvas = None
        print("🧹 Canvas cleared")

    def _is_finger_up(self, landmarks, finger_index, h, w):
        """
        Utility to check if a specific finger is extended.
        Indices: 8=Index, 12=Middle, 16=Ring, 20=Pinky
        """
        tip = landmarks.landmark[finger_index]
        pip = landmarks.landmark[finger_index - 2]
        return tip.y < pip.y

    def process(self, frame_bgr) -> Tuple[np.ndarray, List[dict]]:
        if not self.available:
            return frame_bgr, []

        events: List[dict] = []

        # 1. Mirror for natural interaction
        frame = cv2.flip(frame_bgr, 1)
        h, w, _ = frame.shape

        # 2. Initialize persistent canvas if it doesn't exist
        if self.canvas is None:
            self.canvas = np.zeros((h, w, 3), dtype=np.uint8)
            print("🆕 New canvas created")

        # 3. MediaPipe Processing
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        # Handle "No Hand" case
        if not result.multi_hand_landmarks:
            self.prev_pt = None
            self.drawing_state = False
            # Blend canvas with frame
            out = cv2.addWeighted(frame, 1.0, self.canvas, 1.0, 0)
            self.last_frame_with_canvas = out
            return out, events

        hand_landmarks = result.multi_hand_landmarks[0]
        
        # Visual feedback: Draw the hand skeleton
        self.drawer.draw_landmarks(frame, hand_landmarks, self.mp.solutions.hands.HAND_CONNECTIONS)

        # 4. Finger Tracking (Index Tip = Index 8)
        index_tip = hand_landmarks.landmark[8]
        ix, iy = int(index_tip.x * w), int(index_tip.y * h)

        # 5. Gesture Logic
        index_up = self._is_finger_up(hand_landmarks, 8, h, w)
        middle_up = self._is_finger_up(hand_landmarks, 12, h, w)
        ring_up = self._is_finger_up(hand_landmarks, 16, h, w)
        pinky_up = self._is_finger_up(hand_landmarks, 20, h, w)

        # DRAWING MODE: Index Up, others down
        should_draw = index_up and not middle_up and not ring_up and not pinky_up
        
        # DEBUG PRINT - Moved inside the method
        print(f"🎯 Drawing state: {self.drawing_state}, should_draw: {should_draw}")
        
        # Visual Cursor
        cursor_color = (0, 255, 0) if should_draw else (0, 0, 255)
        cv2.circle(frame, (ix, iy), 10, cursor_color, -1)

        if should_draw:
            if self.prev_pt is not None:
                # Draw on the persistent canvas
                cv2.line(self.canvas, self.prev_pt, (ix, iy), (0, 0, 139), 6)
            
            self.prev_pt = (ix, iy)
            
            if not self.drawing_state:
                self.drawing_state = True
                events.append({
                    "type": "gesture",
                    "confidence": 1.0,
                    "timestamp": time.time(),
                    "meta": {"status": "drawing_started"}
                })
        else:
            if self.drawing_state:
                events.append({
                    "type": "gesture",
                    "confidence": 1.0,
                    "timestamp": time.time(),
                    "meta": {"status": "drawing_stopped"}
                })
            self.drawing_state = False
            self.prev_pt = None

        # 6. Final Composition - Add the drawing canvas onto the live frame
        out = cv2.addWeighted(frame, 1.0, self.canvas, 1.0, 0)
        
        # Draw a small indicator that canvas exists
        if np.any(self.canvas):  # If canvas has any drawings
            cv2.putText(out, "✏️ Drawing Active", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        self.last_frame_with_canvas = out
        return out, events
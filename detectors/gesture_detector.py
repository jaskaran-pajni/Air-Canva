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
        self.total_lines_drawn = 0
        self.debug_mode = True

        try:
            import mediapipe as mp
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
        self.total_lines_drawn = 0
        print("🧹 Canvas cleared - ALL drawings removed")

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

        # REMOVE THE FLIP - use original frame
        frame = frame_bgr  # Just use original, no flip
        h, w, _ = frame.shape

        # 2. Initialize canvas with matching shape and uint8 type
        if self.canvas is None or self.canvas.shape != frame.shape:
            self.canvas = np.zeros_like(frame, dtype=np.uint8)
            print("🆕 New canvas created", flush=True)

        # 3. MediaPipe Processing (expects RGB) - Use original frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)


        # Handle "No Hand" case
        if not result.multi_hand_landmarks:
            self.prev_pt = None
            self.drawing_state = False
            # Blend canvas with frame
            out = cv2.addWeighted(frame, 1.0, self.canvas, 1.0, 0)
            self.last_frame_with_canvas = out
            return out.astype(np.uint8), events

        hand_landmarks = result.multi_hand_landmarks[0]
        
        # Visual feedback: Draw the hand skeleton on the flipped frame
        self.drawer.draw_landmarks(frame, hand_landmarks, self.mp.solutions.hands.HAND_CONNECTIONS)

        # 4. Finger Tracking - Use direct coordinates (no extra mirroring)
        # Since we already flipped the frame, the landmarks are already aligned
        index_tip = hand_landmarks.landmark[8]
        ix = int(index_tip.x * w)  # Direct coordinate - no (1 - x) needed!
        iy = int(index_tip.y * h)

        # 5. Gesture Logic
        index_up = self._is_finger_up(hand_landmarks, 8, h, w)
        middle_up = self._is_finger_up(hand_landmarks, 12, h, w)
        ring_up = self._is_finger_up(hand_landmarks, 16, h, w)
        pinky_up = self._is_finger_up(hand_landmarks, 20, h, w)

        # DRAWING MODE: Index Up, others down
        should_draw = index_up and not middle_up and not ring_up and not pinky_up
        
        # Visual Cursor
        cursor_color = (0, 255, 0) if should_draw else (0, 0, 255)
        cv2.circle(frame, (ix, iy), 10, cursor_color, -1)

        if should_draw:
            if self.prev_pt is not None:
                # Draw on the persistent canvas
                cv2.line(self.canvas, self.prev_pt, (ix, iy), (0, 0, 139), 6)
                self.total_lines_drawn += 1
                print(f"✅ Line drawn! Total: {self.total_lines_drawn}", flush=True)
            
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

        # 6. Blend canvas with frame
        out = cv2.addWeighted(frame, 1.0, self.canvas, 1.0, 0)
        
        # Add debug info
        if self.total_lines_drawn > 0:
            cv2.putText(out, f"Lines: {self.total_lines_drawn}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(out, "✅ CANVAS HAS DRAWINGS", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(out, "❌ CANVAS EMPTY", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        self.last_frame_with_canvas = out
        # Ensure uint8 type for WebRTC
        return out.astype(np.uint8), events
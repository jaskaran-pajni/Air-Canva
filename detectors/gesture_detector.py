import cv2
import numpy as np
import datetime


class GestureDetector:
    def __init__(self, draw_skeleton=False):
        """
        draw_skeleton: Set to True only for debugging.
        False saves CPU on Raspberry Pi.
        """
        # --- ROBUST IMPORT ---
        try:
            from mediapipe.python.solutions import hands as mp_hands
            from mediapipe.python.solutions import drawing_utils as mp_draw
        except ImportError:
            import mediapipe.solutions.hands as mp_hands
            import mediapipe.solutions.drawing_utils as mp_draw

        self.mp_hands = mp_hands
        self.mp_draw = mp_draw
        self.draw_skeleton = draw_skeleton

        # Lower confidence slightly for better tracking on low-res Pi inputs
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )

        self.canvas = None
        self.x_prev = 0
        self.y_prev = 0
        self.brush_thickness = 10
        self.draw_color = (0, 0, 255)  # Red

    def process(self, frame):
        """
        Input: Raw frame.
        Output: (annotated_frame, events_list)
        """
        events = []
        timestamp = datetime.datetime.now().isoformat()

        # Flip for intuitive interaction
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape

        # Lazy Init Canvas
        if self.canvas is None or self.canvas.shape != frame.shape:
            self.canvas = np.zeros_like(frame)

        # MediaPipe Processing
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb_frame)

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:

                # Optional: Draw Skeleton
                if self.draw_skeleton:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                # Get Coordinates
                lm_list = []
                for id, lm in enumerate(hand_landmarks.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([id, cx, cy])

                if len(lm_list) != 0:
                    x1, y1 = lm_list[8][1], lm_list[8][2]  # Index Tip
                    x2, y2 = lm_list[12][1], lm_list[12][2]  # Middle Tip

                    # Finger Detection
                    index_up = lm_list[8][2] < lm_list[6][2]
                    middle_up = lm_list[12][2] < lm_list[10][2]

                    current_action = "none"

                    # --- GESTURE LOGIC ---
                    if index_up and middle_up:
                        current_action = "hover"
                        self.x_prev, self.y_prev = 0, 0

                        # UI Feedback
                        cv2.rectangle(frame, (x1, y1 - 25), (x2, y2 + 25), self.draw_color, cv2.FILLED)
                        cv2.putText(frame, "Hover", (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                    elif index_up and not middle_up:
                        current_action = "draw"
                        cv2.circle(frame, (x1, y1), 15, self.draw_color, cv2.FILLED)

                        if self.x_prev == 0 and self.y_prev == 0:
                            self.x_prev, self.y_prev = x1, y1

                        cv2.line(self.canvas, (self.x_prev, self.y_prev), (x1, y1), self.draw_color,
                                 self.brush_thickness)
                        self.x_prev, self.y_prev = x1, y1

                    else:
                        self.x_prev, self.y_prev = 0, 0

                    # --- EVENT GENERATION ---
                    if current_action != "none":
                        event_data = {
                            "type": "gesture",
                            "confidence": 1.0,  # Hand detected
                            "timestamp": timestamp,
                            "meta": {
                                "gesture_type": current_action,
                                "cursor_pos": (x1, y1),
                                "fingers_up": [index_up, middle_up]
                            }
                        }
                        events.append(event_data)

        # Blend Canvas
        img_gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, img_inv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
        img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
        frame = cv2.bitwise_and(frame, img_inv)
        frame = cv2.bitwise_or(frame, self.canvas)

        return frame, events

    def clear_canvas(self):
        self.canvas = None
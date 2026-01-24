import cv2


class MotionDetectorEngine:
    def __init__(self, min_area=500):
        """
        min_area: Smallest change (in pixels) to count as motion.
        """
        self.background_model = None
        self.min_area = min_area

    def process_frame(self, frame):
        """
        Input: Raw frame from Pi/Camera.
        Output: Annotated frame, Events dictionary.
        """
        events = {
            "motion_detected": False,
            "motion_area": 0
        }

        # 1. Pre-processing (Grayscale + Blur)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # 2. Initialize Background (if first frame or reset)
        if self.background_model is None:
            self.background_model = gray
            return frame, events

        # 3. Calculate Difference
        frame_delta = cv2.absdiff(self.background_model, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

        # Dilate to fill holes
        thresh = cv2.dilate(thresh, None, iterations=2)

        # 4. Find Contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            if cv2.contourArea(contour) < self.min_area:
                continue

            # Motion Found!
            events["motion_detected"] = True
            events["motion_area"] = cv2.contourArea(contour)

            # Draw green box
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return frame, events

    def reset_background(self):
        """Force the engine to retake the background photo."""
        self.background_model = None
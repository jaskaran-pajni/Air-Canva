import cv2
import datetime


class MotionDetector:
    def __init__(self, min_area=500, weight=0.5):
        """
        min_area: Minimum pixel area to count as motion.
        weight: How fast the background adapts (0.01 = slow, 0.5 = fast).
        """
        self.min_area = min_area
        self.weight = weight
        self.avg_frame = None  # We use a float accumulator for adaptive background

    def process(self, frame):
        """
        Input: Raw frame from Pi.
        Output: (annotated_frame, events_list)
        """
        events = []
        timestamp = datetime.datetime.now().isoformat()

        # 1. Pre-process (Grayscale + Blur)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # 2. Initialize or Adapt Background
        if self.avg_frame is None:
            self.avg_frame = gray.astype("float")
            return frame, []  # No events on first frame

        # Adapt the background (Running Average)
        # This allows the system to ignore slow lighting changes
        cv2.accumulateWeighted(gray, self.avg_frame, self.weight)
        background = cv2.convertScaleAbs(self.avg_frame)

        # 3. Calculate Difference
        frame_delta = cv2.absdiff(background, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        # 4. Find Contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue

            # Motion Found! Create standardized event
            (x, y, w, h) = cv2.boundingRect(contour)

            event_data = {
                "type": "motion",
                "confidence": min(1.0, area / 10000),  # Rough confidence score based on size
                "timestamp": timestamp,
                "meta": {
                    "area": area,
                    "bounding_box": [x, y, w, h]
                }
            }
            events.append(event_data)

            # Draw green box on the frame
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return frame, events
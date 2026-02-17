import cv2
import datetime
import numpy as np

class MotionDetector:
    def __init__(self, min_area=500, weight=0.5):
        """
        min_area: Minimum pixel area to count as motion.
        weight: How fast the background adapts (0.01 = slow, 0.5 = fast).
        """
        self.min_area = min_area
        self.weight = weight
        self.avg_frame = None  # We use a float accumulator for adaptive background
        self.motion_count = 0
        self.debug_mode = True
        print(f"🔍 MotionDetector initialized - min_area: {min_area}, weight: {weight}")

    def process(self, frame):
        """
        Input: Raw frame from Pi.
        Output: (annotated_frame, events_list)
        """
        events = []
        timestamp = datetime.datetime.now().isoformat()
        
        print(f"\n--- Motion Detection Frame ---", flush=True)
        print(f"📏 Input frame shape: {frame.shape}", flush=True)

        # 1. Pre-process (Grayscale + Blur)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        print(f"⚪ Grayscale frame shape: {gray.shape}", flush=True)

        # 2. Initialize or Adapt Background
        if self.avg_frame is None:
            self.avg_frame = gray.astype("float")
            print("🆕 Initializing background model (first frame)", flush=True)
            return frame, []  # No events on first frame

        # Adapt the background (Running Average)
        cv2.accumulateWeighted(gray, self.avg_frame, self.weight)
        background = cv2.convertScaleAbs(self.avg_frame)
        print("🔄 Background model updated", flush=True)

        # 3. Calculate Difference
        frame_delta = cv2.absdiff(background, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Calculate statistics
        diff_mean = np.mean(frame_delta)
        diff_max = np.max(frame_delta)
        thresh_pixels = np.count_nonzero(thresh)
        thresh_percentage = (thresh_pixels / thresh.size) * 100
        
        print(f"📊 Difference stats - mean: {diff_mean:.2f}, max: {diff_max:.2f}", flush=True)
        print(f"📊 Threshold - non-zero pixels: {thresh_pixels} ({thresh_percentage:.2f}%)", flush=True)

        # 4. Find Contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"🔍 Found {len(contours)} contours", flush=True)

        motion_detected = False
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            if area < self.min_area:
                print(f"  Contour {i}: area {area:.1f} < {self.min_area} - ignoring", flush=True)
                continue

            # Motion Found!
            motion_detected = True
            self.motion_count += 1
            (x, y, w, h) = cv2.boundingRect(contour)
            
            confidence = min(1.0, area / 10000)
            print(f"  ✅ MOTION DETECTED! Contour {i}: area {area:.1f}, box ({x},{y},{w},{h}), confidence: {confidence:.2f}", flush=True)
            print(f"  📊 Total motions detected: {self.motion_count}", flush=True)

            event_data = {
                "type": "motion",
                "confidence": confidence,
                "timestamp": timestamp,
                "meta": {
                    "area": area,
                    "bounding_box": [x, y, w, h],
                    "motion_count": self.motion_count
                }
            }
            events.append(event_data)

            # Draw on frame
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Motion {confidence:.0%}", (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        # Add debug info to frame
        cv2.putText(frame, f"Motions: {self.motion_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.putText(frame, f"Contours: {len(contours)}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
        cv2.putText(frame, f"Motion: {'YES' if motion_detected else 'NO'}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0) if motion_detected else (0,0,255), 2)

        # Show threshold image in corner for debugging
        h, w = frame.shape[:2]
        thresh_small = cv2.resize(thresh, (100, 100))
        thresh_color = cv2.cvtColor(thresh_small, cv2.COLOR_GRAY2BGR)
        frame[10:110, w-110:w-10] = thresh_color

        print(f"📤 Returning frame with {len(events)} motion events", flush=True)
        return frame, events
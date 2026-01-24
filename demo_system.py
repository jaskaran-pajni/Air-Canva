import cv2
import time

# Import your two custom modules
from air_canvas import AirCanvasEngine
from motion_detector import MotionDetectorEngine


def main():
    # --- HARDWARE SETUP ---
    CAMERA_INDEX = 1  # Your Brio
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("❌ Camera not found. Check connection.")
        return

    # --- SOFTWARE SETUP ---
    # Load both engines into memory
    motion_engine = MotionDetectorEngine()
    canvas_engine = AirCanvasEngine()

    # Default Mode
    current_mode = "motion"  # Options: "motion", "canvas"

    print("\n--- DEMO SYSTEM STARTED ---")
    print("Press 'm' -> Switch to SAFETY MODE (Motion Detection)")
    print("Press 'g' -> Switch to GESTURE MODE (Air Canvas)")
    print("Press 'r' -> Reset (Background or Canvas)")
    print("Press 'q' -> Quit")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # --- MODE SWITCHING LOGIC ---
        if current_mode == "motion":
            # Pass frame to Motion Engine
            processed_frame, events = motion_engine.process_frame(frame)

            # Add UI Text
            status = "Status: UNSAFE" if events["motion_detected"] else "Status: Secure"
            color = (0, 0, 255) if events["motion_detected"] else (0, 255, 0)
            cv2.putText(processed_frame, f"MODE: SAFETY | {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        elif current_mode == "canvas":
            # Pass frame to Air Canvas Engine
            processed_frame, events = canvas_engine.process_frame(frame)

            # Add UI Text
            gesture = events.get("gesture", "None")
            cv2.putText(processed_frame, f"MODE: GESTURE | Action: {gesture}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 100, 0), 2)

        # --- DISPLAY ---
        cv2.imshow("Raspberry Pi Main Dashboard", processed_frame)

        # --- CONTROLS ---
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('m'):
            current_mode = "motion"
            print("Switched to Motion Detection")
        elif key == ord('g'):
            current_mode = "canvas"
            print("Switched to Air Canvas")
        elif key == ord('r'):
            if current_mode == "motion":
                motion_engine.reset_background()
                print("Background Reset!")
            else:
                canvas_engine.clear_canvas()
                print("Canvas Cleared!")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
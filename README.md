# ConUHacksXMotionDetector

🎨 AirMotion Canvas

Draw in the air using hand gestures and real-time computer vision

🧩 Problem Statement

Traditional drawing tools require physical contact devices. These tools may not always be accessible, intuitive, or hygienic.

There is a need for a natural, contactless drawing interface that allows users to interact with a digital canvas using simple hand gestures and real-time motion sensing.

💡 Solution Overview

AirMotion Canvas is a gesture-controlled virtual drawing system that allows users to draw in mid-air using their index finger. The system uses computer vision and hand-tracking to detect gestures and translate them into drawing actions on a digital canvas.

Additionally, a motion detection module monitors environmental movement, enabling future extensions such as gesture-based mode switching, activity detection, or smart interaction triggers.

✨ Key Features

Real-time hand tracking using MediaPipe

Gesture-based drawing and pause control

Smooth stroke rendering with dynamic tracking

Motion detection using background subtraction

Modular engine-based architecture

Live visual feedback for gestures and motion

🏗️ System Architecture

The system is divided into two independent processing engines:

Air Canvas Engine

Detects hand landmarks

Identifies gestures (Draw / Hover)

Renders strokes onto a virtual canvas

Motion Detector Engine

Tracks  motion

Detects movement regions using frame differencing

Outputs motion events for future integration


⚙️ Installation & Setup
Prerequisites

Python 3.8+

Webcam

Supported OS: Windows / macOS / Linux


Note: A main controller file can be added to combine both engines into a unified pipeline.

🔄 How It Works (Step-by-Step)

Capture live video frames from the camera

Flip and preprocess frames for natural interaction

Detect hand landmarks using MediaPipe

Identify finger states (index up, middle up/down)

Map gestures:

Index up → Draw

Index + Middle up → Hover (pause)

Draw strokes onto a transparent canvas layer

Detect motion using background subtraction

Merge canvas and camera feed into final output

🧪 Example Use Cases

Touchless drawing or whiteboard systems

Interactive presentations or classrooms

Computer vision learning projects

📁 Folder Structure
project-root/
│
├── air_canvas.py          # Hand tracking and drawing engine
├── motion_detector.py     # Motion detection engine
├── main.py                # (Placeholder) Application entry point
├── requirements.txt       # Dependencies
└── README.md

🧠 Challenges & Learnings

Stabilizing hand tracking during fast movement

Reducing false positives in motion detection

Managing drawing continuity between frames

Designing gesture logic that feels natural and intuitive

Building modular, reusable computer vision components

🏁 Conclusion

AirMotion Canvas demonstrates how computer vision can enable natural human-computer interaction without physical contact. By combining hand tracking and motion detection in a modular design, the project lays a strong foundation for future smart interaction systems and real-world applications.
Clean, modern design using:

Cards

Icons

Status colors (green = active, red = alert)

Designed specifically to look advanced and professional for judges

All styling organized and reusable via CSS style


8️⃣ Files Delivered

index.html → Dashboard layout and structure 

index

style.css → Complete UI styling and animations 

style

app.js → All dashboard logic, simulation, and interactions 

app

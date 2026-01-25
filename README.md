# ConUHacksXAirMotionCanvas

🎨 Air Motion Canvas
Gesture-Based Virtual Drawing System | ConUHacks 2026

Air Motion Canvas turns the air into a digital workspace. By leveraging Edge AI on a low-power Raspberry Pi, we have created a touchless, intuitive interaction model that bridges the gap between human intent and digital creativity.

🧩 Problem Statement
Traditional digital input devices like mice and tablets are physically restrictive, can cause repetitive strain, and lack the natural feel of free-hand drawing. There is a critical need for Natural Human-Computer Interaction (HCI) that is accessible, hygienic, and works without specialized expensive hardware.

💡 Solution Overview
Air Motion Canvas is a standalone "Smart Appliance" that uses a standard webcam to track hand movements in 3D space. The system is optimized to run on a 15W ARM processor, performing real-time hand-landmark detection and translating specific gestures into drawing actions on a digital dashboard.

✨ Key Features
Edge AI Processing: Real-time hand tracking using MediaPipe optimized for the Raspberry Pi.

Intuitive Gesture States: Seamlessly switch between "Drawing" and "Hovering" using natural hand shapes.

Low-Latency Feedback: Flask-based backend utilizing Server-Sent Events (SSE) for zero-lag visual updates.

Environmental Monitoring: Background subtraction-based motion detection for secondary surveillance or mode-triggering.

Mirror Mode: Pre-processed frames ensure a natural "selfie-style" interaction for the user.

🏗️ System Architecture
The project is built with a modular, engine-based architecture:

Hardware Foundation: Raspberry Pi (ARM64) serving as the dedicated compute hub.

Air Canvas Engine: Handles 3D landmark detection and persistent NumPy-based canvas rendering.

Motion Detector Engine: Monitors environment changes using frame differencing.

Web Interface: Real-time MJPEG stream and event logging system.

🔄 How It Works (Step-by-Step)
Capture: Captures frames from the webcam and normalizes resolution to maintain high FPS.

Analyze: MediaPipe processes the RGB frame to identify 21 hand landmarks.

Classify Gesture:

Index Finger Extended: Triggers "Pen Down" mode (Green cursor).

Closed Fist: Triggers "Hover Mode" (Red cursor) for navigation without drawing.

Render: Connects previous and current index coordinates on a persistent canvas layer.

Stream: Blends the canvas with the live feed and streams it to the dashboard via SSE.

⚙️ Technical Optimisation
To ensure high performance on 15W hardware, we implemented:

Resolution Scaling: Fixed 640×480 processing to reduce CPU load.

Coordinate Normalization: Ensures gestures are mapped accurately regardless of the user's distance from the camera.

Vectorised Drawing: Used NumPy-based bitwise addition for fast canvas blending.

📁 Folder Structure
project-root/
│
├── gesture_detector.py # Hand tracking and drawing state logic
├── motion_detector.py  # Background subtraction engine
├── server.py           # Flask backend & SSE implementation
├── camera_manager.py   # Camera I/O and frame normalization
├── app/
│   ├── templates/      # index.html
│   └── static/         # style.css & backend-integration.js
└── README.md

🧠 Challenges & Learnings

Stabilising hand tracking during fast movement

Reducing false positives in motion detection

Managing drawing continuity between frames

Designing gesture logic that feels natural and intuitive

Building modular, reusable computer vision components

🏁 Conclusion

Air Motion Canvas demonstrates how computer vision can bridge the gap between human intent and digital creativity without physical contact. By combining high-precision hand tracking with a modular detection engine, we have laid a strong foundation for the future of Natural Human-Computer Interaction (HCI).


Our system is designed to look advanced and professional for judges, featuring:

Modular Architecture: Independent engines for gesture and motion allow for high reliability and future scalability.

Clean, Modern UI: A card-based dashboard utilising professional icons and intuitive status colours (Green for Active/Drawing, Red for Alert/Hover).

Edge Optimization: High-performance software specifically engineered to run efficiently on low-resource hardware like the Raspberry Pi.

8️⃣ Files Delivered

server.py: The Flask-based backend serving as the central hub for video streaming and SSE event handling.

gesture_detector.py: The core state machine managing the transition between Index-Drawing and Fist-Hovering.

motion_detector.py: A background-subtraction engine for real-time environmental monitoring.

index.html: The dashboard structure provides a real-time MJPEG feed and activity logs.

style.css: Complete UI styling including animations, card layouts, and responsive design elements.

backend-integration.js: Frontend logic for SSE connection, mode switching, and canvas clearing.

⚠️ Notes (Mac / MediaPipe)

On some macOS environments, the mediapipe package may install without exposing mp.solutions. We have engineered a robust fail-safe for this scenario :

Graceful Degradation: Gesture mode is automatically disabled to prevent system crashes.

System Stability: The Motion Detection engine and dashboard remain fully functional.

Target Hardware: Full gesture capabilities are optimised for and best tested on the Raspberry Pi or standard Windows/Linux builds.

👥 The Team

Ayaan Vashistha: Systems Lead & Integration Architect.

Jaskaran: Frontend Developer & Dashboard Integration.

Zohair: Computer Vision Engineer (Gesture & Motion Logic).

Pawan: Repository Lead & Presentation Strategist.

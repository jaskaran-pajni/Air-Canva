# ConUHacksXMotionDetector

The problem we solve


📌 Work Summary – Web Dashboard (Motion Monitoring System)

The front-end web dashboard for our motion-based monitoring demo is judge-friendly, realistic, and visually impressive even without a live Pi feed.


1️⃣ Overall Concept Implemented

Built a real-time surveillance dashboard UI that simulates:

Live camera feed

Motion detection

Event logging

System monitoring controls

Designed it so later we can plug in Raspberry Pi / backend data easily without redesigning the UI.


2️⃣ Live Video Feed (Canvas-based)

Implemented a simulated camera feed using HTML5 <canvas>.

Includes:

Dark surveillance-style gradient background. This black background of the canvas is transparent so you can see your drawing "floating" over your video!

Subtle ambient noise for realism

Animated motion detection bounding box when motion is triggered

Live timestamp overlay updates every second.

Recording (“REC”) indicator turns ON when monitoring is active 



3️⃣ Motion Detection Simulation

Motion can be:

Triggered manually (for live demo)

Triggered automatically in demo mode

When motion is detected:

Motion badge appears on video

Status updates to “Motion Detected”

Event counter increases

Motion ends automatically after a short duration

This mimics what real CV motion detection would do later 



4️⃣ Activity Log System

Implemented a real-time activity log:

Logs “Motion Started” and “Motion Ended”

Shows timestamp + relative time

Limits log size to keep UI clean

Logs can be cleared individually or reset completely 



5️⃣ System Status & Metrics

Dashboard shows:

Current system status (Active / Paused)

Total number of detected events

System uptime (live counter)

Status indicator visually changes color when monitoring is paused or active index


6️⃣ Control Panel Features

Start / Stop Monitoring button

Sensitivity slider (ready to be wired to backend later)

Alert sound toggle (UI logic complete)

Clear logs and reset system buttons

“Auto Mode” for demo (auto-triggers motion multiple times) 

index


7️⃣ UI / Design Work

Fully responsive layout (desktop → tablet friendly)

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

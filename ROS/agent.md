# kobuki_app_bridge — Copilot Agent Instructions

## Project overview
This is a ROS2 Humble Python package called `kobuki_app_bridge`.
It bridges a Kobuki robot with a mobile/web app that already exists.
The app connects over WebSocket (port 9090) and HTTP REST (port 8080).

The app can:
- Receive live robot data over WebSocket (pose, battery, bumpers)
- Fetch the current map as a PNG image over HTTP GET /map
- Send velocity commands over WebSocket by publishing to /app/command
- Send navigation goals over WebSocket by publishing to /app/command
- Display goal status received from /app/goal_status

This package does NOT implement the app. It only implements the ROS2 side.

## Workspace layout (already exists, do not change)

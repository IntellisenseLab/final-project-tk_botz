# QBot — ROS 2 Mobile Robot Platform

A complete software interface system for a ROS 2-based mobile robot with simulation and real-world deployment capabilities. Includes a custom web UI that replaces RViz and teleop tools, built on React + roslibjs + WebSocket communication via `rosbridge_server`.

---

## Table of contents

- [Overview](#overview)
- [System architecture](#system-architecture)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the system](#running-the-system)
- [Web interface](#web-interface)
- [ROS 2 interfaces](#ros-2-interfaces)
- [Node reference](#node-reference)
- [Configuration](#configuration)
- [Communication architecture](#communication-architecture)
- [Simulation vs real-world deployment](#simulation-vs-real-world-deployment)
- [Extending the system](#extending-the-system)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

This project implements a layered software architecture for a differential-drive mobile robot (QBot). The system covers four layers:

1. **Web interface layer** — React-based dashboard replacing RViz and teleop_twist_keyboard
2. **Interface contract layer** — Custom ROS 2 actions, messages, and services
3. **Application behavior layer** — Navigation server, mapper, odometry, and orchestration nodes
4. **Robot and simulation infrastructure** — URDF/SDF models, Gazebo, ros2_control, and launch system

---

## System architecture

```
┌─────────────────────────────────────────────────────────┐
│               Web Interface (React + roslibjs)          │
│   Map panel │ Control panel │ Status panel │ Camera feed │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket (JSON)
┌────────────────────────▼────────────────────────────────┐
│              rosbridge_server  (port 9090)               │
└────────────────────────┬────────────────────────────────┘
                         │ ROS 2 topics / services / actions
┌────────────────────────▼────────────────────────────────┐
│              Interface contract layer                    │
│  Navigation.action │ Position.msg │ GetLastPositions.srv │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Application behavior layer                  │
│  navigation_server │ qbot_controller │ mapper_node       │
│  odom_node │ lab_06_simulation_launch                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│          Robot and simulation infrastructure             │
│  qbot.urdf │ qbot.sdf │ qbot_world.sdf │ ros_gz_bridge  │
│  robot_state_publisher │ ros2_control │ Gazebo           │
└─────────────────────────────────────────────────────────┘
```

---

## Repository structure

```
qbot_ws/
├── src/
│   ├── qbot_interfaces/              # Interface contract layer
│   │   ├── action/
│   │   │   └── Navigation.action
│   │   ├── msg/
│   │   │   └── Position.msg
│   │   ├── srv/
│   │   │   └── GetLastPositions.srv
│   │   ├── CMakeLists.txt
│   │   └── package.xml
│   │
│   ├── qbot_description/             # Robot models
│   │   ├── urdf/
│   │   │   └── qbot.urdf
│   │   ├── sdf/
│   │   │   ├── qbot.sdf
│   │   │   └── qbot_world.sdf
│   │   └── config/
│   │       └── qbot_controllers.yaml
│   │
│   ├── qbot_bringup/                 # Launch and orchestration
│   │   ├── launch/
│   │   │   └── lab_06_simulation_launch.py
│   │   └── package.xml
│   │
│   └── qbot_nodes/                   # Application behavior
│       ├── qbot_nodes/
│       │   ├── navigation_server.py
│       │   ├── qbot_controller.py
│       │   ├── mapper_node.py
│       │   └── odom_node.py
│       ├── setup.py
│       └── package.xml
│
└── web_interface/                    # Custom web UI
    ├── public/
    ├── src/
    │   ├── components/
    │   │   ├── MapPanel.jsx
    │   │   ├── ControlPanel.jsx
    │   │   ├── StatusPanel.jsx
    │   │   └── CameraFeed.jsx
    │   ├── ros/
    │   │   └── rosbridge.js          # roslibjs connection + topic helpers
    │   └── App.jsx
    ├── package.json
    └── README.md
```

---

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| Ubuntu | 22.04 LTS | Recommended |
| ROS 2 | Humble Hawksbill | `ros-humble-desktop` |
| Gazebo | Fortress / Garden | Matches your ros_gz_bridge version |
| ros2_control | `ros-humble-ros2-control` | |
| slam_toolbox | `ros-humble-slam-toolbox` | |
| rosbridge_suite | `ros-humble-rosbridge-server` | |
| ros_gz_bridge | `ros-humble-ros-gz-bridge` | |
| Node.js | 18+ | For web interface |
| Python | 3.10+ | Node scripts |

---

## Installation

### 1. Create workspace and clone

```bash
mkdir -p ~/qbot_ws/src
cd ~/qbot_ws/src
git clone https://github.com/your-org/qbot.git .
```

### 2. Install ROS 2 dependencies

```bash
cd ~/qbot_ws
sudo apt update
rosdep install --from-paths src --ignore-src -r -y
```

### 3. Build the workspace

```bash
cd ~/qbot_ws
colcon build --symlink-install
source install/setup.bash
```

Add to your shell profile:

```bash
echo "source ~/qbot_ws/install/setup.bash" >> ~/.bashrc
```

### 4. Install web interface dependencies

```bash
cd ~/qbot_ws/web_interface
npm install
```

---

## Running the system

### Simulation (Gazebo)

Launch the full simulation stack — Gazebo, RViz, ros2_control, SLAM, rosbridge, and all application nodes:

```bash
ros2 launch qbot_bringup lab_06_simulation_launch.py
```

This single launch file starts:

- Gazebo with `qbot_world.sdf`
- `robot_state_publisher` with `qbot.urdf`
- `ros_gz_bridge` for topic bridging between Gazebo and ROS 2
- `ros2_control` controller spawners (diff_drive_controller, joint_state_broadcaster)
- `slam_toolbox` in mapping mode
- `navigation_server`, `qbot_controller`, `mapper_node`, `odom_node`
- `rosbridge_server` on port 9090

### Start the web interface

In a separate terminal:

```bash
cd ~/qbot_ws/web_interface
npm start
```

Open `http://localhost:3000` in your browser.

### Real-world deployment

For hardware deployment, launch without Gazebo:

```bash
ros2 launch qbot_bringup real_robot_launch.py
```

Ensure the hardware interface is configured in `qbot_controllers.yaml` and the robot's serial/USB connection is available.

---

## Web interface

The interface replaces RViz and `teleop_twist_keyboard` with a unified browser-based dashboard.

### Map panel

- Renders the live 2D occupancy grid from `/map` (published by `slam_toolbox`)
- Overlays robot pose from `/odom` and `/tf`
- Click anywhere on free space to set an autonomous navigation goal
- Displays the planned path and lidar scan visualization

### Control panel

- D-pad buttons publish `geometry_msgs/Twist` to `/cmd_vel`
- Supports linear velocity (linear.x) and angular velocity (angular.z)
- Autonomous goal panel shows progress feedback from the `Navigation.action` server

### Status panel

- Robot state badge: Idle / Moving / Goal Reached / Error
- Live topic Hz monitor: `/map`, `/odom`, `/scan`, `/tf`, `/cmd_vel`, `/camera/image_raw`
- ROS console log showing node output

### Camera feed

- Subscribes to `/camera/image_raw` (Kinect or equivalent)
- Streams compressed image data via rosbridge

---

## ROS 2 interfaces

### `Navigation.action`

Goal-based movement interface used by `navigation_server.py`.

```
# Goal
float64 target_x
float64 target_y
float64 target_yaw
---
# Result
bool success
string message
---
# Feedback
float64 distance_remaining
float64 progress_percent
string status
```

### `Position.msg`

Robot pose snapshot stored by `mapper_node`.

```
float64 x
float64 y
float64 yaw
builtin_interfaces/Time stamp
```

### `GetLastPositions.srv`

Retrieves historical position log from `mapper_node`.

```
int32 count        # number of positions to retrieve
---
Position[] positions
```

---

## Node reference

### `navigation_server.py`

ROS 2 action server that accepts `Navigation.action` goals and drives the robot to the target pose. Publishes velocity commands via `qbot_controller` and streams feedback to the action client.

Topics subscribed: `/odom`, `/tf`  
Action server: `/navigate`

### `qbot_controller.py`

Action client that connects to `navigation_server`. Also acts as a direct velocity publisher for manual teleop commands received from the web interface.

Topics published: `/cmd_vel`  
Action client: `/navigate`

### `mapper_node.py`

Stores robot pose snapshots at configurable intervals and serves them via the `GetLastPositions` service. Integrates with `slam_toolbox` to correlate positions with map updates.

Topics subscribed: `/odom`  
Services: `/get_last_positions`

### `odom_node.py`

Optional odometry emulation node for simulation environments where hardware encoders are replaced by Gazebo ground-truth pose. Publishes `nav_msgs/Odometry` to `/odom`.

Topics published: `/odom`

---

## Configuration

### Controller configuration — `qbot_controllers.yaml`

```yaml
controller_manager:
  ros__parameters:
    update_rate: 100

diff_drive_controller:
  ros__parameters:
    left_wheel_names: ["left_wheel_joint"]
    right_wheel_names: ["right_wheel_joint"]
    wheel_separation: 0.35
    wheel_radius: 0.05
    publish_rate: 50.0
    odom_frame_id: odom
    base_frame_id: base_link
    cmd_vel_topic: /cmd_vel
```

### SLAM toolbox

`slam_toolbox` runs in `online_async` mode by default. To save a map:

```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: 'my_map'}}"
```

To switch to localization mode with a saved map, update the launch argument:

```bash
ros2 launch qbot_bringup lab_06_simulation_launch.py slam_mode:=localization map:=/path/to/my_map.yaml
```

---

## Communication architecture

```
Browser (React)
    │
    │  WebSocket  ws://localhost:9090
    ▼
rosbridge_server
    │
    ├── Subscribe  /map              → occupancy grid → MapPanel
    ├── Subscribe  /odom             → pose → robot marker
    ├── Subscribe  /tf               → transform tree
    ├── Subscribe  /camera/image_raw → camera feed
    ├── Publish    /cmd_vel          → manual control
    ├── Service    /get_last_positions
    └── Action     /navigate         → goal + feedback + result
```

The frontend uses `roslibjs` for all ROS communication:

```javascript
import ROSLIB from 'roslib';

const ros = new ROSLIB.Ros({ url: 'ws://localhost:9090' });

// Subscribe to map
const mapTopic = new ROSLIB.Topic({
  ros, name: '/map', messageType: 'nav_msgs/OccupancyGrid'
});
mapTopic.subscribe(msg => renderMap(msg));

// Publish cmd_vel
const cmdVel = new ROSLIB.Topic({
  ros, name: '/cmd_vel', messageType: 'geometry_msgs/Twist'
});
cmdVel.publish(new ROSLIB.Message({ linear: {x: 0.3}, angular: {z: 0.0} }));

// Send navigation goal
const navClient = new ROSLIB.ActionClient({
  ros, serverName: '/navigate', actionName: 'qbot_interfaces/action/Navigation'
});
const goal = new ROSLIB.Goal({ actionClient: navClient, goalMessage: { target_x: 1.0, target_y: 2.0, target_yaw: 0.0 } });
goal.on('feedback', fb => console.log(fb.progress_percent));
goal.send();
```

---

## Simulation vs real-world deployment

| Feature | Simulation | Real world |
|---|---|---|
| Robot model | `qbot.sdf` (Gazebo) | `qbot.urdf` (hardware) |
| Odometry | `odom_node.py` (ground truth) | Hardware encoders via ros2_control |
| Sensors | Gazebo plugins (lidar, camera) | Physical Kinect / RPLidar |
| Bridge | `ros_gz_bridge` | Not needed |
| Launch file | `lab_06_simulation_launch.py` | `real_robot_launch.py` |

---

## Extending the system

The interface is designed to be modular. Some suggested extensions:

- **Object detection** — subscribe to a `/detections` topic and overlay bounding boxes on the map panel
- **Dynamic obstacles** — visualize costmap inflation layers from `/global_costmap/costmap`
- **Multi-robot support** — namespace each robot (`/robot1/cmd_vel`, `/robot2/cmd_vel`) and add a robot selector in the UI
- **Path recording** — use `GetLastPositions.srv` to replay recorded routes
- **3D visualization** — embed a Three.js point cloud renderer subscribed to `/scan` or `/pointcloud`

---

## Troubleshooting

**rosbridge not connecting**  
Check that `rosbridge_server` is running: `ros2 node list | grep rosbridge`. Verify port 9090 is not blocked by a firewall.

**Map not rendering**  
Confirm `slam_toolbox` is publishing: `ros2 topic hz /map`. The first map message may take a few seconds after launch.

**Robot not moving**  
Check that the `diff_drive_controller` is active: `ros2 control list_controllers`. Ensure `/cmd_vel` is being received: `ros2 topic echo /cmd_vel`.

**Navigation goal not accepted**  
Verify `navigation_server` is running: `ros2 node list | grep navigation_server`. Check action server is available: `ros2 action list`.

**Gazebo and ROS 2 topics not bridged**  
Confirm `ros_gz_bridge` is running and the bridge config matches your topic names and message types.

---

## License

MIT License. See `LICENSE` for details.
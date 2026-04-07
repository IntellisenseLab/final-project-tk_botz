"""
state_broadcaster.py

Purpose:
- Aggregate robot state from odom, battery, bumper topics.
- Publish a single JSON state payload to /app/robot_state at fixed rate.

Subscribes:
- /odom (default): nav_msgs/Odometry
- /kobuki/battery_state (default): sensor_msgs/BatteryState
- /kobuki/bumper_event (default): kobuki_ros_interfaces/BumperEvent if available, else std_msgs/String

Publishes:
- /app/robot_state (default): std_msgs/String
"""

import json
import math
import threading
import time
from typing import Dict, Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState

try:
    from kobuki_ros_interfaces.msg import BumperEvent as KobukiBumperEvent
except Exception:  # pragma: no cover
    KobukiBumperEvent = None

from std_msgs.msg import String as StdString


def _yaw_from_quaternion(z: float, w: float) -> float:
    return 2.0 * math.atan2(z, w)


class StateBroadcaster(Node):
    def __init__(self) -> None:
        super().__init__("state_broadcaster")

        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("battery_topic", "/kobuki/battery_state")
        self.declare_parameter("bumper_topic", "/kobuki/bumper_event")
        self.declare_parameter("robot_state_topic", "/app/robot_state")
        self.declare_parameter("state_broadcast_rate_hz", 5.0)

        odom_topic = str(self.get_parameter("odom_topic").value)
        battery_topic = str(self.get_parameter("battery_topic").value)
        bumper_topic = str(self.get_parameter("bumper_topic").value)
        robot_state_topic = str(self.get_parameter("robot_state_topic").value)
        rate_hz = float(self.get_parameter("state_broadcast_rate_hz").value)
        if rate_hz <= 0.0:
            rate_hz = 5.0

        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "pose": {"x": 0.0, "y": 0.0, "theta": 0.0},
            "battery_percent": 0.0,
            "is_charging": False,
            "bumper": {"left": False, "center": False, "right": False},
            "timestamp": 0.0,
        }

        self.pub = self.create_publisher(String, robot_state_topic, 20)

        self.create_subscription(Odometry, odom_topic, self._on_odom, 20)
        self.create_subscription(BatteryState, battery_topic, self._on_battery, 20)

        if KobukiBumperEvent is not None:
            self.create_subscription(KobukiBumperEvent, bumper_topic, self._on_bumper_kobuki, 20)
            self.get_logger().info("Using kobuki_ros_interfaces/BumperEvent")
        else:
            self.create_subscription(StdString, bumper_topic, self._on_bumper_fallback, 20)
            self.get_logger().warn(
                "kobuki_ros_interfaces not available. Using std_msgs/String bumper fallback."
            )

        self.timer = self.create_timer(1.0 / rate_hz, self._publish_state)
        self.get_logger().info(
            f"State broadcaster started. output={robot_state_topic} rate={rate_hz:.2f}Hz"
        )

    def _on_odom(self, msg: Odometry) -> None:
        try:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            theta = _yaw_from_quaternion(q.z, q.w)
            with self._lock:
                self._state["pose"] = {"x": float(p.x), "y": float(p.y), "theta": float(theta)}
        except Exception as exc:
            self.get_logger().warn(f"Odom callback error: {exc}")

    def _on_battery(self, msg: BatteryState) -> None:
        try:
            percent = float(msg.percentage * 100.0) if msg.percentage <= 1.0 else float(msg.percentage)
            charging = bool(msg.power_supply_status == BatteryState.POWER_SUPPLY_STATUS_CHARGING)
            with self._lock:
                self._state["battery_percent"] = max(0.0, min(100.0, percent))
                self._state["is_charging"] = charging
        except Exception as exc:
            self.get_logger().warn(f"Battery callback error: {exc}")

    def _on_bumper_kobuki(self, msg) -> None:
        try:
            # kobuki_ros_interfaces/BumperEvent:
            # bumper: LEFT=0, CENTER=1, RIGHT=2
            # state: PRESSED=1, RELEASED=0
            left = center = right = False
            pressed = int(msg.state) == 1
            bumper_id = int(msg.bumper)
            if bumper_id == 0:
                left = pressed
            elif bumper_id == 1:
                center = pressed
            elif bumper_id == 2:
                right = pressed

            with self._lock:
                current = self._state["bumper"]
                self._state["bumper"] = {
                    "left": left or current["left"],
                    "center": center or current["center"],
                    "right": right or current["right"],
                }
        except Exception as exc:
            self.get_logger().warn(f"Bumper(kobuki) callback error: {exc}")

    def _on_bumper_fallback(self, msg: StdString) -> None:
        try:
            text = msg.data.lower()
            with self._lock:
                self._state["bumper"] = {
                    "left": "left" in text,
                    "center": "center" in text,
                    "right": "right" in text,
                }
        except Exception as exc:
            self.get_logger().warn(f"Bumper(fallback) callback error: {exc}")

    def _publish_state(self) -> None:
        try:
            with self._lock:
                payload = {
                    "pose": dict(self._state["pose"]),
                    "battery_percent": float(self._state["battery_percent"]),
                    "is_charging": bool(self._state["is_charging"]),
                    "bumper": dict(self._state["bumper"]),
                    "timestamp": time.time(),
                }

            out = String()
            out.data = json.dumps(payload)
            self.pub.publish(out)
        except Exception as exc:
            self.get_logger().error(f"State publish error: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StateBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
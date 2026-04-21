"""
rest_api_node.py

Purpose:
- Provide Flask REST API for app:
  GET /status    -> robot state JSON
  GET /map       -> latest map PNG
  GET /last_positions -> pose history JSON (query: ?count=N)
- Subscribe to ROS topics for status and map updates.
- Run Flask in a background thread.
- Maintain thread-safe shared state between ROS callbacks and Flask handlers.

Subscribes:
- /odom (default): nav_msgs/Odometry
- /kobuki/battery_state (default): sensor_msgs/BatteryState
- /kobuki/bumper_event (default): std_msgs/String fallback style
- /map (default): nav_msgs/OccupancyGrid
"""

import io
import json
import math
import threading
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image
from flask import Flask, jsonify, Response, request
from werkzeug.serving import make_server

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

from .map_server_bridge import get_latest_map_png, set_latest_map_png


def _yaw_from_quaternion(z: float, w: float) -> float:
    # Yaw extraction for planar robots.
    return 2.0 * math.atan2(z, w)


class _ServerThread(threading.Thread):
    def __init__(self, app: Flask, host: str, port: int):
        super().__init__(daemon=True)
        self._server = make_server(host, port, app)
        self._ctx = app.app_context()
        self._ctx.push()

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()


class RestApiNode(Node):
    def __init__(self) -> None:
        super().__init__("rest_api_node")

        self.declare_parameter("http_host", "0.0.0.0")
        self.declare_parameter("http_port", 8080)
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("battery_topic", "/kobuki/battery_state")
        self.declare_parameter("bumper_topic", "/kobuki/bumper_event")
        self.declare_parameter("map_topic", "/map")

        self.http_host = str(self.get_parameter("http_host").value)
        self.http_port = int(self.get_parameter("http_port").value)
        self.declare_parameter("max_history_len", 100)
        self.max_history_len = int(self.get_parameter("max_history_len").value)

        odom_topic = str(self.get_parameter("odom_topic").value)
        battery_topic = str(self.get_parameter("battery_topic").value)
        bumper_topic = str(self.get_parameter("bumper_topic").value)
        map_topic = str(self.get_parameter("map_topic").value)

        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "battery": {"percent": 0.0, "is_charging": False, "voltage": 0.0},
            "pose": {"x": 0.0, "y": 0.0, "theta": 0.0},
            "is_moving": False,
            "bumper": {"left": False, "center": False, "right": False},
        }
        self._pose_history: list = []  # Bounded history of pose samples
        self._map_png: Optional[bytes] = None

        self.create_subscription(Odometry, odom_topic, self._on_odom, 20)
        self.create_subscription(BatteryState, battery_topic, self._on_battery, 20)
        self.create_subscription(String, bumper_topic, self._on_bumper, 20)
        self.create_subscription(OccupancyGrid, map_topic, self._on_map, 5)

        self._app = Flask("kobuki_app_bridge_rest")
        self._register_routes()

        self._server_thread = _ServerThread(self._app, self.http_host, self.http_port)
        self._server_thread.start()

        self.get_logger().info(
            f"REST API started on http://{self.http_host}:{self.http_port}"
        )

    def _register_routes(self) -> None:
        @self._app.get("/status")
        def status_handler():
            with self._lock:
                payload = {
                    "battery": dict(self._state["battery"]),
                    "pose": dict(self._state["pose"]),
                    "is_moving": bool(self._state["is_moving"]),
                    "bumper": dict(self._state["bumper"]),
                }
            return jsonify(payload)

        @self._app.get("/map")
        def map_handler():
            with self._lock:
                local_png = self._map_png

            if local_png is None:
                # Fallback to module-shared map buffer (useful in single-process runs)
                local_png = get_latest_map_png()

            if local_png is None:
                return jsonify({"error": "map not available yet"}), 503

            return Response(local_png, status=200, mimetype="image/png")

        @self._app.get("/last_positions")
        def last_positions_handler():
            try:
                count = int(request.args.get("count",10))
                count = max(1, min(count, self.max_history_len))
            except (ValueError, TypeError):
                count = 10

            with self._lock:
                positions = list(self._pose_history[-count:])

            return jsonify({"positions": positions})

    def _on_odom(self, msg: Odometry) -> None:
        try:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            t = msg.twist.twist

            theta = _yaw_from_quaternion(q.z, q.w)
            speed = math.sqrt((t.linear.x ** 2) + (t.linear.y ** 2))
            is_moving = speed > 0.01 or abs(t.angular.z) > 0.01

            current_pose = {"x": float(p.x), "y": float(p.y), "theta": float(theta)}

            with self._lock:
                self._state["pose"] = dict(current_pose)
                self._state["is_moving"] = bool(is_moving)
                # Append pose to history (bounded by max_history_len)
                self._pose_history.append(current_pose)
                if len(self._pose_history) > self.max_history_len:
                    self._pose_history.pop(0)
        except Exception as exc:
            self.get_logger().warn(f"Odom processing failed: {exc}")

    def _on_battery(self, msg: BatteryState) -> None:
        try:
            percent = float(msg.percentage * 100.0) if msg.percentage <= 1.0 else float(msg.percentage)
            with self._lock:
                self._state["battery"] = {
                    "percent": max(0.0, min(100.0, percent)),
                    "is_charging": bool(msg.power_supply_status == BatteryState.POWER_SUPPLY_STATUS_CHARGING),
                    "voltage": float(msg.voltage),
                }
        except Exception as exc:
            self.get_logger().warn(f"Battery processing failed: {exc}")

    def _on_bumper(self, msg: String) -> None:
        try:
            data = json.loads(msg.data)
            left = bool(data.get("left", False))
            center = bool(data.get("center", False))
            right = bool(data.get("right", False))
            with self._lock:
                self._state["bumper"] = {"left": left, "center": center, "right": right}
        except Exception:
            # Graceful fallback if bumper topic is plain string.
            text = msg.data.strip().lower()
            with self._lock:
                self._state["bumper"] = {
                    "left": "left" in text,
                    "center": "center" in text,
                    "right": "right" in text,
                }

    def _on_map(self, msg: OccupancyGrid) -> None:
        try:
            width = int(msg.info.width)
            height = int(msg.info.height)
            if width <= 0 or height <= 0:
                return

            arr = np.array(msg.data, dtype=np.int16).reshape((height, width))
            img = np.full((height, width), 128, dtype=np.uint8)
            img[arr == 0] = 255
            img[arr >= 100] = 0
            mid = (arr > 0) & (arr < 100)
            img[mid] = np.uint8(255 - (arr[mid] * 255 // 100))
            img = np.flipud(img)

            pil_img = Image.fromarray(img, mode="L")
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            png = buf.getvalue()

            with self._lock:
                self._map_png = png

            set_latest_map_png(png)
        except Exception as exc:
            self.get_logger().warn(f"Map conversion in REST node failed: {exc}")

    def destroy_node(self) -> bool:
        try:
            if hasattr(self, "_server_thread"):
                self._server_thread.shutdown()
        except Exception as exc:
            self.get_logger().warn(f"REST server shutdown warning: {exc}")
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RestApiNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
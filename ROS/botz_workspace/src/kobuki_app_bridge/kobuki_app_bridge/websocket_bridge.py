"""
websocket_bridge.py

Purpose:
- Manage rosbridge websocket process (port configurable, default 9090).
- Monitor rosout logs to report client connect/disconnect events from rosbridge.
- Keep rosbridge lifecycle tied to this node when enabled.

Subscribes:
- /rosout: rcl_interfaces/msg/Log (for rosbridge client connect/disconnect messages)

Publishes:
- None
"""

import subprocess
from typing import Optional

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import Log


class WebsocketBridge(Node):
    def __init__(self) -> None:
        super().__init__("websocket_bridge")

        self.declare_parameter("websocket_port", 9090)
        self.declare_parameter("launch_internal_rosbridge", True)

        self.websocket_port = int(self.get_parameter("websocket_port").value)
        self.launch_internal_rosbridge = bool(self.get_parameter("launch_internal_rosbridge").value)

        self._proc: Optional[subprocess.Popen] = None
        self.create_subscription(Log, "/rosout", self._on_rosout, 100)

        if self.launch_internal_rosbridge:
            self._start_rosbridge()
        else:
            self.get_logger().info("Internal rosbridge launch disabled by parameter.")

        self.get_logger().info(
            f"Websocket bridge ready on port {self.websocket_port}. "
            f"internal_launch={self.launch_internal_rosbridge}"
        )

    def _start_rosbridge(self) -> None:
        try:
            cmd = [
                "ros2",
                "launch",
                "rosbridge_server",
                "rosbridge_websocket_launch.xml",
                f"port:={self.websocket_port}",
            ]
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.get_logger().info("Started rosbridge_server subprocess.")
        except Exception as exc:
            self.get_logger().error(f"Failed to start rosbridge_server: {exc}")

    def _on_rosout(self, msg: Log) -> None:
        try:
            name = msg.name.lower()
            text = msg.msg.lower()
            if "rosbridge" not in name:
                return

            if ("client connected" in text) or ("new client" in text):
                self.get_logger().info(f"Rosbridge client connected: {msg.msg}")
            elif ("client disconnected" in text) or ("closed connection" in text):
                self.get_logger().info(f"Rosbridge client disconnected: {msg.msg}")
        except Exception as exc:
            self.get_logger().warn(f"rosout parsing error: {exc}")

    def destroy_node(self) -> bool:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3.0)
                self.get_logger().info("Stopped rosbridge_server subprocess.")
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WebsocketBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
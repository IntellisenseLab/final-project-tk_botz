"""
command_router.py

Purpose:
- Consume app commands from /app/command as JSON strings.
- Validate and route commands to robot ROS interfaces.

Subscribes:
- /app/command (default): std_msgs/String

Publishes:
- /cmd_vel (default): geometry_msgs/Twist
- /goal_pose (default): geometry_msgs/PoseStamped
"""

import json
import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist, PoseStamped


def _yaw_to_quaternion(theta: float):
    return math.sin(theta / 2.0), math.cos(theta / 2.0)


class CommandRouter(Node):
    def __init__(self) -> None:
        super().__init__("command_router")

        self.declare_parameter("app_command_topic", "/app/command")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("goal_topic", "/goal_pose")
        self.declare_parameter("goal_frame", "map")
        self.declare_parameter("max_linear_speed", 0.3)
        self.declare_parameter("max_angular_speed", 1.0)

        app_command_topic = str(self.get_parameter("app_command_topic").value)
        cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        goal_topic = str(self.get_parameter("goal_topic").value)
        self.goal_frame = str(self.get_parameter("goal_frame").value)

        self.max_linear_speed = float(self.get_parameter("max_linear_speed").value)
        self.max_angular_speed = float(self.get_parameter("max_angular_speed").value)

        self.cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 20)
        self.goal_pub = self.create_publisher(PoseStamped, goal_topic, 10)
        self.create_subscription(String, app_command_topic, self._on_command, 50)

        self.get_logger().info(
            f"Command router started. input={app_command_topic} cmd_vel={cmd_vel_topic} goal={goal_topic}"
        )

    def _safe_float(self, value, field_name: str):
        try:
            return float(value)
        except Exception:
            raise ValueError(f"Field '{field_name}' must be numeric")

    def _publish_stop(self) -> None:
        msg = Twist()
        self.cmd_vel_pub.publish(msg)
        self.get_logger().info("Published emergency stop (zero Twist)")

    def _publish_velocity(self, linear: float, angular: float) -> None:
        linear = max(-self.max_linear_speed, min(self.max_linear_speed, linear))
        angular = max(-self.max_angular_speed, min(self.max_angular_speed, angular))

        msg = Twist()
        msg.linear.x = float(linear)
        msg.angular.z = float(angular)
        self.cmd_vel_pub.publish(msg)

        self.get_logger().info(f"Published velocity linear={linear:.3f} angular={angular:.3f}")

    def _publish_goal(self, x: float, y: float, theta: float) -> None:
        qz, qw = _yaw_to_quaternion(theta)

        msg = PoseStamped()
        msg.header.frame_id = self.goal_frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.orientation.z = float(qz)
        msg.pose.orientation.w = float(qw)

        self.goal_pub.publish(msg)
        self.get_logger().info(f"Published goal x={x:.3f} y={y:.3f} theta={theta:.3f}")

    def _on_command(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
            if not isinstance(payload, dict):
                raise ValueError("Command payload must be a JSON object")
        except Exception as exc:
            self.get_logger().warn(f"Malformed /app/command JSON ignored: {exc}")
            return

        cmd_type = str(payload.get("type", "")).strip().lower()
        if cmd_type == "":
            self.get_logger().warn("Command missing required field 'type'")
            return

        try:
            if cmd_type == "velocity":
                if "linear" not in payload or "angular" not in payload:
                    raise ValueError("Velocity command requires fields: linear, angular")
                linear = self._safe_float(payload["linear"], "linear")
                angular = self._safe_float(payload["angular"], "angular")
                self._publish_velocity(linear, angular)
                return

            if cmd_type == "goal":
                required = ("x", "y", "theta")
                for field in required:
                    if field not in payload:
                        raise ValueError(f"Goal command requires field: {field}")
                x = self._safe_float(payload["x"], "x")
                y = self._safe_float(payload["y"], "y")
                theta = self._safe_float(payload["theta"], "theta")
                self._publish_goal(x, y, theta)
                return

            if cmd_type == "stop":
                self._publish_stop()
                return

            self.get_logger().warn(f"Unknown command type '{cmd_type}' ignored")
        except Exception as exc:
            self.get_logger().warn(f"Rejected invalid command '{cmd_type}': {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CommandRouter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
"""
goal_manager.py

Purpose:
- Act as Nav2 NavigateToPose action client.
- Accept goals from app topic and forward to Nav2.
- Publish goal lifecycle status to app status topic.
- Cancel active goal when a zero-velocity cmd_vel is observed.

Subscribes:
- /app/goal (default): geometry_msgs/PoseStamped
- /goal_pose (default): geometry_msgs/PoseStamped (compatibility with command_router)
- /cmd_vel (default): geometry_msgs/Twist

Publishes:
- /app/goal_status (default): std_msgs/String (JSON)
"""

import json
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Twist
from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose


class GoalManager(Node):
    def __init__(self) -> None:
        super().__init__("goal_manager")

        self.declare_parameter("app_goal_topic", "/app/goal")
        self.declare_parameter("goal_pose_topic", "/goal_pose")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("goal_status_topic", "/app/goal_status")
        self.declare_parameter("navigate_action_name", "/navigate_to_pose")

        app_goal_topic = str(self.get_parameter("app_goal_topic").value)
        goal_pose_topic = str(self.get_parameter("goal_pose_topic").value)
        cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        goal_status_topic = str(self.get_parameter("goal_status_topic").value)
        action_name = str(self.get_parameter("navigate_action_name").value)

        self.status_pub = self.create_publisher(String, goal_status_topic, 20)
        self.create_subscription(PoseStamped, app_goal_topic, self._on_goal, 10)
        if goal_pose_topic != app_goal_topic:
            self.create_subscription(PoseStamped, goal_pose_topic, self._on_goal, 10)
        self.create_subscription(Twist, cmd_vel_topic, self._on_cmd_vel, 30)

        self.nav_client = ActionClient(self, NavigateToPose, action_name)

        self._lock = threading.Lock()
        self._active_goal_handle = None
        self._active_goal_xy: Optional[dict] = None

        self.get_logger().info(
            f"Goal manager started. app_goal={app_goal_topic} goal_pose={goal_pose_topic} action={action_name}"
        )

    def _publish_status(self, status: str, goal_xy: Optional[dict] = None, details: str = "") -> None:
        payload = {"status": status, "goal": goal_xy or {"x": 0.0, "y": 0.0}}
        if details:
            payload["details"] = details

        msg = String()
        msg.data = json.dumps(payload)
        self.status_pub.publish(msg)

    def _on_goal(self, msg: PoseStamped) -> None:
        try:
            goal_xy = {"x": float(msg.pose.position.x), "y": float(msg.pose.position.y)}

            if not self.nav_client.wait_for_server(timeout_sec=2.0):
                self.get_logger().error("NavigateToPose action server unavailable")
                self._publish_status("failed", goal_xy, "NavigateToPose action server unavailable")
                return

            goal_msg = NavigateToPose.Goal()
            goal_msg.pose = msg

            send_future = self.nav_client.send_goal_async(
                goal_msg,
                feedback_callback=self._on_feedback,
            )
            send_future.add_done_callback(lambda future: self._on_goal_response(future, goal_xy))
            self.get_logger().info(f"Sent goal to Nav2: {goal_xy}")
        except Exception as exc:
            self.get_logger().error(f"Goal dispatch failed: {exc}")
            self._publish_status("failed", {"x": 0.0, "y": 0.0}, str(exc))

    def _on_goal_response(self, future, goal_xy: dict) -> None:
        try:
            goal_handle = future.result()
            if goal_handle is None or not goal_handle.accepted:
                self.get_logger().warn("Nav2 rejected goal")
                self._publish_status("failed", goal_xy, "Goal rejected")
                return

            with self._lock:
                self._active_goal_handle = goal_handle
                self._active_goal_xy = dict(goal_xy)

            self._publish_status("navigating", goal_xy)
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(self._on_result)
        except Exception as exc:
            self.get_logger().error(f"Goal response handling failed: {exc}")
            self._publish_status("failed", goal_xy, str(exc))

    def _on_feedback(self, _feedback_msg) -> None:
        with self._lock:
            goal_xy = dict(self._active_goal_xy) if self._active_goal_xy else {"x": 0.0, "y": 0.0}
        self._publish_status("navigating", goal_xy)

    def _on_result(self, future) -> None:
        try:
            wrapped = future.result()
            status = int(wrapped.status)

            with self._lock:
                goal_xy = dict(self._active_goal_xy) if self._active_goal_xy else {"x": 0.0, "y": 0.0}
                self._active_goal_handle = None
                self._active_goal_xy = None

            if status == GoalStatus.STATUS_SUCCEEDED:
                self._publish_status("arrived", goal_xy)
            elif status == GoalStatus.STATUS_CANCELED:
                self._publish_status("cancelled", goal_xy)
            else:
                self._publish_status("failed", goal_xy, f"Nav2 result status={status}")
        except Exception as exc:
            self.get_logger().error(f"Result handling failed: {exc}")
            self._publish_status("failed", {"x": 0.0, "y": 0.0}, str(exc))

    def _on_cmd_vel(self, msg: Twist) -> None:
        # Cancel active goal when stop command is observed via zero velocity.
        try:
            is_zero = (
                abs(msg.linear.x) < 1e-6
                and abs(msg.linear.y) < 1e-6
                and abs(msg.linear.z) < 1e-6
                and abs(msg.angular.x) < 1e-6
                and abs(msg.angular.y) < 1e-6
                and abs(msg.angular.z) < 1e-6
            )
            if not is_zero:
                return

            with self._lock:
                goal_handle = self._active_goal_handle
                goal_xy = dict(self._active_goal_xy) if self._active_goal_xy else {"x": 0.0, "y": 0.0}

            if goal_handle is None:
                return

            cancel_future = goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(lambda _f: self._publish_status("cancelled", goal_xy))
            self.get_logger().info("Zero cmd_vel detected. Requested active goal cancellation.")
        except Exception as exc:
            self.get_logger().warn(f"cmd_vel cancel check failed: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GoalManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
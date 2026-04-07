import json
import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from std_msgs.msg import String
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from nav2_msgs.action import NavigateToPose


def yaw_to_quaternion(theta: float):
    qz = math.sin(theta / 2.0)
    qw = math.cos(theta / 2.0)
    return qz, qw


class BridgeNode(Node):
    def __init__(self):
        super().__init__("kobuki_app_bridge")

        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("battery_topic", "/battery_state")
        self.declare_parameter("bumper_topic", "/bumper_state")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("nav_action_name", "/navigate_to_pose")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("max_linear", 0.4)
        self.declare_parameter("max_angular", 1.2)

        odom_topic = self.get_parameter("odom_topic").get_parameter_value().string_value
        battery_topic = self.get_parameter("battery_topic").get_parameter_value().string_value
        bumper_topic = self.get_parameter("bumper_topic").get_parameter_value().string_value
        cmd_vel_topic = self.get_parameter("cmd_vel_topic").get_parameter_value().string_value
        nav_action_name = self.get_parameter("nav_action_name").get_parameter_value().string_value

        self.max_linear = float(self.get_parameter("max_linear").value)
        self.max_angular = float(self.get_parameter("max_angular").value)
        self.map_frame = self.get_parameter("map_frame").get_parameter_value().string_value

        self.pose_pub = self.create_publisher(String, "/app/pose", 10)
        self.battery_pub = self.create_publisher(String, "/app/battery", 10)
        self.bumper_pub = self.create_publisher(String, "/app/bumpers", 10)
        self.goal_status_pub = self.create_publisher(String, "/app/goal_status", 10)

        self.cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        self.create_subscription(Odometry, odom_topic, self.on_odom, 10)
        self.create_subscription(BatteryState, battery_topic, self.on_battery, 10)
        self.create_subscription(String, bumper_topic, self.on_bumper, 10)

        self.create_subscription(String, "/app/command", self.on_app_command, 10)

        self.nav_client = ActionClient(self, NavigateToPose, nav_action_name)

        self.get_logger().info("kobuki_app_bridge node started")

    def publish_json(self, pub, payload):
        msg = String()
        msg.data = json.dumps(payload)
        pub.publish(msg)

    def on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = 2.0 * math.atan2(q.z, q.w)
        self.publish_json(self.pose_pub, {"x": p.x, "y": p.y, "theta": yaw})

    def on_battery(self, msg: BatteryState):
        self.publish_json(self.battery_pub, {
            "voltage": msg.voltage,
            "percentage": msg.percentage,
            "present": msg.present,
        })

    def on_bumper(self, msg: String):
        try:
            data = json.loads(msg.data)
        except Exception:
            data = {"raw": msg.data}
        self.publish_json(self.bumper_pub, data)

    def clamp(self, value, lo, hi):
        return max(lo, min(hi, value))

    def on_app_command(self, msg: String):
        try:
            cmd = json.loads(msg.data)
        except Exception as e:
            self.get_logger().warn(f"Invalid JSON on /app/command: {e}")
            return

        cmd_type = cmd.get("type", "")

        if cmd_type == "velocity":
            linear = float(cmd.get("linear", 0.0))
            angular = float(cmd.get("angular", 0.0))
            linear = self.clamp(linear, -self.max_linear, self.max_linear)
            angular = self.clamp(angular, -self.max_angular, self.max_angular)

            t = Twist()
            t.linear.x = linear
            t.angular.z = angular
            self.cmd_vel_pub.publish(t)
            return

        if cmd_type == "nav_goal":
            x = float(cmd.get("x", 0.0))
            y = float(cmd.get("y", 0.0))
            theta = float(cmd.get("theta", 0.0))
            self.send_nav_goal(x, y, theta)
            return

        self.get_logger().warn(f"Unknown command type: {cmd_type}")

    def send_nav_goal(self, x, y, theta):
        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            self.publish_json(self.goal_status_pub, {
                "status": "error",
                "message": "NavigateToPose action server unavailable"
            })
            return

        goal = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = self.map_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        qz, qw = yaw_to_quaternion(theta)
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        goal.pose = pose

        self.publish_json(self.goal_status_pub, {
            "status": "accepted",
            "message": f"Goal accepted: ({x:.2f}, {y:.2f}, {theta:.2f})"
        })

        send_future = self.nav_client.send_goal_async(goal, feedback_callback=self.on_feedback)
        send_future.add_done_callback(self.on_goal_response)

    def on_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        self.publish_json(self.goal_status_pub, {
            "status": "navigating",
            "message": "Navigation in progress",
            "distance_remaining": getattr(fb, "distance_remaining", None)
        })

    def on_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.publish_json(self.goal_status_pub, {
                "status": "rejected",
                "message": "Goal rejected"
            })
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.on_result)

    def on_result(self, future):
        result = future.result().result
        self.publish_json(self.goal_status_pub, {
            "status": "finished",
            "message": "Navigation finished",
            "result": str(result)
        })


def main(args=None):
    rclpy.init(args=args)
    node = BridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
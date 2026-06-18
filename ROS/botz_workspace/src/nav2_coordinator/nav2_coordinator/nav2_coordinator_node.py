#!/usr/bin/env python3

import math
import threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus

from nav_coordinator_interfaces.srv import NavigateToCoordinate


def yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class Nav2CoordinatorNode(Node):

    def __init__(self):
        super().__init__('nav2_coordinator_node')

        self._cb_group = ReentrantCallbackGroup()

        self._action_client = ActionClient(
            self,
            NavigateToPose,
            'navigate_to_pose',
            callback_group=self._cb_group,
        )

        self._service = self.create_service(
            NavigateToCoordinate,
            'navigate_to_coordinate',
            self._handle_navigate_request,
            callback_group=self._cb_group,
        )

        self._goal_lock = threading.Lock()
        self._active_goal_handle = None

        self.get_logger().info('Nav2CoordinatorNode is ready.')

    def _handle_navigate_request(self, request, response):
        self.get_logger().info(
            f'Received navigation request: x={request.x:.3f}, y={request.y:.3f}, '
            f'theta={request.theta:.3f}, xy_tol={request.xy_tolerance:.3f}, '
            f'yaw_tol={request.yaw_tolerance:.3f}'
        )

        if not self._action_client.wait_for_server(timeout_sec=5.0):
            msg = 'Nav2 action server not available after 5 s.'
            self.get_logger().error(msg)
            response.success = False
            response.message = msg
            return response

        goal_msg = NavigateToPose.Goal()

        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = request.x
        pose.pose.position.y = request.y
        pose.pose.position.z = 0.0
        pose.pose.orientation = yaw_to_quaternion(request.theta)

        goal_msg.pose = pose

        if hasattr(goal_msg, 'behavior_tree'):
            goal_msg.behavior_tree = ''

        send_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback,
        )

        rclpy.spin_until_future_complete(self, send_future)

        goal_handle = send_future.result()

        if goal_handle is None:
            msg = 'Failed to send goal to Nav2 (no response from action server).'
            self.get_logger().error(msg)
            response.success = False
            response.message = msg
            return response

        if not goal_handle.accepted:
            msg = 'Goal was rejected by Nav2.'
            self.get_logger().warn(msg)
            response.success = False
            response.message = msg
            return response

        self.get_logger().info('Goal accepted by Nav2, waiting for result...')

        with self._goal_lock:
            self._active_goal_handle = goal_handle

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        with self._goal_lock:
            self._active_goal_handle = None

        wrapped = result_future.result()

        if wrapped is None:
            msg = 'Navigation failed: no result received from action server.'
            self.get_logger().error(msg)
            response.success = False
            response.message = msg
            return response

        status = wrapped.status

        if status == GoalStatus.STATUS_SUCCEEDED:
            msg = 'Navigation succeeded.'
            self.get_logger().info(msg)
            response.success = True
            response.message = msg

        elif status == GoalStatus.STATUS_CANCELED:
            msg = 'Navigation was cancelled.'
            self.get_logger().warn(msg)
            response.success = False
            response.message = msg

        elif status == GoalStatus.STATUS_ABORTED:
            msg = 'Navigation was aborted by Nav2 (obstacle or planner failure).'
            self.get_logger().error(msg)
            response.success = False
            response.message = msg

        else:
            msg = f'Navigation ended with unexpected status code: {status}.'
            self.get_logger().error(msg)
            response.success = False
            response.message = msg

        return response

    def _feedback_callback(self, feedback_msg):
        fb = feedback_msg.feedback
        try:
            remaining = fb.distance_remaining
        except AttributeError:
            remaining = float('nan')

        try:
            nav_time = fb.navigation_time.sec + fb.navigation_time.nanosec * 1e-9
        except AttributeError:
            nav_time = float('nan')

        try:
            eta = fb.estimated_time_remaining.sec + fb.estimated_time_remaining.nanosec * 1e-9
        except AttributeError:
            eta = float('nan')

        self.get_logger().info(
            f'[Nav2 Feedback] distance_remaining={remaining:.3f} m  '
            f'nav_time={nav_time:.1f} s  '
            f'eta={eta:.1f} s'
        )


def main(args=None):
    rclpy.init(args=args)

    node = Nav2CoordinatorNode()

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Nav2CoordinatorNode.')
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
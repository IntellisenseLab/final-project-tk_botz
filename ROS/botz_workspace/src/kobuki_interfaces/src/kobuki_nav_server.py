import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
import time

from geometry_msgs.msg import PoseStamped
from kobuki_interfaces.srv import RobotNav
from kobuki_interfaces.msg import RobotNavFeedback, RobotNavResult

class KobukiNavServer(Node):
    def __init__(self):
        super().__init__('kobuki_nav_server')
        
        # Service for sending goal
        self.srv = self.create_service(RobotNav, 'robot_nav', self.handle_nav_request)
        
        # Publish feedback continuously
        self.feedback_pub = self.create_publisher(RobotNavFeedback, '/robot_nav/feedback', 10)
        
        self.get_logger().info('Kobuki Navigation Server Ready!')

    def handle_nav_request(self, request, response):
        self.get_logger().info(f'Received goal: x={request.target_pose.pose.position.x}, y={request.target_pose.pose.position.y}')
        
        feedback = RobotNavFeedback()
        
        # Simulate movement
        for i in range(10, 0, -1):
            feedback.distance_remaining = float(i)
            feedback.status = f"Moving... {i}m left"
            self.feedback_pub.publish(feedback)
            self.get_logger().info(f'Feedback: {i}m remaining')
            time.sleep(0.8)
        
        response.success = True
        response.message = "Goal reached successfully"
        return response

def main(args=None):
    rclpy.init(args=args)
    node = KobukiNavServer()
    executor = MultiThreadedExecutor()
    rclpy.spin(node, executor=executor)

if __name__ == '__main__':
    main()

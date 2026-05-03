import rclpy
import time
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from kobuki_interfaces.srv import RobotNav
from kobuki_interfaces.msg import RobotNavFeedback

class KobukiNavServer(Node):
    def __init__(self):
        super().__init__('kobuki_nav_server')
        
        # Service to receive goal
        self.srv = self.create_service(RobotNav, 'robot_nav', self.handle_nav_goal)
        
        # Topic to publish feedback
        self.feedback_pub = self.create_publisher(RobotNavFeedback, '/robot_nav/feedback', 10)
        
        self.get_logger().info('Kobuki Navigation Service Ready on /robot_nav')

    def handle_nav_goal(self, request, response):
        self.get_logger().info(f'Goal received → X={request.pose.pose.position.x}, Y={request.pose.pose.position.y}')
        
        feedback = RobotNavFeedback()
        
        # Simulate navigation with feedback
        for i in range(10, 0, -1):
            feedback.distance_remaining = float(i)
            feedback.status = f"Moving... {i}m remaining"
            self.feedback_pub.publish(feedback)
            self.get_logger().info(f'Feedback: {i}m left')
            time.sleep(1.0)
        
        self.get_logger().info('Goal reached successfully!')
        response.success = True
        response.message = "Goal reached successfully"
        return response

def main(args=None):
    rclpy.init(args=args)
    node = KobukiNavServer()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
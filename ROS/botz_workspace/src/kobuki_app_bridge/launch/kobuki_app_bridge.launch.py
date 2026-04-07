from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="kobuki_app_bridge",
            executable="bridge_node",
            name="kobuki_app_bridge",
            output="screen",
            parameters=[{
                "odom_topic": "/odom",
                "battery_topic": "/battery_state",
                "bumper_topic": "/bumper_state",
                "cmd_vel_topic": "/cmd_vel",
                "nav_action_name": "/navigate_to_pose",
                "map_frame": "map",
                "max_linear": 0.4,
                "max_angular": 1.2,
            }],
        ),
        Node(
            package="kobuki_app_bridge",
            executable="map_http_node",
            name="map_http_node",
            output="screen",
            parameters=[{
                "map_topic": "/map",
                "http_host": "0.0.0.0",
                "http_port": 8080,
            }],
        ),
    ])
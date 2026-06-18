from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        
        # Kinect Driver Node
        Node(
            package='kinect_ros2',
            executable='kinect_ros2_node',
            name='kinect_ros2_node',
            parameters=[
                {'resolution': '640x480'},
                {'frame_rate': 15}
            ],
            output='screen'
        ),

        # Web Video Server (MJPEG Stream)
        Node(
            package='web_video_server',
            executable='web_video_server',
            name='web_video_server',
            parameters=[
                {'port': 8080},
                {'quality': 50},
                {'frame_rate': 12}
            ],
            output='screen'
        ),
    ])
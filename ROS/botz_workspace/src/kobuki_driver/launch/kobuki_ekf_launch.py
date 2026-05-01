import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    kobuki_pkg_dir = get_package_share_directory('kobuki_driver')
    ekf_launch_file = os.path.join(kobuki_pkg_dir, 'launch', 'ekf_launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/ttyUSB0',
            description='Serial port for Kobuki',
        ),
        DeclareLaunchArgument(
            'cmd_timeout',
            default_value='0.5',
            description='Command timeout in seconds',
        ),
        
        # Kobuki driver node
        Node(
            package='kobuki_driver',
            executable='kobuki_node',
            name='kobuki_node',
            output='screen',
            parameters=[
                {'port': LaunchConfiguration('port')},
                {'cmd_timeout': LaunchConfiguration('cmd_timeout')},
                {'cmd_rate': 10},
                {'odom_pub_rate': 10},
            ],
        ),
        
        # Include EKF launch file
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_launch_file),
        ),
    ])

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    kobuki_pkg_dir = get_package_share_directory('kobuki_driver')
    lidar_pkg_dir = get_package_share_directory('lidar_driver')
    
    kobuki_ekf_launch = os.path.join(kobuki_pkg_dir, 'launch', 'kobuki_ekf_launch.py')
    lidar_launch = os.path.join(lidar_pkg_dir, 'launch', 'lidar_launch.py')
    slam_launch = os.path.join(kobuki_pkg_dir, 'launch', 'slam_launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'kobuki_port',
            default_value='/dev/kobuki',
            description='Serial port for Kobuki',
        ),
        DeclareLaunchArgument(
            'lidar_port',
            default_value='/dev/lidar',
            description='Serial port for LiDAR',
        ),
        
        # Kobuki driver + EKF fusion
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(kobuki_ekf_launch),
            launch_arguments=[('port', LaunchConfiguration('kobuki_port'))],
        ),
        
        # LiDAR driver
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments=[('serial_port', LaunchConfiguration('lidar_port'))],
        ),
        
        # SLAM Toolbox
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch),
        ),
        
        # Static transform: laser frame relative to base_link
        # Laser mounted 0.1m forward (X) and 0.05m above (Z) the robot center
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '0.1',      # x offset (meters forward)
                '0.0',      # y offset (meters left/right)
                '0.05',     # z offset (meters above)
                '0.0',      # roll
                '0.0',      # pitch
                '0.0',      # yaw
                'base_link',  # parent frame
                'laser'       # child frame
            ],
            name='laser_tf_publisher',
        ),
    ])

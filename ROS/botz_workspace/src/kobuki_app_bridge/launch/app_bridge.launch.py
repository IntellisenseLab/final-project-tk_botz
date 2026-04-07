from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description():
    pkg_share = FindPackageShare("kobuki_app_bridge")
    rosbridge_launch = PathJoinSubstitution(
        [FindPackageShare("rosbridge_server"), "launch", "rosbridge_websocket_launch.xml"]
    )
    params_file = PathJoinSubstitution([pkg_share, "config", "bridge_params.yaml"])

    return LaunchDescription(
        [
            IncludeLaunchDescription(
                XMLLaunchDescriptionSource(rosbridge_launch),
                launch_arguments={"port": "9090"}.items(),
            ),
            Node(
                package="kobuki_app_bridge",
                executable="websocket_bridge",
                name="websocket_bridge",
                output="screen",
                parameters=[params_file, {"launch_internal_rosbridge": False}],
            ),
            Node(
                package="kobuki_app_bridge",
                executable="map_server_bridge",
                name="map_server_bridge",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="kobuki_app_bridge",
                executable="rest_api_node",
                name="rest_api_node",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="kobuki_app_bridge",
                executable="command_router",
                name="command_router",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="kobuki_app_bridge",
                executable="state_broadcaster",
                name="state_broadcaster",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="kobuki_app_bridge",
                executable="goal_manager",
                name="goal_manager",
                output="screen",
                parameters=[params_file],
            ),
        ]
    )
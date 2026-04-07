from setuptools import setup

package_name = "kobuki_app_bridge"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/app_bridge.launch.py"]),
        (f"share/{package_name}/config", ["config/bridge_params.yaml"]),
    ],
    install_requires=[
        "setuptools",
        "flask",
        "numpy",
        "Pillow",
    ],
    zip_safe=True,
    maintainer="nidharshan",
    maintainer_email="vigneshnidhar@gmail.com",
    description="ROS2 app bridge for Kobuki robot",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "websocket_bridge = kobuki_app_bridge.websocket_bridge:main",
            "rest_api_node = kobuki_app_bridge.rest_api_node:main",
            "command_router = kobuki_app_bridge.command_router:main",
            "state_broadcaster = kobuki_app_bridge.state_broadcaster:main",
            "goal_manager = kobuki_app_bridge.goal_manager:main",
            "map_server_bridge = kobuki_app_bridge.map_server_bridge:main",
        ],
    },
)

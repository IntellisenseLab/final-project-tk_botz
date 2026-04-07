from setuptools import setup

package_name = "kobuki_app_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/kobuki_app_bridge.launch.py"]),
    ],
    install_requires=["setuptools", "aiohttp", "numpy", "Pillow"],
    zip_safe=True,
    maintainer="your_name",
    maintainer_email="you@example.com",
    description="App bridge for Kobuki on ROS2",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "bridge_node = kobuki_app_bridge.bridge_node:main",
            "map_http_node = kobuki_app_bridge.map_http_node:main",
        ],
    },
)

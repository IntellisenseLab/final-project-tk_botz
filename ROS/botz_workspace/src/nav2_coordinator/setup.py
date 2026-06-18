from setuptools import setup

package_name = 'nav2_coordinator'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='Thin ROS 2 service wrapper around Nav2 NavigateToPose action.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'nav2_coordinator_node = nav2_coordinator.nav2_coordinator_node:main',
        ],
    },
)
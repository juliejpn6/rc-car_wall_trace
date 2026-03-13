from setuptools import setup
import os
from glob import glob

package_name = 'picamera2_node'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yoshi',
    maintainer_email='yoshi@todo.todo',
    description='Launch wrapper for camera_ros with Pi Camera V3 Wide (IMX708)',
    license='MIT',
    entry_points={
        'console_scripts': [],
    },
)

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('width', default_value='640',
                              description='Image width in pixels'),
        DeclareLaunchArgument('height', default_value='480',
                              description='Image height in pixels'),
        DeclareLaunchArgument('format', default_value='RGB888',
                              description='Pixel format'),

        Node(
            package='camera_ros',
            executable='camera_node',
            name='camera',
            output='screen',
            parameters=[{
                'width': LaunchConfiguration('width'),
                'height': LaunchConfiguration('height'),
                'format': LaunchConfiguration('format'),
            }],
        ),
    ])

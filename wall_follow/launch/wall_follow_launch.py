from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('wall_follow'),
        'config',
        'wall_follow.yaml'
    )

    config_la = DeclareLaunchArgument(
        'wall_follow_config',
        default_value=config,
        description='Path to wall follow config file'
    )

    wall_follow_node = Node(
        package='wall_follow',
        executable='wall_follow_node',
        name='wall_follow_node',
        output='screen',
        parameters=[LaunchConfiguration('wall_follow_config')]
    )

    return LaunchDescription([
        config_la,
        wall_follow_node,
    ])

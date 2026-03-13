# =============================================================================
# TT-02 Integrated Bringup Launch File
# =============================================================================
# All nodes for autonomous driving on Tamiya TT-02 chassis:
#
# [Sensing]
#   - sllidar_ros2        : RPLidar A1-M8 LiDAR -> /scan
#   - encoder_odometry    : Optical encoder -> /odom + TF(odom -> base_link)
#   - camera_ros          : Pi Camera V3 Wide -> /camera/image_raw
#
# [Control]
#   - pigpio_pwm_driver   : /drive -> Steering & throttle PWM
#   - ackermann_mux       : /drive topic multiplexer (nav / teleop priority)
#
# [Planning]
#   - wall_follow         : /scan -> PID wall following -> /drive
#                           (starts DISABLED, enable via service call)
#
# [TF]
#   - static TF           : base_link -> laser, base_link -> camera_link
#
# Usage:
#   ros2 launch f1tenth_stack bringup_tt02_launch.py
#
# Start driving:
#   ros2 service call /wall_follow_node/enable std_srvs/srv/SetBool "{data: true}"
#
# Stop driving:
#   ros2 service call /wall_follow_node/enable std_srvs/srv/SetBool "{data: false}"
# =============================================================================

import math
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # =========================================================================
    # Config file paths
    # =========================================================================
    mux_config = os.path.join(
        get_package_share_directory('f1tenth_stack'),
        'config',
        'mux.yaml'
    )
    wall_follow_config = os.path.join(
        get_package_share_directory('wall_follow'),
        'config',
        'wall_follow.yaml'
    )

    # =========================================================================
    # Launch arguments
    # =========================================================================
    mux_la = DeclareLaunchArgument(
        'mux_config',
        default_value=mux_config,
        description='Path to ackermann mux config'
    )
    wall_follow_la = DeclareLaunchArgument(
        'wall_follow_config',
        default_value=wall_follow_config,
        description='Path to wall follow config'
    )

    # LiDAR arguments
    lidar_serial_port_la = DeclareLaunchArgument(
        'lidar_serial_port',
        default_value='/dev/ttyUSB0',
        description='LiDAR serial port'
    )
    lidar_frame_id_la = DeclareLaunchArgument(
        'lidar_frame_id',
        default_value='laser',
        description='LiDAR TF frame ID'
    )

    # Camera arguments
    camera_width_la = DeclareLaunchArgument(
        'camera_width',
        default_value='640',
        description='Camera image width'
    )
    camera_height_la = DeclareLaunchArgument(
        'camera_height',
        default_value='480',
        description='Camera image height'
    )

    # =========================================================================
    # Sensing Nodes
    # =========================================================================

    # --- LiDAR (RPLidar A1-M8) ---
    lidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        output='screen',
        parameters=[{
            'channel_type': 'serial',
            'serial_port': LaunchConfiguration('lidar_serial_port'),
            'serial_baudrate': 115200,
            'frame_id': LaunchConfiguration('lidar_frame_id'),
            'inverted': False,
            'angle_compensate': True,
            'scan_mode': 'Sensitivity',
        }]
    )

    # --- Encoder Odometry ---
    encoder_odom_node = Node(
        package='encoder_odometry',
        executable='encoder_odom_node',
        name='encoder_odom_node',
        output='screen',
        parameters=[{
            'encoder_a_pin': 22,
            'encoder_b_pin': 27,
            'pulses_per_rev': 36,
            'wheel_diameter': 0.066,
            'wheelbase': 0.257,
            'publish_rate': 30.0,
            'publish_tf': True,
            'odom_frame': 'odom',
            'base_frame': 'base_link',
        }]
    )

    # --- Camera (Pi Camera V3 Wide via camera_ros) ---
    camera_node = Node(
        package='camera_ros',
        executable='camera_node',
        name='camera',
        output='screen',
        parameters=[{
            'width': LaunchConfiguration('camera_width'),
            'height': LaunchConfiguration('camera_height'),
            'format': 'RGB888',
        }]
    )

    # =========================================================================
    # Control Nodes
    # =========================================================================

    # --- PWM Driver (steering & throttle) ---
    pwm_driver_node = Node(
        package='pigpio_pwm_driver',
        executable='pwm_driver_node',
        name='pwm_driver_node',
        remappings=[('/drive', '/ackermann_cmd')],
        output='screen',
        parameters=[{
            'steer_pin': 13,
            'throttle_pin': 12,
            'pwm_frequency': 70,
            'neutral_duty_steer': 10.00,
            'neutral_duty_throttle': 10.48,
            'max_steering_angle': 0.36,
            'max_speed': 3.0,
            'steer_duty_range': 2.0,
            'throttle_duty_range': 2.0,
            'safety_timeout': 0.5,
        }]
    )

    # --- Ackermann Mux ---
    ackermann_mux_node = Node(
        package='ackermann_mux',
        executable='ackermann_mux',
        name='ackermann_mux',
        output='screen',
        parameters=[LaunchConfiguration('mux_config')],
        remappings=[('ackermann_cmd_out', 'drive')]
    )

    # =========================================================================
    # Planning Nodes
    # =========================================================================

    # --- Wall Follow (starts DISABLED for safety) ---
    wall_follow_node = Node(
        package='wall_follow',
        executable='wall_follow_node',
        name='wall_follow_node',
        output='screen',
        parameters=[LaunchConfiguration('wall_follow_config')]
    )

    # =========================================================================
    # Static TF: base_link -> laser
    # =========================================================================
    # Measured values for TT-02:
    #   x = 0.23m (23cm forward from rear axle)
    #   y = 0.0m  (centered on vehicle)
    #   z = 0.12m (12cm above ground)
    #   No rotation (LiDAR mounted level)
    static_tf_base_to_laser = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_base_to_laser',
        arguments=[
            '--x', '0.23',
            '--y', '0.0',
            '--z', '0.12',
            '--roll', '0.0',
            '--pitch', '0.0',
            '--yaw', '0.0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'laser',
        ]
    )

    # =========================================================================
    # Static TF: base_link -> camera_link
    # =========================================================================
    # Measured values for TT-02:
    #   x = 0.22m  (22cm forward from rear axle)
    #   y = -0.005m (-0.5cm, offset right; ROS convention: left=+Y)
    #   z = 0.19m  (19cm above ground)
    #   pitch = -10 deg (tilted downward)
    camera_pitch_rad = -10.0 * math.pi / 180.0  # -0.1745 rad

    static_tf_base_to_camera = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_base_to_camera',
        arguments=[
            '--x', '0.22',
            '--y', '-0.005',
            '--z', '0.19',
            '--roll', '0.0',
            '--pitch', str(round(camera_pitch_rad, 4)),
            '--yaw', '0.0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'camera_link',
        ]
    )

    # =========================================================================
    # Build LaunchDescription
    # =========================================================================
    ld = LaunchDescription()

    # Launch arguments
    ld.add_action(mux_la)
    ld.add_action(wall_follow_la)
    ld.add_action(lidar_serial_port_la)
    ld.add_action(lidar_frame_id_la)
    ld.add_action(camera_width_la)
    ld.add_action(camera_height_la)

    # Sensing
    ld.add_action(lidar_node)
    ld.add_action(encoder_odom_node)
    ld.add_action(camera_node)

    # Control
    ld.add_action(pwm_driver_node)
    ld.add_action(ackermann_mux_node)

    # Planning
    ld.add_action(wall_follow_node)

    # Static TF
    ld.add_action(static_tf_base_to_laser)
    ld.add_action(static_tf_base_to_camera)

    return ld

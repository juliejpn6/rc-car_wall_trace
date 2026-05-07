import math
import collections
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from ackermann_msgs.msg import AckermannDriveStamped
from std_srvs.srv import SetBool


class WallFollowNode(Node):
    def __init__(self):
        super().__init__('wall_follow_node')

        self.declare_parameter('desired_distance', 0.50)
        self.declare_parameter('kp', 1.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 0.1)
        self.declare_parameter('speed_normal', 0.5)
        self.declare_parameter('speed_slow', 0.4)
        self.declare_parameter('steering_threshold', 0.15)
        self.declare_parameter('left_ray_angle', -90.0)
        self.declare_parameter('right_ray_angle', 90.0)
        self.declare_parameter('max_steering_angle', 0.36)
        self.declare_parameter('drive_topic', '/drive')
        self.declare_parameter('front_stop_distance', 0.25)

        self.desired_distance    = self.get_parameter('desired_distance').value
        self.kp                  = self.get_parameter('kp').value
        self.ki                  = self.get_parameter('ki').value
        self.kd                  = self.get_parameter('kd').value
        self.speed_normal        = self.get_parameter('speed_normal').value
        self.speed_slow          = self.get_parameter('speed_slow').value
        self.steering_threshold  = self.get_parameter('steering_threshold').value
        self.left_ray_angle      = self.get_parameter('left_ray_angle').value
        self.right_ray_angle     = self.get_parameter('right_ray_angle').value
        self.max_steering_angle  = self.get_parameter('max_steering_angle').value
        self.front_stop_distance = self.get_parameter('front_stop_distance').value
        drive_topic              = self.get_parameter('drive_topic').value

        self.enabled      = False
        self.prev_error   = 0.0
        self.integral     = 0.0
        self.prev_time    = None
        self.error_history = collections.deque(maxlen=5)

        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.drive_pub = self.create_publisher(
            AckermannDriveStamped, drive_topic, 10)
        self.enable_srv = self.create_service(
            SetBool, '~/enable', self.enable_callback)

        self.get_logger().info(
            f'Wall Follow ready (center mode): '
            f'front_stop={self.front_stop_distance}m. '
            f'Waiting for enable...'
        )

    def enable_callback(self, request, response):
        self.enabled = request.data
        if self.enabled:
            self.prev_error  = 0.0
            self.integral    = 0.0
            self.prev_time   = None
            self.error_history.clear()
            self.get_logger().info('Wall Follow ENABLED - vehicle will move!')
            response.message = 'Wall follow enabled'
        else:
            self.get_logger().info('Wall Follow DISABLED - sending neutral')
            self._publish_drive(0.0, 0.0)
            response.message = 'Wall follow disabled'
        response.success = True
        return response

    def scan_callback(self, msg: LaserScan):
        if not self.enabled:
            return

        # 前方障害物チェック
        front_dist = self._get_front_distance(msg)
        if front_dist is not None and front_dist < self.front_stop_distance:
            self.get_logger().warn(
                f'FRONT OBSTACLE: {front_dist:.3f}m - STOPPING',
                throttle_duration_sec=0.5)
            self._publish_drive(0.0, 0.0)
            return

        # 左右の壁距離を取得
        left_dist  = self._get_distance_at_angle(msg, self.left_ray_angle)
        right_dist = self._get_distance_at_angle(msg, self.right_ray_angle)

        if left_dist is None and right_dist is None:
            self.get_logger().warn('No walls detected - going straight',
                                   throttle_duration_sec=1.0)
            self._publish_drive(self.speed_normal, 0.0)
            return

        # 片側しか見えない場合は見えている側から誤差を計算
        if left_dist is None:
            # 右壁のみ: 右壁からdesired_distance離れるよう制御
            error = self.desired_distance - right_dist  # 右壁に近い→負→左に切る
            self.get_logger().warn('Left wall not detected - using right wall only',
                                   throttle_duration_sec=1.0)
        elif right_dist is None:
            # 左壁のみ: 左壁からdesired_distance離れるよう制御
            error = left_dist - self.desired_distance  # 左壁に近い→負→右に切る
            self.get_logger().warn('Right wall not detected - using left wall only',
                                   throttle_duration_sec=1.0)
        else:
            # 両壁あり: 中央を走る
            # error > 0 → 左に寄りすぎ → 右に切る(+)
            # error < 0 → 右に寄りすぎ → 左に切る(-)
            error = left_dist - right_dist

        self.error_history.append(error)
        smoothed_error = sum(self.error_history) / len(self.error_history)

        now = self.get_clock().now()
        if self.prev_time is None:
            dt = 0.1
        else:
            dt = (now - self.prev_time).nanoseconds / 1e9
        dt = max(dt, 1e-3)
        self.prev_time = now

        p_term = self.kp * smoothed_error
        self.integral += smoothed_error * dt
        self.integral  = max(-1.0, min(1.0, self.integral))
        i_term = self.ki * self.integral
        d_term = self.kd * (smoothed_error - self.prev_error) / dt
        self.prev_error = smoothed_error

        # +steering=右, -steering=左
        steering_angle = p_term + i_term + d_term
        steering_angle = max(-self.max_steering_angle,
                             min(self.max_steering_angle, steering_angle))

        speed = self.speed_slow if abs(steering_angle) > self.steering_threshold \
                else self.speed_normal

        self._publish_drive(speed, steering_angle)

        left_str  = f'{left_dist:.2f}m'  if left_dist  else 'none'
        right_str = f'{right_dist:.2f}m' if right_dist else 'none'
        front_str = f'{front_dist:.2f}m' if front_dist else 'none'
        self.get_logger().info(
            f'L={left_str} R={right_str} err={error:+.3f} '
            f'steer={math.degrees(steering_angle):+.1f}deg '
            f'speed={speed:.2f} front={front_str}',
            throttle_duration_sec=0.5
        )

    def _get_front_distance(self, msg: LaserScan):
        """物理的前方（ソフト±170°〜±180°）の最小距離"""
        min_dist = None
        for angle_deg in range(165, 181, 2):
            for sign in [1, -1]:
                r = self._get_range_at_angle(msg, math.radians(angle_deg * sign))
                if r is not None:
                    if min_dist is None or r < min_dist:
                        min_dist = r
        return min_dist

    def _get_distance_at_angle(self, msg: LaserScan, angle_deg: float):
        """指定角度付近の距離を取得（±10度の範囲で探索）"""
        for delta in range(0, 11):
            for sign in ([0] if delta == 0 else [delta, -delta]):
                r = self._get_range_at_angle(
                    msg, math.radians(angle_deg + sign))
                if r is not None and r < 3.0:
                    return r
        return None

    def _get_range_at_angle(self, msg: LaserScan, angle_rad: float):
        if angle_rad < msg.angle_min or angle_rad > msg.angle_max:
            return None
        idx = int((angle_rad - msg.angle_min) / msg.angle_increment)
        if not (0 <= idx < len(msg.ranges)):
            return None
        r = msg.ranges[idx]
        if math.isinf(r) or math.isnan(r) or r < msg.range_min or r > msg.range_max:
            return None
        return r

    def _publish_drive(self, speed: float, steering_angle: float):
        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.drive.speed          = float(speed)
        msg.drive.steering_angle = float(steering_angle)
        self.drive_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = WallFollowNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

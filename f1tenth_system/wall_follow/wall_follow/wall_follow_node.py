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

        self.declare_parameter('side', 'right')
        self.declare_parameter('desired_distance', 0.50)
        self.declare_parameter('lookahead_distance', 0.30)
        self.declare_parameter('kp', 1.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 0.1)
        self.declare_parameter('speed_normal', 0.5)
        self.declare_parameter('speed_slow', 0.3)
        self.declare_parameter('steering_threshold', 0.15)
        self.declare_parameter('ray_angle_a', -95.0)
        self.declare_parameter('ray_angle_b', -70.0)
        self.declare_parameter('max_steering_angle', 0.36)
        self.declare_parameter('drive_topic', '/drive')
        self.declare_parameter('front_stop_distance', 0.5)

        self.side                = self.get_parameter('side').value
        self.desired_distance    = self.get_parameter('desired_distance').value
        self.lookahead_distance  = self.get_parameter('lookahead_distance').value
        self.kp                  = self.get_parameter('kp').value
        self.ki                  = self.get_parameter('ki').value
        self.kd                  = self.get_parameter('kd').value
        self.speed_normal        = self.get_parameter('speed_normal').value
        self.speed_slow          = self.get_parameter('speed_slow').value
        self.steering_threshold  = self.get_parameter('steering_threshold').value
        self.ray_angle_a_deg     = self.get_parameter('ray_angle_a').value
        self.ray_angle_b_deg     = self.get_parameter('ray_angle_b').value
        self.max_steering_angle  = self.get_parameter('max_steering_angle').value
        self.front_stop_distance = self.get_parameter('front_stop_distance').value
        drive_topic              = self.get_parameter('drive_topic').value

        self.enabled      = False
        self.prev_error   = 0.0
        self.integral     = 0.0
        self.prev_time    = None
        self.dist_history = collections.deque(maxlen=5)

        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.drive_pub = self.create_publisher(
            AckermannDriveStamped, drive_topic, 10)
        self.enable_srv = self.create_service(
            SetBool, '~/enable', self.enable_callback)

        self.get_logger().info(
            f'Wall Follow ready: side={self.side}, '
            f'desired_dist={self.desired_distance}m, '
            f'front_stop={self.front_stop_distance}m, '
            f'ray_a={self.ray_angle_a_deg}deg, ray_b={self.ray_angle_b_deg}deg. '
            f'Waiting for enable...'
        )

    def enable_callback(self, request, response):
        self.enabled = request.data
        if self.enabled:
            self.prev_error  = 0.0
            self.integral    = 0.0
            self.prev_time   = None
            self.dist_history.clear()
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

        # 前方障害物チェック（LiDAR逆向きのため±160°〜±180°を監視）
        front_dist = self._get_front_distance(msg)
        if front_dist is not None and front_dist < self.front_stop_distance:
            self.get_logger().warn(
                f'FRONT OBSTACLE: {front_dist:.3f}m - STOPPING',
                throttle_duration_sec=0.5)
            self._publish_drive(0.0, 0.0)
            return

        raw_dist = self._get_wall_distance(msg)

        if raw_dist is None:
            self.get_logger().warn(
                'No wall detected - going straight',
                throttle_duration_sec=1.0)
            self._publish_drive(self.speed_normal, 0.0)
            return

        self.dist_history.append(raw_dist)
        distance = sum(self.dist_history) / len(self.dist_history)

        error = self.desired_distance - distance

        now = self.get_clock().now()
        if self.prev_time is None:
            dt = 0.1
        else:
            dt = (now - self.prev_time).nanoseconds / 1e9
        dt = max(dt, 1e-3)
        self.prev_time = now

        p_term = self.kp * error
        self.integral += error * dt
        self.integral  = max(-1.0, min(1.0, self.integral))
        i_term = self.ki * self.integral
        d_term = self.kd * (error - self.prev_error) / dt
        self.prev_error = error

        steering_angle = p_term + i_term + d_term

        if self.side == 'right':
            steering_angle = -steering_angle

        steering_angle = max(-self.max_steering_angle,
                             min(self.max_steering_angle, steering_angle))

        speed = self.speed_slow if abs(steering_angle) > self.steering_threshold \
                else self.speed_normal

        self._publish_drive(speed, steering_angle)

        front_str = f'{front_dist:.2f}m' if front_dist else 'none'
        self.get_logger().info(
            f'raw={raw_dist:.3f}m avg={distance:.3f}m err={error:+.3f} '
            f'steer={math.degrees(steering_angle):+.1f}deg speed={speed:.2f} '
            f'front={front_str}',
            throttle_duration_sec=0.5
        )

    def _get_front_distance(self, msg: LaserScan):
        min_dist = None
        for angle_deg in range(170, 181, 2):
            for sign in [1, -1]:
                r = self._get_range_at_angle(msg, math.radians(angle_deg * sign))
                if r is not None:
                    if min_dist is None or r < min_dist:
                        min_dist = r
        return min_dist

    def _get_wall_distance(self, msg: LaserScan):
        """
        two-ray法:
          ray_a = 真横レイ（-95°）
          ray_b = 斜め前レイ（-70°）← 進行方向側（0°方向）

        数式の正しい役割:
          dist_a（数式）= 斜めレイ = ray_b（-70°）
          dist_b（数式）= 真横レイ = ray_a（-95°）
        """
        SEARCH_DEG = 10
        MAX_DIST = self.desired_distance * 3.0

        # ray_a = 真横（-95°付近）
        result_near = self._find_valid_range(
            msg, self.ray_angle_a_deg, SEARCH_DEG, MAX_DIST)
        # ray_b = 斜め前（-70°付近）
        result_far = self._find_valid_range(
            msg, self.ray_angle_b_deg, SEARCH_DEG, MAX_DIST)

        if result_near is None or result_far is None:
            return None

        dist_near, angle_near_deg = result_near  # 真横レイ
        dist_far,  angle_far_deg  = result_far   # 斜めレイ

        angle_near_rad = math.radians(angle_near_deg)
        angle_far_rad  = math.radians(angle_far_deg)

        theta = abs(angle_near_rad - angle_far_rad)
        if theta < math.radians(5):
            return None

        # two-ray法: dist_a=斜めレイ, dist_b=真横レイ の順で渡す
        dist_a = dist_far   # 斜めレイ（-70°）
        dist_b = dist_near  # 真横レイ（-95°）

        denom = dist_a * math.sin(theta)
        if abs(denom) < 1e-6:
            return None

        alpha = math.atan2(dist_a * math.cos(theta) - dist_b, denom)
        d_current   = dist_b * math.cos(alpha)
        d_projected = d_current + self.lookahead_distance * math.sin(alpha)

        if d_projected <= 0.0 or d_projected > MAX_DIST:
            return None

        return d_projected

    def _find_valid_range(self, msg: LaserScan, center_deg: float,
                          search_deg: int, max_dist: float):
        for delta in range(0, search_deg + 1):
            for sign in ([0] if delta == 0 else [delta, -delta]):
                angle_deg = center_deg + sign
                r = self._get_range_at_angle(msg, math.radians(angle_deg))
                if r is not None and r <= max_dist:
                    return (r, angle_deg)
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

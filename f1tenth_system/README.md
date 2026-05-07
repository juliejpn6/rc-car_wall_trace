# RC Car 自律走行プロジェクト

Tamiya TT-02シャーシをベースにした自律走行RCカーのROS2パッケージ群です。

---

## ハードウェア構成

| パーツ | 型番 |
|--------|------|
| シャーシ | Tamiya TT-02 |
| SBC | Raspberry Pi 4B (4GB) |
| LiDAR | RPLidar A1M8-R6 |
| エンコーダ | 光学式タイヤエンコーダ 36ppr (左後輪) |
| モーター制御 | pigpio ハードウェアPWM |

### PWMピン配置

| 機能 | GPIOピン |
|------|---------|
| ステアリング | GPIO 13 |
| スロットル | GPIO 12 |

### LiDAR座標系（重要）

RPLidar A1M8-R6は**物理的に180°反転して搭載**されています。

| ソフトウェア角度 | 車両の物理方向 |
|----------------|--------------|
| 0° | 車両後方 |
| ±180° | 車両前方 |
| -90° | 車両左側 |
| +90° | 車両右側 |

この補正のため、`bringup_tt02_launch.py`のTF設定では `yaw=3.14159` を設定しています。

---

## ソフトウェア構成

- **OS**: Raspbian Trixie 64-bit
- **ROS2**: Humble（Dockerコンテナ内で動作）
- **Dockerイメージ**: `ros2_humble`

### パッケージ一覧

| パッケージ | 役割 |
|-----------|------|
| `ackermann_mux` | /driveトピックの優先度付き多重化 |
| `encoder_odometry` | エンコーダによるオドメトリ計算 |
| `f1tenth_stack` | メインlaunchファイル・アルゴリズム群 |
| `pigpio_pwm_driver` | ステアリング・スロットルPWM制御 |
| `sllidar_ros2` | RPLidar A1ドライバ |
| `wall_follow` | PID壁追従アルゴリズム |

---

## セットアップ手順

### 1. リポジトリのクローン

🖥️ **ホスト（RPi）** にて：

\`\`\`bash
mkdir -p ~/f1tenth_ws/src
cd ~/f1tenth_ws/src
git clone https://github.com/juliejpn6/rc-car_wall_trace.git f1tenth_system
\`\`\`

### 2. Dockerコンテナの起動

🖥️ **ホスト（RPi）** にて：

\`\`\`bash
cd ~/f1tenth_ws/src/f1tenth_system/scripts
bash run_container.sh
\`\`\`

### 3. ビルド

🐳 **Docker内** にて：

\`\`\`bash
cd /root/f1tenth_ws
colcon build --packages-skip vesc_ackermann vesc_driver vesc_msgs vesc
source install/setup.bash
\`\`\`

### 4. pigpiodの起動確認

🖥️ **ホスト（RPi）** にて：

\`\`\`bash
sudo systemctl start pigpiod
sudo systemctl status pigpiod
\`\`\`

---

## 走行手順

### 壁追従（Wall Follow）

🐳 **Docker内** にて：

\`\`\`bash
# 全ノード起動
ros2 launch f1tenth_stack bringup_tt02_launch.py

# 別ターミナルで走行開始
ros2 service call /wall_follow_node/enable std_srvs/srv/SetBool "{data: true}"

# 停止
ros2 service call /wall_follow_node/enable std_srvs/srv/SetBool "{data: false}"
\`\`\`

---

## パラメータ調整

### 壁追従パラメータ

\`wall_follow/config/wall_follow.yaml\` を編集：

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| \`ray_angle_a\` | 壁検出レイA [deg] | 50.0 |
| \`ray_angle_b\` | 壁検出レイB [deg] | 90.0 |
| \`desired_distance\` | 壁からの目標距離 [m] | 0.8 |

### PWMパラメータ

\`f1tenth_stack/launch/bringup_tt02_launch.py\` 内の \`pwm_driver_node\` を編集：

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| \`neutral_duty_steer\` | ステアリングセンター [%] | 10.00 |
| \`neutral_duty_throttle\` | スロットルニュートラル [%] | 10.48 |
| \`steer_duty_range\` | 最大舵角時のデューティ変化量 [%] | 2.0 |

> ⚠️ PWM安全範囲: 7.5%〜13.0%。この範囲を超えないよう注意してください。

---

## ブランチ構成

| ブランチ | 内容 |
|---------|------|
| \`main\` | 動作確認済みの安定版（壁追従） |
| \`feature/camera\` | カメラノード実装用（開発中） |
| \`feature/follow-the-gap\` | Follow-the-Gapアルゴリズム実装用 |

---

## トピック構成

\`\`\`
/scan          ← sllidar_node が配信
    ↓
/wall_follow_node
    ↓
/drive         ← AckermannDriveStamped
    ↓
/ackermann_mux
    ↓
/ackermann_cmd
    ↓
/pwm_driver_node → GPIO PWM出力
\`\`\`

#!/usr/bin/env bash
# =============================================================================
# start_drive.sh - 自律走行システム起動スクリプト（Docker内で実行）
# =============================================================================
# 使い方（Docker内で）: bash /root/f1tenth_ws/src/f1tenth_system/scripts/start_drive.sh
#
# 走行開始: bash scripts/start_drive.sh --enable
# 走行停止: bash scripts/start_drive.sh --disable
# =============================================================================

WORKSPACE="/root/f1tenth_ws"

if [ ! -f /.dockerenv ]; then
    echo "[ERROR] このスクリプトはDockerコンテナ内で実行してください"
    exit 1
fi

if [ "$1" == "--enable" ]; then
    echo "[INFO] 壁追従を開始します..."
    ros2 service call /wall_follow_node/enable std_srvs/srv/SetBool "{data: true}"
    exit 0
fi

if [ "$1" == "--disable" ]; then
    echo "[INFO] 壁追従を停止します..."
    ros2 service call /wall_follow_node/enable std_srvs/srv/SetBool "{data: false}"
    exit 0
fi

source /opt/ros/humble/setup.bash
source "$WORKSPACE/install/setup.bash"

echo "[INFO] ホスト側でpigpiodが起動していることを確認してください"
echo "       sudo systemctl start pigpiod"
echo ""
echo "[INFO] 全ノードを起動します..."
echo "       走行開始: bash scripts/start_drive.sh --enable"
echo "       走行停止: bash scripts/start_drive.sh --disable"
echo ""

ros2 launch f1tenth_stack bringup_tt02_launch.py

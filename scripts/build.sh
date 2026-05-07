#!/usr/bin/env bash
# =============================================================================
# build.sh - ワークスペースのビルドスクリプト（Docker内で実行）
# =============================================================================
# 使い方（Docker内で）: bash /root/f1tenth_ws/src/f1tenth_system/scripts/build.sh
# =============================================================================

WORKSPACE="/root/f1tenth_ws"

if [ ! -f /.dockerenv ]; then
    echo "[ERROR] このスクリプトはDockerコンテナ内で実行してください"
    exit 1
fi

echo "[INFO] ビルドを開始します..."
cd "$WORKSPACE"

source /opt/ros/humble/setup.bash

colcon build \
    --packages-skip vesc_ackermann vesc_driver vesc_msgs vesc \
    --symlink-install

if [ $? -ne 0 ]; then
    echo "[ERROR] ビルドに失敗しました"
    exit 1
fi

echo ""
echo "[INFO] ビルド完了！次のコマンドで環境を有効化してください："
echo "       source /root/f1tenth_ws/install/setup.bash"

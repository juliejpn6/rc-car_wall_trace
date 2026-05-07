#!/usr/bin/env bash
# =============================================================================
# run_container.sh - 初回起動用スクリプト
# =============================================================================
# 使い方: bash scripts/run_container.sh
# =============================================================================

CONTAINER_NAME="ros2_humble"
IMAGE_NAME="ros2_humble"
WORKSPACE="$HOME/f1tenth_ws"

mkdir -p "$WORKSPACE"

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[INFO] 既存のコンテナ '${CONTAINER_NAME}' を削除します..."
    docker rm -f "$CONTAINER_NAME"
fi

echo "[INFO] コンテナを起動します: ${CONTAINER_NAME}"

docker run -it \
    --name "$CONTAINER_NAME" \
    --privileged \
    --network host \
    -v "$WORKSPACE":/root/f1tenth_ws \
    -v /dev:/dev \
    "$IMAGE_NAME" \
    bash

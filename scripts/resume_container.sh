#!/usr/bin/env bash
# =============================================================================
# resume_container.sh - 既存コンテナへの再接続スクリプト
# =============================================================================
# 使い方: bash scripts/resume_container.sh
# =============================================================================

CONTAINER_NAME="ros2_humble"

if ! sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[ERROR] コンテナ '${CONTAINER_NAME}' が見つかりません"
    echo "        先に run_container.sh を実行してください"
    exit 1
fi

if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[INFO] コンテナを起動します..."
    sudo docker start "$CONTAINER_NAME"
fi

echo "[INFO] コンテナに接続します: ${CONTAINER_NAME}"
sudo docker exec -it "$CONTAINER_NAME" bash

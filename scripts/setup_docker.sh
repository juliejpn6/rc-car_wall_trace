#!/usr/bin/env bash
# =============================================================================
# setup_docker.sh - Dockerイメージセットアップスクリプト
# =============================================================================
# 初回のみ実行してください。Dockerfileを生成してイメージをビルドします。
#
# 使い方: bash scripts/setup_docker.sh
# =============================================================================

IMAGE_NAME="ros2_humble"
DOCKERFILE_DIR="$HOME/ros2_docker"

# すでにイメージが存在する場合はスキップ
if docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "[INFO] イメージ '${IMAGE_NAME}' はすでに存在します"
    echo "       再ビルドする場合は以下を実行してください："
    echo "       docker rmi ${IMAGE_NAME}"
    exit 0
fi

echo "[INFO] Dockerfileを作成します..."
mkdir -p "$DOCKERFILE_DIR"

cat << 'DOCKERFILE' > "$DOCKERFILE_DIR/Dockerfile"
FROM arm64v8/ros:humble
SHELL ["/bin/bash", "-c"]

RUN apt-get update --fix-missing && \
    apt-get install -y \
        git nano vim \
        python3-pip \
        python3-colcon-common-extensions \
        python3-rosdep \
        tmux && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y \
        ros-humble-rmw-cyclonedds-cpp \
        ros-humble-demo-nodes-cpp \
        ros-humble-demo-nodes-py \
        ros-humble-tf-transformations \
        ros-humble-camera-ros \
        ros-humble-ackermann-msgs \
        ros-humble-diagnostic-updater \
        python3-transforms3d && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install opencv-python-headless pigpio

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

WORKDIR /root/f1tenth_ws
DOCKERFILE

echo "[INFO] Dockerイメージをビルドします: ${IMAGE_NAME}"
echo "       ※ 初回は10〜20分かかります..."
echo ""

docker build -t "$IMAGE_NAME" "$DOCKERFILE_DIR"

if [ $? -ne 0 ]; then
    echo "[ERROR] イメージのビルドに失敗しました"
    exit 1
fi

echo ""
echo "[INFO] ビルド完了！次のコマンドでコンテナを起動してください："
echo "       bash scripts/run_container.sh"

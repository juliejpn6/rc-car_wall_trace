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

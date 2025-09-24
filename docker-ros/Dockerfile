FROM ros:noetic

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install basic ROS tools and user management utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ros-noetic-desktop-full \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    git \
    nano \
    build-essential \
    sudo \
    passwd && \
    rm -rf /var/lib/apt/lists/*

# Create a new user 'ros' and add to sudoers
RUN useradd -m -s /bin/bash ros && \
    usermod -aG sudo ros && \
    echo "ros:ros" | chpasswd && \
    echo "ros ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to the ros user
USER ros
WORKDIR /home/ros

# Set up ROS environment for the ros user
SHELL ["/bin/bash", "-c"]
RUN echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc

CMD ["bash"]
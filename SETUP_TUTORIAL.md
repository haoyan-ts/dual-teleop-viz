# Dual Teleop Visualization Setup Tutorial

This tutorial will guide you through setting up the dual teleop visualization project using Docker and ROS Noetic.

## Prerequisites

Before you begin, make sure you have the following installed on your system:

- **Docker**: For containerized ROS environment
- **Docker Compose**: For managing multi-container applications
- **Git**: For version control (if cloning the repository)
- **X11 Server** (for GUI applications):
  - **Windows**: Install [VcXsrv](https://sourceforge.net/projects/vcxsrv/) or [Xming](https://sourceforge.net/projects/xming/)
  - **macOS**: Install [XQuartz](https://www.xquartz.org/)
  - **Linux**: X11 is usually pre-installed

## GUI Setup (Windows/macOS)

### For Windows Users:

1. **Install VcXsrv (recommended) or Xming**
2. **Start VcXsrv with these settings:**
   - Display number: 0
   - Start no client: ✓
   - Clipboard: ✓ 
   - Primary Selection: ✓
   - Native opengl: ✓
   - **Disable access control: ✓** (Important!)

3. **Configure Windows Firewall:**
   - Allow VcXsrv through Windows Defender Firewall
   - Allow both private and public networks

### For macOS Users:

1. **Install and start XQuartz**
2. **Enable network connections:**
   ```bash
   xhost +localhost
   ```

### For Linux Users:

Allow Docker to connect to X11:
```bash
xhost +local:docker
```

## Project Structure

This project contains:
- `docker-ros/`: Docker configuration files
- `assets/`: Robot models and configurations (dual, dual_v2, dual_v3)
- `src/`: Source code files
- `log/`: Output logs

## Step-by-Step Setup

### Step 1: Start the Docker Container

1. Navigate to the docker-ros directory:
   ```bash
   cd docker-ros
   ```

2. Build and start the ROS container:
   ```bash
   docker-compose up -d
   ```

3. Access the container:
   ```bash
   docker exec -it dual-teleop-viz-ros bash
   ```

### Step 2: Set Up ROS Workspace

Once inside the container, you'll be logged in as the `ros` user. Follow these steps:

1. **Create ROS workspace structure:**
   ```bash
   mkdir -p ros_ws/src
   ```

2. **Update system packages:**
   ```bash
   sudo apt update
   ```

3. **Install additional tools (if needed):**
   ```bash
   sudo apt install zip
   ```

### Step 3: Copy Robot Assets

Copy the robot model assets to your workspace:

```bash
cp -r /assets/* ros_ws/src/
```

Verify the assets were copied:
```bash
ls ros_ws/src/
```
You should see directories like `dual`, `dual_v2`, and `dual_v3`.

### Step 4: Build the Workspace

1. **Navigate to the workspace:**
   ```bash
   cd ros_ws/
   ```

2. **Build the catkin workspace:**
   ```bash
   catkin_make
   ```

   **Note:** You may see warnings about package naming conventions. This is normal and doesn't affect functionality.

### Step 5: Source the Workspace

After building, you need to source the workspace to make the packages available:

```bash
source ~/ros_ws/devel/setup.bash
```

**Important:** Add this to your `.bashrc` to automatically source it in new terminals:
```bash
echo "source ~/ros_ws/devel/setup.bash" >> ~/.bashrc
```

### Step 6: Generate URDF Files

Now you can generate URDF files from the XACRO files:

1. **For dual_v3 (recommended):**
   ```bash
   xacro src/dual_v3/urdf/20250918_test.xacro > model.urdf
   ```

2. **For dual_v2 (if needed):**
   ```bash
   xacro src/dual_v2/urdf/20250914_test.xacro > model.urdf
   ```

## Troubleshooting

### Common Issues and Solutions

1. **"resource not found" error when running xacro:**
   - **Problem:** Package not found in ROS path
   - **Solution:** Make sure you've run `catkin_make` and sourced the workspace:
     ```bash
     cd ~/ros_ws
     catkin_make
     source devel/setup.bash
     ```

2. **UTF-8 codec error:**
   - **Problem:** Binary files in URDF directory
   - **Solution:** Use dual_v3 instead of dual_v2, or check for binary mesh files

3. **Package naming warnings:**
   - **Problem:** Package names don't follow ROS conventions
   - **Solution:** This is a warning only and doesn't prevent functionality

### Verification Steps

To verify your setup is working correctly:

1. **Check if packages are available:**
   ```bash
   rospack list | grep test_description
   ```

2. **Validate URDF file:**
   ```bash
   check_urdf model.urdf
   ```

3. **View the model in RViz:**
   ```bash
   roslaunch dual_v3 display.launch
   ```

4. **Test GUI with a simple application:**
   ```bash
   # Install and test xeyes (simple GUI test)
   sudo apt install x11-apps
   xeyes
   ```

## GUI Troubleshooting

### Common GUI Issues and Solutions

1. **"cannot connect to X server" error:**
   - **Windows**: Ensure VcXsrv is running and "Disable access control" is checked
   - **macOS**: Run `xhost +localhost` and restart XQuartz
   - **Linux**: Run `xhost +local:docker`

2. **Black window or no display:**
   - Check if your X11 server is running
   - Verify firewall settings allow connections
   - Try restarting the container: `docker-compose restart`

3. **Performance issues with GUI:**
   - The `QT_X11_NO_MITSHM=1` environment variable is set to improve compatibility
   - Consider using hardware acceleration if available

## Next Steps

After completing the setup:

1. **Explore the launch files** in `src/dual_v3/launch/` for different visualization options
2. **Modify robot parameters** in the URDF/XACRO files as needed
3. **Use Gazebo simulation** with the provided launch files
4. **Integrate with your teleop control system**

## Container Management

- **Start container:** `docker-compose up -d`
- **Stop container:** `docker-compose down`
- **Access running container:** `docker exec -it dual-teleop-viz-ros bash`
- **View container logs:** `docker-compose logs`

## File Locations

- **Host assets:** `../assets/` (mounted as `/assets` in container)
- **Container workspace:** `/home/ros/ros_ws/`
- **Generated URDF:** `/home/ros/ros_ws/model.urdf`
- **Package sources:** `/home/ros/ros_ws/src/`

---

**Note:** This setup uses ROS Noetic running on Ubuntu 20.04 (Focal) in a Docker container. The assets are mounted from the host system, allowing you to edit them outside the container while building and running inside the containerized ROS environment.

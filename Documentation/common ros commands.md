# Setup Workspace
mkdir -p ~/[workspace]/src

cd ~/[workspace]/

catkin init

catkin build

source devel/setup.bash


# Create Package
cd ~/[workspace]/src

catkin create pkg [name] --catkin-deps [depend1] [depend 2]

cd ~/[workspace]

catkin build

# Programs
## PlotJuggler
rosrun plotjuggler plotjuggler
## RViz
rosrun rviz rviz
## Other executables
rosrun fuming_feathers [file]

[command] [package name] [executable]

### Make a file executable
chmod +x ~/[workspace]/src/fuming_feathers/src/[filename]

## rosbag
rosbag record -O [title].bag /topic1 /topic2 --duration=5

rosbag info [title].bag

rostopic list -b [title].bag

rosbag play [title].bag


# Topics
## List all available topics

rostopic list
## Get info about a specific topic

rostopic info /topic_name

## See message type of a topic

rostopic type /topic_name

## Echo (print) messages from a topic

rostopic echo /topic_name

### See rate/frequency of messages

rostopic hz /topic_name

### See bandwidth usage of a topic

rostopic bw /topic_name

# Nodes
## List all nodes

rosnode list
## Get info about a specific node

rosnode info /node_name

# Parameters
## List all parameters
rosparam list


# test enemy_detector
chmod +x ~/ros/src/fuming_feathers/enemy_detector.py

roscore
rosrun fuming_feathers enemy_detector.py

rosnode list [find enemy_detector node to see if running]:#
rosnode info /enemy_detector
rostopic list | grep realsense

rostopic hz /realsense/color/image_raw
rostopic hz /realsense/depth/points
rqt_image_view

rqt_console
rostopic echo /fuming_feathers/score



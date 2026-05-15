#!/usr/bin/env python3

# slingshot_node.py
# ---------------------------------------
# ROS node:
# - Subscribes to Falcon input (Twist)
# - Converts to slingshot trajectory
# - Visualizes trajectory in RViz
# ---------------------------------------

import rospy
from geometry_msgs.msg import TwistStamped, Point, Pose
from visualization_msgs.msg import Marker
from moveit_commander import MoveGroupCommander
from slingshot_sim import simulate_slingshot
from franka_msgs.msg import ErrorRecoveryActionGoal #for error reset
from moveit_msgs.msg import DisplayTrajectory
from std_msgs.msg import Bool

class SlingshotNode:
    def __init__(self):
        rospy.init_node("slingshot_node")

        # --- Subscribe to Falcon output ---
        self.sub = rospy.Subscriber(
            "/fuming_feathers/velocity_cmd",
            TwistStamped,
            self.callback
        )
        
        self.sub = rospy.Subscriber(
            "/fuming_feathers/detector_flag",
            Bool,
            self.reset_everything
        )
        
        # --- Publisher for RViz visualization ---
        self.marker_pub = rospy.Publisher(
            "/slingshot_trajectory",
            Marker,
            queue_size=1
        )

        #publisher for error reset
        self.error_pub =rospy.Publisher('/franka_control/error_recovery/goal', ErrorRecoveryActionGoal, queue_size=1)

        # Falcon scaling factor (must match falcon_input.py)
        self.scale = 2.0

        rospy.loginfo("Slingshot node ready (RViz mouide)")

    # ---------------------------------------
    # Convert trajectory → RViz Marker
    # ---------------------------------------
    def publish_trajectory_marker(self, points):
        marker = Marker()

        marker.header.frame_id = "table_top"  # IMPORTANT frame
        marker.header.stamp = rospy.Time.now()

        marker.ns = "slingshot"
        marker.id = 0
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.pose.orientation.w= 1.0

        # Line thickness
        marker.scale.x = 0.01

        # Color (green)
        marker.color.r = 0.0
        marker.color.g = 1.0
        marker.color.b = 0.0
        marker.color.a = 1.0

        # Convert points
        for p in points:
            pt = Point()
            pt.x = p[0]
            pt.y = p[1]
            pt.z = p[2]
            marker.points.append(pt)

        self.marker_pub.publish(marker)


    def reset_everything(self, msg):
        
        #reset errors
        if msg.data == True:
            error = ErrorRecoveryActionGoal()
            self.error_pub.publish(error)

            #go up
            group= MoveGroupCommander("arm")
            p_2 = group.get_current_pose()
            p_2.pose.position.z+=0.2
            
            group.set_pose_target(p_2)
            group.go(wait=True)
            group.clear_pose_targets

            #go back to start
            group1= MoveGroupCommander("arm")
            p_3 = group.get_current_pose()
            

            group1.set_named_target("fuming_feathers_start")
            group1.go(wait=True)
            group1.clear_pose_targets
    

    # ---------------------------------------
    # Callback when Falcon publishes data
    # ---------------------------------------
    def callback(self, msg):
        # --- Step 1: Extract vector ---
        x = msg.twist.linear.x / self.scale
        y = msg.twist.linear.y / self.scale
        z = msg.twist.linear.z / self.scale

        rospy.loginfo(f"Pull vector: {x:.3f}, {y:.3f}, {z:.3f}")

        # --- Step 2: Reverse direction (release) ---
        x, y, z = y, x, -z

        # --- Step 3: Simulate trajectory ---
        points, times, speed = simulate_slingshot(x, y, z)

        rospy.loginfo(f"Launch speed: {speed:.2f} m/s")

        # --- Step 4: Scale trajectory for safety ---
        points = points * 1

        # --- Step 5: Publish to RViz ---
        self.publish_trajectory_marker(points)

        # robot traj
        poses= []
        for p in points:
            pt = Pose()
            pt.position.x, pt.position.y, pt.position.z = p[0], p[1], p[2]
            pt.orientation.x = -0.7082269342272834
            pt.orientation.y = -0.7058263855613506
            pt.orientation.z = -0.014673126208097463
            pt.orientation.w = 0.002902145362304433
            poses.append(pt)
        mgc= MoveGroupCommander("arm")
        traj, fraction = mgc.compute_cartesian_path(poses, 0.1)
        traj = mgc.retime_trajectory(mgc.get_current_state(), traj, 1.0, 1.0, "time_optimal_trajectory_generation")
        rospy.loginfo(f"robot could follow through {fraction*100:.2}% of the throwing path")
        trajectory_pub = rospy.Publisher('slingshot_robot_trajectory', DisplayTrajectory, queue_size= 1, latch= True)
        trajectory_pub.publish(DisplayTrajectory(trajectory = [traj]))
        mgc.execute(traj)

        


if __name__ == "__main__":
    SlingshotNode()
    rospy.spin()

#!/usr/bin/env python3

# slingshot_node.py
# ---------------------------------------
# ROS node:
# - Subscribes to Falcon input (Twist)
# - Converts to slingshot trajectory
# - Visualizes trajectory in RViz
# ---------------------------------------

import rospy
from geometry_msgs.msg import TwistStamped, Point
from visualization_msgs.msg import Marker

from slingshot_sim import simulate_slingshot


class SlingshotNode:
    def __init__(self):
        rospy.init_node("slingshot_node")

        # --- Subscribe to Falcon output ---
        self.sub = rospy.Subscriber(
            "/fuming_feathers/velocity_cmd",
            TwistStamped,
            self.callback
        )

        # --- Publisher for RViz visualization ---
        self.marker_pub = rospy.Publisher(
            "/slingshot_trajectory",
            Marker,
            queue_size=1
        )

        # Falcon scaling factor (must match falcon_input.py)
        self.scale = 2.0

        rospy.loginfo("Slingshot node ready (RViz mode)")

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


if __name__ == "__main__":
    SlingshotNode()
    rospy.spin()

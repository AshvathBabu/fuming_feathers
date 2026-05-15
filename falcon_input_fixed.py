#!/usr/bin/env python3
import rospy
import threading
import numpy as np
from geometry_msgs.msg import PoseStamped, WrenchStamped, Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

class falcon:
    def __init__(self):
        self.lock = threading.Lock()

        self.servo_cf_msg = WrenchStamped()
        self.servo_cf_msg.header.xd_id = 'falcon_grip'

        # Publishers
        self.pub = rospy.Publisher('falcon/servo_cf', WrenchStamped, queue_size=1)
        self.velocity_pub = rospy.Publisher('/fuming_feathers/velocity_cmd', Twist, queue_size=1)
        self.button_state_pub = rospy.Publisher('/falcon/centre_button_state', Bool, queue_size=1) 

        # Subscribers
        self.position_sub = rospy.Subscriber('falcon/measured_cp', PoseStamped, self.get_position)
        self.joy_sub = rospy.Subscriber('falcon/joy', Joy, self.joy_callback)

        # Initial variables
        self.gain = rospy.get_param('~gain', 100.0)
        self.setpoint_cp = None
        self.position = None

        # Falcon state
        self.button_pressed = False
        self.pulling = False
        self.pull_start_pos = None  
        self.pull_end_pos = None 

    def main(self):
        r = rospy.Rate(500)

        while not rospy.is_shutdown() and self.position is None:
            r.sleep()

        while not rospy.is_shutdown():
            self.servo_cf()
            if self.detect_release():
                vector = self.calculate_pull_vector()
                if vector is not None:
                    self.publish_panda_command(vector)
            r.sleep()

    def servo_cf(self):
        with self.lock:
            setpoint = self.setpoint_cp
            position = self.position

        if setpoint is None or position is None:
            self.pub.publish(self.servo_cf_msg)
            return

        force = self.gain * (setpoint - position)
        self.servo_cf_msg.wrench.force.x = force[0]
        self.servo_cf_msg.wrench.force.y = force[1]
        self.servo_cf_msg.wrench.force.z = force[2]
        self.pub.publish(self.servo_cf_msg)

    def joy_callback(self, msg):
        if len(msg.buttons) < 3:
            rospy.logerr("Unexpected button count: %d", len(msg.buttons))
            return

        with self.lock:
            if self.position is None:
                return

            CENTER_BUTTON = 2
            current_button_state = (msg.buttons[CENTER_BUTTON] == 1)

            # Detect press edge and save start position
            if current_button_state and not self.button_pressed:
                self.pull_start_pos = self.position.copy()
                self.pulling = True
                rospy.loginfo("Center button pressed, pull started")

            self.button_pressed = current_button_state

        self.button_state_pub.publish(Bool(data=current_button_state))

    def get_position(self, msg):
        p = msg.pose.position
        with self.lock:
            self.position = np.array([p.x, p.y, p.z])
            if self.setpoint_cp is None:
                self.setpoint_cp = self.position.copy()

    def detect_release(self):
        with self.lock:
            if not self.button_pressed and self.pulling and self.pull_start_pos is not None:
                self.pulling = False
                self.pull_end_pos = self.position.copy()
                rospy.loginfo("Button released, stopped pulling")
                return True
        return False

    def calculate_pull_vector(self):
        with self.lock:
            if self.pull_start_pos is None or self.pull_end_pos is None:
                rospy.logwarn("Pull positions not set, skipping vector calculation")
                return None

            x = self.pull_end_pos[0] - self.pull_start_pos[0]
            y = self.pull_end_pos[1] - self.pull_start_pos[1]
            z = self.pull_end_pos[2] - self.pull_start_pos[2]

        rospy.loginfo("X = %f \n Y = %f \n Z = %f", x, y, z)
        return (x, y, z)

    def publish_panda_command(self, vector):
        twist = Twist()
        scale = 2.0

        twist.linear.x = vector[0] * scale
        twist.linear.y = vector[1] * scale
        twist.linear.z = vector[2] * scale

        self.velocity_pub.publish(twist)
        rospy.loginfo("Published velocity to Panda")

if __name__ == '__main__':
    rospy.init_node('falcon_input')
    falcon().main()
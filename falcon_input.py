#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import PoseStamped, WrenchStamped, Twist
from sensor_msgs.msg import Joy
import numpy as np

class falcon:
#sets up publishers, subscribers, init variables
    def __init__(self): 
        self.servo_cf_msg = WrenchStamped()
        self.servo_cf_msg.header.frame_id = 'falcon_grip'

        #publisher
        self.pub = rospy.Publisher('falcon/servo_cf', WrenchStamped, queue_size=1)
            #for panda Twist messages
        self.velocity_pub = rospy.Publisher('/fuming_feathers/velocity_cmd', Twist, queue_size=1)
        #subscribers
        self.position_sub = rospy.Subscriber('falcon/measured_cp', PoseStamped, self.get_position)
        self.joy_sub = rospy.Subscriber('falcon/joy', Joy, self.joy_callback)
        #initial variables
        self.gain = rospy.get_param('~gain', 100.0)
        self.setpoint_cp = None
        self.position = None

        #added, falcon state
        self.button_pressed = False
        self.pull_start_position = None
        self.pulling = False

#main loop
    def main(self): 
        r= rospy.Rate(20)

        while not rospy.is_shutdown() and self.position is None: #sleep mode
            r.sleep()
        while not rospy.is_shutdown(): #running
            #give haptic feedback
            self.servo_cf()
            r.sleep()
            #check for button release and give the info to panda
            if self.detect_release():
                vector = self.calculate_pull_vector()
                self.publish_panda_command(vector)

#user haptic feedback by falcon
    def servo_cf(self): #
        if self.setpoint_cp is None:
            # publish zero force if no setpoint is defined
            self.pub.publish(self.servo_cf_msg)
            return #exit

        #force = gain × (set pos - current pos)
        force = self.gain * (self.setpoint_cp - self.position)
        self.servo_cf_msg.wrench.force.x = force[0] 
        self.servo_cf_msg.wrench.force.y = force[1]
        self.servo_cf_msg.wrench.force.z = force[2]
        self.pub.publish(self.servo_cf_msg)

#messages by joystick
    def joy_callback(self, msg):
        #checks buttons, throws error if not 4
        assert len(msg.buttons) == 4, "Expected standard 4 grip buttons"
        #exit if no position data
        if self.position is None:
            return
        
        #added, press detection for center
        CENTER_BUTTON = 2 # let center be index 2
        current_button_state = (msg.buttons[CENTER_BUTTON] == 1)
        
        #checks press in the moment, and save position from initial press
        if current_button_state == True and self.button_pressed == False:
            self.pull_start_pos = self.position.copy()
            self.pulling = True #currently pulling
            rospy.loginfo("Center button pressed, pull started")

            # Update button state for next time
        self.button_pressed = current_button_state

#get current position
    def get_position(self, msg): 
        p = msg.pose.position #gets position data
        self.position = np.array([p.x, p.y, p.z]) #store info in array
        # set initial setpoint from first measurement if unset
        if self.setpoint_cp is None:
            self.setpoint_cp = self.position[:]

#added, detect end of pull, when button is released
    def detect_release(self):
        if self.button_pressed == False and self.pulling == True:
            self.pulling = False
            rospy.loginfo("Button released, stopped pulling")
            self.pull_end_pos = self.position.copy()
            return True
        return False
            

#added, use current position compared to final pose
    def calculate_pull_vector(self):
        #arrays, with force values x,y,z in indices 0,1,2 
        start = self.pull_start_pos
        end = self.pull_end_pos

        x = end[0] - start[0]
        y = end[1] - start[1]
        z = end[2] - start[2]

        rospy.loginfo("X = %f \n Y = %f \n Z = %f", x,y,z)

        return (x, y, z)

#added, give vector to panda, panda file will check limits
    def publish_panda_command(self, vector):
        twist = Twist()
        scale = 2.0 #multiply with distance to get vel, so this is 0.2 m/s for 10cm

        #set twist linear velocity fields x,y,z
        twist.linear.x = vector[0] * scale
        twist.linear.y = vector[1] * scale
        twist.linear.z = vector[2] * scale
        
        self.velocity_pub.publish(twist)
        rospy.loginfo("Published velocity to Panda")

if __name__ == '__main__': #run code when file is executed
    rospy.init_node('falcon_input')
    falcon().main()

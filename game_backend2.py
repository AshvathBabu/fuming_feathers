#!/usr/bin/env python3

import rospy
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
from enum import Enum

class GameState(Enum):
    IDLE = 0
    PULLING = 1
    RELEASED = 2
    FIRING = 3
    RESET = 4

class GameBackend:
    def __init__(self):
        self.state = GameState.IDLE

        # Publishers
        self.ui_pub = rospy.Publisher("/game/ui_state", String, queue_size=1)
        self.fire_pub = rospy.Publisher("/game/fire_vector", Twist, queue_size=1)

        # Subscribers
        rospy.Subscriber("/falcon/button_state", Bool, self.button_callback)
        rospy.Subscriber("/falcon/pull_vector", Twist, self.pull_callback)

        self.button_down = False
        self.pull_vector = None

    def button_callback(self, msg):
        self.button_down = msg.data

    def pull_callback(self, msg):
        self.pull_vector = msg

    def run(self):
        rate = rospy.Rate(20)

        while not rospy.is_shutdown():

            if self.state == GameState.IDLE:
                self.ui_pub.publish("press_button")
                if self.button_down:
                    self.state = GameState.PULLING

            elif self.state == GameState.PULLING:
                self.ui_pub.publish("pulling")
                if not self.button_down:
                    self.state = GameState.RELEASED

            elif self.state == GameState.RELEASED:
                self.ui_pub.publish("release_detected")
                self.state = GameState.FIRING

            elif self.state == GameState.FIRING:
                if self.pull_vector is not None:
                    self.fire_pub.publish(self.pull_vector)
                self.ui_pub.publish("firing")
                self.state = GameState.RESET

            elif self.state == GameState.RESET:
                self.ui_pub.publish("reset")
                self.state = GameState.IDLE

            rate.sleep()

if __name__ == "__main__":
    rospy.init_node("game_backend")
    GameBackend().run()
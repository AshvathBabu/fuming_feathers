#!/usr/bin/env python3

import rospy
from std_msgs.msg import String, Bool, Int32
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
        rospy.Subscriber("/fuming_feathers/score", Int32, self.score_callback)

        # Internal state
        self.button_down = False
        self.pull_vector = None
        self.current_score = 0

        # Cooldown
        self.cooldown_time = 2.0
        self.last_fire_time = None

        # Force scaling
        self.MAX_PULL = 0.10

    
    def button_callback(self, msg):
        self.button_down = msg.data

    def pull_callback(self, msg):
        self.pull_vector = msg

    def score_callback(self, msg):
        self.current_score = msg.data
        self.ui_pub.publish(f"score:{self.current_score}")

   
    def cooldown_active(self):
        if self.last_fire_time is None:
            return False
        return (rospy.get_time() - self.last_fire_time) < self.cooldown_time

   
   
    def compute_magnitude(self, vector):
        return (vector.x**2 + vector.y**2 + vector.z**2) ** 0.5

    def normalized_force(self, magnitude):
        return min(magnitude / self.MAX_PULL, 1.0)

    def force_level(self, norm_force):
        if norm_force < 0.33:
            return "low"
        elif norm_force < 0.66:
            return "medium"
        else:
            return "high"

    def publish_force_feedback(self, vector):
        mag = self.compute_magnitude(vector)
        norm = self.normalized_force(mag)
        level = self.force_level(norm)

        self.ui_pub.publish(f"force_level:{level}")
        self.ui_pub.publish(f"normalized_force:{norm}")

   #main loop
    def run(self):
        rate = rospy.Rate(20)

        while not rospy.is_shutdown():

            if self.state == GameState.IDLE:
                self.ui_pub.publish("idle")
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
                    self.publish_force_feedback(self.pull_vector)

                self.last_fire_time = rospy.get_time()
                self.ui_pub.publish("firing")
                self.state = GameState.RESET

            elif self.state == GameState.RESET:
                if self.cooldown_active():
                    self.ui_pub.publish("cooldown")
                else:
                    self.ui_pub.publish("reset")
                    self.state = GameState.IDLE

            rate.sleep()


if __name__ == "__main__":
    rospy.init_node("game_backend")
    GameBackend().run()

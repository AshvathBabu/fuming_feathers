#!/usr/bin/env python3

import rospy
import numpy as np
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
from enum import Enum

#set up game states 
class GameState(Enum):
    IDLE = 0
    READY = 1
    PULLING = 2
    RELEASED = 3
    FIRING = 4
    RESET = 5


class GameBackend:
    #sets up publishers, subscribers, init variables
    def __init__(self):
        self.state = GameState.IDLE

        #publishers
        self.ui_pub = rospy.Publisher("/game/ui_state", String, queue_size=1)
        self.fire_pub = rospy.Publisher("/game/fire_vector", Twist, queue_size=1)

        #subscribers
        rospy.Subscriber("/falcon/button_state", Bool, self.button_callback)
        rospy.Subscriber("/falcon/pull_vector", Twist, self.pull_callback)

        #falcon data
        self.button_down = False
        self.pull_vector = None

        #cooldown system
        self.cooldown_time = 2.0  # seconds
        self.last_fire_time = None

        #force scaling
        self.MAX_PULL = 0.10  # meters (10 cm max pull)

        #callbacks
    def button_callback(self, msg):
        self.button_down = msg.data

    def pull_callback(self, msg):
        self.pull_vector = msg

    #checkes if still cooling down or done
    def cooldown_active(self):
        if self.last_fire_time is None:
            return False
        return (rospy.get_time() - self.last_fire_time) < self.cooldown_time

    #force mag using 
    def compute_magnitude(self, vector):
        return np.sqrt(vector.x**2 + vector.y**2 + vector.z**2)
        

    def normalized_force(self, magnitude):
        return min(magnitude / self.MAX_PULL, 1.0)

    def force_level(self, norm_force):
        if norm_force < 0.33:
            return "low"      # thin arrow
        elif norm_force < 0.66:
            return "medium"   # medium arrow
        else:
            return "high"     # thick arrow

    #scoring system PLACEHOLDER
    def compute_score(self, hit_data):
        """
        Placeholder scoring function
        'hit_data' will come from Nicci
        Expected fields:
            - hit: bool
            - block_color: str
            - impact_force: float
        """
        if not hit_data["hit"]:
            return 0

        color_scores = {
            "red": 50,
            "blue": 30,
            "green": 20,
            "yellow": 10
        }

        base = color_scores.get(hit_data["block_color"], 0)
        bonus = hit_data["impact_force"] * 5  # placeholder

        return int(base + bonus)

    
    #Publish force feedback
   
    def publish_force_feedback(self, vector):
        mag = self.compute_magnitude(vector)
        norm = self.normalized_force(mag)
        level = self.force_level(norm)

        
        self.ui_pub.publish(f"force_level:{level}")
        self.ui_pub.publish(f"normalized_force:{norm}")


    def run(self):
        rate = rospy.Rate(20)

        while not rospy.is_shutdown():

            #idle
            if self.state == GameState.IDLE:
                self.ui_pub.publish("idle")
                if self.button_down:
                    self.state = GameState.READY

          #ready
            elif self.state == GameState.READY:
                self.ui_pub.publish("ready")
                if self.button_down:
                    self.state = GameState.PULLING

           
            #pupling
            elif self.state == GameState.PULLING:
                self.ui_pub.publish("pulling")
                if not self.button_down:
                    self.state = GameState.RELEASED

            #released
            elif self.state == GameState.RELEASED:
                self.ui_pub.publish("release_detected")
                self.state = GameState.FIRING

            #firing
            elif self.state == GameState.FIRING:
                if self.pull_vector is not None:
                    # Send fire vector to Panda
                    self.fire_pub.publish(self.pull_vector)

                    # Send force feedback to GUI
                    self.publish_force_feedback(self.pull_vector)

                self.last_fire_time = rospy.get_time()
                self.ui_pub.publish("firing")
                self.state = GameState.RESET

            #reset state asnd cooldown
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
#!/usr/bin/env python3
import pygame
import rospy
import smach
import threading
import os
from std_msgs.msg import Bool, Int32
from enum import Enum

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True
BASE_DIR = os.path.dirname(__file__)

class GameState(Enum):
    IDLE = 0
    PULLING = 1
    RESET = 2
    SCORE = 3
    LOADING = 4

STATE_TO_INSTRUCTION = {
    GameState.IDLE: "idle",
    GameState.PULLING: "pulling",
    GameState.RESET: "cooldown",
    GameState.SCORE: "score",
    GameState.LOADING: "loading",
}

INSTRUCTIONS = {
    "idle": {
        "heading": "Welcome to Fuming Feathers!",
        "instruction": "Press and hold the center button on the Joystick in front of you to start playing",
        "sub": "Player Tip: Keep holding the center button!",
    },
    "pulling": {
        "heading": "All aboard the slingbot",
        "instruction": "Pull the joystick backwards to stretch the slingbot",
        "sub": "Player Tip: The further you pull, the further the bird will fly!",
    },
    "cooldown": {
        "heading": "Resetting Stage",
        "instruction": "Press the center button when you are ready for the next round",
        "sub": "",
    },
    "loading": {
        "heading": "ENCORE! FIRE IN THE HOLE",
        "instruction": "Well done! Lets try that again, Press the center button and pull to shoot the bird",
        "sub": "Did you know? This game is still in beta testing, try aiming the slingbot towards the right to get the best hit",
    },
    "score": {
        "heading": "Justice Served!",
        "instruction": "Your final score:",
        "sub": "Press center button on the falcon to return to the main menu.",
    },
}

WAIT_CASE = {
    "heading": "",
    "instruction": "Installing Bird feathers...wait this isn't right",
    "sub": "",
}

MAX_ROUNDS = 3

class GameData:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_state = GameState.IDLE
        self.current_score = 0
        self.total_score = 0
        self.round_scores = []
        self.game_started = False
        self.round_count = 0
        self.last_fire_time = 0
        self.button_down = False

        # Publishers
        self.detectorflag = rospy.Publisher('/fuming_feathers/detector_flag', Bool, queue_size=1)
        #Subscriber
        rospy.Subscriber("/fuming_feathers/score", Int32, self.score_callback)
        rospy.Subscriber("/falcon/centre_button_state", Bool, self.button_callback)
        rospy.loginfo("[GameData] Subscribed to /falcon/centre_button_state")

    def button_callback(self, msg):
        with self.lock:
            self.button_down = msg.data

    def score_callback(self, msg):
        with self.lock:
            self.current_score = msg.data


class Idle(smach.State):
    def __init__(self, data):
        smach.State.__init__(self, outcomes=["button_pressed"])
        self.data = data
# Executes at Idle state when user presses the center button on the falcon
    def execute(self, data):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.IDLE
        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            if pressed:
                if not self.data.game_started:
                    self.data.detectorflag.publish(Bool(data=True))
                    self.data.game_started = True #Boolean flag to start the game (init state is false)
                return "button_pressed"
            rate.sleep()

#When the button is no longer pressed, the state machine determines that the button was released 
class Pulling(smach.State):
    def __init__(self, data):
        smach.State.__init__(self, outcomes=["button_released"])
        self.data = data

    def execute(self, data):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.PULLING
        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            if not pressed:
                return "button_released"
            rate.sleep()

class Loading(smach.State):
    def __init__(self, data):
        smach.State.__init__(self, outcomes=["button_pressed"])
        self.data = data
# Executes at Idle state when user presses the center button on the falcon
    def execute(self, data):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.LOADING

        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            if pressed:
                self.data.detectorflag.publish(Bool(data=True))
                return "button_pressed"
            rate.sleep()

class Reset(smach.State):
    def __init__(self, data):
        smach.State.__init__(self, outcomes=["next_round", "game_over"])
        self.data = data

    def execute(self, data):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.RESET
            round_score = self.data.current_score
            self.data.round_scores.append(round_score)
            self.data.total_score += round_score
            self.data.current_score = 0
        self.data.detectorflag.publish(Bool(data=False)) #IF SOMETHING SCREWS UP REMOVE
        # Wait for button press before advancing
        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            
            if pressed:
                with self.data.lock:
                    self.data.round_count += 1
                    rounds_done = self.data.round_count
                
                if rounds_done >= MAX_ROUNDS:
                    return "game_over"
                else:
                    self.data.detectorflag.publish(Bool(data=True))
                    return "next_round"
            rate.sleep()


class Score(smach.State):
    def __init__(self, data):
        smach.State.__init__(self, outcomes=["play_again"])
        self.data = data

    def execute(self, data):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.SCORE

        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            if pressed:
                with self.data.lock:
                    self.data.round_count = 0
                    self.data.game_started = False
                    self.data.current_score = 0
                    self.data.total_score = 0
                    self.data.round_scores = []
                #self.data.detectorflag.publish(Bool(data=False))
                return "play_again"
            rate.sleep()


if __name__ == "__main__":
    # rospy.init_node MUST come before GameData() so subscribers register correctly
    rospy.init_node("GameEngine", disable_signals=True)
    data = GameData()

    def ros_spin():
        rospy.spin()

    ros_thread = threading.Thread(target=ros_spin, daemon=True)
    ros_thread.start()

    sm = smach.StateMachine(outcomes=["shutdown"])
    with sm:
        smach.StateMachine.add("IDLE",Idle(data),transitions={"button_pressed":  "PULLING"})
        smach.StateMachine.add("LOADING",Loading(data),transitions={"button_pressed":"PULLING"})
        smach.StateMachine.add("PULLING",Pulling(data),transitions={"button_released": "RESET"})
        smach.StateMachine.add("RESET", Reset(data),transitions={"next_round": "LOADING", "game_over": "SCORE"})
        smach.StateMachine.add("SCORE", Score(data),transitions={"play_again":"IDLE"})

    threading.Thread(target=sm.execute, daemon=True).start()

    bg_image = pygame.transform.scale(
        pygame.image.load(os.path.join(BASE_DIR, "Images", "ff_bg.jpg")),
        (1280, 720)
    )
    font = {
        "heading":     pygame.font.SysFont(None, 64),
        "instruction": pygame.font.SysFont(None, 50),
        "sub":         pygame.font.SysFont(None, 26),
        "score":       pygame.font.SysFont(None, 120),
        "round_score": pygame.font.SysFont(None, 38),
        "round_label": pygame.font.SysFont(None, 32),
    }

    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.blit(bg_image, (0, 0))

        with data.lock:
            state       = data.current_state
            score       = data.current_score
            total_score = data.total_score
            round_count = data.round_count
            round_scores = list(data.round_scores)

        key     = STATE_TO_INSTRUCTION.get(state, "idle")
        content = INSTRUCTIONS.get(key, WAIT_CASE)

        heading_surf = font["heading"].render(content["heading"], True, (7, 57, 60))
        instr_surf   = font["instruction"].render(content["instruction"], True, (0, 0, 0))
        sub_surf     = font["sub"].render(content["sub"], True, (44, 102, 110))

        screen.blit(heading_surf, (640 - heading_surf.get_width() // 2, 200))
        screen.blit(instr_surf,   (640 - instr_surf.get_width()   // 2, 320))
        screen.blit(sub_surf,     (640 - sub_surf.get_width()     // 2, 420))

        if state not in (GameState.IDLE, GameState.SCORE):
            label = font["round_label"].render(
                f"Round {min(round_count + 1, MAX_ROUNDS)} / {MAX_ROUNDS}",
                True, (7, 57, 60)
            )
            screen.blit(label, (1280 - label.get_width() - 20, 20))

        if state not in (GameState.IDLE, GameState.SCORE):
            live_label = font["round_label"].render(
                f"Score: {score}", True, (7, 57, 60)
            )
            screen.blit(live_label, (20, 20))

        if state == GameState.SCORE:
            score_surf = font["score"].render(str(total_score), True, (255, 215, 0))
            screen.blit(score_surf, (640 - score_surf.get_width() // 2, 460))

            for i, rs in enumerate(round_scores):
                breakdown = font["round_score"].render(
                    f"Round {i + 1}:  {rs} pts", True, (200, 200, 200)
                )
                screen.blit(breakdown, (640 - breakdown.get_width() // 2, 590 + i * 38))

        pygame.display.flip()

pygame.quit()
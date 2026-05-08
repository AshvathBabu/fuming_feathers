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

#We created a class with user defined constants for each gamestate
class GameState(Enum):
    IDLE = 0
    PULLING = 1
    RELEASED = 2
    FIRING = 3
    RESET = 4
    SCORE = 5

#Helps us link the enums defined to the instruction instructions key
STATE_TO_INSTRUCTION = {
    GameState.IDLE:"idle",
    GameState.PULLING:"pulling",
    GameState.RELEASED:"firing",
    GameState.FIRING:"firing",
    GameState.RESET:"cooldown",
    GameState.SCORE:"score",
}

#These will be the instructions that will be output
INSTRUCTIONS = {
    "idle": {
        "heading": "Welcome to Fuming Feathers!",
        "instruction": "Press the center button on the Joystick in front of you to start playing",
        "sub": "",
    },
    "string_held": {
        "heading": "Preparing the Fuming Birds, They're hungry for destruction",
        "instruction": "Press and hold the center button on the joystick when you are ready to pull",
        "sub": "",
    },
    "pulling": {
        "heading": "All aboard the slingbot",
        "instruction": "Pull the joystick backwards to stretch the slingbot",
        "sub": "Player Tip: The further you pull, the harder the bird will fly!",
    },
    "aiming": {
        "heading": "Find your target",
        "instruction": "Move the joystick left or right to aim at the evil blocks",
        "sub": "Player Tip: Try to line up your shot before you release.",
    },
    "firing": {
        "heading": "Avenge your fore-feather-fathers",
        "instruction": "Release the button to launch the bird.",
        "sub": "",
    },
    "cooldown": {
        "heading": "That'll show em!",
        "instruction": "Reloading and Irritating the next bird...",
        "sub": "Get ready to pull again.",
    },
    "score": {
        "heading": "Justice Served!",
        "instruction": "Your final score:", #Please render the score below this 
        "sub": "Press the centre button to play again.",
    },
    "reset": {
        "heading": "Resetting...",
        "instruction": "The game is resetting... Stand by",
        "sub": "",
    },
}
#The default state of the game in case there is nothing working
WAIT_CASE = {
    "heading": "",
    "instruction": "Installing Bird feathers...wait this isn't right",
    "sub": "",
}

#Set max round constants
MAX_ROUNDS = 3

class GameData:
    def __init__(self):
        self.lock = threading.Lock()
        #Gamestate inits
        self.current_state = GameState.IDLE
        self.current_score = 0
        self.game_started = False
        self.round_count = 0 #Must be incremented to 3 later during reset
        self.last_fire_time = 0
        self.cooldown_time = 2.0
        #Initial button state
        self.button_down = False

        #Publishers
        #Start enemy detector (true) and reset the enemy dectector (false)
        self.detectorflag = rospy.Publisher('/fuming_feathers/detectorflag', Bool, queue_size=1)

        # Subscribers
        rospy.Subscriber("/fuming_feathers/score", Int32, self.score_callback)
        rospy.Subscriber("/falcon/centre_button_state", Bool, self.button_callback)

    def button_callback(self, msg):
        with self.lock:
            self.button_down = msg.data

    def score_callback(self, msg):
        with self.lock:
            self.current_score = msg.data

    def cooldown_active(self):
        return (rospy.get_time() - self.last_fire_time) < self.cooldown_time

class Idle(smach.State):
    def __init__(self,data):
        #You can only really have a button press as an outcome of this smach state
        smach.State.__init__(self, outcomes=["button_pressed"])
        self.data = data

    def execute(self,userdata):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.IDLE
        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            #flag true for the enemy detector to start counting
            if pressed:
                if not self.data.game_started:
                    self.data.detectorflag.publish(Bool(data=True))
                    self.data.game_started = True
                return "button_pressed"
            #Switches to PULLING state
            rate.sleep()


class Pulling(smach.State):
    def __init__(self,data):
        smach.State.__init__(self, outcomes=["button_released"])
        self.data = data

    def execute(self,userdata):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.PULLING
        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            if not pressed:
                #Switches to RELEASED state
                return "button_released"
            rate.sleep()


class Released(smach.State):
    def __init__(self,data):
        smach.State.__init__(self, outcomes=["immediate"])
        self.data = data

    def execute(self,userdata):
        with self.data.lock:
            self.data.current_state = GameState.RELEASED
        return "immediate" #this is an immediate switch to the FIRING stage


class Firing(smach.State):
    def __init__(self,data):
        smach.State.__init__(self, outcomes=["fired"])
        self.data = data

    def execute(self,userdata):
        with self.data.lock:
            self.data.current_state =GameState.FIRING
            self.data.last_fire_time =rospy.get_time()
        return "fired" #transitions to reset status


class Reset(smach.State):
    def __init__(self,data):
        #Here we have 2 outcomes when either the game state resets to the beginning or goes to the game over screen
        smach.State.__init__(self, outcomes=["next_round", "game_over"])
        self.data = data

    def execute(self,userdata):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state =GameState.RESET

        #Here the cooldown will occur for the arm to return to its initial state
        while not rospy.is_shutdown():
            if not self.data.cooldown_active():
                with self.data.lock:
                    self.data.round_count += 1
                    rounds_done = self.data.round_count

                if rounds_done >= MAX_ROUNDS:
                    #If done with 3 rounds we end the game and give a string to switch to score screen 
                    return "game_over" 
                else:
                    #elif we go to the next round
                    self.data.detectorflag.publish(Bool(data=False))
                    return "next_round" #switches to the idle state 
            rate.sleep()


class Score(smach.State):
    def __init__(self,data):
        smach.State.__init__(self, outcomes=["play_again"])
        self.data = data

    def execute(self,userdata):
        rate = rospy.Rate(20)
        with self.data.lock:
            self.data.current_state = GameState.SCORE

        #Button to restart is shown which provides a fresh restart
        while not rospy.is_shutdown():
            with self.data.lock:
                pressed = self.data.button_down
            if pressed:
                with self.data.lock:
                    self.data.round_count = 0
                    self.data.game_started = False
                    self.data.current_score = 0
                self.data.detectorflag.publish(Bool(data=False))#send a flag to enemy dectector to reset 
                return "play_again" #switches to idle
            rate.sleep()


if __name__ == "__main__":
    rospy.init_node("GameEngine", disable_signals=True)
    data = GameData()
    #sets up the state machine for the 
    sm = smach.StateMachine(outcomes=["shutdown"])
    with sm:
        smach.StateMachine.add("IDLE",Idle(data),transitions={"button_pressed":"PULLING"})
        smach.StateMachine.add("PULLING",Pulling(data),transitions={"button_released":"RELEASED"})
        smach.StateMachine.add("RELEASED", Released(data),transitions={"immediate":"FIRING"})
        smach.StateMachine.add("FIRING",Firing(data),transitions={"fired":"RESET"})
        smach.StateMachine.add("RESET",Reset(data),transitions={"next_round":"IDLE", "game_over":"SCORE"})
        smach.StateMachine.add("SCORE",Score(data),transitions={"play_again":"IDLE"})

    threading.Thread(target=sm.execute, daemon=True).start()

    bg_image = pygame.transform.scale(
        pygame.image.load(os.path.join(BASE_DIR, "Images", "ff_bg.jpg")),
        (1280, 720)
    )
    font = {
        "heading":pygame.font.SysFont(None, 64),
        "instruction":pygame.font.SysFont(None, 50),
        "sub":pygame.font.SysFont(None, 26),
        "score":pygame.font.SysFont(None, 120),
    }

    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.blit(bg_image, (0, 0))

        with data.lock:
            state = data.current_state
            score = data.current_score

        key = STATE_TO_INSTRUCTION.get(state, "idle")
        content = INSTRUCTIONS.get(key, WAIT_CASE)

        heading_surf = font["heading"].render(content["heading"], True, (255, 255, 255))
        instr_surf = font["instruction"].render(content["instruction"], True, (255, 255, 255))
        sub_surf = font["sub"].render(content["sub"], True, (200, 200, 200))
        screen.blit(heading_surf, (640 - heading_surf.get_width() // 2, 200))
        screen.blit(instr_surf, (640 - instr_surf.get_width() // 2, 320))
        screen.blit(sub_surf, (640 - sub_surf.get_width() // 2, 420))

        if state == GameState.SCORE:
            score_surf = font["score"].render(str(score), True, (255, 215, 0))
            screen.blit(score_surf, (640 - score_surf.get_width() // 2, 500))

        pygame.display.flip()

pygame.quit()
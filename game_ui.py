#!/usr/bin/env python3
import pygame
import rospy
import threading
import os
from std_msgs.msg import String
from geometry_msgs.msg import Twist, PoseStamped

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True
BASE_DIR = os.path.dirname(__file__)
#Dictionary for the button state calls
INSTRUCTIONS = {
    "idle":{
        "heading": "Welcome to Fuming Feathers!",
        "instruction": "Press the centre button on the Joystick infront of you",
        "sub": "",
    },
    "ready":{
        "heading": "Loading the Fuming Birds, They're hungry for destruction",
        "instruction": "Press the centre button on the joystick when you are ready to pull",
        "sub": "",
    },
    "pulling": {
        "heading": "All aboard the slingbot",
        "instruction": "Pull the joystick backwards to stretch the slingbot",
        "sub": "Player Tip: The further you pull, the harder the bird will fly!",
    },
    "aiming": {
        "heading": "Find your target",
        "instruction": "Move the joystick left or right to aim at the evil cats",
        "sub": "Player Tip: Try to line up your shot before you release.",
    },
    "firing": {
        "heading": "Avenge your fore-feather-fathers",
        "instruction": "Release the joystick to launch the bird.",
        "sub": "",
    },
    "cooldown": {
        "heading": "That'll show em!",
        "instruction": "Reloading and Irritating the next bird...",
        "sub": "Get ready to pull again.",
    },
    "result": {
        "heading": "Justice Served!",
        "instruction": "Check your score on screen.",
        "sub": "Press the centre button to play another round.",
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

class GameFrontend:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = "idle" 
        #Subscribes to the ui state
        self.ui_sub = rospy.Subscriber("/game/ui_state", String,self.on_ui_state)
  
    def on_ui_state(self,msg):
        with self.lock:
            self.state = msg.data

if __name__ == "__main__":
    rospy.init_node("game_frontend", disable_signals=True)
    frontend = GameFrontend()
    threading.Thread(target=rospy.spin, daemon=True).start()

    #load bg image and elements (loading once only,blit every instance)

    bg_image =  pygame.transform.scale(pygame.image.load(os.path.join(BASE_DIR, "Images", "ff_bg.jpg")),
                                       (1280,720))
    font = {
        "heading": pygame.font.SysFont(None, 64),
        "instruction": pygame.font.SysFont(None, 50),
        "sub": pygame.font.SysFont(None, 26),
    } 
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        with frontend.lock:
            current_state = frontend.state
        step = INSTRUCTIONS.get(current_state, WAIT_CASE)
        screen.blit(bg_image, (0, 0)) #This is like loading frames and acts like a renderer 
    
        if step["heading"]:
            pygame.draw.rect(screen, (245, 208, 197), (90, 205, 700, 80))
            render_heading = font["heading"].render(step["heading"], True, (255, 200, 50))
            screen.blit(render_heading, (100, 220))

        render_instruc = font["instruction"].render(step["instruction"], True, (255, 255, 255))
        screen.blit(render_instruc, (100, 330))

        if step["sub"]:
            render_sub = font["sub"].render(step["sub"], True, (200, 200, 200))
            screen.blit(render_sub, (100, 410))
        
        pygame.display.flip() #ensure the images are updated to the monitor

    pygame.quit()
    rospy.signal_shutdown("window closed")
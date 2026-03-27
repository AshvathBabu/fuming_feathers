#!/usr/bin/env python3
import pygame
import rospy
import threading
import os
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True
BASE_DIR = os.path.dirname(__file__)
#set a defined start position for the bird
start_pos_x = 640
start_pos_y = 580 
pull_scale = 300

class GameFrontend:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = "idle" #If this code screws up, you know where 
        self.pull_x = 0.0
        self.pull_y = 0.0
        self.bird_x = start_pos_x
        self.bird_y = start_pos_y
        self.vel_x  = 0.0
        self.vel_y  = 0.0
        self.in_flight = False

        self.pull_sub = rospy.Subscriber("/falcon/pull_vector", Twist, self.on_pull_vector)
        self.ui_sub = rospy.Subscriber("/game/ui_state", String,self.on_ui_state)
        self.fire_sub = rospy.Subscriber("/game/fire_vector", Twist,self.on_fire_vector)
        
    def on_ui_state(self,msg):
        with self.lock:
            self.state = msg.data
            
            if msg.data == 'cooldown':
                pass
                
            if msg.data == 'firing':
                self.in_flight = True 

            if msg.data == 'reset':
                self.bird_x = start_pos_x
                self.bird_y = start_pos_y
                self.vel_x  = 0.0
                self.vel_y  = 0.0
                self.pull_x = 0.0
                self.pull_y = 0.0
                self.in_flight = False


    def on_fire_vector(self,msg):
        with self.lock:
            self.vel_x = msg.linear.x
            self.vel_y = msg.linear.y

    def on_pull_vector(self, msg):
        with self.lock:
            self.pull_x = msg.linear.x
            self.pull_y = msg.linear.y

if __name__ == "__main__":
    rospy.init_node("game_frontend", disable_signals=True)
    frontend = GameFrontend()
    threading.Thread(target=rospy.spin, daemon=True).start()

    #load bg image and elements (loading once only,blit every instance)

    bg_image =  pygame.transform.scale(pygame.image.load(os.path.join(BASE_DIR, "Images", "ff_bg.jpg")),
                                       (1280,720))
    bird_img = pygame.transform.scale(pygame.image.load(os.path.join(BASE_DIR, "Images", "bird.png")),
                                       (450,155))
    font = pygame.font.SysFont(None, 48)
    #I put the game code for interface here
    while running:
        dt = clock.tick(60) /1000.0 #to get the time 
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        with frontend.lock:
            if frontend.in_flight:
                frontend.vel_y += 800 * dt #this sets the gravity
                frontend.bird_x += frontend.vel_x * dt
                frontend.bird_y += frontend.vel_y * dt
                if frontend.bird_y > 720:
                    frontend.in_flight = False
                    #Adding locks to our Ros thread so that it doesnt give us an error
            current_state = frontend.state
            bird_x = frontend.bird_x
            bird_y = frontend.bird_y
            pull_x        = frontend.pull_x
            pull_y        = frontend.pull_y
            in_flight = frontend.in_flight

        if current_state == "pulling":
            draw_x = start_pos_x + int(pull_x * pull_scale)
            draw_y = start_pos_y + int(pull_y * pull_scale)
        else:
            draw_x = int(bird_x)
            draw_y = int(bird_y)
        
                
        screen.blit(bg_image, (0, 0)) #This is like loading frames and acts like a renderer 
        if current_state == "pulling":                        
            pygame.draw.line(screen, (200, 160, 60),
                             (start_pos_x, start_pos_y),(draw_x, draw_y), 4)
        screen.blit(bird_img, (draw_x - 225, draw_y - 77)) 
        
        if current_state == "cooldown":
            #Here a reloading title shows up
            text = font.render("Reloading Da Birb...", True, (255, 255, 255))
            screen.blit(text, (540, 50))
        
        pygame.display.flip() #ensure the images are updated to the monitor

    pygame.quit()
    rospy.signal_shutdown("window closed")
#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from std_msgs.msg import Int32, Bool

'''
HSV at pixels (519,256): [ 19  15 190]
HSV at pixels (7,562): [ 30  11 145]
HSV at pixels (1215,703): [ 30   6 160]
HSV at pixels (1249,325): [ 93  12 190]

LIMIT TO THESE PIXELS
'''

class enemy_detector:
    #initializer
    def __init__(self):
        print("starting enemy detector node")
        rospy.init_node('enemy_detector')
        
        self.bridge = CvBridge()
        #publisher to game file
        self.score_pub = rospy.Publisher('/fuming_feathers/score', Int32, queue_size=1)

        #subscriber, color only
        self.color_sub = rospy.Subscriber('/realsense/color/image_raw', Image, self.color_callback)
        print("subscribed to realsense topic, waiting for data")
        
        #subscriber from game file for reset
        self.reset_sub = rospy.Subscriber('/fuming_feathers/detector_flag', Bool, self.reset_callback)

        #variable declaration
        self.color_current = None
        self.initial_counts = {}
        self.blocks_initialized = False
        self.suspected_knockdown = {}
        self.confirmed_knockdown = {}
        self.frames_to_confirm = 60 #note: pls lower if score is not happening
        
        #hsv color ranges - CHANGE IF ERRORS
        self.color_ranges = {
            'red':   ([0, 160, 75],   [10, 200, 180]),
            'green': ([46, 78, 34], [66, 170, 140]),
            'blue':  ([91, 160, 65], [111, 220, 170])
        }
        
        #point/scoring system
        self.points_per_color = {
            'red': 5,
            'green': 3,
            'blue': 2
        }

    #get block count from contours
    def get_block_count(self, contours):
        count = 0
        for cnt in contours:
            if cv2.contourArea(cnt) > 150:
                count += 1
        return count
    
    #loop, all block colors and mask to find blocks
    def get_contours_for_color(self, hsv, color):
        lower, upper = self.color_ranges[color]
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours
    
    #setup frame, runs at start
    def initialize_blocks(self, hsv):
        print("initializing blocks, capturing reference frame")
        for color in self.color_ranges.keys():
            contours = self.get_contours_for_color(hsv, color)
            self.initial_counts[color] = self.get_block_count(contours)
        self.blocks_initialized = True
        print("reference captured, now monitoring for changes")
        print("Initialized block counts:", self.initial_counts)


    #each frame after, gives current block counts
    def detect_current_blocks(self, hsv):
        current_counts = {}
        
        #match colors, contours, block counts in a frame
        for color in self.color_ranges.keys():
            contours = self.get_contours_for_color(hsv, color)
            current_counts[color] = self.get_block_count(contours)
        
            #draw green boxes
            for cnt in contours:
                if cv2.contourArea(cnt) > 100:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cv2.rectangle(self.color_current, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(self.color_current, color, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        #show image
        cv2.imshow("Block Detection", self.color_current)
        cv2.setMouseCallback("Block Detection", self.click_event) #hsv click checker - PLS CHECK
        cv2.waitKey(1)
        
        #initial vs current, scoring system
        for color in self.color_ranges.keys():
            initial = self.initial_counts.get(color, 0)
            current = current_counts.get(color, 0)
            
            if current < initial:
                #suspected knockdown, first check
                self.suspected_knockdown[color] = self.suspected_knockdown.get(color, 0) + (initial - current)
                self.confirmed_knockdown[color] = self.confirmed_knockdown.get(color, 0) + 1
                
                if self.confirmed_knockdown[color] >= self.frames_to_confirm:
                    #confirmed knoe[color] >= sckdown if knocked down even if hand covers
                    points = self.points_per_color.get(color, 0) * self.suspected_knockdown[color]
                    self.score_pub.publish(points)
                    print(f"{color} block knocked down! +{points} points")
                    self.initial_counts[color] = current
                    self.suspected_knockdown[color] = 0
                    self.confirmed_knockdown[color] = 0
            else:
                #if false alarm block count, then go back to initial state
                self.suspected_knockdown[color] = 0
                self.confirmed_knockdown[color] = 0
    
    #check image and blocks
    def process_frame(self):
        if self.color_current is None:
            return
        
        #convert bgr to hsv
        hsv = cv2.cvtColor(self.color_current, cv2.COLOR_BGR2HSV)
        
        if not self.blocks_initialized:
            self.initialize_blocks(hsv)
        else:
            self.detect_current_blocks(hsv)

    #get each new image, convert to opencv, save current colors, process blocks
    def color_callback(self, msg):
        self.color_current = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        if self.color_current is None:
            return
        self.process_frame()
    
    def reset_callback(self, msg):
        if msg.data == True:
            print ("New round, resetting the game")
            self.blocks_initialized = False
            self.initial_count = {} #reset blocks
            self.score_pub.publish(0) #reset score
            print("Score reset to 0")

    def run(self): #continuous info running
        rospy.spin()
    
    #hsv checker with mouse click - PLS CHECK
    def click_event(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            hsv = cv2.cvtColor(self.color_current, cv2.COLOR_BGR2HSV)
            print(f"HSV at pixels ({x},{y}): {hsv[y, x]}")

#run program loop
if __name__ == '__main__':
    try:
        detector = enemy_detector()
        detector.run()
    except rospy.ROSInterruptException:
        pass
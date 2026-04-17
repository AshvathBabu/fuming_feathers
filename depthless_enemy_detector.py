#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from std_msgs.msg import Int32

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
        
        #variable declaration
        self.color_current = None
        self.initial_counts = {}
        self.blocks_initialized = False
        self.frame_count = 0 
        
        #hsv color ranges
        self.color_ranges = {
            'red':   ([3, 31, 42],   [7, 83, 82]),
            'green': ([112, 39, 29], [119, 76, 60]),
            'blue':  ([200, 40, 32], [206, 79, 85])
        }
        
        #point/scoring system
        self.points_per_color = {
            'red': 5,
            'green': 1,
            'blue': 1
        }

    #get block count from contours
    def get_block_count(self, contours):
        count = 0
        for cnt in contours:
            if cv2.contourArea(cnt) > 500:
                count += 1
        return count
    
    #loop, all block colors and mask to find blocks
    def get_contours_for_color(self, hsv, color):
        lower, upper = self.color_ranges[color]
        lower_np = np.array(lower)
        upper_np = np.array(upper)
        mask = cv2.inRange(hsv, lower_np, upper_np)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours
    
    #setup frame, run at start
    def initialize_blocks(self, hsv):
        print("initializing blocks, capturing reference frame")
        for color in self.color_ranges.keys():
            contours = self.get_contours_for_color(hsv, color)
            self.initial_counts[color] = self.get_block_count(contours)
        
        self.blocks_initialized = True
        print("reference captured, now monitoring for changes")
        rospy.loginfo("Initialized block counts: %s", self.initial_counts)
    
    #check image and blocks
    def process_frame(self):
        if self.color_current is None:
            return
        
        self.frame_count += 1
        
        #convert bgr to hsv
        hsv = cv2.cvtColor(self.color_current, cv2.COLOR_BGR2HSV)
        
        if not self.blocks_initialized:
            print(f"\n[frame {self.frame_count}], first frame - initializing reference")
            self.initialize_blocks(hsv)
        else:
            print(f"\n[frame {self.frame_count}], checking for changes")
            self.detect_current_blocks(hsv)

    #get each new image, convert to opencv, save current colors, process blocks
    def color_callback(self, msg):
        try:
            self.color_current = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            if self.color_current is None:
                rospy.logwarn("Received empty image")
                return
            self.process_frame()
        except CvBridgeError as e:
            rospy.logerr("CV Bridge error: %s", e)
        except Exception as e:
            rospy.logerr("Unexpected error: %s", e)
    
    #each frame, current block counts
    def detect_current_blocks(self, hsv):
        current_counts = {}
        
        for color in self.color_ranges.keys():
            contours = self.get_contours_for_color(hsv, color)
            
            # Draw green boxes
            for cnt in contours:
                if cv2.contourArea(cnt) > 500:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cv2.rectangle(self.color_current, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(self.color_current, color, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            current_counts[color] = self.get_block_count(contours)
            print(f"    currently seeing {current_counts[color]} {color} blocks")
        
        # Show image
        cv2.imshow("Block Detection", self.color_current)
        cv2.waitKey(1)
        
        print("\n  comparing reference vs current frame:")
        knockdown_happened = False
        
        #initial vs current
        for color in self.color_ranges.keys():
            initial = self.initial_counts.get(color, 0)
            current = current_counts.get(color, 0)
            
            print(f"    {color}: reference={initial} blocks, current={current} blocks")
            
            if current < initial:
                knocked = initial - current
                points = self.points_per_color.get(color, 0)
                for _ in range(knocked):
                    self.score_pub.publish(points)
                    print(f"      >>> +{points} points sent to game file <<<")
                knockdown_happened = True
                self.initial_counts[color] = current
        
        if not knockdown_happened:
            print("    no knockdowns detected this frame")
    
    def run(self):
        rospy.spin()

#run program loop
if __name__ == '__main__':
    try:
        detector = enemy_detector()
        detector.run()
    except rospy.ROSInterruptException:
        pass
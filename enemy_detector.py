#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image, PointCloud2
from cv_bridge import CvBridge, CvBridgeError
import sensor_msgs.point_cloud2 as pc2
from std_msgs.msg import Int32

class enemy_detector:
    #initializer
    def __init__(self):
        print("starting enemy detector node") #check
        rospy.init_node('enemy_detector')
        
        self.bridge = CvBridge()
        #publisher to game file
        self.score_pub = rospy.Publisher('/fuming_feathers/score', Int32, queue_size=1)

        #subscribers, color and point cloud
        self.color_sub = rospy.Subscriber('/realsense/color/image_raw', Image, self.color_callback)
        self.depth_sub = rospy.Subscriber('/realsense/depth/points', PointCloud2, self.depth_callback)
        print("subscribed to realsense topics, waiting for data") #check
        
        #variable declaration
        self.color_current = None
        self.depth_current = None
        self.initial_depths = {}
        self.blocks_initialized = False
        self.frame_count = 0 
        
        #hsv color ranges
        self.color_ranges = {
            'red':   ([3, 31, 42],   [7, 83, 82]),
            'green': ([129, 41.2, 16.1], [151.5, 48.8, 38]), #changed
            'blue':  ([200, 40, 32], [206, 79, 85])
            #add more here, or change if diff colors
        }
        
        #point/scoring system
        self.points_per_color = {
            'red': 5,
            'green': 1,
            'blue': 1
        }

    #get center point, depth, store array
    def get_block_depths(self, contours):
        depths = []
        for i in contours:
            if cv2.contourArea(i) > 500:
                M = cv2.moments(i)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    depth = self.get_depth(cx, cy)
                    if depth is not None:
                        depths.append(depth)
        return depths
    
    #loop, all block colors and mask to find blocks
    def get_contours_for_color(self, hsv, color):
        lower, upper = self.color_ranges[color]
        lower_np = np.array(lower)
        upper_np = np.array(upper)
        mask = cv2.inRange(hsv, lower_np, upper_np)

        #ignore hierarchy
        #convert b&w mask, ignore holes, and compress points
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours
    
    #setup frame, run at start
    def initialize_blocks(self, hsv):
        print("initializing blocks, capturing reference frame") #check
        for color in self.color_ranges.keys():
            contours = self.get_contours_for_color(hsv, color)
            self.initial_depths[color] = self.get_block_depths(contours)
        
        self.blocks_initialized = True #confirm
        print("reference captured, now monitoring for changes") #check
        rospy.loginfo("Initialized depth values: %s", self.initial_depths)
    
    #check image and blocks
    def process_frame(self):
        if self.color_current is None:
            return
        
        self.frame_count += 1
        
        #convert to bgr to hsv
        hsv = cv2.cvtColor(self.color_current, cv2.COLOR_BGR2HSV)
        
        if not self.blocks_initialized: #initialize if first time
            print(f"\n[frame {self.frame_count}], first frame - initializing reference")
            self.initialize_blocks(hsv)
        else:
            print(f"\n[frame {self.frame_count}], checking for changes")
            self.detect_current_blocks(hsv) #update frame and detect

    #get each new image, convert to opencv, save current colors, process blocks
    def color_callback(self, msg): #per camera image
        try:
            self.color_current = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            if self.color_current is None:
                rospy.logwarn("Received empty image")
                return
            self.process_frame() #for block detection
        except CvBridgeError as e:
            rospy.logerr("CV Bridge error: %s", e)
        except Exception as e:
            rospy.logerr("Unexpected error: %s", e)
    
    #get new point cloud info and store
    def depth_callback(self, msg):
        self.depth_current = msg
    
    #maps pixel location (x,y) to depth, point cloud
    def get_depth(self, x, y):
        if self.depth_current is None:
            return None
        
        #array conversion
        points = pc2.read_points(self.depth_current, skip_nans=True)
        
        #find approximate 3D location (update after calibration)
        for point in points:
            #2d projection
            px = int(point[0] * 100)
            py = int(point[1] * 100)
            if abs(px - x) < 10 and abs(py - y) < 10:
                return point[2]  #return depth, or z
        return None
    
    #each frame, current depth values
    def detect_current_blocks(self, hsv):
        current_blocks = {}
        
        for color in self.color_ranges.keys():
            contours = self.get_contours_for_color(hsv, color)

            #green box visualization
            for cnt in contours:
                if cv2.contourArea(cnt) > 500: #bigger than 500 px, change if not detecting
                    x, y, w, h = cv2.boundingRect(cnt) #coor
                    cv2.rectangle(self.color_current, (x, y), (x+w, y+h), (0, 255, 0), 2) #green box
                    cv2.putText(self.color_current, color, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2) #color name
        
            current_blocks[color] = self.get_block_depths(contours)
            print(f"    currently seeing {len(current_blocks[color])} {color} blocks at depths {[round(d,3) for d in current_blocks[color]]}")
        
            # Show image
            cv2.imshow("Block Detection", self.color_current)
            cv2.waitKey(1)
            print("\n  comparing reference vs current frame:")
        #initial vs current
        knockdown_happened = False
        for color in self.color_ranges.keys():
            initial_depths = self.initial_depths.get(color, [])
            current_depths = current_blocks.get(color, [])
            
            print(f"    {color}: reference={len(initial_depths)} blocks, current={len(current_depths)} blocks")
            
            blocks_to_remove = []
            for init_depth in initial_depths:
                #check if this specific block is still there
                still_there = False
                for curr in current_depths:
                    if abs(init_depth - curr) < 0.05:
                        still_there = True
                        print(f"      block at depth {init_depth:.3f} still standing (matches {curr:.3f})")
                        break
                
                if not still_there:
                    #if missing, then it's knocked down
                    print(f"      block removed! {color} at depth {init_depth:.3f} is gone <<<")
                    points = self.points_per_color.get(color, 0)
                    self.score_pub.publish(points)
                    print(f"      >>> +{points} points sent to game file <<<")
                    blocks_to_remove.append(init_depth)
                    knockdown_happened = True
            
            #remove knocked down blocks from baseline
            for depth in blocks_to_remove:
                self.initial_depths[color].remove(depth)
        
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

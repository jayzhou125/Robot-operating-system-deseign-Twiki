#!/usr/bin/env python

import rospy
import location
import pid
from std_msgs.msg import Empty, Float64
from geometry_msgs.msg import Twist
from cmvision.msg import Blobs, Blob
from sensor_msgs.msg import Image
from batch_controller import execute, cancel
from rightTriangle import *
from struct import pack, unpack
from balloon_tracking_test import scan, get_blob_offset, rawBlobs


pub_command = rospy.Publisher("/kobuki_command", Twist, queue_size=10)  # publish command
pub_stop = rospy.Publisher("/emergency_stop", Empty, queue_size=10)   # publish stop
kinect_angle = 0.0

depth_map = Image()
depth_available = False

##THOUGHTS:
# we probably need the pid to keep the balloon in the center of the screen
# We also might need to move quickly to the pid (sharpen the movement)


# get the angle of kinect
def angleCallback(data):
	global kinect_angle
	kinect_angle = data.data

def depthCallback(data):
	global depth_map, depth_available
	depth_map = data
	depth_available = True


def getDepth(x, y):
	global depth_map
	data = depth_map.data
	offset = (depth_map.step * y) + (4 * x)
        print "depth map size {}, offset {}:{}".format(len(data), offset, offset+3)
	dist = unpack('f', depth_map.data[offset] + depth_map.data[offset+1] + depth_map.data[offset+2] + depth_map.data[offset+3])
	return dist[0]

def cleanUp():
	global pub_stop
	pub_stop.publish(Empty())
	
# stop the robot
def zero():
    result = Twist();
    result.angular.z = 0
    result.linear.x = 0

    return result

def catcher():
	global pub_stop, pub_command, kinect_angle, depth_available

	rospy.init_node("balloon_catcher")
	rospy.Subscriber("/cur_tilt_angle", Float64, angleCallback)
	rospy.Subscriber("/camera/depth/image", Image, depthCallback)
        location.init()
	rospy.on_shutdown(cleanUp)

        while not depth_available:
        	rospy.sleep(0.1)

	# get the balloon in the center of the screen(ball_tracker)
	targetBlob = scan(pub_command)
	
	KINECT_PIXELS_PER_DEGREE = 10
	
	dist = None
	horizontal = 0
	vertical = 0
	v_prev = 0
	V_THRESHOLD = 0.02 # 2cm
        
    while v_prev - vertical >= V_THRESHOLD:
		rospy.sleep(0.01)
		print (v_prev, vertical, v_prev - vertical)
		centerOffset, targetBlob = get_blob_offset()

		if centerOffset == -1 or targetBlob is None:
			continue

		# calculate angle from ground to camera-balloon line
		angle = kinect_angle + ((depth_map.height/2) - targetBlob.y)/KINECT_PIXELS_PER_DEGREE

		# get the distance to the balloon 
		dist = getDepth(targetBlob.x, targetBlob.y)

		v_prev = vertical
		vertical = getOpposite(angle, dist)
		horizontal = getAdjacent(angle, dist)

	print "balloon falling {} meters from camera".format(dist)
	print "height {} meters, estimated landing point {} meters".format(vertical, horizontal)

	# move the calculated distance 
	# we could use batch command's execute but the trick will be the ball won't be in the center all the time when it falls
	# so we might need to use the tracking blob with a higher sensitivity.

	location.resetOdom()
	command = zero()
	SLEEP = 0.01
	DELTA_X = 0.9 * SLEEP
        Z_MAX = 0.6
        IMAGE_WIDTH = 640
	X_TURN_MAX = 0.7
	while(location.currentLocation[0] < horizontal):
		if command.linear.x < 1:
			command.linear.x += DELTA_X
		if command.linear.x > 1:
			command.linear.x = 1
		
        command.angular.z = 0

        centerOffset, _ = get_blob_offset()
	    if centerOffset is None:
			pub_command.publish(command)
			continue
	    
		speed = 50 * centerOffset/float(IMAGE_WIDTH)    # calculate the right amount of speed for the command

		
		if centerOffset > 20:   # if the offset is bigger than 20
			# print "{} LEFT".format(abs(centerOffset))
			command.angular.z = min(Z_MAX, speed) # turn left and follow
			# print([command.angular.z, centerOffset/rawBlobs.image_width])
		elif centerOffset < -20:    # if the offset is smaller than -20
			# print "{} RIGHT".format(abs(centerOffset))
			command.angular.z = max(-Z_MAX, speed)  # turn right and follow the ball
			# print([command.angular.z, centerOffset/rawBlobs.image_width])

		if abs(command.angular.z) > 0.2 and command.linear.x > X_TURN_MAX:
			command.linear.x = X_TURN_MAX
			print "turning"
		pub_command.publish(command)
		print "x {}, z {}".format(command.linear.x, command.angular.z)
		rospy.sleep(SLEEP)

	command = zero()
	pub_command.publish(command)
	
	
# def track_blobs():
#     global rawBlobs, pub_command, pub_stop

#     Z_MAX = 0.8  # maximum speed

#     zero_count = 0

#     while(True):
# 	rospy.sleep(0.001)

#         command = zero()
#         command.linear.x = Z_MAX #0.35 # update values; .7 = too fast
#         mergedBlobs = mergeBlobs()
#         trackingBlob = None

#        # print mergedBlobs.keys()

#         if "orangeballoon" in mergedBlobs.keys() and len(mergedBlobs["orangeballoon"]) > 0:
#             trackingBlob = mergedBlobs["orangeballoon"][0]
                        
#         if trackingBlob is None:
#             if zero_count < 1000:
#                 zero_count += 1
# 		print zero_count
#             else:
# 		pub_stop.publish(Empty())
#             continue
        
#         zero_count = 0


#         # pid error (Proportional-Integral-Derivative (PID) Controller)
#         p = 0.009 # update values
#         i = 0 # can leave this as zero
#         d = 0 # update values; .5 = crazy turn
#         controller = pid.PID(p, i, d)
#         controller.start()
        
#         center = rawBlobs.image_width//2    # the center of the image
#         centerOffset = center - trackingBlob.x  # the offset that the ball need to travel 
        
#         cor = controller.correction(centerOffset) # added, right angular speed you want
        
# 	# print cor

#         # print "Tracking Blob Object Attr: ", trackingBlob.name, "<<" # added AS
        
#         command.angular.z = cor
        
#         pub_command.publish(command)    # publish the twist command to the kuboki node

# def mergeBlobs():
#     global rawBlobs

#     merged = {}
#     MIN_AREA = 40

#     for b in rawBlobs.blobs:
#         mergeTarget = Blob()
#         mergeNeeded = False
        
#         #check to see if there is an existing blob to merge with
#         if b.name in merged.keys(): 
#             for m in merged[b.name]:
#                 if overlaps(b, m):
#                     mergeTarget = m
#                     mergeNeeded = True
#                     break
        
#         else: # no blobs by that name
#             merged[b.name] = []
        
#         # merge
#         if not mergeNeeded:
#             merged[b.name].append(b)
#         else: # merge needed
#             mergeTarget.left = min(mergeTarget.left, b.left)
#             mergeTarget.right = max(mergeTarget.right, b.right)
#             mergeTarget.top = min(mergeTarget.top, b.top)
#             mergeTarget.bottom = max(mergeTarget.bottom, b.bottom)
#             mergeTarget.area = (mergeTarget.right - mergeTarget.left) * (mergeTarget.bottom - mergeTarget.top)
    
#     for m in merged.keys():
#         merged[m].sort(key=lambda x: x.area, reverse=True)
#         merged[m][:] = [i for i in merged[m] if i.area > MIN_AREA]
    
#     return merged


# def overlaps(blob1, blob2):
#     h_over = False
#     v_over = True
#     if (blob1.left > blob2.left and blob2.left < blob2.right
#     or  blob1.right > blob2.left and blob1.right < blob2.right
#     or  blob2.left > blob1.left and blob2.left < blob1.right
#     or  blob2.right > blob1.left and blob2.right < blob1.right):
#         h_over = True
    
#     if (blob1.top > blob2.top and blob2.top < blob2.bottom
#     or  blob1.bottom > blob2.top and blob1.bottom < blob2.bottom
#     or  blob2.top > blob1.top and blob2.top < blob1.bottom
#     or  blob2.bottom > blob1.top and blob2.bottom < blob1.bottom):
#         v_over = True

#     return h_over and v_over

if __name__ == "__main__":
	catcher()

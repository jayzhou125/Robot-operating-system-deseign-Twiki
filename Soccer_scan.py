#!/usr/bin/python

# This is a node for all the scan functions
# 
# Pseudocode:
# circle 360 degrees
#     when ball is seen (i.e., trackingBlob.name = "blueball"), record odometry
#     when goal is seen, record odometry
#     if ball is found first
#         if goal < 180 
#                turn right from ball
#         if goal > 180 
#                turn left from ball
#     if goal is found first
#         if ball < 180 
#                turn left from ball
#         if ball > 180 
#                turn right from ball    
# This node will return three value： 
#     the angle which the ball is found, 
#     the angle which the goal is found, 
#     the direction of the turn before the second scan (-1 = right/clockwise; 1 = left; ccw)

import rospy
from std_msgs.msg import Empty
from geometry_msgs.msg import Twist
from cmvision.msg import Blobs, Blob
from sensor_msgs.msg import Image
import location

rawBlobs = Blobs()
mergedBlobs = Blobs()
width = 0


def turn_left(speed)
    command.angular.z = speed
    pub_command.publish(command)    # publish the twist command to the kuboki node

# stop the robot
def zero():
    result = Twist();
    result.angular.z = 0
    result.linear.x = 0

    return result

# keep turning left until the ball and the goal is find
def scan():
    global rawBlobs, pub_command
    
    track_blobs("ball")
    ball_angle = record_location()
    
    # record location
    
    track_blobs("goal")
    goal_angle = record_location()
    
    return ball_angle, goal_angle

def track_blobs(mode):
    global rawBlobs, pub_command, ballNotFound, goalNotFound

    Z_MAX = 0.5  # maximum speed

    while(True):
       
        command = zero() 
        mergedBlobs = mergeBlobs()
        trackingBlob = None

        print mergedBlobs.keys()

        if mode == "ball" and "blueball" in mergedBlobs.keys():
            trackingBlob = mergedBlobs["blueball"][0]
        elif mode == "goal" and "pinkgoal" in mergedBlobs.keys() and "yellowgoal" in mergedBlobs.keys():
            for outer in mergedBlobs["yellowgoal"]:
                for inner in mergedBlobs["pinkgoal"]:
                    if (inner.left >= outer.left
                    and inner.right <= outer.right
                    and inner.top >= outer.top
                    and inner.bottom <= outer.bottom):
                        trackingBlob = inner
                        break
                
                if trackingBlob is not None:
                    break
                        
        if trackingBlob is None:
            turn_left()
            continue

        center = rawBlobs.image_width//2    # the center of the image
        centerOffset = center - trackingBlob.x  # the offset that the ball need to travel 
        
        speed = 4 * centerOffset/float(rawBlobs.image_width)    # calculate the right amount of speed for the command

        print "Tracking Blob Object Attr: ", trackingBlob.name, "<<" # added AS

        if centerOffset > 20:   # if the offset is bigger than 20
            command.angular.z = min(Z_MAX, speed) # turn left and follow 
            # print([command.angular.z, centerOffset/rawBlobs.image_width])
        elif centerOffset < -20:    # if the offset is smaller than -20
            command.angular.z = max(-Z_MAX, speed)  # turn right and follow the ball
            # print([command.angular.z, centerOffset/rawBlobs.image_width])
        else
#             ballNotFound = False
            command = zero()
            # stop the robot
            pub_command.publish(command)    # publish the twist command to the kuboki nod
            return 
        
        pub_command.publish(command)    # publish the twist command to the kuboki node


def record_location()
    # record odom
    _, _, angle = location.currentLocation
    return angle
    


# merge bolbs
def mergeBlobs():
    global rawBlobs

    merged = {}

    for b in rawBlobs.blobs:
        mergeTarget = Blob()
        mergeNeeded = False
        
        #check to see if there is an existing blob to merge with
        if b.name in merged.keys(): 
            for m in merged[b.name]:
                if overlaps(b, m):
                    mergeTarget = m
                    mergeNeeded = True
                    break
        
        else: # no blobs by that name
            merged[b.name] = []
        
        # merge
        if not mergeNeeded:
            merged[b.name].append(b)
        else: # merge needed
            mergeTarget.left = min(mergeTarget.left, b.left)
            mergeTarget.right = max(mergeTarget.right, b.right)
            mergeTarget.top = min(mergeTarget.top, b.top)
            mergeTarget.bottom = max(mergeTarget.bottom, b.bottom)
            mergeTarget.area = (mergeTarget.right - mergeTarget.left) * (mergeTarget.bottom - mergeTarget.top)
    
    for m in merged.keys():
        merged[m].sort(key=lambda x: x.area, reverse=True)
    
    return merged

# find the overlap blob
def overlaps(blob1, blob2):
    h_over = False
    v_over = True
    if (blob1.left > blob2.left and blob2.left < blob2.right
    or  blob1.right > blob2.left and blob1.right < blob2.right
    or  blob2.left > blob1.left and blob2.left < blob1.right
    or  blob2.right > blob1.left and blob2.right < blob1.right):
        h_over = True
    
    if (blob1.top > blob2.top and blob2.top < blob2.bottom
    or  blob1.bottom > blob2.top and blob1.bottom < blob2.bottom
    or  blob2.top > blob1.top and blob2.top < blob1.bottom
    or  blob2.bottom > blob1.top and blob2.bottom < blob1.bottom):
        v_over = True

    return h_over and v_over

#!/usr/bin/env python

import rospy
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty


pub_ctrl = rospy.Publisher("/kobuki_command", Twist, queue_size=10)
pub_stop = rospy.Publisher("/emergency_stop", Empty, queue_size=10)
pub_resume = rospy.Publisher("/resume", Empty, queue_size=10)

input = None
command = Twist()
dirty = False
no_accel = True

def joystickCallback(data):
    global input, dirty
    print data.buttons
    print data.axes
    input = data
    dirty = True

def cleanUp():
    global pub_ctrl, command
    command.linear.x = 0.0
    command.angular.z = 0.0
    pub_ctrl.publish(command)
    rospy.sleep(1)

def remoteController():
    global pub_ctrl, command, input, dirty
    rospy.init_node("remoteControl", anonymous=True)
    rospy.Subscriber("joy", Joy, joystickCallback)
    rospy.on_shutdown(cleanUp)

    while not rospy.is_shutdown():
        if dirty:
            dirty = False
            update_command()
            pub_ctrl.publish(command)
	rospy.sleep(0.05)

    #rospy.spin()

def update_command():
    global input, command, pub_stop, no_accel

    # emergency brake
    raw_kill = input.buttons[1] # B

    if raw_kill == 1:
        command.angular.z = 0.0
        command.linear.x = 0.0
	pub_stop.publish(Empty())
        pub_ctrl.publish(command)
        rospy.signal_shutdown("Emergency Stop!!!")

    # resume from stop
    
    resume = input.buttons[3] # Y

    if resume == 1:
        pub_resume.publish(Empty())
    
    # turning
    Z_LIMIT = 1.0
    raw_z = input.axes[0] # LR stick left

    if raw_z < 0:
        command.angular.z = max(raw_z, -1*Z_LIMIT)
    elif raw_z > 0:
	    command.angular.z = min(raw_z, Z_LIMIT)

    # forward/backward
    X_LIMIT = 0.8
    raw_x = input.axes[5] # right trigger
    invert = input.buttons[0] == 1

    if no_accel and raw_x == 0.0: # 0.0 is half-depressed trigger, needs to be 1 for unpressed (no acceleration)
        raw_x = 1.0
    else:
        no_accel = False

    raw_x = ((-1*raw_x) + 1) / 2 # convert depressing right trigger to 0 => 1 instead of 1 => -1

    trim_x = min(raw_x, X_LIMIT)

    if invert:
	    trim_x *= -1

    command.linear.x = trim_x

    # brakes
    raw_brake = input.axes[2] # left trigger

    # if raw_brake < 0.0:
    #    command.linear.x -= 0.2
    #    pub_ctrl.publish(command)
    #    rospy.signal_shutdown("normal brake!!!")
    
    if raw_brake < 0.0: # left trigger depressed more than 50%
       command.linear.x = 0.0
       command.angular.z = 0.0
    #    pub_stop.publish(Empty())

if __name__ == '__main__':
    remoteController()

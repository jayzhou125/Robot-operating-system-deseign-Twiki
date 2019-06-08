#!/usr/bin/python

import rospy
import key_handler
from std_msgs.msg import Int32, Float32, Empty
from threading import Thread
from dir_codes import STOP

pub_keys = rospy.Publisher("/keys", Int32, queue_size=20) # publish the key pressed
pub_dx = rospy.Publisher("/dx", Float32, queue_size=10)   # publish the x value
pub_dz = rospy.Publisher("/dz", Float32, queue_size=10)   # publish the z value
pub_kill = rospy.Publisher("/emergency_stop", Empty, queue_size=10) # publish to stop

handler = Thread(target=key_handler.keypress)   

def key_node(dx=0, dz=0):
    global handler, pub_keys, pub_dx, pub_dz, pub_kill
    rospy.init_node("key_node")
    rospy.on_shutdown(cleanUp)

    # if no subscriber to x and z, pass
    while pub_dx.get_num_connections() == 0 or pub_dz.get_num_connections() == 0:
        pass

    # keep publish the x and z value
    pub_dx.publish(dx)
    pub_dz.publish(dz)

    handler.start() # start keypress handler in background thread

    TIMEOUT = 5
    stop_wait = TIMEOUT
    while not key_handler.kill:

        dirty = key_handler.dirty
        code = key_handler.code


        if dirty:   # new key pressed
            pub_keys.publish(code)  # publish the key code
            key_handler.dirty = False
            stop_wait = 0

        elif code != STOP: # last key was valid, but entered long ago
            if stop_wait == TIMEOUT:
                pub_keys.publish(STOP)
            if stop_wait <= TIMEOUT:
                stop_wait += 1

        rospy.sleep(0.1)
    
    cleanUp()


def cleanUp():
    global handler, pub_kill
    key_handler.kill = True
    
    pub_kill.publish(Empty())
    handler.join()


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description="takes WASD or arrow key inputs and converts them to robot directions")
    
    parser.add_argument("-x", "--delta-x", type=float, nargs='?', const=0, help="set the linear acceleration constant")
    parser.add_argument("-z", "--delta-z", type=float, nargs='?', const=0, help="set the angular acceleration constant")
    args = parser.parse_args()
    
    dx = args.delta_x
    dz = args.delta_z

    key_node(dx, dz)

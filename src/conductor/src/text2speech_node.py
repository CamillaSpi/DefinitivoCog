#!/usr/bin/python3

from __future__ import print_function

from pepper_nodes.srv import Text2Speech
import rospy

def handle_speech(req):
    print(req)
    return 'ack'

def add_two_ints_server():
    rospy.init_node('tts_service')
    s = rospy.Service('tts', Text2Speech, handle_speech)
    print("talk")
    rospy.spin()

if __name__ == "__main__":
    add_two_ints_server()


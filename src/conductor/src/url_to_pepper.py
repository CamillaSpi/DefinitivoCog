#!/usr/bin/python3
import rospy
from std_msgs.msg import String
import numpy as np
from pepper_nodes.srv import LoadUrl, ExecuteJS
import time

# Init node
rospy.init_node('url_to_pepper', anonymous=True)
#rospy.wait_for_service('load_url')
print('mario')
load_url = rospy.ServiceProxy('load_url', LoadUrl)
execute_js = rospy.ServiceProxy('execute_js', ExecuteJS)
# this is called from the background thread
def callback(msg):
    try:
        resp = None
        print('sono js ' , msg.data)
        print("is this prima degli if")
        if "js" in msg.data:
            print("is this dopo js")
            script = """var inject = document.getElementById("clickMe");
    inject.click();"""
            resp = execute_js(script).ack
        if 'reload' in msg.data:
            print("is this in reload")
            script = """var reload = document.getElementById("refresh");
    reload.click();"""
            resp = execute_js(script).ack
        elif 'js' not in msg.data and 'reload' not in msg.data:
            resp = load_url(msg.data).ack

        if resp!= 'ACK':
            print("There is an error in msg, maybe")
            
    except rospy.ServiceException as e:
        print("Service call failed: %s", e)
    
def listener():
    rospy.Subscriber("toShow", String, callback)
    print('toshow')
    rospy.spin()

if __name__ == '__main__':
    listener()
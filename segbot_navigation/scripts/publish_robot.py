#!/usr/bin/env python
import numpy as np
import rospy
from people_msgs.msg import People, Person
from geometry_msgs.msg import Point, PointStamped, PoseWithCovarianceStamped, PoseStamped, Twist


"""
This is a Robot to Person spoofing node that utilizes the estimated pose and commanded velocity of 
a robot, as exposed through a ROSBridge connection.

"""

class MultiRobotPositionInterface:
	WINDOW_SIZE = 5

	def __init__(self):
	    self.robot_pos = PoseWithCovarianceStamped()
	    self.last_robot_pos = PoseWithCovarianceStamped()
	    self.last_time = None
	    self.vel_window_x = np.zeros(self.WINDOW_SIZE)
	    self.vel_window_y = np.zeros(self.WINDOW_SIZE)

	def pose_callback(self, data):
	    self.last_robot_pos = self.robot_pos
	    self.robot_pos = data
	    self.last_time = rospy.Time.now()

	def push(self, a, n):
	     a = np.roll(a, 1)
	     a[0] = n
	     return a
	
	def run(self):
	    rospy.init_node('person_publisher', anonymous=True)
	    person_pub = rospy.Publisher('/people', People, queue_size=1)
	    point_pub = rospy.Publisher('/person_point', PointStamped, queue_size=1)
	    # TODO remove hardcoded hostnames...
	    rospy.Subscriber("/connected_robots/hermes/amcl_pose", PoseWithCovarianceStamped, self.pose_callback)
	    rate = rospy.Rate(10)
	    self.last_time = rospy.Time.now()
	    
	    while not rospy.is_shutdown():
		people_msg = People()
		people_msg.header.frame_id = "/level_mux_map"
		people_msg.header.stamp = rospy.Time.now()
		person_position = Point()
		person_velocity = Point()


		# Stuff person data
		person_position = self.robot_pos.pose.pose.position

		# We track and smooth velocity data due to the large fluctuations between time steps
		x_diff  = (self.robot_pos.pose.pose.position.x - self.last_robot_pos.pose.pose.position.x) / (rospy.Time.now() - self.last_time).to_sec()
		y_diff  = (self.robot_pos.pose.pose.position.y - self.last_robot_pos.pose.pose.position.y) / (rospy.Time.now() - self.last_time).to_sec() 
		self.vel_window_x = self.push(self.vel_window_x, x_diff)
		self.vel_window_y = self.push(self.vel_window_y, y_diff)

		person_velocity.x = np.sum(self.vel_window_x) / self.vel_window_x.size
		person_velocity.y = np.sum(self.vel_window_y) / self.vel_window_y.size
		person_velocity.z = 0

		person = Person()
		point_viz_msg = PointStamped()

		point_viz_msg.header = people_msg.header
		point_viz_msg.point = person_position

		person.name = "Robot"
		person.position = person_position
		person.velocity = person_velocity
		person.reliability = 0.99

		people_msg.people.append(person)       
		
		person_pub.publish(people_msg)
		point_pub.publish(point_viz_msg)
		rate.sleep()

if __name__ == '__main__':
	try:
		mrpi = MultiRobotPositionInterface()
		mrpi.run()
	except rospy.ROSInterruptException:
		pass

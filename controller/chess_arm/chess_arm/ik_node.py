#!/usr/bin/env python3

import sys
import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from moveit_msgs.srv import GetPositionIK

HOME_DEG = {'base_joint': 90, 'shoulder_joint': 90, 'elbow_joint': 0,
            'wrist_pitch_joint': 180, 'wrist_roll_joint': 0}
DIRECTION = {'base_joint': 1, 'shoulder_joint': 1, 'elbow_joint': -1,
             'wrist_pitch_joint': 1, 'wrist_roll_joint': 1}  # placeholders — calibrate these
ERROR_OFFSET = {'base_joint': 0, 'shoulder_joint': 0, 'elbow_joint': -3,
            'wrist_pitch_joint': 10, 'wrist_roll_joint': 0}
Y_OFFSET = 0.044  # 31 mm

class IKNode(Node):

    def __init__(self):
        super().__init__('ik_node')

        self.ik_client = self.create_client(
            GetPositionIK,
            '/compute_ik'
        )

        self.get_logger().info('Waiting for MoveIt /compute_ik service...')

        if not self.ik_client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error(
                'MoveIt /compute_ik service is not available.'
            )
            rclpy.shutdown()
            return

        self.get_logger().info('MoveIt IK service is ready.')

    def calculate_ik(self, x_mm, y_mm, z_mm):

        # MoveIt uses meters
        x = x_mm / 1000.0
        y = (y_mm / 1000.0) + Y_OFFSET
        z = z_mm / 1000.0

        request = GetPositionIK.Request()

        # Which MoveIt planning group should solve the IK?
        request.ik_request.group_name = 'arm'

        # Robot base frame
        request.ik_request.pose_stamped = PoseStamped()
        request.ik_request.pose_stamped.header.frame_id = 'base_link'

        request.ik_request.pose_stamped.pose.position.x = x
        request.ik_request.pose_stamped.pose.position.y = y
        request.ik_request.pose_stamped.pose.position.z = z

        # Position-only IK.
        #
        # The 'arm' group's KDL solver is configured with
        # `position_only_ik: true` (see chess_moveit_config
        # kinematics.yaml), so the orientation below is not
        # enforced -- only the XYZ position of the gripper is
        # solved. The quaternion is kept here for reference,
        # since MoveIt still expects a well-formed pose.
        request.ik_request.pose_stamped.pose.orientation.x = 0.0
        request.ik_request.pose_stamped.pose.orientation.y = 0.0
        request.ik_request.pose_stamped.pose.orientation.z = 0.0
        request.ik_request.pose_stamped.pose.orientation.w = 1.0

        # Allow MoveIt to choose the solution
        request.ik_request.timeout.sec = 1

        # Call IK service
        future = self.ik_client.call_async(request)

        rclpy.spin_until_future_complete(self, future)

        if future.result() is None:
            self.get_logger().error('IK service call failed.')
            return

        response = future.result()

        # MoveIt error code
        if response.error_code.val != 1:
            self.get_logger().error(
                f'IK failed. MoveIt error code: '
                f'{response.error_code.val}'
            )
            return

        joint_state = response.solution.joint_state

        print()
        print('========================================')
        print('           IK SOLUTION')
        print('========================================')
        print(f'Target: X={x_mm} mm, Y={y_mm} mm, Z={z_mm} mm')
        print()

        print('ROS joint angles:')

        for name, position in zip(joint_state.name, joint_state.position):
            if name in HOME_DEG:
                servo_cmd = math.degrees(position)
                servo_cmd_phy = HOME_DEG[name] + DIRECTION[name] * math.degrees(position)
                # servo_cmd = HOME_DEG[name] + ERROR_OFFSET[name] + DIRECTION[name] * math.degrees(position)
                # servo_cmd = max(0, min(180, servo_cmd))  # clamp to servo range
                print(f'{name:20s}: servo command = {servo_cmd:.1f}°')
                
        print('========================================')
        print()
        for name, position in zip(joint_state.name, joint_state.position):
            if name in HOME_DEG:
                servo_cmd = math.degrees(position)
                # servo_cmd_phy = HOME_DEG[name] + DIRECTION[name] * math.degrees(position)
                servo_cmd_phy = abs(HOME_DEG[name] + ERROR_OFFSET[name] + DIRECTION[name] * math.degrees(position))
                # servo_cmd = max(0, min(180, servo_cmd))  # clamp to servo range
                print(f'{name:20s}: servo command phy = {servo_cmd_phy:.1f}°')



def main(args=None):

    if len(sys.argv) != 4:
        print()
        print('Usage:')
        print('  ros2 run chess_arm ik_node X Y Z')
        print()
        print('Example:')
        print('  ros2 run chess_arm ik_node 150 80 120')
        print()
        return

    try:
        x = float(sys.argv[1])
        y = float(sys.argv[2])
        z = float(sys.argv[3])
    except ValueError:
        print('X, Y and Z must be numbers.')
        return

    rclpy.init(args=args)

    node = IKNode()

    node.calculate_ik(x, y, z)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
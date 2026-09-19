#!/usr/bin/env python3

import sys
import math
import time

import serial

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

# Order here MUST match the Arduino's ANGLES argument order:
# base, shoulder, elbow, wristPitch, wristRoll
JOINT_ORDER = list(HOME_DEG.keys())

# Don't change - matches your working setup.
PORT = '/dev/cu.usbserial-1130'
BAUD = 115200

# Keep wrist roll fixed at 180 for now.
WRIST_ROLL_FIXED = 180.0


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
        """
        Solve IK for one XYZ target (mm) and return the 5 physical servo
        angles in JOINT_ORDER (base, shoulder, elbow, wristPitch,
        wristRoll), or None on failure.
        """

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

        # Position-only IK (orientation kept for a well-formed pose only).
        request.ik_request.pose_stamped.pose.orientation.x = 0.0
        request.ik_request.pose_stamped.pose.orientation.y = 0.0
        request.ik_request.pose_stamped.pose.orientation.z = 0.0
        request.ik_request.pose_stamped.pose.orientation.w = 1.0

        request.ik_request.timeout.sec = 1

        future = self.ik_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        if future.result() is None:
            self.get_logger().error('IK service call failed.')
            return None

        response = future.result()

        if response.error_code.val != 1:
            self.get_logger().error(
                f'IK failed. MoveIt error code: '
                f'{response.error_code.val}'
            )
            return None

        joint_state = response.solution.joint_state
        raw_deg = {}

        for name, position in zip(joint_state.name, joint_state.position):
            if name in HOME_DEG:
                raw_deg[name] = math.degrees(position)

        print()
        print('========================================')
        print('           IK SOLUTION')
        print('========================================')
        print(f'Target: X={x_mm} mm, Y={y_mm} mm, Z={z_mm} mm')
        print()

        servo_angles = []

        for name in JOINT_ORDER:
            if name not in raw_deg:
                self.get_logger().error(
                    f'IK solution missing joint "{name}".'
                )
                return None

            servo_cmd_phy = abs(
                HOME_DEG[name] + ERROR_OFFSET[name] +
                DIRECTION[name] * raw_deg[name]
            )
            print(f'{name:20s}: servo command phy = {servo_cmd_phy:.1f}°')
            servo_angles.append(servo_cmd_phy)

        print('========================================')
        print()

        return servo_angles


def send_angles(angles):
    """
    Sends ANGLES,base,shoulder,elbow,wristPitch,wristRoll to the Arduino.
    The Arduino moves there and stops - no pick/place, no return home.
    """

    command = 'ANGLES,' + ','.join(f'{v:.1f}' for v in angles)

    print(f'Connecting to Arduino on {PORT} @ {BAUD}...')

    with serial.Serial(PORT, BAUD, timeout=5) as ser:
        time.sleep(2)  # allow Arduino to reset after opening the port
        ser.reset_input_buffer()

        print(f'Sending: {command}')
        ser.write((command + '\n').encode())

        # Print anything the Arduino sends back for a short while.
        # (The Arduino's ANGLES handler only prints on error, so silence
        # here just means the move completed without complaint.)
        deadline = time.time() + 10
        got_reply = False

        while time.time() < deadline:
            line = ser.readline().decode(errors='replace').strip()

            if line:
                got_reply = True
                print(f'Arduino: {line}')

                if line.startswith('ERROR'):
                    break

        if not got_reply:
            print('(No reply from Arduino - move likely completed silently.)')


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

    angles = node.calculate_ik(x, y, z)

    node.destroy_node()
    rclpy.shutdown()

    if angles is None:
        print('IK failed - not sending anything to the Arduino.')
        return

    angles[4] = WRIST_ROLL_FIXED  # keep wrist roll fixed at 180 for now

    try:
        send_angles(angles)
    except serial.SerialException as e:
        print(f'Serial error: {e}')
        print(f'Check that {PORT} is correct and not already open '
              f'elsewhere (e.g. Arduino Serial Monitor).')


if __name__ == '__main__':
    main()
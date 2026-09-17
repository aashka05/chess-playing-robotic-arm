#```python
#!/usr/bin/env python3

import sys
import math
import serial
import time
import json
import os

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from moveit_msgs.srv import GetPositionIK


# ============================================================
# CONFIGURATION
# ============================================================

# Replace these with your actual chess-square coordinates.
# Coordinates are in mm in YOUR coordinate system.
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
SQ_DICT_PATH = os.path.join(PACKAGE_DIR, 'sq_dict.json')

with open(SQ_DICT_PATH, 'r') as f:
    SQUARES = json.load(f)


# Height at which the gripper should move over the board.
# Change this to your required height.
Z_MM = 30  #mm


# ------------------------------------------------------------
# Coordinate-system offset
#
# Your desired chess-board coordinate:
#
#       Y = 0
#
# corresponds to:
#
#       MoveIt Y = +31 mm
#
# ------------------------------------------------------------
Y_OFFSET = 0.046


# ------------------------------------------------------------
# Servo calibration
# ------------------------------------------------------------

HOME_DEG = {
    'base_joint': 90,
    'shoulder_joint': 90,
    'elbow_joint': 0,
    'wrist_pitch_joint': 180,
    'wrist_roll_joint': 0
}


DIRECTION = {
    'base_joint': 1,
    'shoulder_joint': 1,
    'elbow_joint': -1,
    'wrist_pitch_joint': 1,
    'wrist_roll_joint': 1
}


ERROR_OFFSET = {
    'base_joint': 0,
    'shoulder_joint': 0,
    'elbow_joint': -3,
    'wrist_pitch_joint': 10,
    'wrist_roll_joint': 0
}


# ------------------------------------------------------------
# Arduino serial port
#
# Change this to your Arduino port.
#
# Mac example:
# /dev/cu.usbserial-1130
#
# ------------------------------------------------------------
SERIAL_PORT = '/dev/cu.usbserial-1130'
BAUD_RATE = 115200


# ============================================================
# IK NODE
# ============================================================

class IKNode(Node):

    def __init__(self):

        super().__init__('test_square_ik')

        self.ik_client = self.create_client(
            GetPositionIK,
            '/compute_ik'
        )

        self.get_logger().info(
            'Waiting for MoveIt /compute_ik service...'
        )

        if not self.ik_client.wait_for_service(timeout_sec=10.0):

            self.get_logger().error(
                'MoveIt /compute_ik service is not available.'
            )

            raise RuntimeError(
                'MoveIt /compute_ik service unavailable'
            )

        self.get_logger().info(
            'MoveIt IK service is ready.'
        )


    def calculate_ik(self, x_mm, y_mm, z_mm):

        # ----------------------------------------------------
        # Convert YOUR coordinate system -> MoveIt coordinate
        # ----------------------------------------------------

        x = x_mm / 1000.0

        y = (y_mm / 1000.0) + Y_OFFSET

        z = z_mm / 1000.0


        request = GetPositionIK.Request()

        request.ik_request.group_name = 'arm'

        request.ik_request.pose_stamped = PoseStamped()

        request.ik_request.pose_stamped.header.frame_id = \
            'base_link'


        request.ik_request.pose_stamped.pose.position.x = x
        request.ik_request.pose_stamped.pose.position.y = y
        request.ik_request.pose_stamped.pose.position.z = z


        # Position-only IK
        request.ik_request.pose_stamped.pose.orientation.x = 0.0
        request.ik_request.pose_stamped.pose.orientation.y = 0.0
        request.ik_request.pose_stamped.pose.orientation.z = 0.0
        request.ik_request.pose_stamped.pose.orientation.w = 1.0


        request.ik_request.timeout.sec = 1


        # ----------------------------------------------------
        # Call MoveIt
        # ----------------------------------------------------

        future = self.ik_client.call_async(request)

        rclpy.spin_until_future_complete(
            self,
            future
        )


        if future.result() is None:

            self.get_logger().error(
                'IK service call failed.'
            )

            return None


        response = future.result()


        if response.error_code.val != 1:

            self.get_logger().error(
                f'IK failed. MoveIt error code: '
                f'{response.error_code.val}'
            )

            return None


        return response.solution.joint_state


# ============================================================
# CONVERT ROS ANGLES -> PHYSICAL SERVO ANGLES
# ============================================================

def calculate_servo_angles(joint_state):

    servo_angles = {}


    for name, position in zip(
        joint_state.name,
        joint_state.position
    ):

        if name not in HOME_DEG:
            continue


        ros_deg = math.degrees(position)


        servo_deg = abs(
            HOME_DEG[name]
            + ERROR_OFFSET[name]
            + DIRECTION[name] * ros_deg
        )


        servo_angles[name] = servo_deg


    return servo_angles


# ============================================================
# SEND ANGLES TO ARDUINO
# ============================================================

def send_to_arduino(arduino, servo_angles):

    values = [
        servo_angles['base_joint'],
        servo_angles['shoulder_joint'],
        servo_angles['elbow_joint'],
        servo_angles['wrist_pitch_joint'],
        servo_angles['wrist_roll_joint']
    ]


    # Example:
    #
    # ANGLES,90.0,75.2,30.1,100.4,0.0
    #

    message = (
        f'ANGLES,'
        f'{values[0]:.2f},'
        f'{values[1]:.2f},'
        f'{values[2]:.2f},'
        f'{values[3]:.2f},'
        f'{values[4]:.2f}\n'
    )


    arduino.write(message.encode())

    print()
    print('Sent to Arduino:')
    print(message.strip())


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Check command-line argument
    # --------------------------------------------------------

    if len(sys.argv) == 2:
        square = sys.argv[1].lower()

        if square not in SQUARES:
            print()
            print(f'ERROR: Unknown square "{square}"')
            print()
            print('Available squares:')
            print(' '.join(sorted(SQUARES.keys())))
            print()
            return

        x_mm, y_mm = SQUARES[square]

    elif len(sys.argv) == 4:
        try:
            x_mm = float(sys.argv[1])
            y_mm = float(sys.argv[2])
            z_mm = float(sys.argv[3])
        except ValueError:
            print('ERROR: X, Y, Z must be numbers.')
            return

    else:
        print()
        print('Usage:')
        print('  ros2 run chess_arm test_square e7')
        print('  ros2 run chess_arm test_square X Y Z')
        print()
        print('Examples:')
        print('  ros2 run chess_arm test_square e7')
        print('  ros2 run chess_arm test_square 100 50 30')
        print()
        return
    


    print()
    print('========================================')
    print('         CHESS SQUARE TEST')
    print('========================================')

    print(
        #f'Square:       {square}'
    )

    print(
        f'Input XYZ:    '
        f'X={x_mm:.1f} mm  '
        f'Y={y_mm:.1f} mm  '
        f'Z={Z_MM:.1f} mm'
    )

    print(
        f'MoveIt XYZ:   '
        f'X={x_mm:.1f} mm  '
        f'Y={(y_mm + Y_OFFSET * 1000):.1f} mm  '
        f'Z={Z_MM:.1f} mm'
    )

    print('========================================')


    # --------------------------------------------------------
    # Open Arduino serial
    # --------------------------------------------------------

    try:

        arduino = serial.Serial(
            SERIAL_PORT,
            BAUD_RATE,
            timeout=1
        )

        # Arduino usually resets when serial connection opens.
        time.sleep(2)

        print(
            f'Connected to Arduino: {SERIAL_PORT}'
        )

    except Exception as e:

        print()
        print(
            f'WARNING: Could not connect to Arduino: {e}'
        )

        print(
            'IK will still be calculated, '
            'but angles will NOT be sent.'
        )

        arduino = None


    # --------------------------------------------------------
    # Start ROS
    # --------------------------------------------------------

    rclpy.init()

    node = IKNode()


    # --------------------------------------------------------
    # Calculate IK
    # --------------------------------------------------------

    if len(sys.argv) == 2:
        z_mm = Z_MM

    joint_state = node.calculate_ik(
        x_mm,
        y_mm,
        z_mm
    )


    if joint_state is None:

        node.destroy_node()

        if arduino:
            arduino.close()

        rclpy.shutdown()

        return


    # --------------------------------------------------------
    # Calculate servo angles
    # --------------------------------------------------------

    servo_angles = calculate_servo_angles(
        joint_state
    )


    print()
    print('ROS joint angles:')
    print()


    for name, position in zip(
        joint_state.name,
        joint_state.position
    ):

        if name in HOME_DEG:

            print(
                f'{name:20s}: '
                f'{math.degrees(position):8.2f}°'
            )


    print()
    print('Physical servo angles:')
    print()


    for name in HOME_DEG:

        if name in servo_angles:

            print(
                f'{name:20s}: '
                f'{servo_angles[name]:8.2f}°'
            )


    # --------------------------------------------------------
    # Send to Arduino
    # --------------------------------------------------------

    if arduino:

        send_to_arduino(
            arduino,
            servo_angles
        )


    print()
    print('========================================')
    print('                 DONE')
    print('========================================')
    print()


    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    node.destroy_node()

    if arduino:
        arduino.close()

    rclpy.shutdown()


if __name__ == '__main__':
    main()

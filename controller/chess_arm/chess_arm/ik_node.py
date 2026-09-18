#!/usr/bin/env python3

import sys
import os
import json
import math
import argparse

import serial
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from moveit_msgs.srv import GetPositionIK

# Order here defines the order angles are sent to the Arduino in, and
# MUST match the Arduino's ANGLES / PNP argument order:
# base, shoulder, elbow, wristPitch, wristRoll
HOME_DEG = {'base_joint': 90, 'shoulder_joint': 90, 'elbow_joint': 0,
            'wrist_pitch_joint': 180, 'wrist_roll_joint': 0}
DIRECTION = {'base_joint': 1, 'shoulder_joint': 1, 'elbow_joint': -1,
             'wrist_pitch_joint': 1, 'wrist_roll_joint': 1}  # placeholders — calibrate these
ERROR_OFFSET = {'base_joint': 0, 'shoulder_joint': 0, 'elbow_joint': -3,
                'wrist_pitch_joint': 10, 'wrist_roll_joint': 0}
Y_OFFSET = 0.044  # 31 mm

JOINT_ORDER = list(HOME_DEG.keys())

DEFAULT_PORT = '/dev/cu.usbserial-1130'
DEFAULT_BAUD = 115200
DEFAULT_SQ_DICT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'sq_dict.json')

# sq_dict.json only stores [x, y] per square (mm) — Z is fixed for all
# board squares. Set this to your actual pick/place height in mm.
Z_MM = 50.0


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
        angles in JOINT_ORDER, or None on failure.
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
            return None

        response = future.result()

        # MoveIt error code
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


def load_sq_dict(path):
    if not os.path.exists(path):
        raise ValueError(f"Square dictionary not found: {path}")

    with open(path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse {path} as JSON: {e}")

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected {path} to contain a JSON object mapping "
            f"square -> [x, y, z], got {type(data).__name__}."
        )

    return data


def lookup_square(sq_dict, square):
    key = square.strip()

    # Be forgiving about case (a1 vs A1).
    if key not in sq_dict:
        if key.lower() in sq_dict:
            key = key.lower()
        elif key.upper() in sq_dict:
            key = key.upper()
        else:
            raise ValueError(
                f"Square '{square}' not found in sq_dict.json "
                f"(available keys look like: "
                f"{list(sq_dict.keys())[:5]}...)"
            )

    value = sq_dict[key]

    # sq_dict.json stores [x, y] only — Z is fixed (Z_MM) for every square.
    if isinstance(value, dict):
        try:
            x = float(value['x'])
            y = float(value['y'])
            z = float(value['z']) if 'z' in value else Z_MM
            return (x, y, z)
        except KeyError as e:
            raise ValueError(
                f"sq_dict.json entry for '{square}' is missing key {e}. "
                f"Got: {value}"
            )
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        x, y = value
        return (float(x), float(y), Z_MM)
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(float(v) for v in value)
    else:
        raise ValueError(
            f"sq_dict.json entry for '{square}' has an unexpected shape: "
            f"{value!r}. Expected [x, y], [x, y, z], or "
            f"{{'x':..,'y':..,'z':..}}."
        )


def parse_command(text, sq_dict_path):
    """
    Accepts either:
      - 'square1 square2'                       -> looked up in sq_dict.json
      - 'square1 square2/x1 y1 z1 x2 y2 z2'      -> coordinates given directly

    Returns (square1, square2, (x1, y1, z1), (x2, y2, z2)).
    """

    text = text.strip()

    if '/' in text:
        squares_part, coords_part = text.split('/', 1)
        squares = squares_part.split()

        if len(squares) != 2:
            raise ValueError(
                "Expected exactly two squares before '/', "
                "e.g. 'e2 e4/150 80 120 160 90 130'"
            )

        coords = coords_part.split()

        if len(coords) != 6:
            raise ValueError(
                "Expected exactly 6 numbers after '/': x1 y1 z1 x2 y2 z2"
            )

        try:
            coords = [float(c) for c in coords]
        except ValueError:
            raise ValueError("X, Y and Z values must be numbers.")

        pos1 = tuple(coords[0:3])
        pos2 = tuple(coords[3:6])

        return squares[0], squares[1], pos1, pos2

    else:
        squares = text.split()

        if len(squares) != 2:
            raise ValueError(
                "Expected format: square1 square2  "
                "(or square1 square2/x1 y1 z1 x2 y2 z2)"
            )

        sq_dict = load_sq_dict(sq_dict_path)

        pos1 = lookup_square(sq_dict, squares[0])
        pos2 = lookup_square(sq_dict, squares[1])

        return squares[0], squares[1], pos1, pos2


def build_pnp_command(angles1, angles2):
    values = angles1 + angles2
    return 'PNP,' + ','.join(f'{v:.1f}' for v in values)


def send_to_arduino(port, baud, command):
    print(f'Connecting to Arduino on {port} @ {baud}...')

    with serial.Serial(port, baud, timeout=5) as ser:
        time.sleep(2)  # allow Arduino to reset after opening the port
        ser.reset_input_buffer()

        print(f'Sending: {command}')
        ser.write((command + '\n').encode())

        # Read replies until we see PNP DONE or we time out.
        deadline = time.time() + 30

        while time.time() < deadline:
            line = ser.readline().decode(errors='replace').strip()

            if not line:
                continue

            print(f'Arduino: {line}')

            if line == 'PNP DONE' or line.startswith('ERROR'):
                break


def main(args=None):

    parser = argparse.ArgumentParser(
        description='Compute IK for two chess squares/positions and '
                     'send a pick-and-place command to the Arduino.'
    )
    parser.add_argument(
        'command', nargs='*',
        help="square1 square2  OR  "
             "square1 square2/x1 y1 z1 x2 y2 z2 "
             "(e.g. 'e2 e4'  or  'e2 e4/150 80 120 160 90 130')"
    )
    parser.add_argument('--port', default=DEFAULT_PORT,
                         help=f'Arduino serial port (default: {DEFAULT_PORT})')
    parser.add_argument('--baud', type=int, default=DEFAULT_BAUD,
                         help=f'Serial baud rate (default: {DEFAULT_BAUD})')
    parser.add_argument('--sq-dict', default=DEFAULT_SQ_DICT,
                         help='Path to sq_dict.json '
                              f'(default: {DEFAULT_SQ_DICT})')
    parser.add_argument('--dry-run', action='store_true',
                         help='Compute IK and print the PNP command '
                              'without opening the serial port.')

    parsed_args = parser.parse_args(args=args)

    if parsed_args.command:
        text = ' '.join(parsed_args.command)
    else:
        text = input('Enter: square1 square2/x1 y1 z1 x2 y2 z2\n> ')

    try:
        sq1, sq2, pos1, pos2 = parse_command(text, parsed_args.sq_dict)
    except ValueError as e:
        print(f'Input error: {e}')
        return

    rclpy.init(args=None)

    node = IKNode()

    print(f'\nSolving IK for move {sq1} -> {sq2}')

    angles1 = node.calculate_ik(*pos1)
    angles1[4] = 180
    if angles1 is None:
        print(f'IK failed for position 1 ({sq1}): {pos1}')
        node.destroy_node()
        rclpy.shutdown()
        return

    angles2 = node.calculate_ik(*pos2)
    angles2[4] = 180
    if angles2 is None:
        print(f'IK failed for position 2 ({sq2}): {pos2}')
        node.destroy_node()
        rclpy.shutdown()
        return

    node.destroy_node()
    rclpy.shutdown()

    pnp_command = build_pnp_command(angles1, angles2)
    print(f'\nPNP command: {pnp_command}')

    if parsed_args.dry_run:
        print('(--dry-run set: not sending to Arduino)')
        return

    try:
        send_to_arduino(parsed_args.port, parsed_args.baud, pnp_command)
    except serial.SerialException as e:
        print(f'Serial error: {e}')
        print('Check --port (e.g. /dev/ttyUSB0, /dev/ttyACM0, COM3) '
              'and that nothing else has it open (e.g. Arduino Serial Monitor).')


if __name__ == '__main__':
    main()
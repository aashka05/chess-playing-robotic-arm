#!/usr/bin/env python3

import sys
import os
import json
import time

import serial

# Project root on the path so the vision package can be imported.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from vision.move_detection import main as move_detection_main

# angles_dict.json key format: "<square> <piece_initial>", e.g. "a1 p".
# Value format: [motor0, motor3, motor2, motor1]  (that specific order).
#
# motor4 (wristRoll) is always fixed at 180.
# motor5 (gripper) is driven separately by the pick/place sequence below.

# JSON array index -> physical servo index.
# angles_dict value [v0, v1, v2, v3] means:
#   servo 0 (base)       = v0
#   servo 3 (wristPitch) = v1
#   servo 2 (elbow)      = v2
#   servo 1 (shoulder)   = v3

JSON_MOTOR_ORDER = [0, 3, 2, 1]

WRIST_ROLL_FIXED = 180.0  # motor 4, always fixed for now

GRIPPER_ANGLES = {
    'p': (70, 88),  # pawn: open, grip
    'n': (70, 95),  # knight: open, grip
    'b': (65, 85),  # bishop: open, grip
    'r': (65, 85),  # rook: open, grip
    'q': (65, 85),  # queen: open, grip
    'k': (65, 85),  # king: open, grip
}

# Don't change - matches your working setup.
PORT = '/dev/cu.usbserial-2130'
BAUD = 115200

DEFAULT_ANGLES_DICT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'angles_dict.json'
)


def load_angles_dict(path):
    if not os.path.exists(path):
        raise ValueError(f"Angles dictionary not found: {path}")

    with open(path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse {path} as JSON: {e}")

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected {path} to contain a JSON object mapping "
            f"'square piece' -> [v0, v1, v2, v3], got {type(data).__name__}."
        )

    return data


def lookup_angles(angles_dict, square, piece):
    # key = f"{square.strip().lower()} {piece.strip().lower()}"
    key = f"{square.strip().lower()}"

    value = angles_dict[key]

    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(
            f"angles_dict.json entry for '{key}' has an unexpected shape: "
            f"{value!r}. Expected 4 values [motor0, motor3, motor2, motor1]."
        )

    # Build the 5 arm servo angles in ARDUINO order:
    # base, shoulder, elbow, wristPitch, wristRoll
    arm_angles = [0.0] * 5

    for json_index, servo_index in enumerate(JSON_MOTOR_ORDER):
        arm_angles[servo_index] = float(value[json_index])

    arm_angles[4] = WRIST_ROLL_FIXED  # motor4 always fixed

    return arm_angles


def parse_command(text):
    """
    Accepts:
      '<square> p <piece>'   -> pick from square
      '<square> k <piece>'   -> place onto square
      '<square1> <square2> <piece>' -> pick at square1, then place at square2

    Returns a list of ops, each ('pick' | 'place', square, piece).
    """

    tokens = text.strip().split()

    if len(tokens) != 3:
        raise ValueError(
            "Expected format: '<square> p <piece>', "
            "'<square> k <piece>', or '<square1> <square2> <piece>' "
            "(e.g. 'a1 p n'  or  'a1 a2 n')"
        )

    first, second, piece = tokens

    if second.lower() in ('p', 'k'):
        # Single pick or single place.
        square = first
        mode = 'pick' if second.lower() == 'p' else 'place'
        return [(mode, square, piece)]
    else:
        # Two squares given -> pick at first, place at second.
        square1, square2 = first, second
        return [('pick', square1, piece), ('place', square2, piece)]


def build_seq_command(mode, arm_angles, piece):
    """
    SEQ,g0,base,shoulder,elbow,wristPitch,wristRoll,g1

    pick:  g0 = piece-specific open angle, g1 = piece-specific grip angle
    place: g0 = -1 (skip pre-move step), g1 = piece-specific open angle
    """

    try:
        gripper_open, gripper_grip = GRIPPER_ANGLES[piece.strip().lower()]
    except KeyError:
        raise ValueError(f"Unsupported piece '{piece}'. Expected p, n, b, r, q, or k.")

    if mode == 'pick':
        g0 = gripper_open
        g1 = gripper_grip
    else:  # 'place'
        g0 = -1
        g1 = gripper_open

    values = [g0] + arm_angles + [g1]
    return 'SEQ,' + ','.join(f'{v:.1f}' for v in values)


def send_command(ser, command):
    print(f'Sending: {command}')
    ser.reset_input_buffer()
    ser.write((command + '\n').encode())

    deadline = time.time() + 30

    while time.time() < deadline:
        line = ser.readline().decode(errors='replace').strip()

        if not line:
            continue

        print(f'Arduino: {line}')

        if line == 'SEQ DONE' or line.startswith('ERROR'):
            return line

    print('(Timed out waiting for a reply from the Arduino.)')
    return None

def mirror_square(square):
    f, r = square.strip().lower()
    f = chr(ord('a') + ord('h') - ord(f))
    r = str(9 - int(r))
    return f + r

def get_command_text(parsed_args):
    # Mode 1: single arg that is an existing file -> run vision pipeline
    if len(parsed_args) == 1 and os.path.isfile(parsed_args[0]):
        robot_arm_move = move_detection_main(parsed_args[0])

        if not robot_arm_move:
            raise ValueError("Vision pipeline returned no move.")
            
        return ' '.join(robot_arm_move)

    # Mode 2: manual move on the CLI (original behaviour), e.g. "e2 e3 p"
    if parsed_args:
        return ' '.join(parsed_args)

    # Mode 3: no args -> interactive prompt (original behaviour)
    return input(
        "Enter: '<square> p <piece>'  or  '<square> k <piece>'  or  "
        "'<square1> <square2> <piece>'\n> "
    )


def main(args=None):
    parsed_args = args if args is not None else sys.argv[1:]

    try:
        text = get_command_text(parsed_args)
        ops = parse_command(text)
        print("Ops:", ops)
        ops = [(mode, mirror_square(square), piece) for mode, square, piece in ops]
        angles_dict = load_angles_dict(DEFAULT_ANGLES_DICT)

        resolved = []
        for mode, square, piece in ops:
            arm_angles = lookup_angles(angles_dict, square, piece)
            resolved.append((mode, square, piece, arm_angles))
    except (ValueError, FileNotFoundError) as e:
        print(f'Input error: {e}')
        return


    try:
        print(f'Connecting to Arduino on {PORT} @ {BAUD}...')

        with serial.Serial(PORT, BAUD, timeout=5) as ser:
            time.sleep(2)  # allow Arduino to reset after opening the port

            for mode, square, piece, arm_angles in resolved:
                print(f'\n{mode.upper()} at {square} (piece={piece}): '
                      f'{[f"{a:.1f}" for a in arm_angles]}')

                command = build_seq_command(mode, arm_angles, piece)
                result = send_command(ser, command)

                if result is not None and result.startswith('ERROR'):
                    print('Stopping: Arduino reported an error.')
                    return

    except serial.SerialException as e:
        print(f'Serial error: {e}')
        print(f'Check that {PORT} is correct and not already open '
              f'elsewhere (e.g. Arduino Serial Monitor).')


if __name__ == '__main__':
    main()

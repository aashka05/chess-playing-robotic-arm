#!/usr/bin/env python3
"""Minimal serial smoke-test for chess_arm_controller.

Opens the port, waits for the Arduino's READY, sends ONE safe move
(servo 5 / gripper: 90 -> 85, a 5-degree nudge), and prints every response.

Run this BEFORE the full chess script to confirm that serial communication
works independently of all chess / IK logic.

Usage:
    python test_serial.py
    python test_serial.py --port /dev/cu.usbserial-110
"""

import serial, sys, time

# -- configuration -----------------------------------------------------------
PORT = "/dev/cu.usbserial-130"   # change if needed, or pass --port <name>
BAUD = 115200

# Safe test move: servo 5 (gripper), 90 -> 85  (5 degrees, no arm motion)
TEST_CMD = "M 15 5:85"

READY_TIMEOUT_S = 30   # seconds to wait for READY after boot
ACK_TIMEOUT_S   = 15   # seconds to wait for DONE/ERR after command
# ----------------------------------------------------------------------------

for i, arg in enumerate(sys.argv[1:], 1):
    if arg == "--port" and i < len(sys.argv) - 1:
        PORT = sys.argv[i + 1]
    elif arg.startswith("--port="):
        PORT = arg.split("=", 1)[1]


def hr(label=""):
    print(f"{'─'*50} {label}")


hr("test_serial.py")
print(f"Port : {PORT}")
print(f"Baud : {BAUD}")
print(f"Cmd  : {TEST_CMD!r}")
hr()

# -- open port ---------------------------------------------------------------
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
except Exception as e:
    print(f"FAIL  Could not open port: {e}")
    print("      Check: correct port name, USB cable, driver installed.")
    sys.exit(1)

print(f"OK    Port opened: {PORT}")
print("      Waiting 2 s for Arduino reset ...")
time.sleep(2)

# -- wait for READY ----------------------------------------------------------
print("      Waiting for READY (will also ping P) ...")
deadline = time.time() + READY_TIMEOUT_S
ready = False
while time.time() < deadline:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print(f"  <- {line!r}")
    if line == "READY":
        ready = True
        break
    print("  -> 'P' (ping)")
    ser.write(b"P\n")
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print(f"  <- {line!r}")
    if line == "READY":
        ready = True
        break

if not ready:
    print(f"FAIL  Arduino did not send READY within {READY_TIMEOUT_S} s.")
    print("      Check: firmware uploaded, Serial Monitor closed, baud=115200.")
    ser.close()
    sys.exit(1)

print("OK    Arduino is READY.")
hr()

# -- send test command --------------------------------------------------------
print(f"  -> {TEST_CMD!r}")
ser.write((TEST_CMD + "\n").encode())

deadline = time.time() + ACK_TIMEOUT_S
got_ack = False
while time.time() < deadline:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print(f"  <- {line!r}")
    if line == "DONE":
        got_ack = True
        break
    if line == "ERR":
        print("FAIL  Arduino replied ERR -- command was not parsed correctly.")
        print("      With #define DEBUG 1 in the firmware you will see PARSED lines above.")
        ser.close()
        sys.exit(1)

hr()
if got_ack:
    print("OK    Communication test PASSED -- servo 5 moved to 85 deg.")
    print("      If the gripper did NOT physically move, check:")
    print("        * External servo power supply connected and switched on")
    print("        * Common GND between Arduino/PCA9685 and power supply")
    print("        * PCA9685 I2C address is 0x40 (all ADDR pins to GND)")
    print("        * SDA/SCL wires from Arduino to PCA9685")
    print("        * Servo signal wire plugged into PCA9685 channel 5")
else:
    print(f"FAIL  No DONE received within {ACK_TIMEOUT_S} s.")
    print("      Upload firmware, check I2C wiring, close Serial Monitor.")

ser.close()

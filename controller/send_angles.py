import json, math, sys, time
import serial

PORT = "/dev/cu.usbserial-130"
BAUD = 115200
SQUARES_FILE = "angles_dict.json"

L1, L2, L3 = 103.0, 150.0, 185.0
S1, S2, S3 = -1, 1, 1
LIFT = 50.0          # mm: clearance above the square (5 cm)
STEP_MM = 3.0
ROLL_OFFSET = 0      # wrist roll = base angle + this (0 -> same as base)
RELEASE_AT_END = True

# JSON value order → servo index mapping.
# angles_dict.json: [servo0 (base), servo3 (wristPitch), servo2 (elbow), servo1 (shoulder)]
JSON_MOTOR_ORDER = [0, 3, 2, 1]

# Servo 5 (gripper) angles — sole source of truth for gripper positions.
# Format: piece_letter -> (open_angle, grip_angle)
GRIPPER_ANGLES = {
    'p': (70, 88),  # pawn: open, grip
    'n': (70, 95),  # knight: open, grip
    'b': (65, 85),  # bishop: open, grip
    'r': (65, 85),  # rook: open, grip
    'q': (65, 85),  # queen: open, grip
    'k': (65, 85),  # king: open, grip
}
HOME = [95, 180, 70, 80, 90, 90]
VERTICAL = 180       # wrist angle (deg) when the wrist link points straight down

cur = HOME[:]
ser = None

# ---------------------------------------------------------------------------
# DEBUG / DRY_RUN — flip these flags to aid troubleshooting.
#
#   DEBUG    True → print every TX command and every non-empty RX line.
#            Set False for normal operation (no extra console noise).
#            Also enabled by the --debug CLI flag.
#
#   DRY_RUN  True → skip serial entirely; just print what *would* be sent.
#            Useful for validating servo-angle logic without hardware.
#            Also enabled by the --dry-run CLI flag.
# ---------------------------------------------------------------------------
DEBUG   = False
DRY_RUN = False

# ---------------------------------------------------------------------------
# MOVE_MODE — change this single value to switch motion strategies.
#
#   1  Simultaneous  — all servos start and finish together.  Each servo's
#                      speed is proportional to its own angular travel, so
#                      every joint arrives at the same time (synchronised).
#   2  Grouped       — existing behaviour: servo5 first, then {servo0, servo4}
#                      together, then {servo1, servo2, servo3} together.
#                      Reversed on retract / return moves.
#   3  Sequential    — one servo at a time: 5 → 0 → 4 → 3 → 2 → 1.
#                      Reversed on retract: 1 → 2 → 3 → 4 → 0 → 5.
#
# The Arduino firmware is UNCHANGED — all mode logic lives here in Python.
# ---------------------------------------------------------------------------
MOVE_MODE = 3

# Servo grouping used by modes 2 and 3.
# Mode 2 moves each inner list simultaneously.
# Mode 3 flattens this to one servo per step.
_GROUP_ORDER = [[5], [0, 4], [1, 2, 3]]  # forward (extend / pick)
_SEQ_ORDER   = [5, 0, 4, 3, 2, 1]        # flattened forward sequence


def connect():
    """Open the serial port and wait for the Arduino to signal readiness.

    The firmware emits "READY" once at power-on (end of setup) and again in
    response to a "P" ping.  We read any buffered data first; if we don't
    see READY we send a ping and try once more.

    BUG FIX: the previous version called reset_input_buffer() at the start of
    every loop iteration, which could silently wipe the Arduino's startup READY
    message just before readline() ran.  Removing that call fixes the race.

    Note: Arduino setup() takes ~6.5 s (500 ms + 6 × 1000 ms servo delays)
    before it prints READY.  The 2-second sleep covers the reset/boot phase;
    the 30-second deadline covers the full servo-init delay.
    """
    global ser
    if DRY_RUN:
        print("[DRY-RUN] connect() skipped — no serial port opened.")
        return

    print(f"[connect] Opening {PORT} at {BAUD} baud …")
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print("[connect] Waiting 2 s for Arduino reset …")
    time.sleep(2)

    deadline = time.time() + 30
    while time.time() < deadline:
        # Try to read a line already in the buffer (e.g. the startup READY).
        line = ser.readline().decode(errors="ignore").strip()
        if DEBUG and line:
            print(f"[RX] {line!r}")
        if line == "READY":
            print("[connect] Arduino ready.")
            return
        # Nothing useful yet — send a ping and wait one more second.
        if DEBUG:
            print("[TX] P (ping)")
        ser.write(b"P\n")
        line = ser.readline().decode(errors="ignore").strip()
        if DEBUG and line:
            print(f"[RX] {line!r}")
        if line == "READY":
            print("[connect] Arduino ready.")
            return

    raise RuntimeError(
        "Arduino not responding after 30 s.\n"
        "Check: correct COM port, baud 115200, firmware uploaded, "
        "Serial Monitor closed, USB cable."
    )


def send(cmd):
    """Write *cmd* (no newline) to the serial port and block until "DONE".

    The firmware replies "DONE" on success and "ERR" on any parse failure.
    Non-protocol lines (e.g. debug prints) are silently skipped so that
    adding Serial.print() statements to the firmware doesn't break Python.

    With DEBUG=True every TX command and every non-empty RX line is printed.
    With DRY_RUN=True the command is only printed, never sent.
    """
    if DEBUG or DRY_RUN:
        print(f"[TX] {cmd}")
    if DRY_RUN:
        return   # skip actual serial I/O

    ser.write((cmd + "\n").encode())
    deadline = time.time() + 60
    while time.time() < deadline:
        line = ser.readline().decode(errors="ignore").strip()
        if DEBUG and line:
            print(f"[RX] {line!r}")
        if line == "DONE":
            return
        if line == "ERR":
            raise RuntimeError(f"Arduino rejected command: {cmd!r}")
    raise RuntimeError(
        f"Timeout (60 s) waiting for DONE.\n"
        f"  Command was: {cmd!r}\n"
        "  Check: firmware running, I2C/PCA9685 wired and at address 0x40, "
        "Serial Monitor closed."
    )


def _build_move_cmd(angles, delay=15, indices=None):
    """Build an M-command string for the new firmware protocol.

    Format:  "M <delay_ms> <idx>:<angle> [...]"

    If *indices* is None, all servo channels 0-5 are included.
    If *indices* is a list/set of ints, only those channels are included.
    """
    if indices is None:
        indices = range(len(angles))
    pairs = " ".join(f"{i}:{angles[i]}" for i in indices)
    return f"M {delay} {pairs}"


def move_sync(angles, delay=15, indices=None):
    """Send one M-command: the listed servos (default: all) move simultaneously.

    *angles* is always the full 6-element list so *cur* stays consistent.
    *indices* restricts which channels are included in the wire command,
    letting modes 2 and 3 send only the servos that actually change in
    each stage without re-sending the unchanged ones.
    """
    send(_build_move_cmd(angles, delay, indices))
    cur[:] = angles


# ---------------------------------------------------------------------------
# Mode implementations  (all logic in Python; Arduino is unaware of modes)
# ---------------------------------------------------------------------------

def _move_mode1(angles, delay=15):
    """Mode 1 — simultaneous move; all servos finish at the same time.

    Python scales the per-step delay by (max_travel / 90) and issues a single
    M-command.  The Arduino's moveSubset then linearly interpolates all servos
    over that travel distance, so every joint arrives together.

    Streaming individual waypoints from Python was considered but rejected:
    each waypoint would require a full serial round-trip, adding latency and
    fragility without any benefit over the Arduino's built-in interpolation.
    """
    changed = [i for i in range(len(angles)) if angles[i] != cur[i]]
    if not changed:
        return
    diffs = [abs(angles[i] - cur[i]) for i in changed]
    max_diff = max(diffs)
    scaled_delay = max(1, int(round(delay * max_diff / 90)))
    move_sync(angles, scaled_delay, indices=changed)


def _move_mode2(angles, delay=15, reverse=False):
    """Mode 2 — original grouped sequence.

    Forward:  servo5 → {servo0, servo4} → {servo1, servo2, servo3}
    Reverse:  {servo1, servo2, servo3} → {servo0, servo4} → servo5

    Only the servos in each group that actually need to move are included
    in the M-command, so unchanged channels are never re-sent.
    """
    groups = _GROUP_ORDER if not reverse else list(reversed(_GROUP_ORDER))
    intermediate = list(cur)
    for group in groups:
        changed = [idx for idx in group if intermediate[idx] != angles[idx]]
        if not changed:
            continue
        for idx in group:
            intermediate[idx] = angles[idx]
        move_sync(intermediate[:], delay, indices=changed)


def _move_mode3(angles, delay=15, reverse=False):
    """Mode 3 — fully sequential, one servo at a time.

    Forward:  5 → 0 → 4 → 3 → 2 → 1
    Reverse:  1 → 2 → 3 → 4 → 0 → 5

    Each M-command contains exactly one idx:angle pair.
    """
    seq = _SEQ_ORDER if not reverse else list(reversed(_SEQ_ORDER))
    intermediate = list(cur)
    for idx in seq:
        if intermediate[idx] == angles[idx]:
            continue  # skip servos already at their target
        intermediate[idx] = angles[idx]
        move_sync(intermediate[:], delay, indices=[idx])


def move(angles, delay=15, reverse=False):
    """Dispatch to the active MOVE_MODE handler.

    *reverse* signals a retract/return motion so modes 2 and 3 can run
    their servo sequences in reverse order.  Mode 1 ignores *reverse*.
    """
    if MOVE_MODE == 1:
        _move_mode1(angles, delay)
    elif MOVE_MODE == 2:
        _move_mode2(angles, delay, reverse=reverse)
    elif MOVE_MODE == 3:
        _move_mode3(angles, delay, reverse=reverse)
    else:
        raise ValueError(f"Unknown MOVE_MODE: {MOVE_MODE}")


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------

def gripper(angle):
    """Move servo 5 (gripper) to *angle*; leave all other servos alone."""
    target = cur[:5] + [angle]
    move_sync(target, 20, indices=[5])


def at_home():
    return cur[:5] == HOME[:5]


def fk(s):
    a1 = math.radians(S1 * (s[1] - 90))
    a2 = a1 + math.radians(S2 * s[2])
    a3 = a2 + math.radians(S3 * s[3])
    return L1 * math.sin(a1) + L2 * math.sin(a2), L1 * math.cos(a1) + L2 * math.cos(a2), math.degrees(a3)


def tip(s):
    r, z, a3 = fk(s)
    t = math.radians(a3)
    return (s[0], r + L3 * math.sin(t), z + L3 * math.cos(t), a3)


def pose(st):
    """Servo angles (integers) for tip at (r, z) with the wrist link at angle a3."""
    base, r, z, a3 = st
    t = math.radians(a3)
    pr, pz = r - L3 * math.sin(t), z - L3 * math.cos(t)
    c = (pr * pr + pz * pz - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if abs(c) > 1:
        raise ValueError(f"unreachable: r={pr:.1f} z={pz:.1f}")
    th = math.acos(c)
    a1 = math.atan2(pr, pz) - math.atan2(L2 * math.sin(th), L1 + L2 * math.cos(th))
    a1d = math.degrees(a1)

    # Round shoulder and elbow first, then solve the wrist from the ROUNDED values
    # so the wrist-link angle is exact (not off by accumulated rounding error).
    s1 = int(round(90 + a1d / S1))
    s2 = int(round(math.degrees(th) / S2))
    a2d = S1 * (s1 - 90) + S2 * s2
    s3 = int(round((a3 - a2d) / S3))

    # Build the 6-element output: servo 4 derived from servo 0; servo 5 (gripper)
    # left at its current value — only pick_place / gripper() may change it.
    p = [int(round(base)), s1, s2, s3, int(round(base + ROLL_OFFSET)), cur[5]]
    if any(v < 0 or v > 180 for v in p):
        raise ValueError(f"servo out of range: {p}")
    return p


def plan_path(p0, p1):
    """Compute every waypoint's servo angles up front (raises before any motion)."""
    dist = math.hypot(p1[1] - p0[1], p1[2] - p0[2])
    n = max(1, math.ceil(max(dist / STEP_MM, abs(p1[0] - p0[0]) / 2, abs(p1[3] - p0[3]) / 2)))
    return [pose([p0[k] + (p1[k] - p0[k]) * (i / n) for k in range(4)]) for i in range(1, n + 1)]


def run_path(poses, delay=15, reverse=False):
    for p in poses:
        move(p, delay, reverse=reverse)


def move_path(p0, p1, delay=15, reverse=False):
    run_path(plan_path(p0, p1), delay, reverse=reverse)


def lift():
    """Straight up by LIFT mm, wrist kept vertical.  Skipped at home.

    Lifting is always a retract motion, so modes 2 and 3 run their sequences
    in reverse order (arm retracts safely before swinging back).
    """
    if at_home():
        return
    b, r, z, _ = tip(cur)
    move_path(tip(cur), (b, r, z + LIFT, VERTICAL), reverse=True)


def taught(v):
    """Convert a JSON angles list to a 6-element servo-index-ordered list.

    Applies JSON_MOTOR_ORDER to map [servo0, servo3, servo2, servo1] values
    to their correct servo positions, derives servo 4 from servo 0, and
    appends the current gripper angle (servo 5) unchanged.
    """
    arm = [0] * 5
    for json_index, servo_index in enumerate(JSON_MOTOR_ORDER):
        arm[servo_index] = v[json_index]
    arm[4] = arm[0] - 5   # servo 4 always = servo 0 + ROLL_OFFSET
    return arm + [cur[5]]           # servo 5 (gripper) preserved from current state


def goto(v):
    dest = taught(v)
    b, r, z, _ = tip(dest)
    hover = (b, r, z + LIFT, VERTICAL)
    bottom = (b, r, z, VERTICAL)

    # Validate the hover pose and the descent before moving anything.
    hover_pose = pose(hover)
    descent = plan_path(hover, bottom)

    if at_home():
        move(hover_pose, 20, reverse=False)   # extend from home: forward sequence
    else:
        lift()
        move_path(tip(cur), hover, reverse=False)
    run_path(descent, 20, reverse=False)      # descend: forward sequence
    move(dest, 20, reverse=False)


def home():
    lift()
    target = HOME[:5] + [cur[5]]
    # Only send channels that aren't already at home; servo 5 is never changed here.
    changed = [i for i in range(5) if cur[i] != target[i]]
    if changed:
        move_sync(target, 20, indices=changed)   # direct move, no perpendicularity constraint


def pick_place(squares, start, end, piece="p"):
    g_open, g_grip = GRIPPER_ANGLES[piece]
    gripper(g_open)
    goto(squares[start])
    gripper(g_grip)
    goto(squares[end])
    if RELEASE_AT_END:
        gripper(g_open)


def check(squares):
    for name, v in squares.items():
        d = taught(v)
        _, r, z, a3 = tip(d)
        p = pose((d[0], r, z, VERTICAL))
        print(f"{name}: tip r={r:.0f} z={z:.0f} wrist={a3:.0f}  vertical pose={p[:4]}  taught={d[:4]}")


def main():
    global DEBUG, DRY_RUN

    # Strip flag arguments before positional parsing.
    raw = sys.argv[1:]
    if "--debug"   in raw: DEBUG   = True
    if "--dry-run" in raw: DRY_RUN = True
    args = [a for a in raw if a not in ("--debug", "--dry-run")]

    squares = json.load(open(SQUARES_FILE))
    if args and args[0] == "check":
        check(squares)
        return
    if args == ["home"]:
        connect()
        try:
            home()
        finally:
            if ser:
                ser.close()
        return
    rest = [a.lower() for a in args[2:]]
    go_home = "home" in rest
    pieces = [a for a in rest if a != "home"]
    piece = pieces[0] if pieces else "p"
    if len(args) < 2 or len(pieces) > 1 or piece not in GRIPPER_ANGLES:
        print("usage: python send_angles.py <start> <end> [piece p|n|b|r|q|k] [home] [--debug] [--dry-run]")
        return
    connect()
    try:
        pick_place(squares, args[0], args[1], piece)
        if go_home:
            home()
    finally:
        if ser:
            ser.close()


if __name__ == "__main__":
    main()

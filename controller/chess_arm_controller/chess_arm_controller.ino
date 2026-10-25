#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN  120   // unchanged
#define SERVOMAX  520   // unchanged

const int NUM_SERVOS = 6;

// ---------------------------------------------------------------------------
// DEBUG — set to 1 to enable verbose serial logging (GOT / PARSED / DONE).
// Set to 0 for normal operation.  Single flag; no other code changes needed.
// ---------------------------------------------------------------------------
#define DEBUG 0

// Home pose — mirrors Python HOME list exactly.
int currentAngle[NUM_SERVOS] = {95, 180, 70, 80, 90, 90};

// ---------------------------------------------------------------------------
// angleToPulse
// ---------------------------------------------------------------------------
int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

// ---------------------------------------------------------------------------
// moveSubset — simultaneously interpolate only the servos listed in indices[].
//
// All listed servos start and finish together: each servo's step size is
// proportional to its own travel so they all arrive at the same time
// (time-proportional interpolation, same algorithm as the old moveSync).
//
//  targets[]  target angle for each entry in indices[]
//  indices[]  which servo channels to move (0-5)
//  count      number of valid entries in the two arrays
//  stepDelay  milliseconds to wait between each interpolation step
// ---------------------------------------------------------------------------
void moveSubset(const int targets[], const int indices[], int count, int stepDelay) {
  int startAngle[NUM_SERVOS];
  int targetAngle[NUM_SERVOS];
  int maxDist = 0;

  // Seed from current position; override only the requested channels.
  for (int i = 0; i < NUM_SERVOS; i++) {
    startAngle[i]  = currentAngle[i];
    targetAngle[i] = currentAngle[i];
  }
  for (int k = 0; k < count; k++) {
    int ch = indices[k];
    if (ch < 0 || ch >= NUM_SERVOS) continue;
    targetAngle[ch] = constrain(targets[k], 0, 180);
    maxDist = max(maxDist, abs(targetAngle[ch] - startAngle[ch]));
  }

  if (maxDist == 0) return;   // all servos already at target

  for (int s = 1; s <= maxDist; s++) {
    for (int k = 0; k < count; k++) {
      int ch = indices[k];
      if (ch < 0 || ch >= NUM_SERVOS) continue;
      int a = startAngle[ch] + (long)(targetAngle[ch] - startAngle[ch]) * s / maxDist;
      if (a != currentAngle[ch]) {
        currentAngle[ch] = a;
        pwm.setPWM(ch, 0, angleToPulse(a));
      }
    }
    delay(stepDelay);
  }

  // Snap to exact target to eliminate integer-rounding residual.
  for (int k = 0; k < count; k++) {
    int ch = indices[k];
    if (ch < 0 || ch >= NUM_SERVOS) continue;
    if (currentAngle[ch] != targetAngle[ch]) {
      currentAngle[ch] = targetAngle[ch];
      pwm.setPWM(ch, 0, angleToPulse(targetAngle[ch]));
    }
  }
}

// ---------------------------------------------------------------------------
// setup
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);   // baud rate unchanged
  pwm.begin();
  pwm.setPWMFreq(50);     // 50 Hz — standard for analogue servos
  delay(500);

  // Drive servos to home in reverse-index order (safe start).
  for (int i = NUM_SERVOS - 1; i >= 0; i--) {
    pwm.setPWM(i, 0, angleToPulse(currentAngle[i]));
    delay(1000);
  }

  Serial.println("READY");
}

// ---------------------------------------------------------------------------
// loop
// ---------------------------------------------------------------------------
void loop() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  char cmd = line.charAt(0);

  // --- P: ping ---
  if (cmd == 'P') {
    Serial.println("READY");
    return;
  }

  // --- M: move ---
  //   "M <delay_ms> <idx>:<angle> [<idx>:<angle> ...]"
  if (cmd == 'M') {
    int targets[NUM_SERVOS];
    int indices[NUM_SERVOS];
    int count     = 0;
    int stepDelay = 15;
    bool parseOk  = true;

#if DEBUG
    Serial.print("GOT: "); Serial.println(line);
#endif

    const char *p = line.c_str() + 1;   // skip 'M'

    // First token: delay_ms
    char *endPtr;
    stepDelay = (int)strtol(p, &endPtr, 10);
    if (endPtr == p) { Serial.println("ERR"); return; }
    p = endPtr;

    // Subsequent tokens: idx:angle pairs
    while (*p != '\0' && count < NUM_SERVOS) {
      while (*p == ' ' || *p == '\t') p++;
      if (*p == '\0') break;

      int idx = (int)strtol(p, &endPtr, 10);
      if (endPtr == p) { parseOk = false; break; }
      p = endPtr;

      if (*p != ':') { parseOk = false; break; }
      p++;   // skip ':'

      int angle = (int)strtol(p, &endPtr, 10);
      if (endPtr == p) { parseOk = false; break; }
      p = endPtr;

      if (idx < 0 || idx >= NUM_SERVOS) { parseOk = false; break; }
      indices[count] = idx;
      targets[count] = angle;
      count++;

#if DEBUG
      Serial.print("  PARSED servo "); Serial.print(idx);
      Serial.print(" -> "); Serial.println(angle);
#endif
    }

    if (!parseOk || count == 0) { Serial.println("ERR"); return; }

    moveSubset(targets, indices, count, stepDelay);
    Serial.println("SEQ DONE");
    return;
  }

  // --- unknown command ---
  Serial.println("ERROR");
}
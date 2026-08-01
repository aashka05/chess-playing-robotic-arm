#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN 120
#define SERVOMAX 520

const int NUM_SERVOS = 6;

// Home position
int currentAngle[NUM_SERVOS] = {
  97,   // Servo 0
  180,  // Servo 1
  120,  // Servo 2
  0,    // Servo 3
  180,  // Servo 4
  90    // Servo 5
};

int homeAngle[NUM_SERVOS] = {
  97,
  180,
  120,
  0,
  180,
  90
};

int angleToPulse(int angle)
{
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void moveServoSmooth(int servo, int targetAngle)
{
  targetAngle = constrain(targetAngle, 0, 180);

  int step = (targetAngle > currentAngle[servo]) ? 1 : -1;

  while (currentAngle[servo] != targetAngle)
  {
    currentAngle[servo] += step;
    pwm.setPWM(servo, 0, angleToPulse(currentAngle[servo]));
    delay(15);
  }
}

// Move one servo in sequence
void moveJoint(int servo, int angle)
{
  Serial.print("Servo ");
  Serial.print(servo);
  Serial.print(" -> ");
  Serial.println(angle);

  moveServoSmooth(servo, angle);
  delay(300);
}

// -------------------------
// HOME
// -------------------------
void goHome()
{
  Serial.println("Returning Home");

  // Reverse-safe order
  moveJoint(1, 180);
  moveJoint(2, 120);
  moveJoint(3, 0);
  moveJoint(0, 97);
  moveJoint(5, 90);
  moveJoint(4, 180);
}

// -------------------------
// PICKUP AT e2
// -------------------------
void moveToE2()
{
  Serial.println("Moving to e2");

  // EXACT ORDER PROVIDED
  moveJoint(5, 70);
  moveJoint(0, 97);
  moveJoint(1, 170);
  moveJoint(2, 137);
  moveJoint(3, 0);
  moveJoint(4, 180);

  Serial.println("Pickup pawn");
  // Close gripper here if needed.
}

// -------------------------
// PLACE AT e4
// -------------------------
void moveToE4()
{
  Serial.println("Moving to e4");

  // EXACT ORDER PROVIDED
  moveJoint(5, 90);
  moveJoint(3, 30);
  moveJoint(0, 98);
  moveJoint(2, 130);
  moveJoint(1, 140);
  moveJoint(4, 180);
  moveJoint(5, 70);

  Serial.println("Placed pawn");

  goHome();
}

void setup()
{
  Serial.begin(9600);

  pwm.begin();
  pwm.setPWMFreq(50);
  delay(500);

  // Initialize at home
  for (int i = NUM_SERVOS - 1; i >= 0; i--)
  {
    pwm.setPWM(i, 0, angleToPulse(homeAngle[i]));
    delay(500);
  }

  Serial.println();
  Serial.println("Commands:");
  Serial.println("e2");
  Serial.println("e4");
}

void loop()
{
  if (Serial.available())
  {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.equalsIgnoreCase("e2"))
    {
      moveToE2();
    }
    else if (cmd.equalsIgnoreCase("e4"))
    {
      moveToE4();
    }
    else
    {
      Serial.println("Unknown command.");
    }
  }
}
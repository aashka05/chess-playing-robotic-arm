#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN 120
#define SERVOMAX 520

const int NUM_SERVOS = 6;

// Current angle of each servo
int currentAngle[NUM_SERVOS] = {
  97,   // Servo 0
  180,  // Servo 1
  120,  // Servo 2
  0,    // Servo 3
  180,  // Servo 4
  90    // Servo 5
};

int angleToPulse(int angle)
{
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

// Smooth movement
void moveServoSmooth(int servo, int targetAngle)
{
  targetAngle = constrain(targetAngle, 0, 180);

  int step = (targetAngle > currentAngle[servo]) ? 1 : -1;

  while (currentAngle[servo] != targetAngle)
  {
    currentAngle[servo] += step;
    pwm.setPWM(servo, 0, angleToPulse(currentAngle[servo]));
    delay(15);     // Increase for slower movement (20-30 ms)
  }
}

void setup()
{
  Serial.begin(9600);

  pwm.begin();
  pwm.setPWMFreq(50);
  delay(500);

  // Move all servos to home position
  for (int i = NUM_SERVOS-1; i >= 0; i--)
  {
    pwm.setPWM(i, 0, angleToPulse(currentAngle[i]));
    delay(1000);
  }

  Serial.println("--------------------------------");
  Serial.println("Servo Controller Ready");
  Serial.println("Enter:");
  Serial.println("servo_number angle");
  Serial.println("Example:");
  Serial.println("4 90");
  Serial.println("--------------------------------");
}

void loop()
{
  if (Serial.available())
  {
    int servo = Serial.parseInt();
    int angle = Serial.parseInt();

    while (Serial.available())
      Serial.read();

    if (servo >= 0 && servo < NUM_SERVOS &&
        angle >= 0 && angle <= 180)
    {
      Serial.print("Moving Servo ");
      Serial.print(servo);
      Serial.print(" to ");
      Serial.print(angle);
      Serial.println(" degrees");

      moveServoSmooth(servo, angle);
    }
    else
    {
      Serial.println("Invalid input.");
      Serial.println("Format: servo_number angle");
      Serial.println("Example: 2 135");
    }
  }
}
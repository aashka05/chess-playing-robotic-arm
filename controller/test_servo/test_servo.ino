#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN 120
#define SERVOMAX 520

#define GRIPPER_SERVO 5

int angleToPulse(int angle)
{
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void setup()
{
  Serial.begin(9600);

  pwm.begin();
  pwm.setPWMFreq(50);

  Serial.println("Gripper Control");
  Serial.println("Enter an angle (0-180):");
}

void loop()
{
  if (Serial.available())
  {
    int angle = Serial.parseInt();

    if (angle >= 0 && angle <= 360)
    {
      int pulse = angleToPulse(angle);
      pwm.setPWM(GRIPPER_SERVO, 0, pulse);

      Serial.print("Moved to ");
      Serial.print(angle);
      Serial.println(" degrees");
    }
    else
    {
      Serial.println("Invalid angle! Enter 0-180.");
    }

    // Clear remaining characters (newline, etc.)
    while (Serial.available())
      Serial.read();
  }
}
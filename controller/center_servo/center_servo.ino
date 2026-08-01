#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN 120
#define SERVOMAX 520

#define SERVO_COUNT 6

int angleToPulse(int angle)
{
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void setup()
{
  Serial.begin(9600);

  pwm.begin();
  pwm.setPWMFreq(50);   // Standard servo frequency

  delay(1000);

  int pulse = angleToPulse(45);  // Center position

  for (int i = 0; i < SERVO_COUNT; i++)
  {
    pwm.setPWM(i, 0, pulse);

    Serial.print("Servo ");
    Serial.print(i);
    Serial.println(" set to 90 degrees");
    
    delay(200);
  }

  Serial.println("All servos centered");
}

void loop()
{
  // Hold position
}
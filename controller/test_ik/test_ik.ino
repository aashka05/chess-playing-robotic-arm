#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN 120
#define SERVOMAX 520

const int NUM_SERVOS = 6;
const int UPDATE_INTERVAL = 30;

float currentAngle[NUM_SERVOS] = {
  95,
  180,
  70,
  80,
  180,
  90
};

int angleToPulse(float angle)
{
  angle = constrain(angle, 0, 180);
  return map((int)round(angle), 0, 180, SERVOMIN, SERVOMAX);
}

void moveAllServos(
  float base,
  float shoulder,
  float elbow,
  float wristPitch
)
{
  float target[4] = {
    constrain(base, 0, 180),
    constrain(shoulder, 0, 180),
    constrain(elbow, 0, 180),
    constrain(wristPitch, 0, 180)
  };

  bool moving = true;

  while (moving)
  {
    moving = false;

    for (int i = 0; i < 4; i++)
    {
      if (currentAngle[i] != target[i])
      {
        if (currentAngle[i] < target[i])
          currentAngle[i] += 1;
        else
          currentAngle[i] -= 1;

        if (
          (currentAngle[i] < target[i] && currentAngle[i] > target[i]) ||
          (currentAngle[i] > target[i] && currentAngle[i] < target[i])
        )
        {
          currentAngle[i] = target[i];
        }

        if (abs(currentAngle[i] - target[i]) < 1)
          currentAngle[i] = target[i];

        pwm.setPWM(
          i,
          0,
          angleToPulse(currentAngle[i])
        );

        moving = true;
      }
    }

    delay(UPDATE_INTERVAL);
  }
}

void processManualCommand()
{
  int servo = Serial.parseInt();
  int angle = Serial.parseInt();

  while (Serial.available())
    Serial.read();

  if (
    servo >= 0 &&
    servo < NUM_SERVOS &&
    angle >= 0 &&
    angle <= 180
  )
  {
    float step = (angle > currentAngle[servo]) ? 1 : -1;

    while (currentAngle[servo] != angle)
    {
      currentAngle[servo] += step;

      pwm.setPWM(
        servo,
        0,
        angleToPulse(currentAngle[servo])
      );

      delay(UPDATE_INTERVAL);
    }
  }
  else
  {
    Serial.println("Invalid input.");
    Serial.println("Format: servo_number angle");
    Serial.println("Example: 2 135");
  }
}

void setup()
{
  Serial.begin(115200);

  pwm.begin();
  pwm.setPWMFreq(50);

  delay(500);

  moveAllServos(
    95,
    180,
    70,
    80
  );

  pwm.setPWM(
    4,
    0,
    angleToPulse(180)
  );

  pwm.setPWM(
    5,
    0,
    angleToPulse(90)
  );

  Serial.println("--------------------------------");
  Serial.println("Servo Controller Ready");
  Serial.println();
  Serial.println("IK command:");
  Serial.println("ANGLES,base,shoulder,elbow,wristPitch,wristRoll");
  Serial.println();
  Serial.println("Example:");
  Serial.println("ANGLES,90,75,30,100,180");
  Serial.println();
  Serial.println("Manual command:");
  Serial.println("servo_number angle");
  Serial.println("Example: 2 135");
  Serial.println("--------------------------------");
}

void loop()
{
  if (Serial.available())
  {
    if (Serial.peek() == 'A')
    {
      String command = Serial.readStringUntil('\n');
      command.trim();

      if (command.startsWith("ANGLES,"))
      {
        command.remove(0, 7);

        float angles[5];

        int index = 0;
        int start = 0;

        while (index < 5)
        {
          int comma = command.indexOf(',', start);

          String value;

          if (comma == -1)
            value = command.substring(start);
          else
            value = command.substring(start, comma);

          angles[index] = value.toFloat();

          index++;

          if (comma == -1)
            break;

          start = comma + 1;
        }

        bool valid = true;

        for (int i = 0; i < 5; i++)
        {
          if (
            angles[i] < 0 ||
            angles[i] > 180
          )
          {
            valid = false;
          }
        }

        if (valid)
        {
          moveAllServos(
            angles[0],
            angles[1],
            angles[2],
            angles[3]
          );
        }
        else
        {
          Serial.println("ERROR: Invalid ANGLES command.");
        }
      }
      else
      {
        Serial.println("ERROR: Unknown command.");
      }
    }
    else
    {
      processManualCommand();
    }
  }
}
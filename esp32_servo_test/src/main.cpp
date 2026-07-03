/*
 * Basic servo test for ESP32-S3 DevKitC.
 *
 * Control it from the PC over USB with serial_control.html (Web Serial), or
 * from any serial monitor at 115200 baud.
 *
 * Wiring (small servo, e.g. SG90, powered from the board for a quick test):
 *   Servo signal (orange/yellow) -> GPIO 4
 *   Servo VCC    (red)           -> 5V pin on the DevKitC
 *   Servo GND    (brown/black)   -> GND pin
 *
 * Commands (one per line):
 *   90        set angle to 90 degrees (any number 0-180)
 *   A<deg>    set angle, e.g. A135
 *   +<step>   nudge up by step (default 5), e.g. +10
 *   -<step>   nudge down by step (default 5)
 *   C         center (90)
 *   S         start sweep
 *   X         stop sweep
 *   ?         report current angle
 */

#include <Arduino.h>
#include <ESP32Servo.h>

static const int SERVO_PIN = 4;
static const int SERVO_MIN_US = 500;   // pulse width at 0 degrees
static const int SERVO_MAX_US = 2400;  // pulse width at 180 degrees

Servo servo;
int angle = 90;
bool sweeping = false;
int sweepDir = 1;
const int SWEEP_STEP = 2;
const unsigned long SWEEP_INTERVAL_MS = 20;
unsigned long lastSweep = 0;
String buf;

void applyAngle(int a) {
  angle = constrain(a, 0, 180);
  servo.write(angle);
}

void report() {
  Serial.print("POS ");
  Serial.println(angle);
}

void handleLine(String line) {
  line.trim();
  if (!line.length()) return;

  char c = line.charAt(0);
  if (c >= '0' && c <= '9') {  // bare number -> absolute angle
    sweeping = false;
    applyAngle(line.toInt());
    report();
    return;
  }

  c = toupper(c);
  String rest = line.substring(1);
  rest.trim();
  switch (c) {
    case 'A': sweeping = false; applyAngle(rest.toInt()); report(); break;
    case '+': sweeping = false; applyAngle(angle + (rest.length() ? rest.toInt() : 5)); report(); break;
    case '-': sweeping = false; applyAngle(angle - (rest.length() ? rest.toInt() : 5)); report(); break;
    case 'C': sweeping = false; applyAngle(90); report(); break;
    case 'S': sweeping = true; Serial.println("SWEEP on"); break;
    case 'X': sweeping = false; Serial.println("SWEEP off"); break;
    case '?': report(); break;
    default:  Serial.print("ERR "); Serial.println(line); break;
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  ESP32PWM::allocateTimer(0);
  servo.setPeriodHertz(50);
  servo.attach(SERVO_PIN, SERVO_MIN_US, SERVO_MAX_US);
  applyAngle(90);
  Serial.println("READY esp32 servo on GPIO 4 @115200");
  Serial.println("Cmds: <0-180>, A<deg>, +<step>, -<step>, C(center), S(sweep), X(stop), ?(status)");
}

void loop() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (buf.length()) {
        handleLine(buf);
        buf = "";
      }
    } else if (buf.length() < 40) {
      buf += ch;
    }
  }

  if (sweeping && millis() - lastSweep >= SWEEP_INTERVAL_MS) {
    lastSweep = millis();
    int next = angle + sweepDir * SWEEP_STEP;
    if (next >= 180) {
      next = 180;
      sweepDir = -1;
    } else if (next <= 0) {
      next = 0;
      sweepDir = 1;
    }
    applyAngle(next);
    static int rc = 0;
    if (++rc % 10 == 0) report();  // throttle position spam during sweep
  }
}

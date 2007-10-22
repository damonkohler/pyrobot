int led_pin = 13;
int power_pin = 12;
int power_sensor = 11;
int flashlight_pin = 10;
int relay_pin = 9;
int val;

void setup()
{
  Serial.begin(9600);
  pinMode(power_pin, OUTPUT);
  pinMode(flashlight_pin, OUTPUT);
  pinMode(led_pin, OUTPUT);
  pinMode(relay_pin, OUTPUT);
  pinMode(power_sensor, INPUT);
}

void loop()
{
  if (Serial.available()) {
    val = Serial.read();
    digitalWrite(led_pin, HIGH);
    delay(100);
    digitalWrite(led_pin, LOW);
    if (val == 'P') {
      digitalWrite(power_pin, LOW);
      digitalWrite(power_pin, HIGH);
      delay(100);
      digitalWrite(power_pin, LOW);
    }
    if (val == 'S') {
      if (digitalRead(power_sensor) == HIGH) {
        Serial.print(1);
      } else {
        Serial.print(0);
      }
    }
    if (val == 'L') {
      digitalWrite(flashlight_pin, HIGH);
    }
    if (val == 'D') {
      digitalWrite(flashlight_pin, LOW);
    }
    if (val == 'R') {
      digitalWrite(relay_pin, HIGH);
    }
    if (val == 'V') {
      digitalWrite(relay_pin, LOW);
    }
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(13, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    digitalWrite(13, HIGH);
    Serial.print("ECHO: ");
    Serial.println(c);
    delay(10);
    digitalWrite(13, LOW);
  }
}

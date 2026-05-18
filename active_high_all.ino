void setup() {
  for (int i = 2; i <= 13; i++) {
    pinMode(i, OUTPUT);
    digitalWrite(i, HIGH);
  }
  pinMode(A0, OUTPUT); digitalWrite(A0, HIGH);
  pinMode(A1, OUTPUT); digitalWrite(A1, HIGH);
  pinMode(A2, OUTPUT); digitalWrite(A2, HIGH);
  pinMode(A3, OUTPUT); digitalWrite(A3, HIGH);
}

void loop() {
  // Stay high
}

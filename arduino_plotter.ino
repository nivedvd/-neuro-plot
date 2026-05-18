// Optimization: Removed Stepper.h for direct pin control and C-string parsing
// Reduces overhead and memory usage.

// --- CONFIGURATION ---
#define STEPS_PER_REV 2048
#define Z_LIFT_STEPS 300
// Speed control: Delay in microseconds between steps.
// Lower = faster. 28BYJ-48 limit ~1200us.
// 2500us is a safe, high-torque speed for most hardware.
#define STEP_DELAY_MICROS 2500 

// --- PINS ---
// X Axis (Moved to Pins 4,5,6,7)
const int pinX[4] = {4, 5, 6, 7};
// Y Axis (Temporary shift to Analog for testing)
const int pinY[4] = {A0, A1, A2, A3};
// Z Axis (Disabled for now to save power)
const int pinZ[4] = {A4, A5, 2, 3};

// --- STATE ---
int stepIndexX = 0;
int stepIndexY = 0;
int stepIndexZ = 0;

// Buffer for serial data
const int MAX_CMD_LEN = 32;
char cmdBuffer[MAX_CMD_LEN];
int bufPos = 0;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  // Startup Blink: 3 fast blinks
  for(int i=0; i<3; i++) {
    digitalWrite(LED_BUILTIN, HIGH); delay(100);
    digitalWrite(LED_BUILTIN, LOW);  delay(100);
  }

  Serial.begin(9600);
  
  // Setup pins
  for(int i=0; i<4; i++) {
    pinMode(pinX[i], OUTPUT);
    pinMode(pinY[i], OUTPUT);
    pinMode(pinZ[i], OUTPUT);
  }

  // Lift pen (Safety: Disabled auto-move on startup to prevent crashes)
  // moveZ(Z_LIFT_STEPS);
  Serial.println("Plotter ready");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n') {
      digitalWrite(LED_BUILTIN, HIGH); // LED ON processing
      cmdBuffer[bufPos] = '\0'; // Terminate string
      processCommand();
      bufPos = 0; // Reset buffer
      digitalWrite(LED_BUILTIN, LOW);  // LED OFF done
    } else {
      if (bufPos < MAX_CMD_LEN - 1) {
        cmdBuffer[bufPos++] = c;
      }
    }
  }
}

void processCommand() {
  if (bufPos == 0) return;
  
  // Parse command (MOVE x y, PEN UP, PEN DOWN, STOP)
  // Simple parsing to avoid heavy String object
  
  if (strncmp(cmdBuffer, "MOVE", 4) == 0) {
    int dx, dy;
    if (sscanf(cmdBuffer, "MOVE %d %d", &dx, &dy) == 2) {
      drawLine(dx, dy);
      disableMotors(); // Save power and heat
      Serial.println("OK");
    } else {
      Serial.println("ERROR");
    }
  } 
  else if (strncmp(cmdBuffer, "STEPZ", 5) == 0) {
    int steps;
    if (sscanf(cmdBuffer, "STEPZ %d", &steps) == 1) {
      moveZ(steps);
      Serial.println("OK");
    } else {
      Serial.println("ERROR");
    }
  }
  else if (strcmp(cmdBuffer, "PEN UP") == 0) {
    moveZ(Z_LIFT_STEPS);
    Serial.println("OK");
  } 
  else if (strcmp(cmdBuffer, "PEN DOWN") == 0) {
    moveZ(-Z_LIFT_STEPS);
    Serial.println("OK");
  } 
  else if (strcmp(cmdBuffer, "STOP") == 0) {
    disableMotors();
    Serial.println("STOPPED");
    while(1);
  }
  else if (strcmp(cmdBuffer, "PING") == 0) {
    // Distinct blink for PING
    digitalWrite(LED_BUILTIN, LOW); delay(50);
    digitalWrite(LED_BUILTIN, HIGH); delay(50);
    digitalWrite(LED_BUILTIN, LOW); delay(50);
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.println("PONG");
  }
  else {
    Serial.println("ERROR");
  }
}

// Low-level stepper sequence (Standard 4-step sequence for 28BYJ-48)
void oneStep(const int pins[4], int dir, int *stepIndex) {
  // Update step index
  *stepIndex += dir;
  if (*stepIndex > 3) *stepIndex = 0;
  if (*stepIndex < 0) *stepIndex = 3;
  
  // 4-step sequence: 1010, 0110, 0101, 1001
  switch(*stepIndex) {
    case 0: // 1010
      digitalWrite(pins[0], 1); digitalWrite(pins[1], 0);
      digitalWrite(pins[2], 1); digitalWrite(pins[3], 0);
      break;
    case 1: // 0110
      digitalWrite(pins[0], 0); digitalWrite(pins[1], 1);
      digitalWrite(pins[2], 1); digitalWrite(pins[3], 0);
      break;
    case 2: // 0101
      digitalWrite(pins[0], 0); digitalWrite(pins[1], 1);
      digitalWrite(pins[2], 0); digitalWrite(pins[3], 1);
      break;
    case 3: // 1001
      digitalWrite(pins[0], 1); digitalWrite(pins[1], 0);
      digitalWrite(pins[2], 0); digitalWrite(pins[3], 1);
      break;
  }
}

void drawLine(int dx, int dy) {
  long x0 = 0, y0 = 0;
  long x1 = dx, y1 = dy;
  long dx_abs = abs(dx), dy_abs = -abs(dy);
  long sx = (x0 < x1) ? 1 : -1;
  long sy = (y0 < y1) ? 1 : -1;
  long err = dx_abs + dy_abs;
  
  while(true) {
    if (x0 == x1 && y0 == y1) break;
    long e2 = 2 * err;
    if (e2 >= dy_abs) { err += dy_abs; x0 += sx; oneStep(pinX, sx, &stepIndexX); }
    if (e2 <= dx_abs) { err += dx_abs; y0 += sy; oneStep(pinY, sy, &stepIndexY); }
    delayMicroseconds(STEP_DELAY_MICROS);
  }
}

void moveZ(int steps) {
  int dir = (steps > 0) ? 1 : -1;
  steps = abs(steps);
  for(int i=0; i<steps; i++) {
    oneStep(pinZ, dir, &stepIndexZ);
    delayMicroseconds(STEP_DELAY_MICROS);
  }
}

void disableMotors() {
  // Disable all motor pins: X (4-7), Y (A0-A3), Z (A4, A5, 2, 3)
  int allPins[] = {4, 5, 6, 7, A0, A1, A2, A3, A4, A5, 2, 3};
  for(int i=0; i<12; i++) digitalWrite(allPins[i], 0);
}

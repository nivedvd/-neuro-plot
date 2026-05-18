/**
 * Neuro Plot - Pro Calibration & Safety Firmware v3.0
 * 
 * Safety Features:
 * - Software Limits: Prevents moving past 0 to 100mm (safety fence)
 * - Absolute Z-Tracking: Prevents pen drift (climbing/falling)
 * - Symmetry Fix: UP/DOWN movements are perfectly matched
 */

// --- CALIBRATION ---
float SMM_X = 89.8; 
float SMM_Y = 89.8; 
long LIMIT_X_MM = 140;
long LIMIT_Y_MM = 140;
long LIMIT_X_STEPS = LIMIT_X_MM * (long)SMM_X; // 0 to 140mm
long LIMIT_Y_STEPS = LIMIT_Y_MM * (long)SMM_Y; // 0 to 140mm

// --- CONFIGURATION ---
int Z_LIFT_STEPS = 250;    
int STEP_DELAY_MIN = 1200; 
int STEP_DELAY_MAX = 2500; 

// --- PINS ---
const int pinX[4] = {2, 3, 4, 5};   
const int pinY[4] = {8, 9, 10, 11}; 
const int pinZ[4] = {A0, A1, A2, A3};

// --- STATE ---
int stepIndexX = 0, stepIndexY = 0, stepIndexZ = 0;
long curX = 0, curY = 0; // Absolute position tracking
int curZ_State = 0;      // 0 = Down, 1 = Up (Absolute Tracking)

void setup() {
  Serial.begin(9600);
  for(int i=0; i<4; i++) {
    pinMode(pinX[i], OUTPUT); digitalWrite(pinX[i], 0);
    pinMode(pinY[i], OUTPUT); digitalWrite(pinY[i], 0);
    pinMode(pinZ[i], OUTPUT); digitalWrite(pinZ[i], 0);
  }
  delay(1000);
  Serial.println("Plotter ready"); 
}

void loop() {
  if (Serial.available() > 0) {
    char cmd[64];
    int len = Serial.readBytesUntil('\n', cmd, sizeof(cmd) - 1);
    if (len > 0) {
      cmd[len] = '\0';
      while(len > 0 && (cmd[len-1] == '\r' || cmd[len-1] == ' ' || cmd[len-1] == '\n')) cmd[--len] = '\0';

      if (strstr(cmd, "PING") != NULL) {
        Serial.println("PONG");
      } 
      else if (strcmp(cmd, "PEN UP") == 0) {
        if (curZ_State == 0) { 
          Serial.println("Moving pen UP...");
          moveZ(Z_LIFT_STEPS); 
          curZ_State = 1; 
          Serial.println("OK - Pen is UP");
        } else {
          Serial.println("OK - Pen already UP");
        }
        disableXY();
      } 
      else if (strcmp(cmd, "PEN DOWN") == 0) {
        if (curZ_State == 1) { 
          Serial.println("Moving pen DOWN...");
          moveZ(-Z_LIFT_STEPS); 
          curZ_State = 0; 
          Serial.println("OK - Pen is DOWN");
        } else {
          Serial.println("OK - Pen already DOWN");
        }
        disableXY();
      } 
      else if (strncmp(cmd, "MOVE", 4) == 0) {
        handleMove(cmd);
        disableXY();
      } 
      else if (strcmp(cmd, "HOME") == 0) {
        // Return to absolute zero safely
        moveSmooth(-curX, -curY);
        disableXY();
        Serial.println("OK");
      } 
      else if (strcmp(cmd, "ZERO") == 0) {
        curX = 0; curY = 0; curZ_State = 0; // Reset absolute markers
        Serial.println("OK");
      } 
      else if (strncmp(cmd, "SETZ", 4) == 0) {
        int steps = 0;
        if (sscanf(cmd, "SETZ %d", &steps) == 1) { Z_LIFT_STEPS = steps; Serial.println("OK"); }
        else Serial.println("ERROR");
      }
      else if (strncmp(cmd, "CALIB", 5) == 0) { // CALIB [StepsPerMM]
        float smm = 0;
        if (sscanf(cmd, "CALIB %f", &smm) == 1) {
          SMM_X = smm;
          SMM_Y = smm;
          LIMIT_X_STEPS = LIMIT_X_MM * (long)SMM_X;
          LIMIT_Y_STEPS = LIMIT_Y_MM * (long)SMM_Y;
          Serial.println("OK");
        } else Serial.println("ERROR");
      }
      else if (strncmp(cmd, "SPEED", 5) == 0) {
        int val = 0;
        if (sscanf(cmd, "SPEED %d", &val) == 1) { if (val > 0) STEP_DELAY_MIN = 1000000L / val; Serial.println("OK"); }
        else Serial.println("ERROR");
      } 
      else if (strcmp(cmd, "STATUS") == 0) {
        Serial.print("Position: X="); Serial.print(curX); 
        Serial.print(" Y="); Serial.print(curY);
        Serial.print(" Z_State="); Serial.println(curZ_State == 0 ? "DOWN" : "UP");
        Serial.println("OK");
      }
      else if (strcmp(cmd, "FORCE UP") == 0) {
        // Force pen up regardless of state
        Serial.println("FORCING pen UP...");
        moveZ(Z_LIFT_STEPS);
        curZ_State = 1;
        disableXY();
        Serial.println("OK - Forced UP");
      }
      else if (strcmp(cmd, "FORCE DOWN") == 0) {
        // Force pen down regardless of state
        Serial.println("FORCING pen DOWN...");
        moveZ(-Z_LIFT_STEPS);
        curZ_State = 0;
        disableXY();
        Serial.println("OK - Forced DOWN");
      }
      else if (strcmp(cmd, "TEST Z") == 0) {
        // Test Z-axis motor - move up then down
        Serial.println("Testing Z motor...");
        moveZ(Z_LIFT_STEPS);
        delay(500);
        moveZ(-Z_LIFT_STEPS);
        Serial.println("OK");
      }
      else if (strcmp(cmd, "DISABLE") == 0) {
        disableAll();
        Serial.println("OK");
      }
    }
  }
}

void handleMove(char* cmd) {
  long dx = 0, dy = 0;
  if (sscanf(cmd, "MOVE %ld %ld", &dx, &dy) == 2) {
    // 🛑 SOFTWARE LIMITS
    // Calculate targeting absolute position
    long targetX = curX + dx;
    long targetY = curY + dy;
    
    // Safety Force: Prevent moving past boundaries
    if (targetX < 0) dx = -curX;
    if (targetX > LIMIT_X_STEPS) dx = LIMIT_X_STEPS - curX;
    
    if (targetY < 0) dy = -curY;
    if (targetY > LIMIT_Y_STEPS) dy = LIMIT_Y_STEPS - curY;
    
    if (dx != 0 || dy != 0) moveSmooth(dx, dy);
    Serial.println("OK");
  } else {
    Serial.println("ERROR");
  }
}

void halfStep(const int pins[4], int dir, int *idx) {
  *idx += dir;
  if (*idx > 7) *idx = 0;
  if (*idx < 0) *idx = 7;
  switch(*idx) {
    case 0: digitalWrite(pins[0], 1); digitalWrite(pins[1], 0); digitalWrite(pins[2], 0); digitalWrite(pins[3], 0); break;
    case 1: digitalWrite(pins[0], 1); digitalWrite(pins[1], 1); digitalWrite(pins[2], 0); digitalWrite(pins[3], 0); break;
    case 2: digitalWrite(pins[0], 0); digitalWrite(pins[1], 1); digitalWrite(pins[2], 0); digitalWrite(pins[3], 0); break;
    case 3: digitalWrite(pins[0], 0); digitalWrite(pins[1], 1); digitalWrite(pins[2], 1); digitalWrite(pins[3], 0); break;
    case 4: digitalWrite(pins[0], 0); digitalWrite(pins[1], 0); digitalWrite(pins[2], 1); digitalWrite(pins[3], 0); break;
    case 5: digitalWrite(pins[0], 0); digitalWrite(pins[1], 0); digitalWrite(pins[2], 1); digitalWrite(pins[3], 1); break;
    case 6: digitalWrite(pins[0], 0); digitalWrite(pins[1], 0); digitalWrite(pins[2], 0); digitalWrite(pins[3], 1); break;
    case 7: digitalWrite(pins[0], 1); digitalWrite(pins[1], 0); digitalWrite(pins[2], 0); digitalWrite(pins[3], 1); break;
  }
}

void moveSmooth(long dx, long dy) {
  long steps_x = abs(dx), steps_y = abs(dy);
  long max_steps = max(steps_x, steps_y);
  if (max_steps == 0) return;
  int sx = (dx > 0) ? 1 : -1, sy = (dy > 0) ? 1 : -1;
  float current_delay = STEP_DELAY_MAX;
  long accel_steps = (max_steps > 400) ? 200 : max_steps / 2;
  long dx_abs = (long)steps_x, dy_abs = -(long)steps_y;
  long err = dx_abs + dy_abs;
  for (long i = 0; i < max_steps; i++) {
    if (i < accel_steps) current_delay -= (current_delay - STEP_DELAY_MIN) / (accel_steps - i + 1);
    else if (i > max_steps - accel_steps) current_delay += (STEP_DELAY_MAX - current_delay) / (max_steps - i + 1);
    if (current_delay < STEP_DELAY_MIN) current_delay = STEP_DELAY_MIN;
    long e2 = 2 * err;
    if (e2 >= dy_abs) { err += dy_abs; halfStep(pinX, sx, &stepIndexX); curX += sx; }
    if (e2 <= dx_abs) { err += dx_abs; halfStep(pinY, sy, &stepIndexY); curY += sy; }
    delayMicroseconds((unsigned int)current_delay);
  }
}

void moveZ(int steps) {
  int dir = (steps > 0) ? 1 : -1;
  steps = abs(steps);
  for(int i = 0; i < steps; i++) {
    halfStep(pinZ, dir, &stepIndexZ);
    delayMicroseconds(4000); // Slower for torque (increased from 3000)
  }
  delay(50); // Allow motor to settle
  // Disable Z motor after movement to prevent heating and turn off LED
  for(int i=0; i<4; i++) digitalWrite(pinZ[i], 0);
}

void disableXY() { for(int i=0; i<4; i++) { digitalWrite(pinX[i], 0); digitalWrite(pinY[i], 0); } }
void disableAll() { disableXY(); for(int i=0; i<4; i++) digitalWrite(pinZ[i], 0); }
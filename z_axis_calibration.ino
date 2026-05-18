/**
 * Z-Axis Calibration & Diagnostic Sketch
 * 
 * This sketch allows you to test and calibrate the Z-axis independently.
 * Commands:
 *   ZTEST <steps> <delay_us>  - Move Z by <steps> with <delay_us> microseconds per step
 *   ZSPEED <delay_us>         - Set default Z delay (lower = faster)
 *   ZDIR                      - Flip Z direction
 *   ZPHASE                    - Swap Z phases (fix shaking)
 *   ZMODE                     - Toggle full-step mode (more torque)
 *   ZINFO                     - Print current Z settings
 *   PING                      - Respond with PONG
 * 
 * Example usage:
 *   ZTEST 100 1000            - Move Z down 100 steps at 1000us/step (1kHz)
 *   ZTEST -100 1000           - Move Z up 100 steps at 1000us/step
 *   ZSPEED 800                - Set Z speed to 800us/step (1.25kHz, faster)
 *   ZDIR                      - Flip direction if moving wrong way
 *   ZINFO                     - See current settings
 */

// --- Z-AXIS PINS ---
const int pinZ[4] = {A0, A1, A2, A3};

// --- Z-AXIS STATE ---
int stepIndexZ = 0;
int Z_DIR = 1;           // 1 or -1
bool SWAP_Z = false;     // Swap phases for shaking fix
bool FULL_STEP_Z = false; // Full-step mode for more torque
int Z_DELAY = 1000;      // Default: 1000 us/step = 1 kHz

void setup() {
  Serial.begin(9600);
  for(int i = 0; i < 4; i++) {
    pinMode(pinZ[i], OUTPUT);
    digitalWrite(pinZ[i], 0);
  }
  delay(1000);
  Serial.println("Z-Axis Calibration Ready");
  Serial.println("Commands: ZTEST <steps> <delay>, ZSPEED <delay>, ZDIR, ZPHASE, ZMODE, ZINFO, PING");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd[64];
    int len = Serial.readBytesUntil('\n', cmd, sizeof(cmd) - 1);
    if (len > 0) {
      cmd[len] = '\0';
      // Strip trailing whitespace
      while(len > 0 && (cmd[len-1] == '\r' || cmd[len-1] == ' ' || cmd[len-1] == '\n')) cmd[--len] = '\0';

      if (strstr(cmd, "PING") != NULL) {
        Serial.println("PONG");
      }
      else if (strncmp(cmd, "ZTEST", 5) == 0) {
        int steps = 0, delay_us = 0;
        if (sscanf(cmd, "ZTEST %d %d", &steps, &delay_us) == 2) {
          Serial.print("Moving Z ");
          Serial.print(steps);
          Serial.print(" steps at ");
          Serial.print(delay_us);
          Serial.println(" us/step...");
          moveZ(steps, delay_us);
          Serial.println("OK");
        } else {
          Serial.println("ERROR: ZTEST <steps> <delay_us>");
        }
      }
      else if (strncmp(cmd, "ZSPEED", 6) == 0) {
        int delay_us = 0;
        if (sscanf(cmd, "ZSPEED %d", &delay_us) == 1) {
          Z_DELAY = delay_us;
          Serial.print("Z speed set to ");
          Serial.print(delay_us);
          Serial.println(" us/step");
          Serial.println("OK");
        } else {
          Serial.println("ERROR: ZSPEED <delay_us>");
        }
      }
      else if (strcmp(cmd, "ZDIR") == 0) {
        Z_DIR *= -1;
        Serial.print("Z direction flipped. Z_DIR = ");
        Serial.println(Z_DIR);
        Serial.println("OK");
      }
      else if (strcmp(cmd, "ZPHASE") == 0) {
        SWAP_Z = !SWAP_Z;
        Serial.print("Z phase swap: ");
        Serial.println(SWAP_Z ? "ON" : "OFF");
        Serial.println("OK");
      }
      else if (strcmp(cmd, "ZMODE") == 0) {
        FULL_STEP_Z = !FULL_STEP_Z;
        Serial.print("Z mode: ");
        Serial.println(FULL_STEP_Z ? "FULL-STEP (more torque)" : "HALF-STEP (smoother)");
        Serial.println("OK");
      }
      else if (strcmp(cmd, "ZINFO") == 0) {
        Serial.println("=== Z-Axis Info ===");
        Serial.print("Z_DIR: ");
        Serial.println(Z_DIR);
        Serial.print("Z_DELAY: ");
        Serial.print(Z_DELAY);
        Serial.println(" us/step");
        Serial.print("SWAP_Z: ");
        Serial.println(SWAP_Z ? "ON" : "OFF");
        Serial.print("FULL_STEP_Z: ");
        Serial.println(FULL_STEP_Z ? "ON" : "OFF");
        Serial.print("Current step index: ");
        Serial.println(stepIndexZ);
        Serial.println("OK");
      }
      else {
        Serial.println("ERROR: Unknown command");
      }
    }
  }
}

void halfStep(int dir) {
  int p0 = pinZ[0], p1 = pinZ[1], p2 = pinZ[2], p3 = pinZ[3];
  
  // Handle phase swap
  if (SWAP_Z) { p1 = pinZ[2]; p2 = pinZ[1]; }

  stepIndexZ += dir;
  
  if (FULL_STEP_Z) {
    // Full-step mode (4 steps per cycle, more torque)
    if (stepIndexZ > 3) stepIndexZ = 0;
    if (stepIndexZ < 0) stepIndexZ = 3;
    switch(stepIndexZ) {
      case 0: digitalWrite(p0, 1); digitalWrite(p1, 0); digitalWrite(p2, 0); digitalWrite(p3, 0); break;
      case 1: digitalWrite(p0, 0); digitalWrite(p1, 1); digitalWrite(p2, 0); digitalWrite(p3, 0); break;
      case 2: digitalWrite(p0, 0); digitalWrite(p1, 0); digitalWrite(p2, 1); digitalWrite(p3, 0); break;
      case 3: digitalWrite(p0, 0); digitalWrite(p1, 0); digitalWrite(p2, 0); digitalWrite(p3, 1); break;
    }
  } else {
    // Half-step mode (8 steps per cycle, smoother)
    if (stepIndexZ > 7) stepIndexZ = 0;
    if (stepIndexZ < 0) stepIndexZ = 7;
    switch(stepIndexZ) {
      case 0: digitalWrite(p0, 1); digitalWrite(p1, 0); digitalWrite(p2, 0); digitalWrite(p3, 0); break;
      case 1: digitalWrite(p0, 1); digitalWrite(p1, 1); digitalWrite(p2, 0); digitalWrite(p3, 0); break;
      case 2: digitalWrite(p0, 0); digitalWrite(p1, 1); digitalWrite(p2, 0); digitalWrite(p3, 0); break;
      case 3: digitalWrite(p0, 0); digitalWrite(p1, 1); digitalWrite(p2, 1); digitalWrite(p3, 0); break;
      case 4: digitalWrite(p0, 0); digitalWrite(p1, 0); digitalWrite(p2, 1); digitalWrite(p3, 0); break;
      case 5: digitalWrite(p0, 0); digitalWrite(p1, 0); digitalWrite(p2, 1); digitalWrite(p3, 1); break;
      case 6: digitalWrite(p0, 0); digitalWrite(p1, 0); digitalWrite(p2, 0); digitalWrite(p3, 1); break;
      case 7: digitalWrite(p0, 1); digitalWrite(p1, 0); digitalWrite(p2, 0); digitalWrite(p3, 1); break;
    }
  }
}

void moveZ(int steps, int delay_us) {
  int dir = (steps > 0) ? 1 : -1;
  dir *= Z_DIR;
  steps = abs(steps);
  
  for(int i = 0; i < steps; i++) {
    halfStep(dir);
    delayMicroseconds(delay_us);
  }
}

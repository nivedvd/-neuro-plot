#!/usr/bin/env python3
"""
Z-Axis Calibration Tool
Interactive utility to test and calibrate the Z-axis.

Usage:
  python z_axis_test.py
  
Then use commands like:
  ZTEST 100 1000    - Move Z down 100 steps at 1000 us/step
  ZTEST -100 1000   - Move Z up 100 steps
  ZSPEED 800        - Set Z speed to 800 us/step (faster)
  ZDIR              - Flip Z direction
  ZPHASE            - Swap Z phases (fix shaking)
  ZMODE             - Toggle full-step mode
  ZINFO             - Print Z settings
  help              - Show this help
  exit              - Exit
"""

import serial
import serial.tools.list_ports
import time
import sys

class ZAxisTester:
    def __init__(self, baud=9600):
        self.ser = None
        self.baud = baud
        self.port = None
    
    def connect(self):
        """Find and connect to the Arduino."""
        print("[INFO] Searching for Arduino...")
        ports = list(serial.tools.list_ports.comports())
        
        # Prefer COM3
        preferred = [p for p in ports if p.device.upper() == "COM3"]
        others = [p for p in ports if p not in preferred]
        ordered_ports = preferred + others
        
        for port_info in ordered_ports:
            port = port_info.device
            print(f"[INFO] Trying {port}...")
            try:
                temp_ser = serial.Serial(port, self.baud, timeout=2)
                temp_ser.dtr = False
                time.sleep(0.1)
                temp_ser.dtr = True
                print("[INFO] Waiting for bootloader...")
                time.sleep(4)
                
                temp_ser.reset_input_buffer()
                for _ in range(3):
                    temp_ser.write(b"\nPING\n")
                    start = time.time()
                    while time.time() - start < 1.5:
                        line = temp_ser.readline().decode('utf-8', errors='ignore').strip()
                        if "PONG" in line or "Ready" in line:
                            print(f"[SUCCESS] Connected to {port}")
                            self.ser = temp_ser
                            self.port = port
                            return True
                temp_ser.close()
            except Exception as e:
                print(f"[ERROR] {port}: {e}")
        
        print("[ERROR] Could not find Arduino")
        return False
    
    def send_command(self, cmd):
        """Send a command and get response."""
        if not self.ser or not self.ser.is_open:
            print("[ERROR] Not connected")
            return False
        
        print(f"[SEND] {cmd}")
        self.ser.write((cmd + "\n").encode())
        
        # Read response
        responses = []
        start = time.time()
        while time.time() - start < 3:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"[RECV] {line}")
                    responses.append(line)
                    if line == "OK" or line == "ERROR":
                        break
            except:
                pass
        
        return True
    
    def disconnect(self):
        """Close connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[INFO] Disconnected")

def print_help():
    print(__doc__)

def main():
    tester = ZAxisTester()
    
    if not tester.connect():
        print("[FATAL] Could not connect to Arduino")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Z-AXIS CALIBRATION TOOL")
    print("="*60)
    print_help()
    print("="*60 + "\n")
    
    try:
        while True:
            try:
                cmd = input(">>> ").strip()
            except KeyboardInterrupt:
                print("\n[INFO] Interrupted")
                break
            except EOFError:
                break
            
            if not cmd:
                continue
            
            if cmd.lower() == "exit":
                break
            elif cmd.lower() == "help":
                print_help()
            elif cmd.upper().startswith("ZTEST") or cmd.upper().startswith("ZSPEED") or \
                 cmd.upper() in ["ZDIR", "ZPHASE", "ZMODE", "ZINFO", "PING"]:
                tester.send_command(cmd.upper())
            else:
                print("[ERROR] Unknown command. Type 'help' for usage.")
    
    finally:
        tester.disconnect()

if __name__ == "__main__":
    main()

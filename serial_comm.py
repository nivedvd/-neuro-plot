import serial
import serial.tools.list_ports
import time

class DummySerial:
    def __init__(self):
        self.is_open = True
    def write(self, data):
        pass
    def reset_input_buffer(self):
        pass
    def reset_output_buffer(self):
        pass
    def readline(self):
        # Always return 'OK\n' after a small delay to simulate processing
        time.sleep(0.01)
        return b"OK\n"
    def close(self):
        self.is_open = False

class PlotterSerial:
    def __init__(self, baud=9600):
        self.baud = baud
        self.ser = None

    def connect(self, simulate=False):
        if self.ser and self.ser.is_open:
            print("[SERIAL] Already connected.")
            return True

        if simulate:
            print("[SERIAL] Starting SIMULATION mode.")
            self.ser = DummySerial()
            self.port = "SIMULATION"
            return True

        print("[SERIAL] Searching for plotter...")
        ports = list(serial.tools.list_ports.comports())

        # Prefer COM3 if available
        preferred = [p for p in ports if p.device.upper() == "COM3"]
        others = [p for p in ports if p not in preferred]
        ordered_ports = preferred + others

        for port_info in ordered_ports:
            port = port_info.device
            print(f"[SERIAL] Trying port {port}...")
            try:
                # Connect with a timeout
                temp_ser = serial.Serial(port, self.baud, timeout=2)
                
                # CLONE FIX: Toggle DTR to force reset, then wait longer
                temp_ser.dtr = False
                time.sleep(0.1)
                temp_ser.dtr = True
                print(f"[SERIAL] Waiting 4s for Clone bootloader...")
                time.sleep(4)
                
                # Active handshake: Send PING multiple times
                temp_ser.reset_input_buffer()
                found = False
                for _ in range(3):
                    print("[SERIAL] Sending PING...")
                    temp_ser.write(b"\nPING\n")
                    
                    start_check = time.time()
                    while time.time() - start_check < 1.5:
                        line = temp_ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"[SERIAL] Received from {port}: '{line}'")
                        
                        line_up = line.upper()
                        if "PONG" in line_up or "READY" in line_up or "PLOTTER" in line_up:
                            found = True
                            break
                    if found: break

                if found:
                    print(f"[SERIAL] Plotter found on {port}!")
                    self.ser = temp_ser
                    self.port = port
                    return True
                else:
                    temp_ser.close()
            except serial.SerialException as e:
                print(f"[SERIAL] Could not open port {port}: {e}")
            except Exception as e:
                print(f"[SERIAL] An error occurred on port {port}: {e}")
                if 'temp_ser' in locals() and temp_ser.is_open:
                    temp_ser.close()

        print("[SERIAL] Plotter not found on any port.")
        return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send(self, cmd, timeout=120):
        if self.port == "SIMULATION":
            # Simulation mode delay to mimic hardware
            print(f"[SIM] Executing: {cmd}")
            time.sleep(0.01)
            return True

        if self.ser and self.ser.is_open:
            # Clear input buffer to remove any stale data
            self.ser.reset_input_buffer()
            
            print(f"[SERIAL] Sending: {cmd}")
            self.ser.write((cmd + "\n").encode())
            
            # Block until we receive a response
            start_time = time.time()
            while True:
                try:
                    # Use existing serial timeout (usually 2s) for readline
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                except Exception:
                    line = ""

                # Skip empty lines
                if not line:
                    if time.time() - start_time > timeout:
                        print(f"[SERIAL] Timeout waiting for response to: {cmd}")
                        return False
                    continue
                
                # Print received line for debugging
                if line:
                    print(f"[SERIAL] Received: {line}")
                
                # Check for OK response (can be "OK" or "OK - message")
                if "OK" in line.upper():
                    return True
                elif "ERROR" in line.upper():
                    print(f"[SERIAL] Error executing command: {cmd}")
                    return False
                elif "STOPPED" in line.upper():
                    raise ConnectionError("Plotter Emergency Stop triggered")
                
                # Skip informational messages (like "Moving pen UP...")
                # and continue waiting for OK/ERROR response
                
                # Check for total operation timeout
                if time.time() - start_time > timeout:
                    print(f"[SERIAL] Timeout waiting for response to: {cmd}")
                    return False
        else:
            raise ConnectionError("Plotter is not connected.")

    def move(self, x, y):
        # Apply hardware inversion if configured
        try:
            from config import INVERT_X_AXIS
            if INVERT_X_AXIS:
                x = -x
        except ImportError:
            pass
            
        self.send(f"MOVE {x} {y}")

    def pen_up(self):
        self.send("PEN UP")

    def pen_down(self):
        self.send("PEN DOWN")

    def set_speed(self, speed):
        """Set the maximum plotter speed (steps per second)."""
        self.send(f"SPEED {speed}", timeout=2)

    def set_acceleration(self, accel):
        """Acceleration is handled automatically by Arduino firmware."""
        # Arduino uses built-in acceleration ramping in moveSmooth()
        print("[INFO] Acceleration managed by firmware (auto-ramping)")
        return True

    def set_z_lift(self, steps):
        """Set the number of steps for pen up/down movement."""
        self.send(f"SETZ {steps}", timeout=2)

    def return_to_home(self):
        """Move the plotter back to (0,0) steps."""
        self.send("HOME")

    def zero_position(self):
        """Reset the logical starting point to current physical location."""
        self.send("ZERO")

    def set_calibration(self, steps_per_mm):
        """Send calibration data to hardware."""
        self.send(f"CALIB {steps_per_mm}")
    
    def tool_change(self, tool_number):
        """
        Request a tool/pen change.
        
        Args:
            tool_number: Integer representing the tool (0=black, 1=red, 2=blue, etc.)
        """
        if self.port == "SIMULATION":
            print(f"[SIMULATION] Tool change to tool {tool_number}")
            return True
        
        try:
            # Send tool change command
            self.send(f"T{tool_number}")
            
            # Wait for TOOL_READY acknowledgment (with timeout)
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                if self.ser and self.ser.in_waiting:
                    response = self.ser.readline().decode().strip()
                    if response == "TOOL_READY":
                        return True
                time.sleep(0.1)
            
            print("[WARNING] Tool change timeout - continuing anyway")
            return False
        except Exception as e:
            print(f"[ERROR] Tool change failed: {e}")
            return False

    def emergency_stop(self):
        """Immediately send STOP command and then disconnect."""
        print("[SERIAL] EMERGENCY STOP TRIGGERED!")
        if self.ser and self.ser.is_open:
            try:
                # Force reset buffers and send STOP immediately
                self.ser.reset_output_buffer()
                self.ser.write(b"\nSTOP\n")
                self.ser.flush()
                time.sleep(0.1)
                self.ser.close()
                print("[SERIAL] Stop command sent, connection closed.")
            except Exception as e:
                print(f"[SERIAL] Error during emergency stop: {e}")
                try: self.ser.close() 
                except: pass
        self.ser = None

# --- For backwards compatibility, though not recommended ---
# These functions use a single global instance, which is less flexible.

_global_serial = PlotterSerial()

def connect():
    return _global_serial.connect()

def disconnect():
    _global_serial.disconnect()

def move(x, y):
    _global_serial.move(x,y)

def pen_up():
    _global_serial.pen_up()

def pen_down():
    _global_serial.pen_down()

def emergency_stop():
    _global_serial.emergency_stop()
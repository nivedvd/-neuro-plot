import re

class GCodeTranslator:
    def __init__(self):
        self.gcode_x = 0.0
        self.gcode_y = 0.0
        self.abs_mode = True # G90 default
        
    def reset_home(self):
        self.gcode_x = 0.0
        self.gcode_y = 0.0
        
    def parse_line(self, cmd_line):
        """
        Parses a single line of G-Code and returns a list of plotter commands.
        Returns None if no command or just state change.
        """
        # 1. Strip comments
        cmd_clean = re.sub(r";.*|\(.*\)", "", cmd_line).strip().upper()
        if not cmd_clean: 
            return None, None # (Command, LogMessage)

        # Check for G-code signature
        if not re.match(r"[GM][0-9]", cmd_clean):
            # Pass raw command if not G-code
            return cmd_clean, None
            
        # --- State Commands ---
        if "G90" in cmd_clean:
            self.abs_mode = True
            return None, "Absolute Mode Set"
        elif "G91" in cmd_clean:
            self.abs_mode = False
            return None, "Relative Mode Set"
        elif "G20" in cmd_clean:
            return None, "WARN: Inches not supported"
        elif "G21" in cmd_clean:
            return None, None # MM mode default

        # --- Homing ---
        if "G28" in cmd_clean:
            self.reset_home()
            return "HOME_SEQUENCE", "Homing..." # Special internal flag

        # --- Pen M-Codes ---
        if "M3" in cmd_clean or "M03" in cmd_clean:
            return "PEN DOWN", "Pen Down"
        elif "M5" in cmd_clean or "M05" in cmd_clean:
            return "PEN UP", "Pen Up"
            
        # --- Movement (G0/G1) ---
        elif "G0" in cmd_clean or "G1" in cmd_clean or "G00" in cmd_clean or "G01" in cmd_clean:
            # Extract Params
            x_val = re.search(r"X\s*([-\d.]+)", cmd_clean)
            y_val = re.search(r"Y\s*([-\d.]+)", cmd_clean)
            z_val = re.search(r"Z\s*([-\d.]+)", cmd_clean)
            
            # 1. Handle Z-Axis (Pen Control)
            if z_val:
                z_target = float(z_val.group(1))
                if z_target < 0 or (z_target > 0 and z_target < 5): 
                     cmd = "PEN DOWN" if z_target < 0 else "PEN UP"
                     # If XY also exists, we technically should do Z first or last.
                     # For simplicity, if Z is present, we return Pen command.
                     # (Real parser would queue multiple ops).
                     # Let's see if XY is also here.
                     if not x_val and not y_val:
                         return cmd, f"Z{z_target} -> {cmd}"
            
            # 2. Handle XY Movement
            dx, dy = 0.0, 0.0
            move_needed = False
            
            if x_val:
                target_x = float(x_val.group(1))
                if self.abs_mode:
                    dx = target_x - self.gcode_x
                    self.gcode_x = target_x
                else:
                    dx = target_x
                    self.gcode_x += dx
                move_needed = True
                
            if y_val:
                target_y = float(y_val.group(1))
                if self.abs_mode:
                    dy = target_y - self.gcode_y
                    self.gcode_y = target_y
                else:
                    dy = target_y
                    self.gcode_y += dy
                move_needed = True
                
            if move_needed:
                # Apply Inversion for G-Code translator too
                final_dx = dx
                try:
                    from config import INVERT_X_AXIS
                    if INVERT_X_AXIS:
                        final_dx = -dx
                except ImportError:
                    pass
                    
                return f"MOVE {final_dx:.2f} {dy:.2f}", f"Move d({dx:.2f}, {dy:.2f})"
        
        return None, "Unknown G-Code"

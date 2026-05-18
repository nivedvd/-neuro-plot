"""
Live Preview Canvas for Neuro Plot
Shows real-time plotter movements on a virtual workspace
"""

import tkinter as tk
from theme import THEME

class PreviewCanvas(tk.Canvas):
    def __init__(self, parent, workspace_mm=100, **kwargs):
        """
        Create a live preview canvas for the plotter.
        
        Args:
            parent: Parent widget
            workspace_mm: Size of workspace in millimeters (default 100x100mm)
        """
        # Set default canvas size
        canvas_size = kwargs.pop('width', 400)
        kwargs['height'] = kwargs.get('height', canvas_size)
        kwargs['width'] = canvas_size
        
        # Apply theme
        kwargs['bg'] = kwargs.get('bg', THEME.get('entry_bg', '#2a2a2a'))
        kwargs['highlightthickness'] = kwargs.get('highlightthickness', 0)
        
        super().__init__(parent, **kwargs)
        
        self.workspace_mm = workspace_mm
        self.canvas_size = canvas_size
        self.scale = canvas_size / workspace_mm  # pixels per mm
        
        # Current pen position (in mm)
        self.pen_x = 0
        self.pen_y = 0
        self.pen_down = False
        self.pen_color = THEME.get('accent_color', '#00ff88')  # Default color
        
        # Drawing history
        self.path_lines = []
        
        # Draw initial grid and pen
        self.draw_grid()
        self.pen_marker = self.create_pen_marker()
        
    def draw_grid(self):
        """Draw the workspace grid."""
        # Background
        self.create_rectangle(
            0, 0, self.canvas_size, self.canvas_size,
            fill='#1a1a1a',
            outline=''
        )
        
        # Grid lines every 10mm
        grid_spacing_mm = 10
        grid_spacing_px = grid_spacing_mm * self.scale
        
        # Vertical lines
        for i in range(0, int(self.workspace_mm) + 1, grid_spacing_mm):
            x = i * self.scale
            self.create_line(
                x, 0, x, self.canvas_size,
                fill='#333333',
                width=1
            )
        
        # Horizontal lines
        for i in range(0, int(self.workspace_mm) + 1, grid_spacing_mm):
            y = i * self.scale
            self.create_line(
                0, y, self.canvas_size, y,
                fill='#333333',
                width=1
            )
        
        # Border
        self.create_rectangle(
            1, 1, self.canvas_size-1, self.canvas_size-1,
            outline=THEME.get('accent_color', '#00ff88'),
            width=2
        )
        
        # Origin marker
        origin_size = 6
        self.create_oval(
            -origin_size, -origin_size,
            origin_size, origin_size,
            fill=THEME.get('accent_color', '#00ff88'),
            outline=''
        )
        
    def create_pen_marker(self):
        """Create the pen position marker."""
        x, y = self.mm_to_canvas(self.pen_x, self.pen_y)
        marker_size = 8
        
        return self.create_oval(
            x - marker_size, y - marker_size,
            x + marker_size, y + marker_size,
            fill=THEME.get('error_color', '#ff4444'),
            outline='white',
            width=2
        )
    
    def mm_to_canvas(self, x_mm, y_mm):
        """Convert mm coordinates to canvas pixels."""
        # Don't flip Y axis - keep it consistent with plotter coordinate system
        canvas_x = x_mm * self.scale
        canvas_y = y_mm * self.scale
        return canvas_x, canvas_y
    
    def move_pen(self, dx_mm, dy_mm):
        """
        Move the pen by a relative amount.
        
        Args:
            dx_mm: Change in X (mm)
            dy_mm: Change in Y (mm)
        """
        old_x, old_y = self.pen_x, self.pen_y
        self.pen_x += dx_mm
        self.pen_y += dy_mm
        
        # Draw line if pen is down
        if self.pen_down:
            x1, y1 = self.mm_to_canvas(old_x, old_y)
            x2, y2 = self.mm_to_canvas(self.pen_x, self.pen_y)
            
            line = self.create_line(
                x1, y1, x2, y2,
                fill=self.pen_color,
                width=2,
                capstyle=tk.ROUND
            )
            self.path_lines.append(line)
        
        # Update pen marker position
        x, y = self.mm_to_canvas(self.pen_x, self.pen_y)
        marker_size = 8
        self.coords(
            self.pen_marker,
            x - marker_size, y - marker_size,
            x + marker_size, y + marker_size
        )
        
        # Force update
        self.update_idletasks()
    
    def set_pen_down(self, down):
        """Set pen up or down state."""
        self.pen_down = down
        
        # Change marker color
        if down:
            self.itemconfig(self.pen_marker, fill=self.pen_color)
        else:
            self.itemconfig(self.pen_marker, fill=THEME.get('error_color', '#ff4444'))
    
    def set_pen_color(self, color):
        """Set the pen color for drawing."""
        self.pen_color = color
        # Update marker if pen is down
        if self.pen_down:
            self.itemconfig(self.pen_marker, fill=color)
    
    def reset(self):
        """Clear the canvas and reset to origin."""
        # Remove all drawn lines
        for line in self.path_lines:
            self.delete(line)
        self.path_lines = []
        
        # Reset pen position
        self.pen_x = 0
        self.pen_y = 0
        self.pen_down = False
        
        # Update marker
        x, y = self.mm_to_canvas(0, 0)
        marker_size = 8
        self.coords(
            self.pen_marker,
            x - marker_size, y - marker_size,
            x + marker_size, y + marker_size
        )
        self.itemconfig(self.pen_marker, fill=THEME.get('error_color', '#ff4444'))

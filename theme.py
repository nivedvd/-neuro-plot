# diy cnc/theme.py
import ctypes
import os
import sys

def load_custom_font():
    """
    Loads the Inter font from the 'font' directory on Windows.
    This allows Tkinter to use 'Inter' family.
    """
    try:
        # Determine the base path. If running as a script, it's the script's dir.
        # But this file is imported, so let's rely on relative path to this file.
        base_path = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(base_path, "font", "Inter-VariableFont_opsz,wght.ttf")
        
        if not os.path.exists(font_path):
            print(f"Warning: Font file not found at {font_path}")
            return False

        # Windows GDI AddFontResourceEx
        # FR_PRIVATE  = 0x10
        # FR_NOT_ENUM = 0x20
        FR_PRIVATE = 0x10
        path_buf = ctypes.create_unicode_buffer(font_path)
        add_font_resource_ex = ctypes.windll.gdi32.AddFontResourceExW
        num_fonts_added = add_font_resource_ex(path_buf, FR_PRIVATE, 0)
        
        if num_fonts_added > 0:
            return True
        else:
            print("Warning: Failed to load font via GDI")
            return False
    except Exception as e:
        print(f"Error loading font: {e}")
        return False

# Attempt to load the font
_font_loaded = load_custom_font()
FONT_FAMILY = "Inter" if _font_loaded else "Segoe UI"

# A modern, dark theme for the AI Plotter Controller application.
# refined palette for better contrast and "premium" feel.
THEME = {
    # Backgrounds
    "root_bg": "#0f172a",       # Slate 900 (Deep blue-black)
    "frame_bg": "#1e293b",      # Slate 800 (Card background)
    "entry_bg": "#334155",      # Slate 700 (Input fields)
    
    # Text
    "text_color": "#f8fafc",    # Slate 50 (Primary text)
    "label_color": "#cbd5e1",   # Slate 300 (Secondary labels)
    "disabled_fg": "#64748b",   # Slate 500 (Disabled/Placeholder)
    "entry_fg": "#f1f5f9",      # Slate 100 (Input text)
    
    # Accents
    "accent_color": "#3b82f6",  # Blue 500 (Primary Action)
    "accent_fg": "#ffffff",     # White text on accent
    "accent_hover": "#2563eb",  # Blue 600
    
    # Buttons
    "button_bg": "#334155",     # Slate 700
    "button_fg": "#f8fafc",     # Slate 50
    "button_hover": "#475569",  # Slate 600
    
    # Status
    "success_color": "#22c55e", # Green 500
    "warning_color": "#f59e0b", # Amber 500
    "error_color": "#ef4444",   # Red 500
    
    # Specifics
    "voice_bg": "#8b5cf6",      # Violet 500 (Distinct for voice)
    "voice_fg": "#ffffff",
    
    # Tabs
    "tab_bg": "#0f172a",        # Match root
    "tab_fg": "#94a3b8",        # Slate 400
    "selected_tab_bg": "#1e293b", # Match frame
    "selected_tab_fg": "#3b82f6", # Accent color
}

# Font settings
FONTS = {
    "body": (FONT_FAMILY, 10),
    "body_bold": (FONT_FAMILY, 10, "bold"),
    "title": (FONT_FAMILY, 16, "bold"),
    "h1": (FONT_FAMILY, 14, "bold"),
    "h2": (FONT_FAMILY, 11, "bold"),  # Section headers
    "small": (FONT_FAMILY, 8),
    "small_bold": (FONT_FAMILY, 8, "bold"),
    "code": ("Consolas", 10),
    "code_small": ("Consolas", 8)
}

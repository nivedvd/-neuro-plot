"""
Tool change dialog for multi-pen support
"""
import tkinter as tk
from tkinter import messagebox
from theme import THEME, FONTS

class ToolChangeDialog:
    """Dialog to prompt user for pen/marker changes."""
    
    # Color mapping for tool numbers
    TOOL_COLORS = {
        0: "Black",
        1: "Red",
        2: "Blue",
        3: "Green",
        4: "Yellow",
        5: "Orange"
    }
    
    def __init__(self, parent, tool_number):
        """
        Create a tool change dialog.
        
        Args:
            parent: Parent window
            tool_number: Integer representing the tool to change to
        """
        self.result = False
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Tool Change Required")
        self.dialog.geometry("400x250")
        self.dialog.configure(bg=THEME["root_bg"])
        self.dialog.resizable(False, False)
        
        # Make it modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (250 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Content
        color_name = self.TOOL_COLORS.get(tool_number, f"Tool {tool_number}")
        
        tk.Label(
            self.dialog,
            text="⚠️ Tool Change Required",
            font=FONTS["h1"],
            bg=THEME["root_bg"],
            fg=THEME["accent_color"]
        ).pack(pady=(30, 10))
        
        tk.Label(
            self.dialog,
            text=f"Please insert {color_name} pen/marker",
            font=FONTS["h2"],
            bg=THEME["root_bg"],
            fg=THEME["text_color"]
        ).pack(pady=10)
        
        tk.Label(
            self.dialog,
            text=f"Tool Number: {tool_number}",
            font=FONTS["body"],
            bg=THEME["root_bg"],
            fg=THEME["disabled_fg"]
        ).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self.dialog, bg=THEME["root_bg"])
        button_frame.pack(pady=30)
        
        tk.Button(
            button_frame,
            text="✓ Ready - Continue",
            command=self.on_continue,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            activebackground=THEME["accent_hover"],
            activeforeground=THEME["accent_fg"],
            font=FONTS["body_bold"],
            relief="flat",
            bd=0,
            width=18,
            cursor="hand2"
        ).pack(side="left", padx=10)
        
        tk.Button(
            button_frame,
            text="✕ Cancel",
            command=self.on_cancel,
            bg=THEME["error_color"],
            fg="white",
            activebackground="#dc2626",
            activeforeground="white",
            font=FONTS["body"],
            relief="flat",
            bd=0,
            width=12,
            cursor="hand2"
        ).pack(side="left", padx=10)
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def on_continue(self):
        """User confirmed tool change."""
        self.result = True
        self.dialog.destroy()
    
    def on_cancel(self):
        """User cancelled."""
        self.result = False
        self.dialog.destroy()
    
    def show(self):
        """Show the dialog and wait for user response."""
        self.dialog.wait_window()
        return self.result

def show_tool_change_dialog(parent, tool_number):
    """
    Convenience function to show tool change dialog.
    
    Args:
        parent: Parent window
        tool_number: Tool number to change to
        
    Returns:
        bool: True if user confirmed, False if cancelled
    """
    dialog = ToolChangeDialog(parent, tool_number)
    return dialog.show()

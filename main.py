import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import logging
import re
import math # For distance calc if needed
import google.generativeai as genai

from image_processing import process_image
from controller import PlotterController
from motion_planner import draw, draw_actions
from handwriting import text_to_actions
from serial_comm import PlotterSerial
from ai_engine import AIEngine
from gcode_parser import GCodeTranslator
from svg_processor import svg_to_contours
from preview_canvas import PreviewCanvas
from vision_processor import VisionProcessor
from theme import THEME, FONTS
from config import GEMINI_API_KEY

# ================= OPTIONAL VOICE =================
SPEECH_AVAILABLE = False
SPEECH_ERROR = ""
try:
    import speech_recognition as sr
    try:
        _ = sr.Microphone.list_microphone_names()
        SPEECH_AVAILABLE = True
    except Exception as e:
        SPEECH_ERROR = str(e)
        SPEECH_AVAILABLE = False
except ImportError:
    SPEECH_ERROR = "speech_recognition not installed"
    SPEECH_AVAILABLE = False

# ================= LOGGING =================
logging.basicConfig(filename="plotter.log", level=logging.INFO)

# ================= ULN2003 SCALING =================
STEPS_PER_REV = 2048 # Matches 28BYJ-48 standard/arduino_plotter.ino
MM_PER_REV = 8.0 # Standard lead screw or belt pitch
STEPS_PER_MM = 89.8 # Updated to match Arduino firmware calibration


# ==================================================
# ================= SCROLLABLE FRAME ===============
# ==================================================
class ScrollableFrame(tk.Frame):
    """A Tkinter Frame that adds a vertical scrollbar and mouse-wheel support.
    Use 'scrollable_window' as the parent for any widgets you place inside."""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(self, bg=THEME["root_bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Create the scrollable frame inside the canvas
        self.scrollable_window = tk.Frame(self.canvas, bg=THEME["root_bg"])
        
        # Configure the scrollable window to fill the canvas
        self.scrollable_window.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        # Add the window to the canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_window, anchor="nw")
        
        # Configure canvas to scroll
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Layout
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        self.scrollable_window.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_window.bind("<Leave>", self._unbind_mousewheel)
        
        # Handle resizing to fill width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        # Resize the inner frame to match the canvas width
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")





# ================= MAIN APP ========================

class PlotterApp:
    """Main application window for Neuro Plot.

    Manages all UI tabs (Drawing, AI Assistant, Settings), handles
    serial communication with the plotter hardware, and coordinates
    AI-generated drawing actions.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Neuro Plot")
        self.root.geometry("900x550")
        self.root.configure(bg=THEME["root_bg"])

        # -------- STATE --------
        self.selected_image = None
        self.preview_img = None
        self.contours = []
        self.generated_actions = []
        self.preview_canvas = None  # Will be created in create_draw_tab
        
        # -------- SETTINGS --------
        self.speed_var = tk.IntVar(value=1000)
        self.accel_var = tk.IntVar(value=3000)
        self.z_lift_var = tk.IntVar(value=250)
        self.steps_mm_var = tk.DoubleVar(value=89.8)
        
        self.drawing_running = False

        # -------- CONTROLLERS --------
        self.abort_controller = PlotterController()
        self.serial = PlotterSerial()

        # -------- GEMINI --------
        self.gemini = None
        self.ai_engine = None
        self.vision_processor = None
        self.setup_gemini()

        # -------- STYLE --------
        self.setup_style()

        # -------- UI --------
        self.load_logo()
        
        # G-Code Translator (Stateful)
        self.translator = GCodeTranslator()
        
        self.create_ui()

    def load_logo(self):
        try:
            # Load and keep reference to logo
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "assets", "logo.png")
            
            if not os.path.exists(logo_path):
                # Fallback to jpg if png not found
                logo_path = os.path.join(script_dir, "assets", "logo.jpg")
            
            if not os.path.exists(logo_path):
                print(f"[UI] Logo not found at: {logo_path}")
                self.logo_header = None
                return

            full_img = Image.open(logo_path).convert("RGBA")
            
            # Set window icon
            icon_img = ImageTk.PhotoImage(full_img)
            self.root.iconphoto(False, icon_img)
            
            # Create version for header maintaining aspect ratio
            # Target height of 40px for the header
            target_h = 40
            w, h = full_img.size
            ratio = w / h
            target_w = int(target_h * ratio)
            
            self.logo_header = ImageTk.PhotoImage(full_img.resize((target_w, target_h), Image.Resampling.LANCZOS))
        except Exception as e:
            print(f"[UI] Could not load logo: {e}")
            self.logo_header = None

    # --- Thread-safe UI helper ---
    def ui(self, fn):
        """Schedule a UI update on the main thread.
        Always use this when updating widgets from a background thread."""
        self.root.after(0, fn)

    # ================= AI =================
    def setup_gemini(self):
        """Initialise the Gemini AI engine and vision processor.
        Skips setup gracefully if no API key has been configured."""
        if not GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
            print("[Warning] Gemini API key is not set — AI features will be disabled.")
            return
        
        try:
            self.ai_engine = AIEngine(GEMINI_API_KEY)
            self.vision_processor = VisionProcessor(GEMINI_API_KEY)
        except Exception as e:
            print(f"[ERROR] Failed to setup Gemini engines: {e}")
            self.logo_header = None

    def upload_handwriting(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        if not path:
            return
        
        self.handwriting_sample_path = path
        self.handwriting_status.config(
            text=f"Selected: {path.split('/')[-1]}",
            fg=THEME["accent_color"]
        )
        self.analyze_btn.config(state="normal")

    def analyze_handwriting_style(self):
        if not self.handwriting_sample_path:
            return

        self.handwriting_status.config(text="Analyzing style...", fg=THEME["accent_color"])
        self.analyze_btn.config(state="disabled")

        def task():
            try:
                analysis, custom_font = self.vision_processor.analyze_and_generate(self.handwriting_sample_path)
                
                if custom_font:
                    # Update the font in the handwriting module
                    import handwriting
                    handwriting.FONT.update(custom_font)
                    
                    msg = f"Style analysis complete!\nSlant: {analysis['slant']}\nStyle: {analysis['style']}\nNeuro Plot has learned this handwriting style."
                    self.ui(lambda: messagebox.showinfo("Analysis Complete", msg))
                    self.ui(lambda: self.handwriting_status.config(text="Style Learned ✓", fg=THEME["success_color"]))
                else:
                    self.ui(lambda: messagebox.showwarning("Analysis Failed", "Gemini could not generate a font from this sample."))
                    self.ui(lambda: self.handwriting_status.config(text="Analysis failed", fg=THEME["error_color"]))
            except Exception as e:
                self.ui(lambda: messagebox.showerror("Error", f"Vision processing error: {e}"))
                self.ui(lambda: self.handwriting_status.config(text="Error occurred", fg=THEME["error_color"]))
            finally:
                self.ui(lambda: self.analyze_btn.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    # ================= STYLE =================
    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure clearer focus highlighting
        style.map("TEntry", fieldbackground=[("active", THEME["entry_bg"])], foreground=[("active", THEME["entry_fg"])])

        style.configure(
            "TProgressbar",
            background=THEME["accent_color"],
            troughcolor=THEME["frame_bg"],
            borderwidth=0,
            thickness=6
        )

        # Style for the notebook and its tabs
        style.configure("TNotebook", background=THEME["root_bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=THEME["tab_bg"],
                        foreground=THEME["tab_fg"],
                        padding=[20, 10],
                        font=FONTS["body_bold"],
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", THEME["selected_tab_bg"])],
                  foreground=[("selected", THEME["selected_tab_fg"])])
        
        # Custom Scrollbar to match theme (dark track, lighter thumb)
        style.configure("Vertical.TScrollbar",
            background=THEME["button_bg"],
            troughcolor=THEME["root_bg"],
            borderwidth=0,
            arrowcolor=THEME["text_color"]
        )

    # ================= UI =================
    def create_ui(self):
        # App header bar
        header = tk.Frame(self.root, bg=THEME["root_bg"]) # Changed to root_bg for cleaner look
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        if self.logo_header:
            tk.Label(header, image=self.logo_header, bg=THEME["root_bg"]).pack(side="right", padx=(15, 0))
        
        title_frame = tk.Frame(header, bg=THEME["root_bg"])
        title_frame.pack(side="left")
        
        tk.Label(
            title_frame,
            text="Neuro Plot",
            font=FONTS["title"],
            fg=THEME["accent_color"],
            bg=THEME["root_bg"]
        ).pack(anchor="w")
        
        tk.Label(
            title_frame,
            text="Precision plotting with AI assistance",
            font=FONTS["small"],
            fg=THEME["disabled_fg"],
            bg=THEME["root_bg"]
        ).pack(anchor="w")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.create_draw_tab()
        self.create_ai_tab()
        self.create_settings_tab()

        # Footer branding (subtle)
        tk.Label(
            self.root,
            text="v2.0",
            font=FONTS["small"],
            fg=THEME["disabled_fg"],
            bg=THEME["root_bg"]
        ).place(relx=1, rely=1, anchor="se", x=-15, y=-15)

    
    # ================= DRAW TAB =======================
    # ==================================================
    def create_draw_tab(self):
        tab = tk.Frame(self.notebook, bg=THEME["root_bg"])
        self.notebook.add(tab, text="Drawing")

        # Create scrollable container
        scroll_frame = ScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True)
        
        # Use the inner scrollable window as the parent for columns
        content = scroll_frame.scrollable_window
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        # -------- IMAGE PREVIEW --------
        # Using a Frame instead of LabelFrame for a cleaner look
        left_col = tk.Frame(content, bg=THEME["root_bg"])
        left_col.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        preview = tk.Frame(left_col, bg=THEME["frame_bg"])
        preview.pack(fill="both", expand=True)

        tk.Label(preview, text="Image Preview", font=FONTS["h2"], bg=THEME["frame_bg"], fg=THEME["text_color"]).pack(pady=(20, 10))

        self.image_label = tk.Label(preview, bg=THEME["entry_bg"])
        self.image_label.pack(padx=20, pady=10)

        self.preview_status = tk.Label(
            preview, text="No image selected",
            font=FONTS["body"],
            fg=THEME["disabled_fg"],
            bg=THEME["frame_bg"]
        )
        self.preview_status.pack(pady=5)

        tk.Button(
            preview, text="Select Image",
            command=self.select_image,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            activebackground=THEME["accent_hover"],
            activeforeground=THEME["accent_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0, width=20,
            cursor="hand2"
        ).pack(pady=15)

        tk.Button(
            preview, text="Export G-code",
            command=self.export_gcode,
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_hover"],
            activeforeground=THEME["button_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0, width=20,
            cursor="hand2"
        ).pack(pady=(0, 20))

        # -------- TEXT TO PLOTTER --------
        text_frame = tk.Frame(left_col, bg=THEME["frame_bg"])
        text_frame.pack(fill="x", pady=20)

        tk.Label(text_frame, text="Text Plotting", font=FONTS["h2"], bg=THEME["frame_bg"], fg=THEME["text_color"]).pack(pady=(15, 5))

        # Entry with better styling
        entry_container = tk.Frame(text_frame, bg=THEME["entry_bg"], highlightthickness=2, highlightbackground=THEME["accent_color"])
        entry_container.pack(pady=10, padx=20, fill="x")
        
        self.text_entry = tk.Entry(
            entry_container,
            font=FONTS["body"],
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["accent_color"],
            relief="flat",
            bd=5
        )
        self.text_entry.pack(fill="x", ipady=5)
        
        # Placeholder text
        self.text_placeholder = "Type text here (e.g., HELLO)"
        self.text_entry.insert(0, self.text_placeholder)
        self.text_entry.config(fg=THEME["disabled_fg"])
        
        def on_text_focus_in(event):
            if self.text_entry.get() == self.text_placeholder:
                self.text_entry.delete(0, tk.END)
                self.text_entry.config(fg=THEME["entry_fg"])
        
        def on_text_focus_out(event):
            if not self.text_entry.get():
                self.text_entry.insert(0, self.text_placeholder)
                self.text_entry.config(fg=THEME["disabled_fg"])
        
        def on_text_enter(event):
            self.plot_text()
        
        self.text_entry.bind("<FocusIn>", on_text_focus_in)
        self.text_entry.bind("<FocusOut>", on_text_focus_out)
        self.text_entry.bind("<Return>", on_text_enter)
        
        # Character counter
        self.text_char_count = tk.Label(
            text_frame, text="0 characters",
            font=FONTS["small"],
            fg=THEME["disabled_fg"],
            bg=THEME["frame_bg"]
        )
        self.text_char_count.pack(pady=(0, 5))
        
        def update_char_count(*args):
            text = self.text_entry.get()
            if text != self.text_placeholder:
                count = len(text)
                self.text_char_count.config(text=f"{count} character{'s' if count != 1 else ''}")
        
        self.text_entry.bind("<KeyRelease>", update_char_count)
        
        # Button container
        btn_container = tk.Frame(text_frame, bg=THEME["frame_bg"])
        btn_container.pack(pady=(5, 20))

        tk.Button(
            btn_container, text="Plot Text",
            command=self.plot_text,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            activebackground=THEME["accent_hover"],
            activeforeground=THEME["accent_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0,
            cursor="hand2",
            width=12
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_container, text="Clear",
            command=lambda: (self.text_entry.delete(0, tk.END), self.text_entry.insert(0, self.text_placeholder), self.text_entry.config(fg=THEME["disabled_fg"]), self.text_char_count.config(text="0 characters")),
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_hover"],
            activeforeground=THEME["button_fg"],
            font=FONTS["body"],
            relief="flat", bd=0,
            cursor="hand2",
            width=8
        ).pack(side="left", padx=5)


        # -------- LIVE PREVIEW --------
        preview_live = tk.Frame(left_col, bg=THEME["frame_bg"], relief="solid", bd=1)
        preview_live.pack(fill="both", expand=True, pady=(10, 20))
        
        tk.Label(
            preview_live, text="Live Preview",
            font=FONTS["h2"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(20, 10))
        
        # Create the preview canvas with better sizing
        canvas_container = tk.Frame(preview_live, bg=THEME["frame_bg"])
        canvas_container.pack(pady=(0, 20))
        
        self.preview_canvas = PreviewCanvas(
            canvas_container,
            workspace_mm=100,
            width=300,
            height=300,
            bg='#1a1a1a',
            highlightthickness=2,
            highlightbackground=THEME["accent_color"]
        )
        self.preview_canvas.pack()

        # -------- CONTROLS --------
        ctrl = tk.Frame(content, bg=THEME["frame_bg"])
        ctrl.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        tk.Label(ctrl, text="Control Panel", font=FONTS["h2"], bg=THEME["frame_bg"], fg=THEME["text_color"]).pack(pady=(20, 10))

        self.create_connection_frame(ctrl).pack(fill="x", pady=10)

        self.status_label = tk.Label(
            ctrl, text="● Status: Idle",
            font=FONTS["h2"],
            fg=THEME["accent_color"],
            bg=THEME["frame_bg"]
        )
        self.status_label.pack(pady=10)

        self.progress = ttk.Progressbar(ctrl, length=280)
        self.progress.pack(pady=10)

        self.eta_label = tk.Label(
            ctrl, text="ETA: --",
            font=FONTS["small"],
            fg=THEME["disabled_fg"],
            bg=THEME["frame_bg"]
        )
        self.eta_label.pack(pady=5)

        self.ctrl_btn(ctrl, "Start Drawing", self.start_drawing)
        self.ctrl_btn(ctrl, "Pause", self.pause)
        self.ctrl_btn(ctrl, "Resume", self.resume)
        self.ctrl_btn(ctrl, "Return to Home", self.return_home)
        self.ctrl_btn(ctrl, "Set Home (Zero)", self.set_home)

        tk.Button(
            ctrl, text="⛔ EMERGENCY STOP",
            command=self.emergency_stop,
            bg=THEME["error_color"],
            fg="white",
            activebackground="#dc2626",
            activeforeground="white",
            font=FONTS["h1"],
            relief="flat", bd=0, width=22,
            cursor="hand2"
        ).pack(pady=20)

    # ================= CONNECTION FRAME =================
    def create_connection_frame(self, parent):
        frame = tk.Frame(parent, bg=THEME["frame_bg"])

        self.conn_status = tk.Label(
            frame, text="● Disconnected",
            font=FONTS["body"],
            fg=THEME["error_color"],
            bg=THEME["frame_bg"]
        )
        self.conn_status.pack(side="left", padx=5)

        btns = tk.Frame(frame, bg=THEME["frame_bg"])
        btns.pack(side="right")

        tk.Button(
            btns, text="Connect", command=self.connect_plotter,
            bg=THEME["button_bg"], fg=THEME["button_fg"], font=FONTS["body"],
            relief="flat", bd=0, width=10
        ).pack(side="left", padx=4)
        
        tk.Button(
            btns, text="Simulate", command=self.simulate_plotter,
            bg=THEME["button_bg"], fg=THEME["button_fg"], font=FONTS["body"],
            relief="flat", bd=0, width=10
        ).pack(side="left", padx=4)

        tk.Button(
            btns, text="Disconnect", command=self.disconnect_plotter,
            bg=THEME["button_bg"], fg=THEME["button_fg"], font=FONTS["body"],
            relief="flat", bd=0, width=10
        ).pack(side="left", padx=4)

        return frame

    def ctrl_btn(self, parent, text, command):
        """Helper to add a consistently styled control button to the panel."""
        tk.Button(
            parent,
            text=text,
            command=command,
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_hover"],
            activeforeground=THEME["button_fg"],
            font=FONTS["body_bold"],
            relief="flat",
            bd=0,
            width=22,
            cursor="hand2"
        ).pack(pady=5)

    # ================= IMAGE =================
    def select_image(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("All Supported", "*.png *.jpg *.jpeg *.svg"),
                ("Images", "*.png *.jpg *.jpeg"),
                ("SVG Files", "*.svg")
            ]
        )
        if not path:
            return

        self.selected_image = path
        
        # Check if SVG or raster image
        if path.lower().endswith('.svg'):
            # Process SVG file
            self.contours = svg_to_contours(path, resolution=0.5)
            
            # Create a simple preview for SVG
            try:
                from cairosvg import svg2png
                png_data = svg2png(url=path, output_width=280, output_height=280)
                from io import BytesIO
                img = Image.open(BytesIO(png_data))
                self.preview_img = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.preview_img)
            except:
                # Fallback if SVG preview fails
                self.image_label.config(image="", text="SVG Loaded\n(Preview unavailable)")
            
            self.preview_status.config(
                text=f"SVG loaded: {len(self.contours)} paths",
                fg=THEME["accent_color"]
            )
        else:
            # Process raster image
            img = Image.open(path)
            img.thumbnail((280, 280))
            self.preview_img = ImageTk.PhotoImage(img)

            self.image_label.config(image=self.preview_img)
            self.preview_status.config(
                text="Image loaded successfully",
                fg=THEME["accent_color"]
            )

            self.contours = process_image(path)

    # ================= G-CODE =================
    def export_gcode(self):
        if not self.contours:
            messagebox.showwarning("No contours", "Load an image and process it before exporting G-code.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".gcode",
            filetypes=[("G-code", "*.gcode")]
        )
        if not path:
            return

        with open(path, "w") as f:
            f.write("G21\nG90\nM5\n")
            for contour in self.contours:
                x0, y0 = contour[0]
                f.write(f"G0 X{x0:.2f} Y{y0:.2f}\nM3\n")
                for x, y in contour[1:]:
                    f.write(f"G1 X{x:.2f} Y{y:.2f}\n")
                f.write("M5\n")
            f.write("G0 X0 Y0\n")

        messagebox.showinfo("Exported", "G-code exported successfully")

    # ================= CONNECTION =================
    def connect_plotter(self):
        def task():
            if self.serial.connect():
                self.ui(lambda: self.conn_status.config(
                    text="● Connected",
                    fg=THEME["success_color"]
                ))
            else:
                self.ui(lambda: self.conn_status.config(
                    text="● Connection Failed",
                    fg=THEME["error_color"]
                ))
        
        self.conn_status.config(
            text="● Connecting...",
            fg=THEME["warning_color"]
        )
        threading.Thread(target=task, daemon=True).start()

    def simulate_plotter(self):
        self.serial.disconnect()
        if self.serial.connect(simulate=True):
            self.conn_status.config(
                text="● Simulation Mode",
                fg=THEME["accent_color"]
            )
        else:
            self.conn_status.config(
                text="● Simulation Failed",
                fg=THEME["error_color"]
            )

    def disconnect_plotter(self):
        # Gracefully stop any ongoing drawing and return to origin if possible
        self.abort_controller.stop()
        try:
            # Let the motion planner/firmware handle returning to origin on stop
            self.serial.disconnect()
        finally:
            self.drawing_running = False
            self.generated_actions = []
            self.ui(lambda: self.progress.config(value=0))
            self.ui(lambda: self.eta_label.config(text="ETA: --"))
            self.set_status("Disconnected", THEME["error_color"])
            self.conn_status.config(
                text="● Disconnected",
                fg=THEME["error_color"]
            )

    def _calculate_total_steps(self, data):
        """Work out how many steps are in the drawing so we can track progress.

        Actions (list of tuples like ('MOVE', x, y)) are counted directly.
        Contours (list of point lists) count every point across all paths.
        """
        if not data:
            return 0
        # Detect whether we have named action tuples or raw coordinate contours
        if isinstance(data[0], tuple) and isinstance(data[0][0], str):
            return len(data)
        else:
            # Sum all points across every contour path
            return sum(len(contour) for contour in data) + 1

    def _update_progress(self, steps_drawn):
        """Update the progress bar and estimated time remaining.
        Called by the drawing worker after each step is sent to the plotter."""
        if self.total_steps == 0:
            return

        progress_percent = (steps_drawn / self.total_steps) * 100
        self.ui(lambda: self.progress.config(value=progress_percent))

        elapsed_time = time.time() - self.start_time
        if steps_drawn > 0:
            time_per_step = elapsed_time / steps_drawn
            remaining_steps = self.total_steps - steps_drawn
            remaining_time = remaining_steps * time_per_step

            # Format as MM:SS for a friendly display
            mins, secs = divmod(int(remaining_time), 60)
            eta_str = f"{mins:02d}:{secs:02d}"
            self.ui(lambda: self.eta_label.config(text=f"ETA: {eta_str}"))

    def start_drawing(self):
        # Behavior B: if a drawing is running, abort it and start the new one
        if getattr(self, "drawing_running", False):
            self.abort_controller.stop()
            # Small delay to let the worker thread notice the stop
            time.sleep(0.1)
            self.drawing_running = False
        if not self.contours and not self.generated_actions:
            messagebox.showwarning("No Data", "Please select an image or generate AI text first.")
            return

        # Use generated actions if available, otherwise use image contours
        data_to_draw = self.generated_actions if self.generated_actions else self.contours
        
        self.total_steps = self._calculate_total_steps(data_to_draw)
        self.start_time = time.time()
        self.drawing_running = True
        
        self.ui(lambda: self.progress.config(value=0))
        self.ui(lambda: self.eta_label.config(text="ETA: Calculating..."))
        self.set_status("Drawing...", THEME["accent_color"])

        threading.Thread(target=self.draw_task, args=(data_to_draw,), daemon=True).start()

    def draw_task(self, data_to_draw):
        self.abort_controller.resume() # Ensure it's not paused from a previous run
        
        # Reset preview canvas
        if self.preview_canvas:
            self.ui(lambda: self.preview_canvas.reset())
        
        try:
            # Check if data_to_draw is actions or contours
            if data_to_draw and isinstance(data_to_draw[0], tuple) and isinstance(data_to_draw[0][0], str):
                 draw_actions(
                     data_to_draw, 
                     self.abort_controller, 
                     self.serial, 
                     scale=STEPS_PER_MM, 
                     progress_callback=self._update_progress,
                     preview_canvas=self.preview_canvas
                 )
            else:
                 draw(
                     data_to_draw, 
                     self.abort_controller, 
                     self.serial, 
                     scale=STEPS_PER_MM, 
                     progress_callback=self._update_progress,
                     preview_canvas=self.preview_canvas
                 )
            
            if not self.abort_controller.stopped:
                self.set_status("Returning Home...", THEME["accent_color"])
                try:
                    self.serial.pen_up()
                    self.serial.return_to_home()
                except:
                    pass
                if self.preview_canvas:
                    self.ui(lambda: self.preview_canvas.reset())
                self.set_status("Drawing completed", THEME["success_color"])
                
        except Exception as e:
            self.ui(lambda: messagebox.showerror("Drawing Error", f"An error occurred while drawing:\n{str(e)}"))
            self.set_status("Error", THEME["error_color"])
        finally:
            self.drawing_running = False
            self.generated_actions = [] # Clear actions after drawing
            self.ui(lambda: self.progress.config(value=100))
            self.ui(lambda: self.eta_label.config(text="ETA: 00:00"))

    # ================= AI TAB =================
    def create_ai_tab(self):
        tab = tk.Frame(self.notebook, bg=THEME["root_bg"])
        self.notebook.add(tab, text="AI Assistant")

        # Header / Branding for Neuro AI
        header = tk.Frame(tab, bg=THEME["root_bg"]) 
        header.pack(fill="x", padx=40, pady=(30, 10))

        title = tk.Label(
            header,
            text="Neuro AI",
            font=FONTS["title"],
            fg=THEME["accent_color"],
            bg=THEME["root_bg"]
        )
        title.pack(side="left")

        subtitle = tk.Label(
            header,
            text="Context-aware assistant for plotting",
            font=FONTS["body"],
            fg=THEME["disabled_fg"],
            bg=THEME["root_bg"]
        )
        subtitle.pack(side="left", padx=15)

        # Card container for input and output
        card = tk.Frame(tab, bg=THEME["frame_bg"])
        card.pack(fill="both", expand=True, padx=40, pady=20)

        # -------- HANDWRITING ANALYSIS (VISION) --------
        vision_frame = tk.Frame(card, bg=THEME["frame_bg"])
        vision_frame.pack(fill="x", padx=20, pady=(0, 20))

        tk.Label(
            vision_frame, text="Style Analysis (Gemini Vision)",
            font=FONTS["body_bold"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(side="left", padx=10)

        self.handwriting_sample_path = None
        self.handwriting_status = tk.Label(
            vision_frame, text="No sample uploaded",
            font=FONTS["small"],
            bg=THEME["frame_bg"],
            fg=THEME["disabled_fg"]
        )
        self.handwriting_status.pack(side="left", padx=10)

        tk.Button(
            vision_frame, text="Upload Sample",
            command=self.upload_handwriting,
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            font=FONTS["small"],
            relief="flat", bd=0, padx=10,
            cursor="hand2"
        ).pack(side="right", padx=5)

        self.analyze_btn = tk.Button(
            vision_frame, text="Analyze Style",
            command=self.analyze_handwriting_style,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            font=FONTS["small_bold"],
            relief="flat", bd=0, padx=10,
            cursor="hand2",
            state="disabled"
        )
        self.analyze_btn.pack(side="right", padx=5)

        # Input row
        input_frame = tk.Frame(card, bg=THEME["frame_bg"]) 
        input_frame.pack(fill="x", padx=20, pady=20)

        self.ai_entry = tk.Entry(
            input_frame,
            font=FONTS["body"],
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["entry_fg"],
            relief="flat",
            width=50
        )
        self.ai_entry.pack(side="left", padx=10, ipady=10, fill="x", expand=True)
        # Placeholder for entry
        self.ai_entry_placeholder = "Ask Neuro AI anything…"
        self.ai_entry_is_placeholder = True
        self.ai_entry.insert(0, self.ai_entry_placeholder)
        self.ai_entry.config(fg=THEME["disabled_fg"])
        def _entry_focus_in(event):
            if self.ai_entry_is_placeholder:
                self.ai_entry.delete(0, tk.END)
                self.ai_entry.config(fg=THEME["entry_fg"])
                self.ai_entry_is_placeholder = False
        def _entry_focus_out(event):
            if not self.ai_entry.get().strip():
                self.ai_entry.insert(0, self.ai_entry_placeholder)
                self.ai_entry.config(fg=THEME["disabled_fg"])
                self.ai_entry_is_placeholder = True
        self.ai_entry.bind("<FocusIn>", _entry_focus_in)
        self.ai_entry.bind("<FocusOut>", _entry_focus_out)

        if SPEECH_AVAILABLE:
            self.voice_btn = tk.Button(
                input_frame, text="🎤",
                command=self.listen_voice,
                bg=THEME["voice_bg"],
                fg=THEME["voice_fg"],
                activebackground="#7c3aed",
                activeforeground="white",
                font=FONTS["body_bold"],
                relief="flat", bd=0, width=4,
                cursor="hand2"
            )
            self.voice_btn.pack(side="left", padx=5, ipady=8)

        tk.Button(
            input_frame, text="✨ Ask",
            command=self.ask_ai,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            activebackground=THEME["accent_hover"],
            activeforeground=THEME["accent_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0, width=12,
            cursor="hand2"
        ).pack(side="left", padx=5, ipady=8)

        # Output box with scrollbar
        output_wrap = tk.Frame(card, bg=THEME["frame_bg"])
        output_wrap.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Inner frame for border
        output_inner = tk.Frame(output_wrap, bg=THEME["entry_bg"], padx=1, pady=1)
        output_inner.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(output_inner, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        self.ai_output = tk.Text(
            output_inner, height=10,
            font=FONTS["body"],
            bg=THEME["entry_bg"],
            fg=THEME["text_color"],
            insertbackground=THEME["text_color"],
            relief="flat", wrap="word",
            yscrollcommand=scrollbar.set,
            padx=10, pady=10
        )
        self.ai_output.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.ai_output.yview)
        
        # Placeholder in output
        self.ai_output_placeholder = "Neuro AI will respond here."
        self.ai_output_is_placeholder = True
        self.ai_output.delete("1.0", tk.END)
        self.ai_output.insert("1.0", self.ai_output_placeholder)
        self.ai_output.config(fg=THEME["disabled_fg"])

        # Actions row
        actions = tk.Frame(card, bg=THEME["frame_bg"]) 
        actions.pack(fill="x", padx=20, pady=(0, 20))

        tk.Button(
            actions, text="Send to Plotter ->",
            command=self.send_ai_to_plotter,
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            activebackground=THEME["button_hover"],
            activeforeground=THEME["button_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0, width=20,
            cursor="hand2"
        ).pack(side="right")

    def plot_text(self):
        text = self.text_entry.get().strip()
        
        # Check for placeholder or empty text
        if not text or text == self.text_placeholder:
            messagebox.showwarning("No Text", "Please enter some text to plot.")
            return
        
        # Generate actions
        self.generated_actions = text_to_actions(text)
        
        # Update preview canvas if available
        if self.preview_canvas:
            self.preview_canvas.reset()
            # Preview the text path (simplified visualization)
            self.ui(lambda: self.preview_status.config(
                text=f"Text ready: '{text}' ({len(self.generated_actions)} actions)",
                fg=THEME["accent_color"]
            ))
        
        messagebox.showinfo(
            "Text Ready",
            f"Text '{text}' converted to {len(self.generated_actions)} actions!\nClick 'Start Drawing' to plot."
        )

    def send_ai_to_plotter(self):
        # If no actions generated, try to plot the text response visible in the output
        if not self.generated_actions:
            # Get text from output box
            output_text = self.ai_output.get("1.0", tk.END).strip()
            
            # Check if it's a valid response (not placeholder or empty)
            if output_text and not getattr(self, "ai_output_is_placeholder", False) and "Error:" not in output_text:
                # Ask user if they want to plot this text
                if messagebox.askyesno("Plot Response?", f"No drawing actions found.\n\nDo you want to write this text?\n\n'{output_text[:50]}...'", icon='question'):
                    # Convert response text to actions
                    self.generated_actions = text_to_actions(output_text[:60]) # Limit length
            
        if not self.generated_actions:
            messagebox.showwarning("No Actions", "Ask AI to 'draw' or 'write' something, or ask a question to plot the answer.")
            return

        self.start_drawing()
        # Switch to drawing tab to see progress
        self.notebook.select(0)

    def ask_ai(self):
        # Respect placeholder as empty input
        prompt = self.ai_entry.get().strip()
        if getattr(self, "ai_entry_is_placeholder", False):
            prompt = ""
        if not prompt:
            return

        # Prepare output area (clear placeholder, set normal color)
        self.ai_output_is_placeholder = False
        self.ai_output.config(fg=THEME["text_color"]) 
        self.ai_output.delete("1.0", tk.END)
        self.ai_output.insert("1.0", "Neuro AI is thinking…")

        def task():
            try:
                resp_type, content = self.ai_engine.ask(prompt)
                
                if resp_type == "ACTIONS":
                    self.generated_actions = self.center_relative_actions(content)
                    display_text = "I've generated the drawing coordinates for you! (Centered on Page)"
                
                elif resp_type == "TEXT_PLOT":
                    # Explicit text plotting request
                    raw = text_to_actions(content)
                    self.generated_actions = self.center_relative_actions(raw)
                    display_text = f"I've prepared the text '{content}' for plotting!\n(Centered on Page)"
                
                elif resp_type == "TEXT":
                    # Just conversation, don't plot
                    self.generated_actions = []
                    display_text = content
                
                else:
                    display_text = f"Error: {content}"
                    self.generated_actions = []

                self.ui(lambda: self.ai_output.delete("1.0", tk.END))
                self.ui(lambda: self.ai_output.insert("1.0", display_text))
            except Exception as e:
                self.ui(lambda: (
                    self.ai_output.delete("1.0", tk.END),
                    self.ai_output.insert("1.0", f"Error: {e}")
                ))

        threading.Thread(target=task, daemon=True).start()

    def listen_voice(self):
        if not SPEECH_AVAILABLE:
            messagebox.showerror("Voice Input Unavailable", f"Microphone not available. {SPEECH_ERROR or ''}")
            return

        if hasattr(self, "voice_btn") and self.voice_btn:
            try:
                self.voice_btn.config(state="disabled", text="Listening…")
            except Exception:
                pass

        def worker():
            try:
                r = sr.Recognizer()
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.5)
                    audio = r.listen(src, timeout=5, phrase_time_limit=10)
                text = r.recognize_google(audio)
                self.ui(lambda: (
                    self.ai_entry.delete(0, tk.END),
                    self.ai_entry.insert(0, text)
                ))
            except sr.WaitTimeoutError:
                self.ui(lambda: messagebox.showwarning("Voice Timeout", "No speech detected. Try again."))
            except sr.UnknownValueError:
                self.ui(lambda: messagebox.showwarning("Voice Not Understood", "Could not understand audio."))
            except sr.RequestError as e:
                self.ui(lambda: messagebox.showerror("Speech Service Error", f"Recognition service failed: {e}"))
            except Exception as e:
                self.ui(lambda: messagebox.showerror("Microphone Error", f"{e}"))
            finally:
                if hasattr(self, "voice_btn") and self.voice_btn:
                    self.ui(lambda: self.voice_btn.config(state="normal", text="🎤"))

        threading.Thread(target=worker, daemon=True).start()

    # ================= CONTROL =================
    def pause(self):
        self.abort_controller.pause()
        self.set_status("Paused", THEME["warning_color"])

    def resume(self):
        self.abort_controller.resume()
        self.set_status("Resumed", THEME["accent_color"])

    def emergency_stop(self):
        self.abort_controller.stop()
        # Call the dedicated emergency_stop method in serial_comm
        self.serial.emergency_stop()
        self.set_status("EMERGENCY STOP", THEME["error_color"])
        # Update connection status in UI
        self.conn_status.config(
            text="● Disconnected (E-Stop)",
            fg=THEME["error_color"]
        )

    def set_status(self, text, color):
        self.ui(lambda: self.status_label.config(text=f"● {text}", fg=color))

    def set_home(self):
        """Reset the logical position to (0,0) and clear preview."""
        if self.preview_canvas:
            self.preview_canvas.reset()
        
        if self.serial and self.serial.port:
            self.serial.zero_position()
        
        # Reset progress bar and eta
        self.ui(lambda: self.progress.config(value=0))
        self.ui(lambda: self.eta_label.config(text="ETA: --"))
        
        messagebox.showinfo("Home Set", "Origin set! Plotter now treats this physical position as (0,0).")
        self.set_status("Home Set", THEME["accent_color"])

    def return_home(self):
        """Manually command the plotter back to origin."""
        if not self.serial or not self.serial.port:
            messagebox.showwarning("Not Connected", "Please connect to the plotter first.")
            return
            
        def task():
            self.set_status("Returning Home...", THEME["accent_color"])
            self.serial.pen_up()
            self.serial.return_to_home()
            if self.preview_canvas:
                self.ui(lambda: self.preview_canvas.reset())
            self.set_status("At Origin", THEME["success_color"])
            
        threading.Thread(target=task, daemon=True).start()


    def create_settings_tab(self):
        tab = tk.Frame(self.notebook, bg=THEME["root_bg"])
        self.notebook.add(tab, text="Settings")

        scrollable = ScrollableFrame(tab)
        scrollable.pack(fill="both", expand=True)
        content = scrollable.scrollable_window

        # Motion Control Card
        card = tk.Frame(content, bg=THEME["frame_bg"])
        card.pack(fill="x", padx=40, pady=20)

        tk.Label(
            card, text="Motion Control",
            font=FONTS["h2"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(20, 10))

        # Speed Slider
        tk.Label(
            card, text="Max Speed (steps/s)",
            font=FONTS["body"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(10, 0))
        
        speed_slider = tk.Scale(
            card, from_=500, to=10000,
            orient="horizontal",
            variable=self.speed_var,
            bg=THEME["frame_bg"],
            fg=THEME["text_color"],
            highlightthickness=0,
            troughcolor=THEME["entry_bg"],
            activebackground=THEME["accent_color"],
            length=400
        )
        speed_slider.pack(pady=5)

        # Acceleration Slider
        tk.Label(
            card, text="Acceleration (steps/s²)",
            font=FONTS["body"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(10, 0))
        
        accel_slider = tk.Scale(
            card, from_=1000, to=20000,
            orient="horizontal",
            variable=self.accel_var,
            bg=THEME["frame_bg"],
            fg=THEME["text_color"],
            highlightthickness=0,
            troughcolor=THEME["entry_bg"],
            activebackground=THEME["accent_color"],
            length=400
        )
        accel_slider.pack(pady=5)

        # Pen Lift Slider
        tk.Label(
            card, text="Pen Lift Distance (steps)",
            font=FONTS["body"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(10, 0))
        
        lift_slider = tk.Scale(
            card, from_=50, to=2000,
            orient="horizontal",
            variable=self.z_lift_var,
            bg=THEME["frame_bg"],
            fg=THEME["text_color"],
            highlightthickness=0,
            troughcolor=THEME["entry_bg"],
            activebackground=THEME["accent_color"],
            length=400
        )
        lift_slider.pack(pady=5)

        # Calibration Entry
        tk.Label(
            card, text="Steps per MM (Resolution)",
            font=FONTS["body"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(10, 0))
        
        calib_entry = tk.Entry(
            card, textvariable=self.steps_mm_var,
            font=FONTS["body"],
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            justify="center",
            width=10
        )
        calib_entry.pack(pady=5)

        tk.Button(
            card, text="Apply Motion Settings",
            command=self.update_motion_params,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0, padx=20, pady=10,
            cursor="hand2"
        ).pack(pady=20)

        # Manual Command / G-Code Terminal
        term_card = tk.Frame(content, bg=THEME["frame_bg"])
        term_card.pack(fill="x", padx=40, pady=20)
        
        tk.Label(
            term_card, text="Manual Command / G-Code",
            font=FONTS["h2"],
            bg=THEME["frame_bg"],
            fg=THEME["text_color"]
        ).pack(pady=(20, 10))
        
        term_input_frame = tk.Frame(term_card, bg=THEME["frame_bg"])
        term_input_frame.pack(fill="x", padx=20, pady=10)
        
        self.term_entry = tk.Entry(
            term_input_frame,
            font=FONTS["code"],
            bg=THEME["entry_bg"],
            fg=THEME["entry_fg"],
            insertbackground=THEME["accent_color"],
            relief="flat"
        )
        self.term_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.term_entry.bind("<Return>", lambda e: self.send_manual_command())
        
        tk.Button(
            term_input_frame, text="Load G-Code File...",
            command=self.load_gcode_file,
            bg=THEME["button_bg"],
            fg=THEME["button_fg"],
            font=FONTS["body"],
            relief="flat", bd=0, padx=10,
            cursor="hand2"
        ).pack(side="right", padx=(10, 0))

        tk.Button(
            term_input_frame, text="Send",
            command=self.send_manual_command,
            bg=THEME["accent_color"],
            fg=THEME["accent_fg"],
            font=FONTS["body_bold"],
            relief="flat", bd=0, padx=20,
            cursor="hand2"
        ).pack(side="right", padx=(10, 0))
        
        # Terminal Output
        self.term_log = tk.Text(
            term_card,
            font=FONTS["code_small"],
            bg=THEME["entry_bg"],
            fg=THEME["disabled_fg"],
            state="disabled",
            height=8,
            relief="flat"
        )
        self.term_log.pack(fill="x", padx=20, pady=(0, 20))

    def update_motion_params(self):
        def task():
            speed = self.speed_var.get()
            accel = self.accel_var.get()
            lift = self.z_lift_var.get()
            smm = self.steps_mm_var.get()
            
            if self.serial and self.serial.port:
                try:
                    self.set_status("Applying Settings...", THEME["accent_color"])
                    self.serial.set_speed(speed)
                    self.serial.set_acceleration(accel)
                    self.serial.set_z_lift(lift)
                    self.serial.set_calibration(smm)

                    self.ui(lambda: messagebox.showinfo("Settings Applied", f"Calibration Saved!\nSteps/MM: {smm}\nPen Lift: {lift}"))
                    self.set_status("Settings Applied", THEME["success_color"])
                except Exception as e:
                    self.ui(lambda: messagebox.showerror("Error", f"Failed to apply settings: {e}"))
                    self.set_status("Settings Failed", THEME["error_color"])
            else:
                self.ui(lambda: messagebox.showwarning("Not Connected", "Please connect to the plotter first."))

        threading.Thread(target=task, daemon=True).start()

    def center_relative_actions(self, actions):
        """
        Shift a list of relative drawing actions so the result is centred
        on the 100 x 100 mm plotter workspace.

        The actions use relative moves (dx, dy), so we simulate the full
        path first to find its bounding box, then prepend a single absolute
        move that places the drawing in the middle of the workspace.
        """
        if not actions: return []
        
        # Simulate Path to find bounds
        rx, ry = 0, 0
        min_x, max_x = 0, 0
        min_y, max_y = 0, 0
        
        for action in actions:
            if action[0] == "MOVE":
                dx, dy = action[1], action[2]
                rx += dx
                ry += dy
                min_x = min(min_x, rx)
                max_x = max(max_x, rx)
                min_y = min(min_y, ry)
                max_y = max(max_y, ry)
                
        # Calculate Dimensions and Center of the drawing
        width = max_x - min_x
        height = max_y - min_y
        
        center_x = min_x + width / 2
        center_y = min_y + height / 2
        
        # Desired Center (Plotter Middle) - 100x100mm workspace
        TARGET_X = 50.0
        TARGET_Y = 50.0
        
        # Shift needed
        shift_x = TARGET_X - center_x
        shift_y = TARGET_Y - center_y
        
        # Prepend the shift (Pen Up first)
        new_actions = [('PEN_UP',), ('MOVE', shift_x, shift_y)] + actions
        return new_actions

    def send_manual_command(self):
        cmd = self.term_entry.get().strip()
        if not cmd:
            return
            
        self.term_entry.delete(0, tk.END)
        self.log_terminal(f"> {cmd}")
        
        # Use Translator
        translated, msg = self.translator.parse_line(cmd)
        
        if msg:
            self.log_terminal(f"  [G-Code] {msg}")
            
        if not translated:
            return 
            
        # Handle special internal sequences
        if translated == "HOME_SEQUENCE":
            if self.serial and self.serial.port:
                 threading.Thread(target=lambda: (
                    self.serial.pen_up(),
                    time.sleep(0.5),
                    self.serial.return_to_home()
                ), daemon=True).start()
            return

        # Send regular command
        if self.serial and self.serial.port:
            try:
                def run_cmd():
                    success = self.serial.send(translated)
                    resp = "OK" if success else "FAIL"
                    self.ui(lambda: self.log_terminal(f"< {resp}"))
                
                threading.Thread(target=run_cmd, daemon=True).start()
            except Exception as e:
                self.log_terminal(f"[ERR] {e}")
        else:
            self.log_terminal("[ERR] Not connected")

    def load_gcode_file(self):
        filename = filedialog.askopenfilename(
            title="Select G-Code File",
            filetypes=[("G-Code Files", "*.gcode;*.nc;*.txt"), ("All Files", "*.*")]
        )
        if not filename:
            return
            
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return

            self.log_terminal(f"Loaded {len(lines)} lines.")
            
            # Execute in thread
            def run_file():
                self.translator.reset_home() # Reset state tracking? Maybe optionally.
                count = 0
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    trans, msg = self.translator.parse_line(line)
                    if msg: 
                         self.ui(lambda m=msg: self.log_terminal(f"  {m}"))
                    
                    if trans and trans != "HOME_SEQUENCE":
                        if self.serial and self.serial.port:
                            self.serial.send(trans) # this blocks until OK
                            count += 1
                        else:
                            break
                    elif trans == "HOME_SEQUENCE":
                        self.serial.pen_up()
                        self.serial.return_to_home()
                    
                    # Small delay (optional, parser is fast but UI log might lag)
                    # time.sleep(0.01)
                
                self.ui(lambda: self.log_terminal(f"Done. Sent {count} commands."))
                self.ui(lambda: messagebox.showinfo("Done", f"G-Code file executed.\n{count} commands sent."))

            threading.Thread(target=run_file, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def log_terminal(self, msg):
        self.term_log.config(state="normal")
        self.term_log.insert(tk.END, msg + "\n")
        self.term_log.see(tk.END)
        self.term_log.config(state="disabled")

# ================= RUN =================
if __name__ == "__main__":
    root = tk.Tk()
    PlotterApp(root)
    root.mainloop()

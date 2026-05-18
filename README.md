# 🤖 Neuro Plot — AI-Powered DIY CNC Plotter

A Python desktop application that turns a DIY 28BYJ-48 stepper-motor CNC plotter into an AI-powered drawing machine.

Just type **"draw a square"** and the plotter draws it. Type **"draw a house"** and it draws that too. The Google Gemini AI understands your request, generates the exact XY coordinates, and sends them directly to the hardware — no manual input needed.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Image to Plot** | Load any PNG/JPG, auto-trace edges, and plot them |
| **SVG Support** | Load SVG files and plot all paths directly |
| **Text Plotting** | Type text and watch the plotter write it out |
| **AI Drawing** | Ask Neuro AI to *"draw a circle"* or *"write Hello"* — powered by Gemini |
| **Handwriting Style** | Upload a handwriting sample; Gemini learns the style |
| **Voice Input** | Speak commands to the AI assistant (microphone required) |
| **G-Code Terminal** | Send raw G-code commands or load a `.gcode` file |
| **Live Preview** | See the drawing path in real-time before/during plotting |
| **Simulation Mode** | Test without hardware connected |
| **Emergency Stop** | One-click abort at any time |

---

## 🧠 How the AI Drawing Works

Neuro Plot uses **Google Gemini AI** as its brain. When you type a command in the AI Assistant tab, here's what happens:

```
You type:  "draw a square"
    ↓
Gemini AI interprets the request and generates a list of
exact plotter coordinates (MOVE / PEN_UP / PEN_DOWN actions)
    ↓
The app centres the drawing on the 100×100 mm workspace
    ↓
The coordinates are sent over serial to the Arduino
    ↓
The stepper motors move and the plotter physically draws it
```

### Example commands you can say:

| You say | What happens |
|---|---|
| `draw a square` | Plotter draws a square |
| `draw a circle` | Plotter draws a circle |
| `draw a star` | Plotter draws a 5-pointed star |
| `draw a house` | Plotter draws a simple house shape |
| `write HELLO` | Plotter writes the word in the current font style |
| `draw a smiley face` | Plotter draws a smiley |

You can also use **voice input** — click the 🎤 button and speak your command aloud.

After Gemini generates the drawing, click **"Send to Plotter →"** and it starts drawing immediately. The live preview canvas shows the path in real-time as the pen moves.

---

## 🛠️ Hardware

- Arduino Uno (or compatible)
- 2× 28BYJ-48 stepper motors + ULN2003 drivers (X and Y axes)
- 1× Servo motor (Z axis / pen lift)
- DIY frame (lead screw or belt drive, 100 × 100 mm workspace)

Upload one of the included Arduino sketches to your board:

| Sketch | Use |
|---|---|
| `arduino_plotter.ino` | Standard plotting firmware |
| `arduino_plotter_smooth.ino` | Smoother acceleration (recommended) |
| `z_axis_calibration.ino` | Z-axis servo tuning |

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/neuro-plot.git
cd neuro-plot
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your Gemini API key
Get a free key at <https://aistudio.google.com/app/apikey>, then:

```bash
# Windows
set GEMINI_API_KEY=your_key_here

# Mac / Linux
export GEMINI_API_KEY=your_key_here
```

> **Alternative:** Open `config.py` and paste your key into the empty string (don't commit this!).

### 5. Run the app
```bash
python main.py
```

---

## 📁 Project Structure

```
neuro-plot/
├── main.py                  # Main application window and UI
├── config.py                # API key + hardware config
├── serial_comm.py           # Serial communication with Arduino
├── motion_planner.py        # Step generation and drawing loop
├── image_processing.py      # Edge detection and contour extraction
├── ai_engine.py             # Gemini AI integration
├── vision_processor.py      # Handwriting style analysis (Gemini Vision)
├── handwriting.py           # Text → plotter actions
├── gcode_parser.py          # G-code interpreter
├── svg_processor.py         # SVG → contours
├── preview_canvas.py        # Live drawing preview widget
├── controller.py            # Pause / stop / abort controller
├── theme.py                 # UI colours and fonts
├── assets/                  # Logo and other images
├── font/                    # Custom fonts
├── arduino_plotter.ino      # Arduino firmware (standard)
├── arduino_plotter_smooth.ino  # Arduino firmware (smooth)
└── requirements.txt
```

---

## ⚙️ Settings

All motion parameters can be tuned inside the **Settings** tab without touching code:

- **Max Speed** — steps per second (500 – 10 000)
- **Acceleration** — steps per second² (1 000 – 20 000)
- **Pen Lift Distance** — Z-axis servo travel in steps
- **Steps per MM** — calibration value (default `89.8` for 28BYJ-48 with standard lead screw)

---

## 🔌 Connection

1. Upload the Arduino firmware
2. Plug in via USB
3. Click **Connect** in the app — it auto-detects the COM port
4. Use **Simulate** to run without hardware

---

## 📦 Dependencies

```
opencv-python    — image edge detection
Pillow           — image loading and display
pyserial         — Arduino serial communication
google-generativeai — Gemini AI (drawing + vision)
SpeechRecognition   — voice input (optional)
svgpathtools     — SVG file parsing
cairosvg         — SVG preview rendering (optional)
```

---

## 🙏 Acknowledgements

Built with Python, Tkinter, OpenCV, and the Google Gemini API.

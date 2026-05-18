import tkinter as tk
from tkinter import ttk
import serial
import time
import threading
from handwriting import text_to_actions

# ---------------- SERIAL ----------------
ser = None

def connect_serial():
    global ser
    try:
        # NOTE: You may need to change "COM3" to the correct port for your device
        ser = serial.Serial("COM3", 9600, timeout=1)
        time.sleep(2) # Wait for the Arduino to reset
        conn_status.config(text="● Connected", fg="#22c55e")
        status.config(text="Status: Connected to plotter")
    except serial.SerialException as e:
        conn_status.config(text="● Error", fg="#ef4444")
        status.config(text=f"Status: {e}")

def disconnect_serial():
    global ser
    if ser and ser.is_open:
        ser.close()
        conn_status.config(text="● Disconnected", fg="#ef4444")
        status.config(text="Status: Disconnected")

def send_command(command):
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        # A small delay to prevent overwhelming the Arduino, but a proper GRBL-style
        # ack/response would be more robust for complex firmwares.
        time.sleep(0.05)

# ---------------- UI ----------------
root = tk.Tk()
root.title("AI Handwriting Plotter")
root.geometry("700x500")
root.configure(bg="#f9fafb")

# ---------------- HEADER & CONNECTION ----------------
header_frame = tk.Frame(root, bg="#f9fafb")
header_frame.pack(pady=10)

tk.Label(
    header_frame, text="AI Handwriting Plotter",
    font=("Segoe UI", 20, "bold"),
    bg="#f9fafb", fg="#2563eb"
).pack(side="left", padx=10)

conn_status = tk.Label(header_frame, text="● Disconnected", font=("Segoe UI", 10), fg="#ef4444", bg="#f9fafb")
conn_status.pack(side="left", padx=10)

# ---------------- INPUT ----------------
frame = tk.Frame(root, bg="#f9fafb")
frame.pack()

tk.Label(frame, text="Enter text to plot:", bg="#f9fafb").pack()
text_entry = tk.Entry(frame, font=("Segoe UI", 12), width=40)
text_entry.pack(pady=5)

# ---------------- STATUS & PROGRESS ----------------
status = tk.Label(root, text="Status: Idle", font=("Segoe UI", 11), bg="#f9fafb", fg="#111827")
status.pack(pady=5)
progress = ttk.Progressbar(root, length=400)
progress.pack(pady=10)
eta_label = tk.Label(root, text="ETA: -- sec", bg="#f9fafb")
eta_label.pack()

# ---------------- DRAW FUNCTION ----------------
def start_plot():
    if not ser or not ser.is_open:
        status.config(text="Status: Not connected to plotter!")
        return
    threading.Thread(target=plot, daemon=True).start()

def plot():
    text = text_entry.get()
    if not text:
        status.config(text="Status: Please enter some text.")
        return

    actions = text_to_actions(text)
    total = len(actions)
    status.config(text="Drawing...")
    start_time = time.time()

    for i, action in enumerate(actions):
        cmd = action[0]
        if cmd == "PEN_UP":
            send_command("PEN UP")
        elif cmd == "PEN_DOWN":
            send_command("PEN DOWN")
        elif cmd == "MOVE":
            _, dx, dy = action
            send_command(f"MOVE {dx} {dy}")

        progress["value"] = (i + 1) / total * 100
        elapsed = time.time() - start_time
        eta = int((elapsed / (i + 1)) * (total - i - 1)) if i < total - 1 else 0
        eta_label.config(text=f"ETA: {eta} sec")
        root.update_idletasks()

    status.config(text="Status: Done ✔")
    progress["value"] = 0
    eta_label.config(text="ETA: -- sec")


# ---------------- BUTTONS ----------------
btn_frame = tk.Frame(root, bg="#f9fafb")
btn_frame.pack(pady=20)

tk.Button(
    btn_frame, text="Connect", font=("Segoe UI", 12), command=connect_serial
).pack(side="left", padx=10)

tk.Button(
    btn_frame, text="Disconnect", font=("Segoe UI", 12), command=disconnect_serial
).pack(side="left", padx=10)

tk.Button(
    btn_frame, text="Start Drawing", font=("Segoe UI", 12, "bold"),
    bg="#2563eb", fg="white", command=start_plot
).pack(side="left", padx=10)


# ---------------- WATERMARK ----------------
tk.Label(
    root, text="TechTitans", font=("Segoe UI", 9),
    fg="#9ca3af", bg="#f9fafb"
).pack(side="bottom", pady=5)

root.mainloop()
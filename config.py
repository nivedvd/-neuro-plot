# config.py — Neuro Plot configuration
#
# HOW TO SET YOUR API KEY (pick one):
#   Option 1 (recommended): Set an environment variable before running:
#       Windows:  set GEMINI_API_KEY=your_key_here
#       Mac/Linux: export GEMINI_API_KEY=your_key_here
#
#   Option 2 (local only, never commit): replace the empty string below
#       with your key, but make sure config.py stays in .gitignore.

import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # <-- put your key here if not using env vars

# Hardware Configuration
INVERT_X_AXIS = False  # Set to True to mirror the X axis if your hardware is reversed

"""
ReCAD Configuration
Contains API keys and settings for the ReCAD skill.
"""

import os
from pathlib import Path

# Load .env file if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# OpenAI API Key for Whisper transcription
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# FreeCAD Installation Path
FREECAD_PATH = "C:/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecadcmd.exe"

# Default Settings
DEFAULT_FPS = 1.5  # Frames per second for video extraction
DEFAULT_NUM_AGENTS = 5  # Number of parallel Claude agents for analysis
DEFAULT_UNITS = "mm"  # Default measurement units

# Output Directories
OUTPUT_BASE_DIR = "docs/outputs/recad"
TEMP_BASE_DIR = "temp/recad"

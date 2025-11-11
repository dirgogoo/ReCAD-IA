"""
ReCAD Configuration
Contains API keys and settings for the ReCAD skill.
"""

# OpenAI API Key for Whisper transcription
# Set via environment variable: export OPENAI_API_KEY="your-key-here"
import os
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

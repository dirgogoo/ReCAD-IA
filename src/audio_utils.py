"""
ReCAD Audio Utilities
Wrapper functions that automatically use config.py settings.
"""
from pathlib import Path
from typing import Dict, Any, Optional

import extract_audio
import config

# Import functions
_extract_audio = extract_audio.extract_audio_from_video
_transcribe = extract_audio.transcribe_audio_with_whisper
OPENAI_API_KEY = config.OPENAI_API_KEY


def extract_audio_from_video(video_path: Path, output_path: Path) -> Path:
    """
    Extract audio from video.
    Direct passthrough to extract_audio module.
    """
    return _extract_audio(video_path, output_path)


def transcribe_audio(
    audio_path: Path,
    language: str = "pt",
    granularity: str = "segment"
) -> Dict[str, Any]:
    """
    Transcribe audio using Whisper with API key from config.py.

    Args:
        audio_path: Path to audio file
        language: Language code (default: "pt")
        granularity: "word" or "segment" (default: "segment")

    Returns:
        Dict with 'text' and 'segments'
    """
    return _transcribe(
        audio_path=audio_path,
        language=language,
        granularity=granularity,
        api_key=OPENAI_API_KEY  # Use API key from config.py
    )


def extract_and_transcribe_video(
    video_path: Path,
    audio_output_path: Path,
    language: str = "pt"
) -> Dict[str, Any]:
    """
    Complete workflow: extract audio from video and transcribe it.

    Args:
        video_path: Path to video file
        audio_output_path: Where to save extracted audio
        language: Language for transcription (default: "pt")

    Returns:
        Dict with transcription results
    """
    # Extract audio
    audio_path = extract_audio_from_video(video_path, audio_output_path)

    # Transcribe
    result = transcribe_audio(audio_path, language=language)

    return result

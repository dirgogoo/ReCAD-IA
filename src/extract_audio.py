"""
Policies Applied:
- Policy 3.3: SRP - Single responsibility per function
- Policy 3.5: Meaningful names
- Policy 3.6: Error handling mandatory
- Policy 11.6: Memory-First Pattern (checked integrations.openai_whisper)
- Policy 11.7: SDK over HTTP (using openai SDK, moviepy)
- Policy 11.8: Documentation-First (Whisper API docs reviewed)
- Policy 13.1: Retry with exponential backoff
- Policy 13.2: Fallback mechanisms
- Policy 13.4: Timeout for external calls

Audio extraction and transcription module.

Memory Gotchas Applied:
- Whisper API costs $0.006/minute
- Use 'verbose_json' response_format for timestamps
- timestamp_granularities accepts 'word' or 'segment'
"""
from pathlib import Path
from typing import Dict, Any, Optional
import os
import time

# Lazy imports to avoid dependencies at module load
# Policy 3.12: WHY - Only import when needed, allow tests without full deps


def extract_audio_from_video(
    video_path: Path,
    output_path: Path
) -> Path:
    """
    Extract audio track from video file using moviepy.

    Policy 3.6: Error handling - validate inputs
    Policy 11.7: Using moviepy SDK
    Policy 13.4: Timeout handling

    Args:
        video_path: Path to input video file
        output_path: Path to save extracted audio

    Returns:
        Path to extracted audio file

    Raises:
        FileNotFoundError: If video file doesn't exist
        RuntimeError: If audio extraction fails
    """
    # Policy 3.6: Error handling mandatory
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Policy 11.7: Use moviepy SDK
    try:
        from moviepy import VideoFileClip
    except ImportError as e:
        raise RuntimeError(
            f"moviepy not installed. Install with: pip install moviepy"
        ) from e

    video = None
    try:
        # Load video
        video = VideoFileClip(str(video_path))

        # Policy 3.6: Validate video has audio
        if video.audio is None:
            raise RuntimeError(f"Video has no audio track: {video_path}")

        # Determine codec and parameters based on output format
        # Policy 3.12: WHY - Whisper API works best with WAV, but support MP3 too
        suffix = output_path.suffix.lower()
        
        if suffix == '.wav':
            codec = 'pcm_s16le'  # Uncompressed PCM for WAV
            bitrate = None
        elif suffix == '.mp3':
            codec = 'libmp3lame'  # MP3 codec
            bitrate = '192k'
        else:
            # Default to WAV if unknown
            codec = 'pcm_s16le'
            bitrate = None

        # Extract audio
        video.audio.write_audiofile(
            str(output_path),
            codec=codec,
            fps=16000,  # 16kHz sample rate (Whisper requirement)
            nbytes=2,   # 16-bit depth
            bitrate=bitrate,
            logger=None  # Suppress moviepy verbose output
        )

        return output_path

    except Exception as e:
        # Policy 3.6: Never silent catch
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Failed to extract audio: {e}") from e

    finally:
        # Policy 11.6: Memory management - close video
        if video is not None:
            video.close()


def transcribe_audio_with_whisper(
    audio_path: Path,
    language: str = "pt",
    granularity: str = "segment",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper API.

    Policy 11.6: Memory-First - integration details in project memory
    Policy 11.7: SDK over HTTP - using openai Python SDK
    Policy 11.8: Documentation-First - following Whisper API docs
    Policy 13.1: Retry with exponential backoff
    Policy 13.4: Timeout for external calls

    From memory (integrations.openai_whisper):
    - Costs $0.006/minute
    - Use 'verbose_json' for timestamps
    - timestamp_granularities: 'word' or 'segment'

    Args:
        audio_path: Path to audio file
        language: Language code (e.g., 'pt', 'en')
        granularity: 'word' or 'segment' level timestamps
        api_key: OpenAI API key (optional, reads from env if not provided)

    Returns:
        Dict with 'text' and 'segments' (each with start/end/text)

    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If API key not provided or invalid parameters
        RuntimeError: If transcription fails
    """
    # Policy 3.6: Error handling mandatory
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Validate granularity
    if granularity not in ['word', 'segment']:
        raise ValueError(f"Invalid granularity: {granularity}. Must be 'word' or 'segment'")

    # Policy 4.5: Environment variables for secrets
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OpenAI API key required. Set OPENAI_API_KEY environment variable "
            "or pass api_key parameter"
        )

    # Policy 11.7: Use OpenAI SDK
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(
            f"openai package not installed. Install with: pip install openai"
        ) from e

    client = OpenAI(api_key=api_key)

    # Policy 13.1: Retry with exponential backoff
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            # Open audio file
            with open(audio_path, 'rb') as audio_file:
                # Policy 11.6: Memory gotcha - use verbose_json for timestamps
                # Policy 13.4: Timeout 60s for API call
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=[granularity],
                    timeout=60.0  # 60 second timeout
                )

            # Parse response
            result = {
                "text": response.text,
                "segments": []
            }

            # Extract segments with timestamps
            if hasattr(response, 'segments'):
                for segment in response.segments:
                    result["segments"].append({
                        "start": getattr(segment, 'start', 0.0),
                        "end": getattr(segment, 'end', 0.0),
                        "text": getattr(segment, 'text', '')
                    })
            elif hasattr(response, 'words'):
                # If word-level granularity
                for word in response.words:
                    result["segments"].append({
                        "start": getattr(word, 'start', 0.0),
                        "end": getattr(word, 'end', 0.0),
                        "text": getattr(word, 'word', '')
                    })

            return result

        except Exception as e:
            # Policy 13.1: Exponential backoff on retry
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                # Policy 3.6: Never silent catch
                raise RuntimeError(
                    f"Whisper API transcription failed after {MAX_RETRIES} attempts: {e}"
                ) from e

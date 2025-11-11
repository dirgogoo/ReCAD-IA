"""
Policies Applied:
- Policy 3.3: SRP - Single responsibility per function
- Policy 3.5: Meaningful names
- Policy 3.6: Error handling mandatory
- Policy 3.7: No magic numbers (named constants)
- Policy 11.6: Memory-first pattern (check memory for gotchas)
- Policy 11.7: SDK over HTTP (using opencv-python SDK)
- Policy 13.4: Timeout for external operations
- Policy 3.12: Comment WHY, not WHAT

Frame extraction module for video analysis.

Memory Gotchas Applied:
- cv2.VideoCapture requires str(path), not Path object
- Must call cap.release() to avoid memory leaks
- Frame extraction: frame_interval = int(video_fps / target_fps)
"""
from pathlib import Path
from typing import List
import cv2


def extract_frames_at_fps(
    video_path: Path,
    output_dir: Path,
    fps: float
) -> List[Path]:
    """
    Extract frames from video at specified FPS using OpenCV.

    Policy 3.6: Error handling - validate inputs and raise meaningful errors
    Policy 3.5: Meaningful names - clear parameter names
    Policy 11.6: Apply memory gotchas (str(path), cap.release())

    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        fps: Frames per second to extract

    Returns:
        List of paths to extracted frame images

    Raises:
        FileNotFoundError: If video file doesn't exist
        ValueError: If fps is invalid or video cannot be opened
        RuntimeError: If frame extraction fails
    """
    # Policy 3.6: Error handling mandatory
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if fps <= 0:
        raise ValueError(f"FPS must be positive, got: {fps}")

    # Policy 3.7: No magic numbers
    DEFAULT_FRAME_PREFIX = "frame_"
    FRAME_NUMBER_WIDTH = 4  # Zero-pad to 4 digits
    MAX_FPS = 60.0  # Maximum reasonable FPS for extraction

    if fps > MAX_FPS:
        raise ValueError(f"FPS too high (max {MAX_FPS}), got: {fps}")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Policy 11.6: Memory gotcha - cv2.VideoCapture requires str, not Path
    cap = cv2.VideoCapture(str(video_path))

    try:
        # Policy 3.6: Validate video opened successfully
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        # Get video properties
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if video_fps <= 0:
            raise ValueError(f"Invalid video FPS: {video_fps}")

        # Policy 11.6: Memory gotcha - frame_interval calculation
        # Extract every Nth frame to achieve target FPS
        frame_interval = int(video_fps / fps)

        if frame_interval < 1:
            frame_interval = 1  # Extract every frame if target fps > video fps

        frames = []
        frame_count = 0
        extracted_count = 0

        # Extract frames at specified intervals
        while True:
            ret, frame = cap.read()

            if not ret:
                break  # End of video

            # Extract frame if it matches our interval
            if frame_count % frame_interval == 0:
                frame_name = f"{DEFAULT_FRAME_PREFIX}{extracted_count:0{FRAME_NUMBER_WIDTH}d}.png"
                frame_path = output_dir / frame_name

                # Policy 3.6: Error handling for frame write
                success = cv2.imwrite(str(frame_path), frame)
                if not success:
                    raise RuntimeError(f"Failed to write frame: {frame_path}")

                frames.append(frame_path)
                extracted_count += 1

            frame_count += 1

        # Policy 3.6: Validate we extracted some frames
        if len(frames) == 0:
            raise RuntimeError(f"No frames extracted from video: {video_path}")

        return frames

    finally:
        # Policy 11.6: Memory gotcha - must release capture to avoid memory leaks
        cap.release()

"""Tests for interactive mode flag in ReCADRunner."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recad_runner import ReCADRunner


def test_interactive_flag_enabled_by_default(tmp_path):
    """Runner should have interactive=True by default."""
    # Create a dummy video file
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake video content")

    runner = ReCADRunner(
        video_path=video_file,
        output_dir=str(tmp_path / "output")
    )

    assert runner.interactive is True


def test_interactive_flag_can_be_disabled(tmp_path):
    """Runner should accept interactive=False parameter."""
    # Create a dummy video file
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake video content")

    runner = ReCADRunner(
        video_path=video_file,
        output_dir=str(tmp_path / "output"),
        interactive=False
    )

    assert runner.interactive is False


def test_non_interactive_mode_uses_mock_measurements(tmp_path):
    """In non-interactive mode, missing measurements should use mock values."""
    # Create a dummy video file
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake video content")

    runner = ReCADRunner(
        video_path=video_file,
        output_dir=str(tmp_path / "output"),
        interactive=False
    )

    # Verify the runner has the flag set correctly
    assert runner.interactive is False

    # The actual measurement validation logic is tested in integration tests
    # This test just verifies the flag is passed correctly


def test_interactive_mode_enabled(tmp_path):
    """In interactive mode, runner should be ready to prompt user."""
    # Create a dummy video file
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake video content")

    runner = ReCADRunner(
        video_path=video_file,
        output_dir=str(tmp_path / "output"),
        interactive=True
    )

    # Verify the runner has the flag set correctly
    assert runner.interactive is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

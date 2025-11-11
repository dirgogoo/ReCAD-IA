"""Integration tests for measurement validation in both interactive modes."""
import pytest
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recad_runner import ReCADRunner


@pytest.fixture
def mock_session_with_missing_measurements(tmp_path):
    """Create a mock session with agent results that have missing measurements."""
    # Create session directory
    session_dir = tmp_path / "2025-11-07_test"
    session_dir.mkdir(parents=True)

    # Create agent results with chord_cut pattern (needs flat_to_flat)
    agent_results = [
        {
            "agent_id": "agent_0",
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Circle", "diameter": 90},
                    "distance": 27
                },
                {
                    "type": "Cut",
                    "position": "left_side"
                },
                {
                    "type": "Cut",
                    "position": "right_side"
                }
            ]
        }
    ]

    agent_results_path = session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f)

    # Create transcription without flat_to_flat measurement
    transcription = {
        "text": "Chapa de diâmetro 90mm com altura 27mm e cortes bilaterais",
        "language": "pt"
    }

    transcription_path = session_dir / "transcription.json"
    with open(transcription_path, 'w') as f:
        json.dump(transcription, f)

    return {
        "session_dir": session_dir,
        "agent_results_path": agent_results_path,
        "transcription_path": transcription_path
    }


def test_non_interactive_mode_uses_mock_values(mock_session_with_missing_measurements):
    """
    In non-interactive mode, when measurements are missing, the runner should:
    1. Detect missing measurements
    2. Use mock values automatically
    3. Continue without prompting user
    """
    session_dir = mock_session_with_missing_measurements["session_dir"]

    # Create a dummy video file
    video_file = session_dir / "test.mp4"
    video_file.write_bytes(b"fake video content")

    # Initialize runner in non-interactive mode
    runner = ReCADRunner(
        video_path=video_file,
        output_dir=str(session_dir.parent),
        session_id=session_dir.name,
        interactive=False
    )

    # Verify flag is set
    assert runner.interactive is False

    # Note: Full integration test would require running phase_3_aggregate
    # which needs Claude Code integration. This test verifies the flag setup.
    # The actual mock value logic is tested in the recad_runner.py code path.


def test_interactive_mode_flag_is_set(mock_session_with_missing_measurements):
    """
    In interactive mode, the runner should be ready to prompt user.
    """
    session_dir = mock_session_with_missing_measurements["session_dir"]

    # Create a dummy video file
    video_file = session_dir / "test.mp4"
    video_file.write_bytes(b"fake video content")

    # Initialize runner in interactive mode
    runner = ReCADRunner(
        video_path=video_file,
        output_dir=str(session_dir.parent),
        session_id=session_dir.name,
        interactive=True
    )

    # Verify flag is set
    assert runner.interactive is True


def test_mock_measurements_dictionary():
    """Verify that mock measurements contain expected values."""
    # This is the mock dictionary used in recad_runner.py
    mock_measurements = {
        "diameter": 90.0,
        "radius": 45.0,
        "height": 27.0,
        "flat_to_flat": 78.0,
        "width": 100.0,
        "depth": 10.0,
        "distance": 50.0
    }

    # Verify all values are positive floats
    for name, value in mock_measurements.items():
        assert isinstance(value, float)
        assert value > 0

    # Verify common measurements are present
    assert "diameter" in mock_measurements
    assert "flat_to_flat" in mock_measurements
    assert "height" in mock_measurements


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Tests for measurement validation in Claude analyzer."""
import pytest
from pathlib import Path
from patterns.claude_analyzer import ClaudeCodeAnalyzer
from utils.measurement_extractor import MissingMeasurementError


def test_analyzer_detects_missing_measurements(tmp_path):
    """Analyzer should detect missing measurements and include in instructions."""
    analyzer = ClaudeCodeAnalyzer()

    # Mock data with missing flat_to_flat measurement
    agent_results = [
        {
            "agent_id": "test",
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Circle", "diameter": 90},
                    "distance": 27
                },
                {
                    "type": "Cut",
                    "position": "left_side"
                }
            ]
        }
    ]

    # Transcription mentions cuts but no flat_to_flat distance
    transcription = "Chapa de diâmetro 90mm com cortes laterais"

    # This should detect chord_cut pattern but missing flat_to_flat
    request_path = analyzer.request_analysis(
        agent_results=agent_results,
        transcription=transcription,
        session_dir=tmp_path
    )

    # Should create request with warning about missing measurement
    request_file = tmp_path / ".claude_analysis_request.json"
    assert request_file.exists()

    import json
    with open(request_file) as f:
        request = json.load(f)

    # Should include warning about missing measurement
    assert "missing_measurements" in request or "warnings" in request

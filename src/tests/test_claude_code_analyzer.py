"""Tests for ClaudeCodeAnalyzer (new workflow)."""

import json
from pathlib import Path
from patterns.claude_analyzer import get_analyzer


def test_analyzer_creates_request_file(tmp_path):
    """Test that analyzer writes request file."""
    analyzer = get_analyzer()

    result = analyzer.request_analysis(
        agent_results=[{"test": "data"}],
        transcription="test transcription",
        session_dir=tmp_path
    )

    # Should create request file
    request_file = tmp_path / ".claude_analysis_request.json"
    assert request_file.exists()

    # Verify request structure
    with open(request_file) as f:
        request = json.load(f)

    assert request["status"] == "pending"
    assert request["task"] == "analyze_and_generate_partbuilder_code"
    assert request["agent_results"] == [{"test": "data"}]
    assert request["transcription"] == "test transcription"
    assert "instructions" in request


def test_analyzer_detects_existing_python_file(tmp_path):
    """Test that analyzer returns path if Python file exists."""
    analyzer = get_analyzer()

    # Create mock Python file
    python_file = tmp_path / "claude_analysis.py"
    python_file.write_text("# mock")

    result = analyzer.request_analysis(
        agent_results=[],
        transcription="",
        session_dir=tmp_path
    )

    assert result == python_file


def test_analyzer_returns_none_if_python_missing(tmp_path):
    """Test that analyzer returns None if Python not ready."""
    analyzer = get_analyzer()

    result = analyzer.request_analysis(
        agent_results=[],
        transcription="",
        session_dir=tmp_path
    )

    assert result is None

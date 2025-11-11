"""Integration test for Claude Code + PartBuilder workflow."""

import json
import subprocess
import sys
from pathlib import Path
import pytest


def test_partbuilder_code_execution(tmp_path):
    """Test executing Claude-generated PartBuilder code."""

    # Get the src directory path
    src_dir = Path(__file__).parent.parent

    # Create mock Claude Code output
    python_code = f'''
import json
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, r"{src_dir}")

from semantic_builder import PartBuilder

builder = PartBuilder("test_part")
builder.add_chord_cut_extrude(radius=45, flat_to_flat=78, height=27)

semantic = builder.to_dict()
with open(Path(__file__).parent / "semantic.json", 'w') as f:
    json.dump(semantic, f)

print("[OK] Generated semantic.json")
'''

    python_file = tmp_path / "claude_analysis.py"
    python_file.write_text(python_code)

    # Execute the code
    result = subprocess.run(
        [sys.executable, str(python_file)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Execution failed: {result.stderr}"
    assert "[OK] Generated" in result.stdout

    # Verify semantic.json was created
    semantic_path = tmp_path / "semantic.json"
    assert semantic_path.exists(), "semantic.json not created"

    with open(semantic_path) as f:
        semantic = json.load(f)

    assert "part" in semantic
    assert "features" in semantic["part"]


def test_request_file_creation(tmp_path):
    """Test that request file is created properly."""
    from patterns.claude_analyzer import get_analyzer

    analyzer = get_analyzer()

    agent_results = [{"test": "data"}]
    transcription = "test transcription"

    result = analyzer.request_analysis(
        agent_results=agent_results,
        transcription=transcription,
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
    assert request["agent_results"] == agent_results
    assert request["transcription"] == transcription


def test_fallback_when_python_missing(tmp_path):
    """Test fallback to Python patterns when Claude Code file missing."""
    from recad_runner import ReCADRunner

    # Create mock video file
    video_path = tmp_path / "test.mp4"
    video_path.touch()

    # Create session directory first
    session_dir = tmp_path / "test_session"
    session_dir.mkdir(parents=True)

    # Create session
    runner = ReCADRunner(
        video_path=video_path,
        session_id="test_session",
        output_dir=tmp_path
    )

    # Create mock agent results (simple rectangle)
    agent_results = [
        {
            "agent_id": "agent_1",
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Rectangle", "width": 100, "height": 100},
                    "distance": 10,
                    "operation": "new_body"
                }
            ],
            "confidence": 0.9
        }
    ]

    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f)

    # Run aggregation (should fallback to Python patterns)
    result = runner.phase_3_aggregate(agent_results_path)

    # Verify semantic.json was created via fallback
    assert result is not None
    assert "semantic_json_path" in result


def test_execution_error_fallback(tmp_path):
    """Test fallback when Claude Code execution fails."""
    from recad_runner import ReCADRunner

    # Create mock video file
    video_path = tmp_path / "test.mp4"
    video_path.touch()

    # Create session directory first
    session_dir = tmp_path / "test_session"
    session_dir.mkdir(parents=True)

    # Create session
    runner = ReCADRunner(
        video_path=video_path,
        session_id="test_session",
        output_dir=tmp_path
    )

    # Create mock agent results
    agent_results = [
        {
            "agent_id": "agent_1",
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Rectangle", "width": 100, "height": 100},
                    "distance": 10,
                    "operation": "new_body"
                }
            ],
            "confidence": 0.9
        }
    ]

    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f)

    # Create faulty Python file (will fail to execute)
    python_file = runner.session_dir / "claude_analysis.py"
    python_file.write_text("import nonexistent_module")

    # Run aggregation (should fallback after error)
    result = runner.phase_3_aggregate(agent_results_path)

    # Verify fallback succeeded
    assert result is not None
    assert "semantic_json_path" in result


def test_successful_claude_code_execution(tmp_path):
    """Test successful Claude Code execution with semantic.json creation."""
    from recad_runner import ReCADRunner

    # Create mock video file
    video_path = tmp_path / "test.mp4"
    video_path.touch()

    # Create session directory first
    session_dir = tmp_path / "test_session"
    session_dir.mkdir(parents=True)

    # Create session
    runner = ReCADRunner(
        video_path=video_path,
        session_id="test_session",
        output_dir=tmp_path
    )

    # Create mock agent results
    agent_results = [
        {
            "agent_id": "agent_1",
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Circle", "diameter": 90},
                    "distance": 27,
                    "operation": "new_body"
                }
            ],
            "confidence": 0.95
        }
    ]

    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f)

    # Create working Python file (simulates Claude Code output)
    python_code = f'''
import json
import sys
from pathlib import Path

# Simple semantic JSON generation
semantic = {{
    "part": {{
        "name": "test_part_claude_code",
        "units": "mm",
        "features": [
            {{
                "id": "extrude_1",
                "type": "Extrude",
                "sketch": {{
                    "plane": {{"type": "work_plane"}},
                    "geometry": [
                        {{"type": "Circle", "center": {{"x": 0, "y": 0}}, "diameter": {{"value": 90, "unit": "mm"}}}}
                    ]
                }},
                "parameters": {{
                    "distance": {{"value": 27, "unit": "mm"}},
                    "direction": "normal",
                    "operation": "new_body"
                }}
            }}
        ]
    }}
}}

with open(Path(__file__).parent / "semantic.json", 'w') as f:
    json.dump(semantic, f, indent=2)

print("[OK] Claude Code generated semantic.json")
'''

    python_file = runner.session_dir / "claude_analysis.py"
    python_file.write_text(python_code)

    # Run aggregation (should execute Claude Code successfully)
    result = runner.phase_3_aggregate(agent_results_path)

    # Verify Claude Code execution
    assert result is not None
    assert result["source"] == "claude_code_partbuilder"
    assert result["part_name"] == "test_part_claude_code"
    assert result["confidence"] == 0.95

    # Verify semantic.json exists
    semantic_path = Path(result["semantic_json_path"])
    assert semantic_path.exists()

    with open(semantic_path) as f:
        semantic = json.load(f)

    assert semantic["part"]["name"] == "test_part_claude_code"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

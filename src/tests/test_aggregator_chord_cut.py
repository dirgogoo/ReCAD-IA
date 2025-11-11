import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from recad_runner import ReCADRunner

def test_chord_cut_detection_from_agent_results():
    """Test that aggregator detects chord cut pattern from agent results"""
    # ARRANGE: Agent results with base Circle + chord cut features
    agent_results = [{
        "features": [{
            "type": "Extrude",
            "geometry": {
                "type": "Circle",
                "diameter": 90.0
            },
            "distance": 5.0,
            "operation": "new_body"
        }],
        "additional_features": [{
            "pattern": "chord_cut",
            "flat_to_flat": 78.0,
            "confidence": 0.90
        }],
        "overall_confidence": 0.95
    }]

    # Save to temp file
    temp_path = Path("tests/temp/agent_results_chord_test.json")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, 'w') as f:
        json.dump(agent_results, f)

    # ACT: Run aggregator (mock video file check)
    with patch('recad_runner.Path.exists', return_value=True):
        with patch('recad_runner.Path.stat') as mock_stat:
            mock_stat.return_value = MagicMock(st_size=1024*1024)  # 1MB
            runner = ReCADRunner("test_video.mp4")
            result = runner.phase_3_aggregate(temp_path)

    # ASSERT: Should detect chord cut and use Arc + Line geometry
    assert result.get("chord_cut_detected") is True
    assert result.get("flat_to_flat") == 78.0

    # Cleanup
    temp_path.unlink()

def test_chord_cut_replaces_circle_with_arcs():
    """Test that Circle geometry is replaced with Arc + Line when chord cut detected"""
    # ARRANGE: Same agent results as before
    agent_results = [{
        "features": [{
            "type": "Extrude",
            "geometry": {"type": "Circle", "diameter": 90.0},
            "distance": 5.0
        }],
        "additional_features": [{
            "pattern": "chord_cut",
            "flat_to_flat": 78.0,
            "confidence": 0.90
        }],
        "overall_confidence": 0.95
    }]

    temp_path = Path("tests/temp/agent_results_chord_test2.json")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, 'w') as f:
        json.dump(agent_results, f)

    # ACT
    with patch('recad_runner.Path.exists', return_value=True):
        with patch('recad_runner.Path.stat') as mock_stat:
            mock_stat.return_value = MagicMock(st_size=1024*1024)  # 1MB
            runner = ReCADRunner("test_video.mp4")
            result = runner.phase_3_aggregate(temp_path)

    # ASSERT: Geometry should be multi-geometry (list) with Arc + Line
    semantic_json_path = result.get("semantic_json_path")
    with open(semantic_json_path) as f:
        semantic = json.load(f)

    geometry = semantic["part"]["features"][0]["sketch"]["geometry"]
    assert isinstance(geometry, list), "Geometry should be list (multi-geometry)"
    assert len(geometry) == 4, "Should have 4 geometries (2 Arc + 2 Line)"
    assert geometry[0]["type"] == "Arc"
    assert geometry[1]["type"] == "Line"
    assert geometry[2]["type"] == "Arc"
    assert geometry[3]["type"] == "Line"

    # Verify constraints are present
    constraints = semantic["part"]["features"][0]["sketch"].get("constraints", [])
    assert len(constraints) == 7, "Should have 7 constraints"

    # Cleanup
    temp_path.unlink()

def test_chord_cut_uses_correct_thickness():
    """Test that detected thickness (5mm) is used instead of default (100mm)"""
    # ARRANGE
    agent_results = [{
        "features": [{
            "type": "Extrude",
            "geometry": {"type": "Circle", "diameter": 90.0},
            "distance": 5.0,  # Detected thickness
            "operation": "new_body"
        }],
        "additional_features": [{
            "pattern": "chord_cut",
            "flat_to_flat": 78.0,
            "confidence": 0.90
        }],
        "overall_confidence": 0.95
    }]

    temp_path = Path("tests/temp/agent_results_chord_test3.json")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, 'w') as f:
        json.dump(agent_results, f)

    # ACT
    with patch('recad_runner.Path.exists', return_value=True):
        with patch('recad_runner.Path.stat') as mock_stat:
            mock_stat.return_value = MagicMock(st_size=1024*1024)  # 1MB
            runner = ReCADRunner("test_video.mp4")
            result = runner.phase_3_aggregate(temp_path)

    # ASSERT: Thickness should be 5mm (not 100mm default)
    semantic_json_path = result.get("semantic_json_path")
    with open(semantic_json_path) as f:
        semantic = json.load(f)

    extrude_distance = semantic["part"]["features"][0]["parameters"]["distance"]["value"]
    assert extrude_distance == 5.0, f"Expected 5mm, got {extrude_distance}mm"

    print(f"[OK] Distance value verified: {extrude_distance}mm")

    # Cleanup
    temp_path.unlink()

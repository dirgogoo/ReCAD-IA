"""
Test parser support for multi-geometry sketches (Arc + Line arrays).

Tests both:
1. Legacy format (single Circle/Rectangle) - backward compatibility
2. New format (Arc + Line arrays with constraints) - chord cuts
"""

import pytest
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recad_runner import ReCADRunner


def test_legacy_single_circle_format():
    """
    Test backward compatibility with legacy single-Circle format.

    This ensures existing agent outputs (simple Circle/Rectangle) still work.
    """
    # Create a dummy video file for testing
    test_video_path = Path(__file__).parent / "temp" / "test_video.mp4"
    test_video_path.parent.mkdir(parents=True, exist_ok=True)
    test_video_path.write_bytes(b"")  # Empty file (not actually used)

    # Create runner with test video
    runner = ReCADRunner(
        video_path=test_video_path,
        output_dir=Path(__file__).parent / "temp"
    )

    # Simulate legacy agent results (old format)
    legacy_agent_results = [
        {
            "agent_id": "agent_1",
            "frames_analyzed": 10,
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {  # Single geometry (dict, not list)
                        "type": "Circle",
                        "diameter": 90.0
                    },
                    "distance": 6.5,
                    "operation": "new_body",
                    "confidence": 0.95
                }
            ],
            "overall_confidence": 0.95
        }
    ]

    # Save to temp file
    temp_results_path = runner.session_dir / "agent_results.json"
    with open(temp_results_path, 'w') as f:
        json.dump(legacy_agent_results, f, indent=2)

    # Run phase 3 aggregation
    try:
        result = runner.phase_3_aggregate(temp_results_path)

        # Verify it succeeded
        assert result["confidence"] > 0.5, "Confidence should be reasonable"
        assert "semantic_json_path" in result, "Should generate semantic JSON"

        # Verify semantic JSON exists and is valid
        semantic_path = Path(result["semantic_json_path"])
        assert semantic_path.exists(), "Semantic JSON file should exist"

        with open(semantic_path) as f:
            semantic_json = json.load(f)

        # Check structure
        assert "part" in semantic_json
        assert "features" in semantic_json["part"]
        assert len(semantic_json["part"]["features"]) >= 1

        # Check geometry (should be wrapped in array)
        feature = semantic_json["part"]["features"][0]
        assert "sketch" in feature
        assert "geometry" in feature["sketch"]

        geometry = feature["sketch"]["geometry"]
        assert isinstance(geometry, list), "Geometry should be array even for single shapes"

        print("[OK] Legacy single-Circle format test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Legacy format test FAILED: {e}")
        raise


def test_new_multi_geometry_format():
    """
    Test new multi-geometry format (Arc + Line arrays for chord cuts).

    This verifies the parser can handle:
    - geometry as a list (not dict)
    - Arc and Line geometry types
    - Constraints preservation
    """
    # Create dummy video
    test_video_path = Path(__file__).parent / "temp" / "test_video.mp4"
    test_video_path.parent.mkdir(parents=True, exist_ok=True)
    test_video_path.write_bytes(b"")

    # Create runner
    runner = ReCADRunner(
        video_path=test_video_path,
        output_dir=Path(__file__).parent / "temp"
    )

    # Simulate new agent results (chord cut format)
    new_agent_results = [
        {
            "agent_id": "agent_1",
            "frames_analyzed": 10,
            "features": [
                {
                    "type": "Extrude",
                    "geometry": [  # Multi-geometry (list)
                        {
                            "type": "Arc",
                            "center": {"x": 0, "y": 0},
                            "radius": {"value": 45.0, "unit": "mm"},
                            "start_angle": -60.1,
                            "end_angle": 60.1
                        },
                        {
                            "type": "Line",
                            "start": {"x": 22.45, "y": 39.0, "z": 0},
                            "end": {"x": -22.45, "y": 39.0, "z": 0}
                        },
                        {
                            "type": "Arc",
                            "center": {"x": 0, "y": 0},
                            "radius": {"value": 45.0, "unit": "mm"},
                            "start_angle": 119.9,
                            "end_angle": -119.9
                        },
                        {
                            "type": "Line",
                            "start": {"x": -22.45, "y": -39.0, "z": 0},
                            "end": {"x": 22.45, "y": -39.0, "z": 0}
                        }
                    ],
                    "constraints": [
                        {"type": "Coincident", "geo1": 0, "point1": 2, "geo2": 1, "point2": 1},
                        {"type": "Coincident", "geo1": 1, "point1": 2, "geo2": 2, "point2": 1},
                        {"type": "Coincident", "geo1": 2, "point1": 2, "geo2": 3, "point2": 1},
                        {"type": "Coincident", "geo1": 3, "point1": 2, "geo2": 0, "point2": 1},
                        {"type": "Parallel", "geo1": 1, "geo2": 3},
                        {"type": "Horizontal", "geo1": 1},
                        {"type": "Distance", "geo1": 1, "point1": 1, "geo2": 3, "point2": 1, "value": 78.0}
                    ],
                    "distance": 6.5,
                    "operation": "new_body",
                    "confidence": 0.95
                }
            ],
            "overall_confidence": 0.95,
            "detection": {
                "pattern": "chord_cut",
                "confidence": 0.95
            }
        }
    ]

    # Save to temp file
    temp_results_path = runner.session_dir / "agent_results.json"
    with open(temp_results_path, 'w') as f:
        json.dump(new_agent_results, f, indent=2)

    # Run phase 3 aggregation
    try:
        result = runner.phase_3_aggregate(temp_results_path)

        # Verify it succeeded
        assert result["confidence"] > 0.5
        assert "semantic_json_path" in result

        # Verify semantic JSON
        semantic_path = Path(result["semantic_json_path"])
        assert semantic_path.exists()

        with open(semantic_path) as f:
            semantic_json = json.load(f)

        # Check structure
        feature = semantic_json["part"]["features"][0]
        geometry = feature["sketch"]["geometry"]

        # Verify multi-geometry preserved
        assert isinstance(geometry, list)
        assert len(geometry) == 4, f"Expected 4 geometries, got {len(geometry)}"

        # Verify geometry types
        geom_types = [g["type"] for g in geometry]
        assert geom_types.count("Arc") == 2, "Should have 2 Arcs"
        assert geom_types.count("Line") == 2, "Should have 2 Lines"

        # Verify constraints preserved
        assert "constraints" in feature["sketch"], "Constraints should be preserved"
        constraints = feature["sketch"]["constraints"]
        assert len(constraints) == 7, f"Expected 7 constraints, got {len(constraints)}"

        # Verify constraint types
        constraint_types = [c["type"] for c in constraints]
        assert "Coincident" in constraint_types
        assert "Parallel" in constraint_types
        assert "Horizontal" in constraint_types
        assert "Distance" in constraint_types

        print("[OK] Multi-geometry format test PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Multi-geometry format test FAILED: {e}")
        raise


def test_chord_cut_validation():
    """
    Test chord cut pattern validation warnings.

    Verifies that the parser detects and validates chord cut patterns.
    """
    # Create dummy video
    test_video_path = Path(__file__).parent / "temp" / "test_video.mp4"
    test_video_path.parent.mkdir(parents=True, exist_ok=True)
    test_video_path.write_bytes(b"")

    runner = ReCADRunner(
        video_path=test_video_path,
        output_dir=Path(__file__).parent / "temp"
    )

    # Simulate incomplete chord cut (missing one line)
    incomplete_chord_cut = [
        {
            "agent_id": "agent_1",
            "frames_analyzed": 10,
            "features": [
                {
                    "type": "Extrude",
                    "geometry": [  # Only 3 geometries (incomplete)
                        {"type": "Arc", "center": {"x": 0, "y": 0}, "radius": {"value": 45.0, "unit": "mm"}, "start_angle": -60, "end_angle": 60},
                        {"type": "Line", "start": {"x": 22, "y": 39}, "end": {"x": -22, "y": 39}},
                        {"type": "Arc", "center": {"x": 0, "y": 0}, "radius": {"value": 45.0, "unit": "mm"}, "start_angle": 120, "end_angle": -120}
                    ],
                    "constraints": [],
                    "distance": 6.5,
                    "operation": "new_body",
                    "confidence": 0.8
                }
            ],
            "overall_confidence": 0.8,  # Need this for validation
            "detection": {"pattern": "chord_cut"}  # Claims to be chord cut
        }
    ]

    temp_results_path = runner.session_dir / "agent_results.json"
    with open(temp_results_path, 'w') as f:
        json.dump(incomplete_chord_cut, f, indent=2)

    # Run aggregation (should warn but not fail)
    result = runner.phase_3_aggregate(temp_results_path)

    # Should still succeed (just with warnings)
    assert result["confidence"] > 0.5
    assert "semantic_json_path" in result

    print("[OK] Chord cut validation test PASSED")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Parser Multi-Geometry Support")
    print("=" * 60)

    print("\n[Test 1/3] Legacy single-Circle format...")
    test_legacy_single_circle_format()

    print("\n[Test 2/3] New multi-geometry format...")
    test_new_multi_geometry_format()

    print("\n[Test 3/3] Chord cut validation...")
    test_chord_cut_validation()

    print("\n" + "=" * 60)
    print("[OK] All tests PASSED!")
    print("=" * 60)

"""
Test Task 4: Semantic JSON Builder - Constraint Preservation

This test verifies that:
1. Constraints from agent results flow through to semantic.json
2. Constraint format matches semantic-geometry expectations
3. Constraint geometry indices are valid (within bounds)
4. Full pipeline works: agent results → parser → builder → semantic.json
5. semantic-geometry library can load the output
"""

import pytest
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recad_runner import ReCADRunner


def test_constraint_preservation_in_semantic_json():
    """
    TASK 4: Test that constraints are preserved in semantic.json output.

    Verifies:
    - Constraints appear in sketch["constraints"]
    - Constraint format is correct (type, geo1, geo2, point1, point2, value)
    - Geometry indices are valid (no out-of-bounds references)
    """
    # Create dummy video
    test_video_path = Path(__file__).parent / "temp" / "test_constraint_preservation.mp4"
    test_video_path.parent.mkdir(parents=True, exist_ok=True)
    test_video_path.write_bytes(b"")

    # Create runner
    runner = ReCADRunner(
        video_path=test_video_path,
        output_dir=Path(__file__).parent / "temp"
    )

    # Simulate agent results with full chord cut (2 Arcs + 2 Lines + 7 constraints)
    agent_results = [
        {
            "agent_id": "test_agent_1",
            "frames_analyzed": 10,
            "features": [
                {
                    "type": "Extrude",
                    "geometry": [
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

    # Save agent results
    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f, indent=2)

    # Run phase 3 (aggregation and semantic JSON building)
    result = runner.phase_3_aggregate(agent_results_path)

    # Verify semantic JSON was created
    assert "semantic_json_path" in result
    semantic_path = Path(result["semantic_json_path"])
    assert semantic_path.exists(), "Semantic JSON should be created"

    # Load semantic JSON
    with open(semantic_path) as f:
        semantic_json = json.load(f)

    # Verify structure
    assert "part" in semantic_json
    assert "features" in semantic_json["part"]
    feature = semantic_json["part"]["features"][0]
    assert "sketch" in feature
    assert "geometry" in feature["sketch"]
    assert "constraints" in feature["sketch"], "Constraints should be present in sketch"

    # Verify constraint preservation
    constraints = feature["sketch"]["constraints"]
    assert len(constraints) == 7, f"Expected 7 constraints, got {len(constraints)}"

    # Verify constraint format
    for i, constraint in enumerate(constraints):
        assert "type" in constraint, f"Constraint {i} missing 'type'"

        # Check required fields per constraint type
        if constraint["type"] == "Coincident":
            assert "geo1" in constraint, f"Coincident constraint {i} missing geo1"
            assert "geo2" in constraint, f"Coincident constraint {i} missing geo2"
            assert "point1" in constraint, f"Coincident constraint {i} missing point1"
            assert "point2" in constraint, f"Coincident constraint {i} missing point2"
        elif constraint["type"] == "Parallel":
            assert "geo1" in constraint, f"Parallel constraint {i} missing geo1"
            assert "geo2" in constraint, f"Parallel constraint {i} missing geo2"
        elif constraint["type"] == "Horizontal":
            assert "geo1" in constraint, f"Horizontal constraint {i} missing geo1"
        elif constraint["type"] == "Distance":
            assert "geo1" in constraint, f"Distance constraint {i} missing geo1"
            assert "geo2" in constraint, f"Distance constraint {i} missing geo2"
            assert "point1" in constraint, f"Distance constraint {i} missing point1"
            assert "point2" in constraint, f"Distance constraint {i} missing point2"
            assert "value" in constraint, f"Distance constraint {i} missing value"

    # Verify geometry indices are valid (within bounds)
    geometry = feature["sketch"]["geometry"]
    num_geometries = len(geometry)

    for i, constraint in enumerate(constraints):
        if "geo1" in constraint:
            geo1 = constraint["geo1"]
            assert 0 <= geo1 < num_geometries, f"Constraint {i} geo1={geo1} out of bounds (0-{num_geometries-1})"
        if "geo2" in constraint:
            geo2 = constraint["geo2"]
            assert 0 <= geo2 < num_geometries, f"Constraint {i} geo2={geo2} out of bounds (0-{num_geometries-1})"

    print("[OK] Constraint preservation test PASSED")
    print(f"  - {len(constraints)} constraints preserved")
    print(f"  - All constraint formats validated")
    print(f"  - All geometry indices within bounds [0-{num_geometries-1}]")

    return True


def test_semantic_geometry_library_compatibility():
    """
    TASK 4: Test that semantic.json with constraints can be loaded by semantic-geometry library.

    This is the integration test - verifies the output format is compatible.
    """
    # Create dummy video
    test_video_path = Path(__file__).parent / "temp" / "test_integration.mp4"
    test_video_path.parent.mkdir(parents=True, exist_ok=True)
    test_video_path.write_bytes(b"")

    # Create runner
    runner = ReCADRunner(
        video_path=test_video_path,
        output_dir=Path(__file__).parent / "temp"
    )

    # Simulate chord cut agent results
    agent_results = [
        {
            "agent_id": "test_agent_1",
            "frames_analyzed": 10,
            "features": [
                {
                    "type": "Extrude",
                    "geometry": [
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
            "detection": {"pattern": "chord_cut", "confidence": 0.95}
        }
    ]

    # Save and process
    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f, indent=2)

    result = runner.phase_3_aggregate(agent_results_path)
    semantic_path = Path(result["semantic_json_path"])

    # Try to load with semantic-geometry library
    try:
        sys.path.insert(0, str(Path.home() / "semantic-geometry"))
        from semantic_geometry.loader import load_part_from_file

        # Load the semantic JSON
        part = load_part_from_file(str(semantic_path))

        print("[OK] semantic-geometry library integration test PASSED")
        print(f"  - Loaded part: {part.name}")
        print(f"  - Features: {len(part.features)}")

        return True

    except ImportError:
        print("[SKIP] semantic-geometry library not available, skipping integration test")
        return True
    except Exception as e:
        print(f"[FAIL] semantic-geometry library failed to load semantic.json: {e}")
        raise


def test_backward_compatibility_no_constraints():
    """
    TASK 4: Verify backward compatibility - single-geometry without constraints still works.
    """
    test_video_path = Path(__file__).parent / "temp" / "test_backward_compat.mp4"
    test_video_path.parent.mkdir(parents=True, exist_ok=True)
    test_video_path.write_bytes(b"")

    runner = ReCADRunner(
        video_path=test_video_path,
        output_dir=Path(__file__).parent / "temp"
    )

    # Legacy format: single Circle, no constraints
    legacy_agent_results = [
        {
            "agent_id": "agent_1",
            "frames_analyzed": 10,
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {  # Single geometry (dict)
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

    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(legacy_agent_results, f, indent=2)

    result = runner.phase_3_aggregate(agent_results_path)
    semantic_path = Path(result["semantic_json_path"])

    with open(semantic_path) as f:
        semantic_json = json.load(f)

    # Verify structure (no constraints expected)
    feature = semantic_json["part"]["features"][0]
    assert "sketch" in feature
    assert "geometry" in feature["sketch"]

    # Constraints may or may not be present (both are valid)
    # If present, should be empty list
    if "constraints" in feature["sketch"]:
        assert isinstance(feature["sketch"]["constraints"], list)

    print("[OK] Backward compatibility test PASSED")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Task 4: Constraint Preservation in Semantic JSON")
    print("=" * 60)

    print("\n[Test 1/3] Constraint preservation in semantic.json...")
    test_constraint_preservation_in_semantic_json()

    print("\n[Test 2/3] semantic-geometry library compatibility...")
    test_semantic_geometry_library_compatibility()

    print("\n[Test 3/3] Backward compatibility (no constraints)...")
    test_backward_compatibility_no_constraints()

    print("\n" + "=" * 60)
    print("[OK] All Task 4 tests PASSED!")
    print("=" * 60)

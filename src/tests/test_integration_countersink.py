"""
Integration tests for countersink pattern detection in full pipeline.

Countersinks are two-stage holes with conical outer cut (for flat-head screws)
and cylindrical inner cut (for screw shaft). Common angles: 82°, 90°, 100°, 120°.
"""

import pytest
from patterns.countersink import CountersinkPattern
from patterns.base import PatternMatch


def test_countersink_integration_direct_geometry():
    """Test countersink detection from direct Countersink geometry in agent results."""
    # Simulate agent results with Countersink geometry
    agent_results = [{
        "frame_analysis": {
            "primary_shape": "Rectangle",
            "dimensions": {"width": 100, "height": 100, "thickness": 20}
        },
        "features": [
            {
                "type": "Extrude",
                "geometry": {
                    "type": "Rectangle",
                    "width": {"value": 100, "unit": "mm"},
                    "height": {"value": 100, "unit": "mm"}
                },
                "parameters": {
                    "distance": {"value": 20, "unit": "mm"},
                    "direction": "normal"
                }
            },
            {
                "type": "Cut",
                "geometry": {
                    "type": "Countersink",
                    "outer_diameter": {"value": 16.0, "unit": "mm"},
                    "inner_diameter": {"value": 8.0, "unit": "mm"},
                    "angle": {"value": 82.0, "unit": "degrees"},
                    "center": {"x": 40, "y": 40}
                },
                "parameters": {
                    "outer_depth": {"value": 5.0, "unit": "mm"},
                    "inner_depth": {"value": 15.0, "unit": "mm"}
                }
            }
        ]
    }]

    transcription = "Placa com furo escareado cônico para parafuso de cabeça chata"

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results, transcription)

    assert match is not None, "Should detect countersink from direct geometry"
    assert match.pattern_name == "countersink"
    assert match.confidence >= 0.95  # High confidence with audio
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0
    assert match.parameters["angle"] == 82.0
    assert match.parameters["outer_depth"] == 5.0
    assert match.parameters["inner_depth"] == 15.0

    # Test geometry generation
    geometry = pattern.generate_geometry(match)
    assert "chamfer_cut" in geometry
    assert "circle_cut" in geometry
    assert geometry["chamfer_cut"]["angle"] == 82.0
    assert geometry["circle_cut"]["cut_distance"] == 10.0  # 15 - 5 = 10

    # Test feature filtering
    all_features = agent_results[0]["features"]
    filtered = pattern.filter_features(all_features, match)
    assert len(filtered) == 1  # Only Extrude remains
    assert filtered[0]["type"] == "Extrude"


def test_countersink_integration_chamfer_circle_inference():
    """Test countersink detection inferred from Chamfer + Circle cuts at same center."""
    agent_results = [{
        "features": [
            {
                "type": "Extrude",
                "geometry": {"type": "Circle", "diameter": {"value": 120, "unit": "mm"}},
                "parameters": {"distance": {"value": 25, "unit": "mm"}}
            },
            # Chamfer cut (conical outer)
            {
                "type": "Cut",
                "geometry": {
                    "type": "Chamfer",
                    "diameter": {"value": 16.0, "unit": "mm"},
                    "angle": {"value": 82.0, "unit": "degrees"},
                    "center": {"x": 0, "y": 0}
                },
                "parameters": {
                    "depth": {"value": 5.0, "unit": "mm"}
                }
            },
            # Circle cut (cylindrical inner)
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 0, "y": 0}
                },
                "parameters": {
                    "distance": {"value": 10.0, "unit": "mm"}  # Relative depth
                }
            }
        ]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    assert match is not None, "Should detect countersink from Chamfer + Circle"
    assert match.pattern_name == "countersink"
    assert match.confidence >= 0.85
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0
    assert match.parameters["angle"] == 82.0
    assert match.parameters["outer_depth"] == 5.0

    # Test feature filtering removes both Chamfer and Circle
    all_features = agent_results[0]["features"]
    filtered = pattern.filter_features(all_features, match)
    assert len(filtered) == 1  # Only Extrude remains
    assert filtered[0]["type"] == "Extrude"


@pytest.mark.skip(reason="Manual test - requires real video with countersink")
def test_countersink_real_video_analysis():
    """
    Placeholder for manual testing with real video.

    To test manually:
    1. Record video showing part with countersink hole (82° conical + cylindrical)
    2. Run ReCAD pipeline: python recad_runner.py video.mp4
    3. Verify agent_results.json contains Countersink or Chamfer+Circle cuts
    4. Verify pattern detection in output
    5. Verify semantic.json has chamfer_cut and circle_cut features at same center
    6. Open .FCStd in FreeCAD and verify countersink geometry (82° cone)
    7. Check that screw head would sit flush with surface
    """
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

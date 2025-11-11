"""
Integration tests for counterbore pattern detection in full pipeline.
"""

import pytest
from patterns.counterbore import CounterborePattern
from patterns.base import PatternMatch


def test_counterbore_integration_direct_geometry():
    """Test counterbore detection from direct Counterbore geometry in agent results."""
    # Simulate agent results with Counterbore geometry
    agent_results = [{
        "frame_analysis": {
            "primary_shape": "Rectangle",
            "dimensions": {"width": 80, "height": 80, "thickness": 15}
        },
        "features": [
            {
                "type": "Extrude",
                "geometry": {
                    "type": "Rectangle",
                    "width": {"value": 80, "unit": "mm"},
                    "height": {"value": 80, "unit": "mm"}
                },
                "parameters": {
                    "distance": {"value": 15, "unit": "mm"},
                    "direction": "normal"
                }
            },
            {
                "type": "Cut",
                "geometry": {
                    "type": "Counterbore",
                    "outer_diameter": {"value": 16.0, "unit": "mm"},
                    "inner_diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 30, "y": 30}
                },
                "parameters": {
                    "outer_depth": {"value": 6.0, "unit": "mm"},
                    "inner_depth": {"value": 15.0, "unit": "mm"}
                }
            }
        ]
    }]

    transcription = "Placa com furo escareado de 16 milímetros externo e 8 interno"

    pattern = CounterborePattern()
    match = pattern.detect(agent_results, transcription)

    assert match is not None, "Should detect counterbore from direct geometry"
    assert match.pattern_name == "counterbore"
    assert match.confidence >= 0.95  # High confidence with audio
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0
    assert match.parameters["outer_depth"] == 6.0
    assert match.parameters["inner_depth"] == 15.0

    # Test geometry generation
    geometry = pattern.generate_geometry(match)
    assert "outer_cut" in geometry
    assert "inner_cut" in geometry
    assert geometry["inner_cut"]["cut_distance"] == 9.0  # 15 - 6 = 9

    # Test feature filtering
    all_features = agent_results[0]["features"]
    filtered = pattern.filter_features(all_features, match)
    assert len(filtered) == 1  # Only Extrude remains
    assert filtered[0]["type"] == "Extrude"


def test_counterbore_integration_two_cuts():
    """Test counterbore detection from two sequential Circle cuts."""
    agent_results = [{
        "features": [
            {
                "type": "Extrude",
                "geometry": {"type": "Circle", "diameter": {"value": 100, "unit": "mm"}},
                "parameters": {"distance": {"value": 20, "unit": "mm"}}
            },
            # Outer cut (larger, shallow)
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 20.0, "unit": "mm"},
                    "center": {"x": 0, "y": 0}
                },
                "parameters": {
                    "cut_type": "distance",
                    "distance": {"value": 8.0, "unit": "mm"}
                }
            },
            # Inner cut (smaller, deeper)
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 10.0, "unit": "mm"},
                    "center": {"x": 0, "y": 0}
                },
                "parameters": {
                    "cut_type": "distance",
                    "distance": {"value": 20.0, "unit": "mm"}
                }
            }
        ]
    }]

    pattern = CounterborePattern()
    match = pattern.detect(agent_results)

    assert match is not None, "Should detect counterbore from two cuts"
    assert match.pattern_name == "counterbore"
    assert match.confidence >= 0.85
    assert match.parameters["outer_diameter"] == 20.0
    assert match.parameters["inner_diameter"] == 10.0


@pytest.mark.skip(reason="Manual test - requires real video with counterbore")
def test_counterbore_real_video_analysis():
    """
    Placeholder for manual testing with real video.

    To test manually:
    1. Record video showing part with counterbore hole
    2. Run ReCAD pipeline: python recad_runner.py video.mp4
    3. Verify agent_results.json contains Counterbore or two Circle cuts
    4. Verify pattern detection in output
    5. Verify semantic.json has two circle_cut features at same center
    6. Open .FCStd in FreeCAD and verify counterbore geometry
    """
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

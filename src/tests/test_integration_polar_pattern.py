"""
Integration test for polar hole pattern detection in ReCAD pipeline.

Tests end-to-end workflow:
1. Video analysis (mocked with 6 holes in circle)
2. Polar pattern detection
3. Semantic JSON generation with multiple holes
"""

import pytest
import math
from pathlib import Path
from patterns.polar_hole import PolarHolePattern


def test_polar_pattern_integration_6_holes():
    """
    Test polar pattern detection with 6 holes at 60° intervals.

    Simulates flange with bolt circle.
    """
    # Arrange - Mock agent results (6 holes in circle)
    pattern_radius = 30.0
    hole_diameter = 8.0
    hole_count = 6

    holes = []
    for i in range(hole_count):
        angle_rad = math.radians(i * 60)
        x = pattern_radius * math.cos(angle_rad)
        y = pattern_radius * math.sin(angle_rad)
        holes.append({
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "center": {"x": round(x, 2), "y": round(y, 2)},
                "diameter": {"value": hole_diameter, "unit": "mm"}
            },
            "parameters": {"cut_type": "through_all"}
        })

    agent_results = [{
        "features": [
            {
                "type": "Extrude",
                "geometry": {"type": "Circle", "diameter": {"value": 100.0}},
                "parameters": {"distance": {"value": 10.0}}
            }
        ] + holes
    }]

    transcription = "flange com 6 furos em círculo, raio de 30 milímetros"

    # Act - Detect pattern
    pattern = PolarHolePattern()
    match = pattern.detect(agent_results, transcription)

    # Assert - Pattern detected
    assert match is not None, "Should detect polar pattern"
    assert match.pattern_name == "polar_hole_pattern"
    assert match.confidence >= 0.85
    assert match.parameters["count"] == 6
    assert match.parameters["diameter"] == 8.0
    assert abs(match.parameters["radius"] - 30.0) < 1.0

    # Generate geometry
    geometry = pattern.generate_geometry(match)
    assert "holes" in geometry
    assert len(geometry["holes"]) == 6

    # Verify hole positions
    for i, hole in enumerate(geometry["holes"]):
        expected_angle = math.radians(i * 60)
        expected_x = pattern_radius * math.cos(expected_angle)
        expected_y = pattern_radius * math.sin(expected_angle)

        actual_x, actual_y = hole["center"]
        assert abs(actual_x - expected_x) < 0.5
        assert abs(actual_y - expected_y) < 0.5


def test_polar_pattern_integration_4_holes_square():
    """
    Test polar pattern with 4 holes at 90° intervals (square on circle).
    """
    # Arrange
    pattern_radius = 25.0
    hole_diameter = 10.0
    holes = []

    for i in range(4):
        angle_rad = math.radians(i * 90)
        x = pattern_radius * math.cos(angle_rad)
        y = pattern_radius * math.sin(angle_rad)
        holes.append({
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "center": {"x": round(x, 2), "y": round(y, 2)},
                "diameter": {"value": hole_diameter, "unit": "mm"}
            },
            "parameters": {"cut_type": "through_all"}
        })

    agent_results = [{"features": holes}]

    # Act
    pattern = PolarHolePattern()
    match = pattern.detect(agent_results, transcription=None)

    # Assert
    assert match is not None
    assert match.parameters["count"] == 4
    assert abs(match.parameters["angle_step"] - 90.0) < 1.0


@pytest.mark.skipif(True, reason="Requires real video file")
def test_polar_pattern_real_video_analysis():
    """
    Manual test with real video containing polar hole pattern.

    Instructions:
    1. Record 10s video showing part with circular hole arrangement
    2. Update video_path below
    3. Remove @pytest.mark.skipif decorator
    4. Run: pytest tests/test_integration_polar_pattern.py::test_polar_pattern_real_video_analysis -v -s
    """
    video_path = Path("path/to/test/video_with_bolt_circle.mp4")
    # TODO: Implement when real video available
    pass

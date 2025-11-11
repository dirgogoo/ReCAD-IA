"""
Test suite for polar hole pattern detection.

Tests PolarHolePattern detector that identifies circular arrangements of holes from:
1. Multiple Cut operations with same diameter
2. Equal angular spacing around center point
3. Audio transcription with pattern cues ("6 furos", "circular", "bolt circle")

TDD Phase: RED - Test written before implementation
"""

import pytest
import math
from patterns.polar_hole import PolarHolePattern
from patterns.base import PatternMatch


def test_polar_pattern_detects_6_holes_60_degrees():
    """
    Test detection of 6 holes equally spaced at 60° intervals.

    Given:
        - 6 Cut operations with Circle geometry (all diameter 8mm)
        - Centers at radius 30mm from origin
        - Angular spacing: 60° (360°/6)
        - Audio: "6 furos em círculo"

    Expected:
        - Pattern detected as "polar_hole_pattern"
        - Confidence >= 0.85
        - Parameters contain: count=6, diameter=8.0, radius=30.0, angle_step=60.0
    """
    # Arrange
    pattern = PolarHolePattern()

    # Calculate 6 hole positions at 30mm radius, 60° apart
    radius = 30.0
    diameter = 8.0
    holes = []
    for i in range(6):
        angle_rad = math.radians(i * 60)  # 0°, 60°, 120°, 180°, 240°, 300°
        x = radius * math.cos(angle_rad)
        y = radius * math.sin(angle_rad)
        holes.append({
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "center": {"x": round(x, 2), "y": round(y, 2)},
                "diameter": {"value": diameter, "unit": "mm"}
            },
            "parameters": {"cut_type": "through_all"}
        })

    agent_results = [{"features": holes}]
    transcription = "placa com 6 furos em círculo"

    # Act
    result = pattern.detect(agent_results, transcription)

    # Assert
    assert result is not None, "Should detect polar hole pattern"
    assert result.pattern_name == "polar_hole_pattern"
    assert result.confidence >= 0.85
    assert result.parameters["count"] == 6
    assert result.parameters["diameter"] == 8.0
    assert abs(result.parameters["radius"] - 30.0) < 0.5  # Tolerance for float
    assert abs(result.parameters["angle_step"] - 60.0) < 1.0


def test_polar_pattern_detects_4_holes_90_degrees():
    """
    Test detection of 4 holes at 90° intervals (square pattern on circle).

    Given:
        - 4 Cut operations (diameter 10mm)
        - Centers at radius 25mm
        - Angular spacing: 90°

    Expected:
        - Pattern detected with count=4, angle_step=90.0
    """
    # Arrange
    pattern = PolarHolePattern()
    radius = 25.0
    diameter = 10.0
    holes = []
    for i in range(4):
        angle_rad = math.radians(i * 90)  # 0°, 90°, 180°, 270°
        x = radius * math.cos(angle_rad)
        y = radius * math.sin(angle_rad)
        holes.append({
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "center": {"x": round(x, 2), "y": round(y, 2)},
                "diameter": {"value": diameter, "unit": "mm"}
            },
            "parameters": {"cut_type": "through_all"}
        })

    agent_results = [{"features": holes}]

    # Act
    result = pattern.detect(agent_results, transcription=None)

    # Assert
    assert result is not None
    assert result.parameters["count"] == 4
    assert abs(result.parameters["angle_step"] - 90.0) < 1.0


def test_polar_pattern_no_false_positive_on_random_holes():
    """
    Test that random holes don't trigger polar pattern detection.

    Given:
        - 5 holes with same diameter
        - Random positions (not circular pattern)

    Expected:
        - No pattern detected (returns None)
    """
    # Arrange
    pattern = PolarHolePattern()
    holes = [
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": 10, "y": 5}, "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": 15, "y": 20}, "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": 30, "y": 8}, "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": 5, "y": 25}, "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": 22, "y": 12}, "diameter": {"value": 8}}},
    ]
    agent_results = [{"features": holes}]

    # Act
    result = pattern.detect(agent_results, transcription=None)

    # Assert
    assert result is None, "Should NOT detect pattern on random holes"


def test_polar_pattern_minimum_3_holes():
    """
    Test that pattern requires minimum 3 holes.

    Given:
        - Only 2 holes (not enough for circular pattern)

    Expected:
        - No pattern detected
    """
    # Arrange
    pattern = PolarHolePattern()
    holes = [
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": 30, "y": 0}, "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "center": {"x": -30, "y": 0}, "diameter": {"value": 8}}},
    ]
    agent_results = [{"features": holes}]

    # Act
    result = pattern.detect(agent_results, transcription=None)

    # Assert
    assert result is None, "Should require minimum 3 holes for polar pattern"


def test_polar_pattern_different_diameters_no_match():
    """
    Test that holes with different diameters don't form pattern.

    Given:
        - 4 holes in circular arrangement
        - Different diameters (8mm, 10mm, 8mm, 10mm)

    Expected:
        - No pattern detected (diameters must match)
    """
    # Arrange
    pattern = PolarHolePattern()
    radius = 25.0
    holes = []
    diameters = [8.0, 10.0, 8.0, 10.0]
    for i in range(4):
        angle_rad = math.radians(i * 90)
        x = radius * math.cos(angle_rad)
        y = radius * math.sin(angle_rad)
        holes.append({
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "center": {"x": round(x, 2), "y": round(y, 2)},
                "diameter": {"value": diameters[i], "unit": "mm"}
            }
        })

    agent_results = [{"features": holes}]

    # Act
    result = pattern.detect(agent_results, transcription=None)

    # Assert
    assert result is None, "Should require matching diameters"


def test_polar_pattern_generate_geometry():
    """
    Test geometry generation returns multiple hole parameters.

    Given:
        - Pattern match with 6 holes at 30mm radius

    Expected:
        - Geometry dict with list of hole centers
        - Each center calculated from radius and angle
    """
    # Arrange
    pattern = PolarHolePattern()
    match = PatternMatch(
        pattern_name="polar_hole_pattern",
        confidence=0.90,
        parameters={
            "count": 6,
            "diameter": 8.0,
            "radius": 30.0,
            "angle_step": 60.0,
            "cut_type": "through_all",
            "start_angle": 0.0
        },
        source="agent_results"
    )

    # Act
    geometry = pattern.generate_geometry(match)

    # Assert
    assert "holes" in geometry
    assert len(geometry["holes"]) == 6
    for hole in geometry["holes"]:
        assert "center" in hole
        assert "diameter" in hole
        assert hole["diameter"] == 8.0
        # Verify center is at radius 30mm from origin
        x, y = hole["center"]
        distance = math.sqrt(x**2 + y**2)
        assert abs(distance - 30.0) < 0.5


def test_polar_pattern_filters_all_hole_features():
    """
    Test that pattern removes all individual hole Cut features.

    Given:
        - Feature list with base Extrude + 6 hole Cuts
        - Polar pattern detected

    Expected:
        - Filtered list contains only base Extrude (all Cuts removed)
    """
    # Arrange
    pattern = PolarHolePattern()
    all_features = [
        {"type": "Extrude", "geometry": {"type": "Circle", "diameter": {"value": 100}}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": {"value": 8}}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": {"value": 8}}},
    ]
    match = PatternMatch(
        pattern_name="polar_hole_pattern",
        confidence=0.90,
        parameters={"count": 6, "diameter": 8.0},
        source="agent_results"
    )

    # Act
    filtered = pattern.filter_features(all_features, match)

    # Assert
    assert len(filtered) == 1, "Should remove all 6 hole Cuts"
    assert filtered[0]["type"] == "Extrude"

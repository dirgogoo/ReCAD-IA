"""
Test suite for hole pattern detection.

Tests HolePattern detector that identifies circular cuts (holes) from:
1. Cut operations with Circle geometry from agents
2. Audio transcription with depth cues

TDD Phase: RED - Test written before implementation
"""

import pytest
from patterns.hole import HolePattern
from patterns.base import PatternMatch


def test_hole_pattern_detects_through_hole():
    """
    Test detection of through-hole from agent results.

    Given:
        - Agent reports Cut operation with Circle geometry (diameter 8mm)
        - Cut type is "through_all"

    Expected:
        - Pattern detected as "hole"
        - Confidence >= 0.90
        - Parameters contain diameter and cut_type="through_all"
    """
    # Arrange
    pattern = HolePattern()
    agent_results = [
        {
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Circle", "diameter": {"value": 50}},
                    "distance": 10.0
                },
                {
                    "type": "Cut",
                    "geometry": {
                        "type": "Circle",
                        "center": {"x": 20, "y": 20},
                        "diameter": {"value": 8.0, "unit": "mm"}
                    },
                    "parameters": {
                        "cut_type": "through_all"
                    }
                }
            ]
        }
    ]

    # Act
    result = pattern.detect(agent_results, transcription=None)

    # Assert
    assert result is not None, "Should detect through-hole"
    assert result.pattern_name == "hole"
    assert result.confidence >= 0.90
    assert result.parameters["diameter"] == 8.0
    assert result.parameters["cut_type"] == "through_all"
    assert result.parameters["center"] == (20, 20)


def test_hole_pattern_detects_blind_hole():
    """
    Test detection of blind hole from agent results.

    Given:
        - Agent reports Cut operation with Circle geometry
        - Cut type is "distance" with depth value
        - Audio contains depth cue: "furo com profundidade de 15mm"

    Expected:
        - Pattern detected as "hole"
        - Parameters contain diameter, depth, and cut_type="distance"
    """
    # Arrange
    pattern = HolePattern()
    agent_results = [
        {
            "features": [
                {
                    "type": "Cut",
                    "geometry": {
                        "type": "Circle",
                        "center": {"x": 0, "y": 0},
                        "diameter": {"value": 12.0, "unit": "mm"}
                    },
                    "parameters": {
                        "cut_type": "distance",
                        "distance": {"value": 15.0, "unit": "mm"}
                    }
                }
            ]
        }
    ]
    transcription = "vou fazer um furo com profundidade de 15mm"

    # Act
    result = pattern.detect(agent_results, transcription)

    # Assert
    assert result is not None, "Should detect blind hole"
    assert result.pattern_name == "hole"
    assert result.confidence >= 0.85
    assert result.parameters["diameter"] == 12.0
    assert result.parameters["cut_type"] == "distance"
    assert result.parameters["depth"] == 15.0


def test_hole_pattern_no_false_positive_on_extrude():
    """
    Test that pattern doesn't detect holes in extrusion operations.

    Given:
        - Agent reports Extrude with Circle (not a hole, just cylinder)

    Expected:
        - No pattern detected (returns None)
    """
    # Arrange
    pattern = HolePattern()
    agent_results = [
        {
            "features": [
                {
                    "type": "Extrude",  # Extrude, not Cut
                    "geometry": {"type": "Circle", "diameter": {"value": 50}},
                    "distance": 10.0
                }
            ]
        }
    ]

    # Act
    result = pattern.detect(agent_results, transcription=None)

    # Assert
    assert result is None, "Should NOT detect hole on Extrude operation"


def test_hole_pattern_filters_cut_features():
    """
    Test that pattern removes Cut features after detection.

    Given:
        - Feature list with Extrude + Cut operations
        - Hole pattern detected

    Expected:
        - Filtered list contains only Extrude (Cut removed)
    """
    # Arrange
    pattern = HolePattern()
    all_features = [
        {
            "type": "Extrude",
            "geometry": {"type": "Circle", "diameter": {"value": 50}},
            "distance": 10.0
        },
        {
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "diameter": {"value": 8.0}
            },
            "parameters": {"cut_type": "through_all"}
        }
    ]
    match = PatternMatch(
        pattern_name="hole",
        confidence=0.95,
        parameters={"diameter": 8.0, "cut_type": "through_all", "center": (0, 0)},
        source="agent_results"
    )

    # Act
    filtered = pattern.filter_features(all_features, match)

    # Assert
    assert len(filtered) == 1, "Should remove Cut feature"
    assert filtered[0]["type"] == "Extrude", "Should keep Extrude feature"


def test_hole_pattern_generate_geometry():
    """
    Test geometry generation returns correct format for PartBuilder.

    Given:
        - Pattern match with hole parameters (diameter, depth, center)

    Expected:
        - Geometry dict with parameters that can be directly passed to add_circle_cut()
    """
    # Arrange
    pattern = HolePattern()
    match = PatternMatch(
        pattern_name="hole",
        confidence=0.95,
        parameters={
            "diameter": 8.0,
            "cut_type": "through_all",
            "center": (20, 20),
            "depth": None
        },
        source="agent_results"
    )

    # Act
    geometry = pattern.generate_geometry(match)

    # Assert - parameters should match PartBuilder.add_circle_cut() signature
    assert geometry["diameter"] == 8.0
    assert geometry["cut_type"] == "through_all"
    assert geometry["center"] == (20, 20)
    assert "cut_distance" not in geometry  # Through-all holes don't have cut_distance


def test_hole_pattern_generate_geometry_blind_hole():
    """
    Test geometry generation for blind holes includes cut_distance.

    Given:
        - Pattern match with blind hole (cut_type="distance" with depth)

    Expected:
        - Geometry dict includes cut_distance parameter
    """
    # Arrange
    pattern = HolePattern()
    match = PatternMatch(
        pattern_name="hole",
        confidence=0.95,
        parameters={
            "diameter": 6.0,
            "cut_type": "distance",
            "center": (15, 15),
            "depth": 10.0
        },
        source="agent_results"
    )

    # Act
    geometry = pattern.generate_geometry(match)

    # Assert - blind holes should have cut_distance
    assert geometry["diameter"] == 6.0
    assert geometry["cut_type"] == "distance"
    assert geometry["center"] == (15, 15)
    assert geometry["cut_distance"] == 10.0

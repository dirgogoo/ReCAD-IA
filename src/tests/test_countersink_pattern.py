"""
Tests for CountersinkPattern (conical counterbores).

Countersinks are two-stage holes with conical outer cut (for flat-head screws)
and cylindrical inner cut (for screw shaft).
"""

import pytest
from patterns.countersink import CountersinkPattern
from patterns.base import PatternMatch


def test_countersink_detects_direct_geometry():
    """Test detection of basic countersink from direct Countersink geometry."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Countersink",
                "outer_diameter": {"value": 16.0, "unit": "mm"},
                "inner_diameter": {"value": 8.0, "unit": "mm"},
                "angle": {"value": 82.0, "unit": "degrees"},
                "center": {"x": 20, "y": 20}
            },
            "parameters": {
                "outer_depth": {"value": 5.0, "unit": "mm"},
                "inner_depth": {"value": 15.0, "unit": "mm"}
            }
        }]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.pattern_name == "countersink"
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0
    assert match.parameters["angle"] == 82.0
    assert match.parameters["outer_depth"] == 5.0
    assert match.parameters["inner_depth"] == 15.0
    assert match.confidence >= 0.90


def test_countersink_detects_from_chamfer_and_circle():
    """Test detection from Chamfer cut + Circle cut at same center."""
    agent_results = [{
        "features": [
            {
                "type": "Cut",
                "geometry": {
                    "type": "Chamfer",
                    "diameter": {"value": 16.0, "unit": "mm"},
                    "angle": {"value": 82.0, "unit": "degrees"},
                    "center": {"x": 30, "y": 30}
                },
                "parameters": {
                    "depth": {"value": 5.0, "unit": "mm"}
                }
            },
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 30, "y": 30}
                },
                "parameters": {
                    "distance": {"value": 10.0, "unit": "mm"}
                }
            }
        ]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.pattern_name == "countersink"
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0
    assert match.parameters["angle"] == 82.0
    assert match.confidence >= 0.85


def test_countersink_validates_angle():
    """Test that invalid cone angles are rejected."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Countersink",
                "outer_diameter": {"value": 16.0, "unit": "mm"},
                "inner_diameter": {"value": 8.0, "unit": "mm"},
                "angle": {"value": 45.0, "unit": "degrees"},  # Invalid angle
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "outer_depth": {"value": 5.0, "unit": "mm"},
                "inner_depth": {"value": 15.0, "unit": "mm"}
            }
        }]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    # Should reject invalid angles (not 82°, 90°, 100°, or 120°)
    assert match is None


def test_countersink_validates_diameter_order():
    """Test that outer diameter must be greater than inner diameter."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Countersink",
                "outer_diameter": {"value": 8.0, "unit": "mm"},  # Smaller!
                "inner_diameter": {"value": 16.0, "unit": "mm"},
                "angle": {"value": 82.0, "unit": "degrees"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "outer_depth": {"value": 5.0, "unit": "mm"},
                "inner_depth": {"value": 15.0, "unit": "mm"}
            }
        }]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    assert match is None  # Invalid: outer must be > inner


def test_countersink_validates_depth_order():
    """Test that outer depth must be less than inner depth."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Countersink",
                "outer_diameter": {"value": 16.0, "unit": "mm"},
                "inner_diameter": {"value": 8.0, "unit": "mm"},
                "angle": {"value": 82.0, "unit": "degrees"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "outer_depth": {"value": 20.0, "unit": "mm"},  # Deeper!
                "inner_depth": {"value": 15.0, "unit": "mm"}
            }
        }]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    assert match is None  # Invalid: outer depth must be < inner depth


def test_countersink_confidence_with_audio():
    """Test that audio cues increase confidence."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Countersink",
                "outer_diameter": {"value": 16.0, "unit": "mm"},
                "inner_diameter": {"value": 8.0, "unit": "mm"},
                "angle": {"value": 82.0, "unit": "degrees"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "outer_depth": {"value": 5.0, "unit": "mm"},
                "inner_depth": {"value": 15.0, "unit": "mm"}
            }
        }]
    }]

    transcription = "furo escareado cônico com cabeça embutida"

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results, transcription)

    assert match is not None
    assert match.confidence == 0.95  # High confidence with audio


def test_countersink_no_false_positive_on_counterbore():
    """Test that counterbores are not detected as countersinks."""
    agent_results = [{
        "features": [
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 16.0, "unit": "mm"},
                    "center": {"x": 0, "y": 0}
                },
                "parameters": {
                    "distance": {"value": 5.0, "unit": "mm"}
                }
            },
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",  # Both are circles - this is counterbore
                    "diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 0, "y": 0}
                },
                "parameters": {
                    "distance": {"value": 10.0, "unit": "mm"}
                }
            }
        ]
    }]

    pattern = CountersinkPattern()
    match = pattern.detect(agent_results)

    assert match is None  # Should not detect - this is a counterbore


def test_countersink_generate_geometry():
    """Test that generate_geometry creates correct chamfer + circle cuts."""
    match = PatternMatch(
        pattern_name="countersink",
        confidence=0.95,
        parameters={
            "outer_diameter": 16.0,
            "inner_diameter": 8.0,
            "angle": 82.0,
            "outer_depth": 5.0,
            "inner_depth": 15.0,
            "center": (20, 20)
        },
        source="agent_results"
    )

    pattern = CountersinkPattern()
    geometry = pattern.generate_geometry(match)

    assert "chamfer_cut" in geometry
    assert "circle_cut" in geometry

    # Chamfer cut (conical outer)
    assert geometry["chamfer_cut"]["diameter"] == 16.0
    assert geometry["chamfer_cut"]["angle"] == 82.0
    assert geometry["chamfer_cut"]["depth"] == 5.0
    assert geometry["chamfer_cut"]["center"] == (20, 20)

    # Circle cut (cylindrical inner)
    assert geometry["circle_cut"]["diameter"] == 8.0
    assert geometry["circle_cut"]["cut_distance"] == 10.0  # Relative: 15 - 5
    assert geometry["circle_cut"]["center"] == (20, 20)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

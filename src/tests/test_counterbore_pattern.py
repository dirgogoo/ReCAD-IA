"""
Tests for counterbore pattern detection.

A counterbore is a two-stage hole:
- Outer (larger) diameter for screw head (shallow depth)
- Inner (smaller) diameter for screw shaft (deeper depth)
"""

import pytest
from patterns.counterbore import CounterborePattern
from patterns.base import PatternMatch


def test_counterbore_detects_two_stage_hole():
    """Test detection of basic counterbore from agent results."""
    agent_results = [{
        "features": [
            {
                "type": "Cut",
                "geometry": {
                    "type": "Counterbore",
                    "outer_diameter": {"value": 16.0, "unit": "mm"},
                    "inner_diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 20, "y": 20}
                },
                "parameters": {
                    "outer_depth": {"value": 5.0, "unit": "mm"},
                    "inner_depth": {"value": 15.0, "unit": "mm"}
                }
            }
        ]
    }]

    pattern = CounterborePattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.pattern_name == "counterbore"
    assert match.confidence >= 0.85
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0
    assert match.parameters["outer_depth"] == 5.0
    assert match.parameters["inner_depth"] == 15.0
    assert match.parameters["center"] == (20, 20)


def test_counterbore_detects_from_two_cuts():
    """Test detection from two sequential Cut operations with same center."""
    agent_results = [{
        "features": [
            # Outer cut (larger diameter, shallow)
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 16.0, "unit": "mm"},
                    "center": {"x": 30, "y": 30}
                },
                "parameters": {
                    "cut_type": "distance",
                    "distance": {"value": 5.0, "unit": "mm"}
                }
            },
            # Inner cut (smaller diameter, deeper)
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 30, "y": 30}
                },
                "parameters": {
                    "cut_type": "distance",
                    "distance": {"value": 15.0, "unit": "mm"}
                }
            }
        ]
    }]

    pattern = CounterborePattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.pattern_name == "counterbore"
    assert match.parameters["outer_diameter"] == 16.0
    assert match.parameters["inner_diameter"] == 8.0


def test_counterbore_high_confidence_with_audio():
    """Test confidence boost when audio mentions counterbore."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Counterbore",
                "outer_diameter": {"value": 12.0, "unit": "mm"},
                "inner_diameter": {"value": 6.0, "unit": "mm"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "outer_depth": {"value": 4.0, "unit": "mm"},
                "inner_depth": {"value": 12.0, "unit": "mm"}
            }
        }]
    }]

    transcription = "Furo escareado com 12 milímetros de diâmetro externo"

    pattern = CounterborePattern()
    match = pattern.detect(agent_results, transcription)

    assert match is not None
    assert match.confidence >= 0.95  # High confidence with audio


def test_counterbore_no_false_positive_on_single_hole():
    """Test that single holes don't trigger counterbore detection."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "diameter": {"value": 8.0, "unit": "mm"},
                "center": {"x": 20, "y": 20}
            },
            "parameters": {
                "cut_type": "through_all"
            }
        }]
    }]

    pattern = CounterborePattern()
    match = pattern.detect(agent_results)

    assert match is None  # Should not detect counterbore


def test_counterbore_no_false_positive_on_different_centers():
    """Test that two holes with different centers don't trigger counterbore."""
    agent_results = [{
        "features": [
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 16.0, "unit": "mm"},
                    "center": {"x": 20, "y": 20}
                },
                "parameters": {"cut_type": "distance", "distance": {"value": 5.0, "unit": "mm"}}
            },
            {
                "type": "Cut",
                "geometry": {
                    "type": "Circle",
                    "diameter": {"value": 8.0, "unit": "mm"},
                    "center": {"x": 40, "y": 40}  # Different center!
                },
                "parameters": {"cut_type": "distance", "distance": {"value": 15.0, "unit": "mm"}}
            }
        ]
    }]

    pattern = CounterborePattern()
    match = pattern.detect(agent_results)

    assert match is None  # Different centers = not counterbore


def test_counterbore_generate_geometry():
    """Test geometry generation for PartBuilder API."""
    match = PatternMatch(
        pattern_name="counterbore",
        confidence=0.90,
        parameters={
            "outer_diameter": 16.0,
            "inner_diameter": 8.0,
            "outer_depth": 5.0,
            "inner_depth": 15.0,
            "center": (25, 25)
        },
        source="agent_results"
    )

    pattern = CounterborePattern()
    geometry = pattern.generate_geometry(match)

    # Should return parameters for two add_circle_cut() calls
    assert "outer_cut" in geometry
    assert "inner_cut" in geometry

    # Outer cut
    assert geometry["outer_cut"]["diameter"] == 16.0
    assert geometry["outer_cut"]["cut_distance"] == 5.0
    assert geometry["outer_cut"]["center"] == (25, 25)

    # Inner cut (depth is relative to outer cut bottom)
    assert geometry["inner_cut"]["diameter"] == 8.0
    assert geometry["inner_cut"]["cut_distance"] == 10.0  # 15 - 5 = 10
    assert geometry["inner_cut"]["center"] == (25, 25)


def test_counterbore_filters_cut_features():
    """Test that counterbore detection removes Cut operations."""
    all_features = [
        {"type": "Extrude", "geometry": {"type": "Rectangle"}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": 16}},
        {"type": "Cut", "geometry": {"type": "Circle", "diameter": 8}},
        {"type": "Extrude", "geometry": {"type": "Circle"}}
    ]

    match = PatternMatch(
        pattern_name="counterbore",
        confidence=0.90,
        parameters={},
        source="agent_results"
    )

    pattern = CounterborePattern()
    filtered = pattern.filter_features(all_features, match)

    # Should remove all Cut operations
    assert len(filtered) == 2
    assert all(f["type"] != "Cut" for f in filtered)


def test_counterbore_requires_outer_larger_than_inner():
    """Test that outer diameter must be larger than inner diameter."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Counterbore",
                "outer_diameter": {"value": 6.0, "unit": "mm"},  # Smaller!
                "inner_diameter": {"value": 12.0, "unit": "mm"},  # Larger!
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "outer_depth": {"value": 5.0, "unit": "mm"},
                "inner_depth": {"value": 15.0, "unit": "mm"}
            }
        }]
    }]

    pattern = CounterborePattern()
    match = pattern.detect(agent_results)

    # Should not detect invalid counterbore (outer must be > inner)
    assert match is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

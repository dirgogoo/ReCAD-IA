"""
Tests for slot pattern detection.

A slot is an elongated rectangular groove:
- Width: narrow dimension (perpendicular to slot direction)
- Length: long dimension (parallel to slot direction)
- Aspect ratio: length/width > 2.0 (typically)
"""

import pytest
from patterns.slot import SlotPattern
from patterns.base import PatternMatch


def test_slot_detects_direct_geometry():
    """Test detection from direct Slot geometry."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Slot",
                "width": {"value": 10.0, "unit": "mm"},
                "length": {"value": 50.0, "unit": "mm"},
                "center": {"x": 0, "y": 0},
                "orientation": {"value": 0.0, "unit": "degrees"}
            },
            "parameters": {
                "depth": {"value": 5.0, "unit": "mm"},
                "cut_type": "distance"
            }
        }]
    }]

    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.pattern_name == "slot"
    assert match.confidence >= 0.90
    assert match.parameters["width"] == 10.0
    assert match.parameters["length"] == 50.0
    assert match.parameters["depth"] == 5.0
    assert match.parameters["center"] == (0, 0)
    assert match.parameters["orientation"] == 0.0


def test_slot_detects_from_elongated_rectangle():
    """Test inference from elongated Rectangle cut (aspect ratio > 2)."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Rectangle",
                "width": {"value": 10.0, "unit": "mm"},
                "height": {"value": 50.0, "unit": "mm"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "distance": {"value": 5.0, "unit": "mm"}
            }
        }]
    }]

    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.pattern_name == "slot"
    assert match.confidence >= 0.85
    # Width is smaller dimension, length is larger
    assert match.parameters["width"] == 10.0
    assert match.parameters["length"] == 50.0


def test_slot_validates_aspect_ratio():
    """Test that square/near-square rectangles are NOT detected as slots."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Rectangle",
                "width": {"value": 20.0, "unit": "mm"},
                "height": {"value": 25.0, "unit": "mm"},  # Aspect ratio 1.25 < 2.0
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "distance": {"value": 5.0, "unit": "mm"}
            }
        }]
    }]

    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    assert match is None  # Should NOT detect - aspect ratio too low


def test_slot_validates_positive_dimensions():
    """Test rejection of invalid dimensions."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Slot",
                "width": {"value": 0.0, "unit": "mm"},  # Invalid
                "length": {"value": 50.0, "unit": "mm"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "depth": {"value": 5.0, "unit": "mm"}
            }
        }]
    }]

    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    assert match is None


def test_slot_confidence_with_audio():
    """Test confidence boost from audio transcription."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Slot",
                "width": {"value": 10.0, "unit": "mm"},
                "length": {"value": 50.0, "unit": "mm"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "depth": {"value": 5.0, "unit": "mm"}
            }
        }]
    }]

    transcription = "Este é um rasgo de 10 por 50 milímetros"

    pattern = SlotPattern()
    match = pattern.detect(agent_results, transcription)

    assert match is not None
    assert match.confidence >= 0.95  # Boosted by audio


def test_slot_handles_orientation():
    """Test that orientation is correctly extracted and normalized."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Slot",
                "width": {"value": 8.0, "unit": "mm"},
                "length": {"value": 40.0, "unit": "mm"},
                "center": {"x": 10, "y": 10},
                "orientation": {"value": 45.0, "unit": "degrees"}
            },
            "parameters": {
                "depth": {"value": 6.0, "unit": "mm"}
            }
        }]
    }]

    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    assert match is not None
    assert match.parameters["orientation"] == 45.0


def test_slot_generate_geometry():
    """Test geometry generation for PartBuilder."""
    pattern = SlotPattern()
    match = PatternMatch(
        pattern_name="slot",
        confidence=0.90,
        parameters={
            "width": 10.0,
            "length": 50.0,
            "depth": 5.0,
            "center": (0, 0),
            "orientation": 0.0
        },
        source="agent_results"
    )

    geometry = pattern.generate_geometry(match)

    assert "center" in geometry
    assert geometry["center"] == (0, 0)
    assert geometry["width"] == 10.0
    assert geometry["length"] == 50.0
    assert geometry["cut_type"] == "distance"
    assert geometry["cut_distance"] == 5.0
    assert geometry["orientation"] == 0.0


def test_slot_no_false_positive_on_circular_holes():
    """Test that circular holes are not detected as slots."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Circle",
                "diameter": {"value": 10.0, "unit": "mm"},
                "center": {"x": 0, "y": 0}
            },
            "parameters": {
                "distance": {"value": 5.0, "unit": "mm"}
            }
        }]
    }]

    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    assert match is None  # Should NOT detect circles as slots

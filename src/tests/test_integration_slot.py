"""Integration tests for slot pattern detection."""

import pytest
from patterns.slot import SlotPattern


def test_slot_integration_direct_geometry():
    """Test slot detection in full pipeline with direct Slot geometry."""
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

    transcription = "Este é um rasgo de 10 por 50 milímetros"

    # Act - Detect pattern
    pattern = SlotPattern()
    match = pattern.detect(agent_results, transcription)

    # Assert - Should detect slot pattern
    assert match is not None
    assert match.pattern_name == "slot"
    assert match.confidence >= 0.95  # High confidence with audio
    assert match.parameters["width"] == 10.0
    assert match.parameters["length"] == 50.0
    assert match.parameters["depth"] == 5.0

    # Test geometry generation
    geometry = pattern.generate_geometry(match)
    assert geometry["width"] == 10.0
    assert geometry["length"] == 50.0
    assert geometry["cut_distance"] == 5.0
    assert geometry["orientation"] == 0.0


def test_slot_integration_elongated_rectangle():
    """Test slot inference from elongated Rectangle cut."""
    agent_results = [{
        "features": [{
            "type": "Cut",
            "geometry": {
                "type": "Rectangle",
                "width": {"value": 8.0, "unit": "mm"},
                "height": {"value": 40.0, "unit": "mm"},  # Aspect ratio 5:1
                "center": {"x": 10, "y": 10}
            },
            "parameters": {
                "distance": {"value": 6.0, "unit": "mm"}
            }
        }]
    }]

    # Act - Detect pattern
    pattern = SlotPattern()
    match = pattern.detect(agent_results)

    # Assert - Should infer slot from elongated rectangle
    assert match is not None
    assert match.pattern_name == "slot"
    assert match.confidence >= 0.85
    # Width is smaller dimension (8), length is larger (40)
    assert match.parameters["width"] == 8.0
    assert match.parameters["length"] == 40.0
    assert match.parameters["depth"] == 6.0


@pytest.mark.skip(reason="Manual test - requires real video analysis")
def test_slot_real_video_analysis():
    """
    Manual test workflow for slot detection from real video.

    Steps:
    1. Record video showing part with slot
    2. Run ReCAD: python recad_runner.py video.mp4
    3. Check agent_results.json for Slot detection
    4. Verify semantic.json includes slot geometry
    5. Import to FreeCAD and validate dimensions
    6. Measure slot width, length, depth in CAD model
    7. Compare with actual part measurements
    """
    pass

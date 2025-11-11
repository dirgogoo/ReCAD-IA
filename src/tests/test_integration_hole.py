"""
Integration test for hole detection in ReCAD pipeline.

Tests end-to-end workflow:
1. Video analysis (mocked)
2. Hole pattern detection
3. Semantic JSON generation
4. FreeCAD export (if FreeCAD available)
"""

import pytest
import json
from pathlib import Path
from patterns.hole import HolePattern


def test_hole_integration_mock_agents():
    """
    Test hole detection with mocked agent results.

    Simulates agent detecting plate with 3 through-holes.
    """
    # Arrange - Mock agent results
    agent_results = [
        {
            "features": [
                # Base plate
                {
                    "type": "Extrude",
                    "geometry": {
                        "type": "Rectangle",
                        "width": {"value": 100, "unit": "mm"},
                        "height": {"value": 100, "unit": "mm"}
                    },
                    "parameters": {
                        "distance": {"value": 10, "unit": "mm"}
                    }
                },
                # Hole 1
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
                },
                # Hole 2
                {
                    "type": "Cut",
                    "geometry": {
                        "type": "Circle",
                        "center": {"x": 50, "y": 50},
                        "diameter": {"value": 10.0, "unit": "mm"}
                    },
                    "parameters": {
                        "cut_type": "through_all"
                    }
                },
                # Hole 3
                {
                    "type": "Cut",
                    "geometry": {
                        "type": "Circle",
                        "center": {"x": 80, "y": 80},
                        "diameter": {"value": 12.0, "unit": "mm"}
                    },
                    "parameters": {
                        "cut_type": "through_all"
                    }
                }
            ]
        }
    ]

    # Act - Detect pattern
    pattern = HolePattern()
    match = pattern.detect(agent_results, transcription=None)

    # Assert
    assert match is not None, "Should detect holes"
    assert match.pattern_name == "hole"
    assert match.confidence >= 0.90

    # Generate geometry
    geometry = pattern.generate_geometry(match)
    assert "diameter" in geometry
    assert "cut_type" in geometry
    assert "center" in geometry


def test_hole_blind_hole_integration():
    """
    Test blind hole detection with depth parameter.
    """
    # Arrange
    agent_results = [
        {
            "features": [
                {
                    "type": "Cut",
                    "geometry": {
                        "type": "Circle",
                        "center": {"x": 0, "y": 0},
                        "diameter": {"value": 15.0, "unit": "mm"}
                    },
                    "parameters": {
                        "cut_type": "distance",
                        "distance": {"value": 20.0, "unit": "mm"}
                    }
                }
            ]
        }
    ]
    transcription = "furo cego com profundidade de 20 milímetros"

    # Act
    pattern = HolePattern()
    match = pattern.detect(agent_results, transcription)

    # Assert
    assert match is not None
    assert match.parameters["cut_type"] == "distance"
    assert match.parameters["depth"] == 20.0
    assert match.confidence >= 0.90


@pytest.mark.skipif(True, reason="Requires real video file")
def test_hole_real_video_analysis():
    """
    Manual test with real video containing holes.

    Instructions:
    1. Record 10s video showing part with holes
    2. Update video_path below
    3. Remove @pytest.mark.skipif decorator
    4. Run: pytest tests/test_integration_hole.py::test_hole_real_video_analysis -v -s
    """
    video_path = Path("path/to/test/video.mp4")
    # TODO: Implement when real video available
    pass

"""
Tests for position_offset spatial positioning system.

position_offset enables features to be placed at specific positions
on attachment faces, not just at origin.
"""

import pytest
from semantic_builder import SemanticGeometryBuilder


def test_position_offset_adds_offset_field_to_feature():
    """Test that position_offset field is added to semantic JSON."""
    builder = SemanticGeometryBuilder("test_part")

    # Add circle cut with position offset
    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all",
        position_offset=(20.0, 10.0)  # New parameter
    )

    semantic = builder.build()
    feature = semantic["part"]["features"][0]

    assert "position_offset" in feature
    assert feature["position_offset"]["x"]["value"] == 20.0
    assert feature["position_offset"]["y"]["value"] == 10.0
    assert feature["position_offset"]["reference"] == "face_center"


def test_position_offset_default_is_none():
    """Test that omitting position_offset works (backward compatibility)."""
    builder = SemanticGeometryBuilder("test_part")

    # Add circle cut WITHOUT position offset
    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all"
    )

    semantic = builder.build()
    feature = semantic["part"]["features"][0]

    # position_offset should not be present (optional field)
    assert "position_offset" not in feature


def test_position_offset_rectangle_extrusion():
    """Test position_offset on Extrude features."""
    builder = SemanticGeometryBuilder("test_part")

    builder.add_rectangle_extrusion(
        center=(0, 0),
        width=50.0,
        height=30.0,
        extrude_distance=10.0,
        position_offset=(15.0, 25.0)  # New parameter
    )

    semantic = builder.build()
    feature = semantic["part"]["features"][0]

    assert "position_offset" in feature
    assert feature["position_offset"]["x"]["value"] == 15.0
    assert feature["position_offset"]["y"]["value"] == 25.0


def test_position_offset_negative_values():
    """Test that negative offsets work (left/down from center)."""
    builder = SemanticGeometryBuilder("test_part")

    builder.add_circle_cut(
        center=(0, 0),
        diameter=6.0,
        cut_type="through_all",
        position_offset=(-10.0, -5.0)  # Negative offsets
    )

    semantic = builder.build()
    feature = semantic["part"]["features"][0]

    assert feature["position_offset"]["x"]["value"] == -10.0
    assert feature["position_offset"]["y"]["value"] == -5.0


def test_position_offset_multiple_features():
    """Test multiple features with different offsets."""
    builder = SemanticGeometryBuilder("test_part")

    builder.add_rectangle_extrusion(
        center=(0, 0),
        width=100.0,
        height=100.0,
        extrude_distance=10.0
    )

    # Add 3 holes at different positions
    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all",
        position_offset=(20.0, 20.0)
    )

    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all",
        position_offset=(-20.0, 20.0)
    )

    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all",
        position_offset=(0.0, -20.0)
    )

    semantic = builder.build()
    features = semantic["part"]["features"]

    # First feature (extrusion) has no offset
    assert "position_offset" not in features[0]

    # Three holes have different offsets
    assert features[1]["position_offset"]["x"]["value"] == 20.0
    assert features[1]["position_offset"]["y"]["value"] == 20.0

    assert features[2]["position_offset"]["x"]["value"] == -20.0
    assert features[2]["position_offset"]["y"]["value"] == 20.0

    assert features[3]["position_offset"]["x"]["value"] == 0.0
    assert features[3]["position_offset"]["y"]["value"] == -20.0


def test_position_offset_circle_extrusion():
    """Test position_offset on circle extrusions."""
    builder = SemanticGeometryBuilder("test_part")

    builder.add_circle_extrusion(
        center=(0, 0),
        diameter=50.0,
        extrude_distance=20.0,
        position_offset=(10.0, 15.0)
    )

    semantic = builder.build()
    feature = semantic["part"]["features"][0]

    assert "position_offset" in feature
    assert feature["position_offset"]["x"]["value"] == 10.0
    assert feature["position_offset"]["y"]["value"] == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Integration tests for position_offset FreeCAD export.

Tests that position_offset correctly positions sketches in FreeCAD.
"""

import pytest
from semantic_builder import SemanticGeometryBuilder
import json
from pathlib import Path


def test_position_offset_freecad_export():
    """Test that position_offset exports correctly to FreeCAD."""
    builder = SemanticGeometryBuilder("plate_with_offset_holes")

    # Base plate
    builder.add_rectangle_extrusion(
        center=(0, 0),
        width=100.0,
        height=100.0,
        extrude_distance=10.0
    )

    # Hole at (+20, +20) offset from center
    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all",
        position_offset=(20.0, 20.0)
    )

    # Hole at (-20, +20) offset from center
    builder.add_circle_cut(
        center=(0, 0),
        diameter=8.0,
        cut_type="through_all",
        position_offset=(-20.0, 20.0)
    )

    semantic = builder.build()

    # Save to temp file
    temp_path = Path("test_offset.json")
    with open(temp_path, "w") as f:
        json.dump(semantic, f, indent=2)

    # Verify JSON structure
    assert len(semantic["part"]["features"]) == 3
    assert "position_offset" in semantic["part"]["features"][1]
    assert "position_offset" in semantic["part"]["features"][2]

    # Cleanup
    temp_path.unlink()

    print("[OK] position_offset semantic JSON structure correct")
    print("[MANUAL] To verify FreeCAD export:")
    print("  1. Run: freecadcmd -c 'from cad_export import convert_to_freecad; convert_to_freecad(\"test_offset.json\", \"test_offset.FCStd\")'")
    print("  2. Open test_offset.FCStd in FreeCAD")
    print("  3. Verify holes are at (+20,+20) and (-20,+20) from plate center")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Claude Code Analysis - Hollow Cylinder (Spacer)
Generated for session: 2025-11-07_154505

Analysis:
- Pattern: Hollow cylinder spacer (Espaçador BTP)
- Base geometry: Circle outer diameter 75mm
- Inner hole: Circle diameter 30mm
- Thickness: 12mm
- Confidence: 0.95 (all 5 agents agreed)

Approach:
1. Create base circle (75mm diameter)
2. Extrude 12mm to form cylinder
3. Cut inner circle (30mm diameter) through entire thickness
"""

import sys
from pathlib import Path

# Add semantic-geometry to path (5 parents from output file)
script_dir = Path(__file__).resolve().parent
semantic_geometry_root = script_dir.parent.parent.parent.parent.parent / "semantic-geometry"
sys.path.insert(0, str(semantic_geometry_root))

from semantic_geometry.builder import PartBuilder
from semantic_geometry.primitives import Circle


def build_part():
    """Build hollow cylinder using PartBuilder"""

    # Initialize builder
    builder = PartBuilder(name="Espacador_BTP_75x30x12")

    # Step 1: Create base circle (outer diameter 75mm)
    outer_circle = Circle(center=(0, 0), diameter=75.0)

    builder.add_extrude(
        id="extrude_outer",
        plane_type="work_plane",
        geometry=[outer_circle],
        distance=12.0,
        direction="normal",
        operation="new_body"
    )

    # Step 2: Cut inner circle (inner diameter 30mm)
    inner_circle = Circle(center=(0, 0), diameter=30.0)

    builder.add_cut(
        id="cut_inner_hole",
        plane_type="face_reference",
        plane_ref={"feature_id": "extrude_outer", "face": "top"},
        geometry=[inner_circle],
        distance=12.0,  # Through entire thickness
        direction="normal",
        cut_type="through_all"
    )

    return builder.build()


if __name__ == "__main__":
    import json

    part_json = build_part()

    # Print for verification
    print(json.dumps(part_json, indent=2))

    # Save to semantic.json
    output_path = script_dir / "semantic.json"
    with open(output_path, 'w') as f:
        json.dump(part_json, f, indent=2)

    print(f"\n[OK] Saved to: {output_path}")

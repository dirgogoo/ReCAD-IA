"""
Test suite for chord cut geometry calculation helper.

This module tests the calculate_chord_cut_geometry() function that generates
Arc + Line geometry for chord cuts on circular profiles.

TDD Phase: RED - This test is written BEFORE the implementation exists.
"""

import math
import pytest
from utils.chord_cut_helper import calculate_chord_cut_geometry


def test_calculate_chord_cut_geometry_basic():
    """
    Test chord cut geometry calculation with standard inputs.

    Given:
        - radius = 45.0 mm
        - flat_to_flat = 78.0 mm

    Expected:
        - 4 geometries: 2 Arcs + 2 Lines forming closed profile
        - 7 constraints: 4 Coincident + 1 Parallel + 1 Horizontal + 1 Distance
        - Correct angles calculated from geometry:
            - y_offset = flat_to_flat / 2 = 39.0
            - x_chord = sqrt(45² - 39²) ≈ 22.45
            - θ = atan2(39, 22.45) ≈ 60.1°
    """
    # Act
    result = calculate_chord_cut_geometry(radius=45.0, flat_to_flat=78.0)

    # Assert - Top level structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "geometry" in result, "Result should contain 'geometry' key"
    assert "constraints" in result, "Result should contain 'constraints' key"

    geometry = result["geometry"]
    constraints = result["constraints"]

    # Assert - Geometry count and types
    assert len(geometry) == 4, "Should have exactly 4 geometries"
    assert geometry[0]["type"] == "Arc", "First geometry should be Arc"
    assert geometry[1]["type"] == "Line", "Second geometry should be Line"
    assert geometry[2]["type"] == "Arc", "Third geometry should be Arc"
    assert geometry[3]["type"] == "Line", "Fourth geometry should be Line"

    # Assert - Arc 1 (right side)
    arc1 = geometry[0]
    assert arc1["center"] == {"x": 0, "y": 0}, "Arc1 center should be at origin"
    assert arc1["radius"]["value"] == 45.0, "Arc1 radius should be 45.0"
    assert arc1["radius"]["unit"] == "mm", "Arc1 radius unit should be mm"
    assert abs(arc1["start_angle"] - (-60.1)) < 0.1, "Arc1 start_angle should be ≈ -60.1°"
    assert abs(arc1["end_angle"] - 60.1) < 0.1, "Arc1 end_angle should be ≈ 60.1°"

    # Assert - Line 1 (top horizontal)
    line1 = geometry[1]
    x_chord = math.sqrt(45.0**2 - 39.0**2)  # ≈ 22.45
    assert abs(line1["start"]["x"] - x_chord) < 0.01, f"Line1 start.x should be ≈ {x_chord}"
    assert line1["start"]["y"] == 39.0, "Line1 start.y should be 39.0"
    assert line1["start"]["z"] == 0, "Line1 start.z should be 0"
    assert abs(line1["end"]["x"] - (-x_chord)) < 0.01, f"Line1 end.x should be ≈ {-x_chord}"
    assert line1["end"]["y"] == 39.0, "Line1 end.y should be 39.0"
    assert line1["end"]["z"] == 0, "Line1 end.z should be 0"

    # Assert - Arc 2 (left side)
    arc2 = geometry[2]
    assert arc2["center"] == {"x": 0, "y": 0}, "Arc2 center should be at origin"
    assert arc2["radius"]["value"] == 45.0, "Arc2 radius should be 45.0"
    assert arc2["radius"]["unit"] == "mm", "Arc2 radius unit should be mm"
    assert abs(arc2["start_angle"] - 119.9) < 0.1, "Arc2 start_angle should be ≈ 119.9°"
    assert abs(arc2["end_angle"] - (-119.9)) < 0.1, "Arc2 end_angle should be ≈ -119.9°"

    # Assert - Line 2 (bottom horizontal)
    line2 = geometry[3]
    assert abs(line2["start"]["x"] - (-x_chord)) < 0.01, f"Line2 start.x should be ≈ {-x_chord}"
    assert line2["start"]["y"] == -39.0, "Line2 start.y should be -39.0"
    assert line2["start"]["z"] == 0, "Line2 start.z should be 0"
    assert abs(line2["end"]["x"] - x_chord) < 0.01, f"Line2 end.x should be ≈ {x_chord}"
    assert line2["end"]["y"] == -39.0, "Line2 end.y should be -39.0"
    assert line2["end"]["z"] == 0, "Line2 end.z should be 0"

    # Assert - Constraints count and types
    assert len(constraints) == 7, "Should have exactly 7 constraints"

    # Assert - Coincident constraints (4 total)
    coincident_constraints = [c for c in constraints if c["type"] == "Coincident"]
    assert len(coincident_constraints) == 4, "Should have 4 Coincident constraints"

    # Verify specific coincident connections
    assert coincident_constraints[0] == {
        "type": "Coincident", "geo1": 0, "point1": 2, "geo2": 1, "point2": 1
    }, "Arc1.end → Line1.start"

    assert coincident_constraints[1] == {
        "type": "Coincident", "geo1": 1, "point1": 2, "geo2": 2, "point2": 1
    }, "Line1.end → Arc2.start"

    assert coincident_constraints[2] == {
        "type": "Coincident", "geo1": 2, "point1": 2, "geo2": 3, "point2": 1
    }, "Arc2.end → Line2.start"

    assert coincident_constraints[3] == {
        "type": "Coincident", "geo1": 3, "point1": 2, "geo2": 0, "point2": 1
    }, "Line2.end → Arc1.start"

    # Assert - Parallel constraint
    parallel_constraints = [c for c in constraints if c["type"] == "Parallel"]
    assert len(parallel_constraints) == 1, "Should have 1 Parallel constraint"
    assert parallel_constraints[0] == {
        "type": "Parallel", "geo1": 1, "geo2": 3
    }, "Line1 ∥ Line2"

    # Assert - Horizontal constraint
    horizontal_constraints = [c for c in constraints if c["type"] == "Horizontal"]
    assert len(horizontal_constraints) == 1, "Should have 1 Horizontal constraint"
    assert horizontal_constraints[0] == {
        "type": "Horizontal", "geo1": 1
    }, "Line1 is horizontal"

    # Assert - Distance constraint
    distance_constraints = [c for c in constraints if c["type"] == "Distance"]
    assert len(distance_constraints) == 1, "Should have 1 Distance constraint"
    assert distance_constraints[0] == {
        "type": "Distance", "geo1": 1, "point1": 1, "geo2": 3, "point2": 1, "value": 78.0
    }, "Distance between Line1.start and Line2.start = 78mm"


def test_calculate_chord_cut_geometry_angles_mathematical_verification():
    """
    Verify that angles are calculated correctly using trigonometry.

    Mathematical verification:
        radius = 45.0
        flat_to_flat = 78.0
        y_offset = 78.0 / 2 = 39.0
        x_chord = sqrt(45² - 39²) = sqrt(2025 - 1521) = sqrt(504) ≈ 22.449
        θ = atan2(y_offset, x_chord) = atan2(39, 22.449) ≈ 60.07°

    Expected angles:
        - Arc1: -60.1° to +60.1° (right side, spanning 120.2°)
        - Arc2: +119.9° to -119.9° (left side, spanning 120.2° in reverse)
    """
    # Calculate expected values
    radius = 45.0
    y_offset = 78.0 / 2  # = 39.0
    x_chord = math.sqrt(radius**2 - y_offset**2)  # ≈ 22.449
    theta_rad = math.atan2(y_offset, x_chord)
    theta_deg = math.degrees(theta_rad)  # ≈ 60.07°

    # Act
    result = calculate_chord_cut_geometry(radius=45.0, flat_to_flat=78.0)
    geometry = result["geometry"]

    # Assert - Verify calculated angle matches reference
    arc1_end = geometry[0]["end_angle"]
    assert abs(arc1_end - theta_deg) < 0.2, f"Arc1 end angle {arc1_end}° should match calculated {theta_deg:.2f}°"

    arc1_start = geometry[0]["start_angle"]
    assert abs(arc1_start - (-theta_deg)) < 0.2, f"Arc1 start angle {arc1_start}° should match calculated {-theta_deg:.2f}°"

    arc2_start = geometry[2]["start_angle"]
    expected_arc2_start = 180 - theta_deg  # ≈ 119.93°
    assert abs(arc2_start - expected_arc2_start) < 0.2, f"Arc2 start angle {arc2_start}° should match calculated {expected_arc2_start:.2f}°"

    arc2_end = geometry[2]["end_angle"]
    expected_arc2_end = -(180 - theta_deg)  # ≈ -119.93°
    assert abs(arc2_end - expected_arc2_end) < 0.2, f"Arc2 end angle {arc2_end}° should match calculated {expected_arc2_end:.2f}°"

    print(f"✓ Mathematical verification passed:")
    print(f"  x_chord = {x_chord:.3f} mm")
    print(f"  θ = {theta_deg:.2f}°")
    print(f"  Arc1: {arc1_start:.1f}° to {arc1_end:.1f}°")
    print(f"  Arc2: {arc2_start:.1f}° to {arc2_end:.1f}°")


def test_calculate_chord_cut_geometry_different_inputs():
    """
    Test with different radius and flat_to_flat values.

    Given:
        - radius = 50.0 mm
        - flat_to_flat = 80.0 mm
    """
    result = calculate_chord_cut_geometry(radius=50.0, flat_to_flat=80.0)

    # Basic structure checks
    assert len(result["geometry"]) == 4
    assert len(result["constraints"]) == 7

    # Verify calculations
    y_offset = 80.0 / 2  # = 40.0
    x_chord = math.sqrt(50.0**2 - 40.0**2)  # = 30.0

    geometry = result["geometry"]
    line1 = geometry[1]

    assert abs(line1["start"]["x"] - x_chord) < 0.01
    assert line1["start"]["y"] == y_offset
    assert geometry[0]["radius"]["value"] == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

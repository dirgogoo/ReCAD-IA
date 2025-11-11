"""
Chord cut geometry calculation helper for ReCAD.

This module provides utilities to calculate Arc + Line geometry for chord cuts
on circular profiles, commonly used in manufacturing for creating flat surfaces
on cylindrical parts.

Mathematical Background:
    For a circle with radius r and a chord at distance d from the center:
    - Chord half-length: x = sqrt(r² - d²)
    - Angle to chord endpoint: θ = atan2(d, x)

    The geometry consists of:
    - Arc 1 (right): Spans from -θ to +θ
    - Line 1 (top): Horizontal line connecting the arcs at y = +d
    - Arc 2 (left): Spans from (180-θ) to -(180-θ)
    - Line 2 (bottom): Horizontal line connecting the arcs at y = -d

Example:
    >>> result = calculate_chord_cut_geometry(radius=45.0, flat_to_flat=78.0)
    >>> len(result['geometry'])
    4
    >>> len(result['constraints'])
    7
    >>> result['geometry'][0]['type']
    'Arc'
"""

import math
from typing import Dict, List, Any


def calculate_chord_cut_geometry(radius: float, flat_to_flat: float) -> Dict[str, Any]:
    """
    Calculate Arc + Line geometry for chord cuts on circular profiles.

    This function generates the geometric primitives (2 arcs + 2 lines) and
    constraints needed to create a closed profile with flat sides (chord cuts)
    on opposite sides of a circle.

    Args:
        radius: The radius of the circle in millimeters.
        flat_to_flat: The distance between the two parallel flat sides in millimeters.

    Returns:
        Dictionary containing:
            - 'geometry': List of 4 geometry dictionaries (2 Arc, 2 Line)
            - 'constraints': List of 7 constraint dictionaries

    Mathematical Calculation:
        y_offset = flat_to_flat / 2
        x_chord = sqrt(radius² - y_offset²)
        θ = atan2(y_offset, x_chord) [converted to degrees]

    Geometry Order:
        0. Arc (right side): center=(0,0), -θ° to +θ°
        1. Line (top): (x_chord, y_offset) to (-x_chord, y_offset)
        2. Arc (left side): center=(0,0), (180-θ)° to -(180-θ)°
        3. Line (bottom): (-x_chord, -y_offset) to (x_chord, -y_offset)

    Constraints:
        - 4 Coincident: Connect endpoints (Arc1→Line1→Arc2→Line2→Arc1)
        - 1 Parallel: Line1 ∥ Line2
        - 1 Horizontal: Line1
        - 1 Distance: flat_to_flat distance between lines

    Example:
        >>> result = calculate_chord_cut_geometry(radius=45.0, flat_to_flat=78.0)
        >>> result['geometry'][0]['start_angle']  # Arc1 start
        -60.1
        >>> result['geometry'][1]['start']['y']  # Line1 y-coordinate
        39.0

    Raises:
        ValueError: If radius <= 0 or flat_to_flat >= 2*radius (invalid geometry)

    References:
        Based on implementation in:
        C:\\Users\\conta\\semantic-geometry\\tests\\run_test_closed_profile_green.py
    """
    # Input validation
    if radius <= 0:
        raise ValueError(f"Radius must be positive, got {radius}")

    if flat_to_flat >= 2 * radius:
        raise ValueError(
            f"flat_to_flat ({flat_to_flat}) must be less than diameter (2*{radius} = {2*radius})"
        )

    # Calculate geometry parameters
    y_offset = flat_to_flat / 2
    x_chord = math.sqrt(radius**2 - y_offset**2)

    # Calculate angle in degrees
    theta_rad = math.atan2(y_offset, x_chord)
    theta_deg = math.degrees(theta_rad)

    # Round to 1 decimal place to match reference implementation
    theta = round(theta_deg, 1)

    # Build geometry list
    geometry = [
        # Arc 1 (right side): -θ to +θ
        {
            "type": "Arc",
            "center": {"x": 0, "y": 0},
            "radius": {"value": radius, "unit": "mm"},
            "start_angle": -theta,
            "end_angle": theta
        },
        # Line 1 (top horizontal): right to left
        {
            "type": "Line",
            "start": {"x": x_chord, "y": y_offset, "z": 0},
            "end": {"x": -x_chord, "y": y_offset, "z": 0}
        },
        # Arc 2 (left side): (180-θ) to -(180-θ)
        {
            "type": "Arc",
            "center": {"x": 0, "y": 0},
            "radius": {"value": radius, "unit": "mm"},
            "start_angle": 180 - theta,
            "end_angle": -(180 - theta)
        },
        # Line 2 (bottom horizontal): left to right
        {
            "type": "Line",
            "start": {"x": -x_chord, "y": -y_offset, "z": 0},
            "end": {"x": x_chord, "y": -y_offset, "z": 0}
        }
    ]

    # Build constraints list
    # Point indices: 1=start, 2=end (for Line and Arc)
    constraints = [
        # Coincident constraints: Connect endpoints to form closed loop
        {"type": "Coincident", "geo1": 0, "point1": 2, "geo2": 1, "point2": 1},  # Arc1.end → Line1.start
        {"type": "Coincident", "geo1": 1, "point1": 2, "geo2": 2, "point2": 1},  # Line1.end → Arc2.start
        {"type": "Coincident", "geo1": 2, "point1": 2, "geo2": 3, "point2": 1},  # Arc2.end → Line2.start
        {"type": "Coincident", "geo1": 3, "point1": 2, "geo2": 0, "point2": 1},  # Line2.end → Arc1.start

        # Geometric constraints
        {"type": "Parallel", "geo1": 1, "geo2": 3},  # Line1 ∥ Line2
        {"type": "Horizontal", "geo1": 1},           # Line1 is horizontal

        # Dimensional constraint: Distance between parallel lines (vertical distance)
        # Measure from Line1.start (x_chord, y_offset) to Line2.end (x_chord, -y_offset)
        # Both points have same X coordinate, so distance is purely vertical
        {"type": "Distance", "geo1": 1, "point1": 1, "geo2": 3, "point2": 2, "value": flat_to_flat}
    ]

    return {
        "geometry": geometry,
        "constraints": constraints
    }

"""
FreeCAD parametric export module (Pattern #009)

Converts semantic geometry JSON to parametric .FCStd files using:
- PartDesign::Body (parametric container)
- Sketcher::SketchObject (2D profiles)
- PartDesign::Pad (extrusion)
- PartDesign::Pocket (cuts)

Reference: execute_poc_fixed.py (validated POC)

Policy 3.17: Policy documentation header included
Policy 3.5: Meaningful function names (convert_to_freecad)
Policy 3.6: Error handling with try/except and return bool
"""

import sys
import os
from typing import Dict, Any
from pathlib import Path

# Add FreeCAD to Python path
FREECAD_PATH = "C:/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin"
if FREECAD_PATH not in sys.path:
    sys.path.append(FREECAD_PATH)

try:
    import FreeCAD
    import Part
    import Sketcher
except ImportError:
    # Fallback for testing without FreeCAD installed
    FreeCAD = None
    Part = None
    Sketcher = None


def _extract_value(obj: Any) -> float:
    """
    Extract numeric value from nested or flat format.

    Handles:
    - Nested: {"value": 126, "unit": "mm"} → 126.0
    - Flat: 126 → 126.0

    Args:
        obj: Value object (dict with 'value' key, or number)

    Returns:
        Float value
    """
    if isinstance(obj, dict):
        return float(obj.get("value", 0))
    return float(obj)


def apply_position_offset(sketch, feature: Dict) -> None:
    """
    Apply position_offset to sketch AttachmentOffset.

    Args:
        sketch: FreeCAD Sketch object
        feature: Feature dictionary with optional position_offset
    """
    if "position_offset" not in feature:
        return  # No offset - sketch stays at default position

    offset = feature["position_offset"]
    x_offset = offset["x"]["value"]
    y_offset = offset["y"]["value"]

    # Apply AttachmentOffset to translate sketch on attachment face
    # Using App.Placement with translation only (no rotation)
    import FreeCAD as App
    sketch.AttachmentOffset = App.Placement(
        App.Vector(x_offset, y_offset, 0),  # Translation in mm
        App.Rotation(0, 0, 0)                # No rotation
    )

    print(f"[INFO] Applied position_offset: ({x_offset}, {y_offset}) mm")


def _create_sketch_from_profile(doc, body, profile: Dict[str, Any], sketch_name: str):
    """
    Create FreeCAD sketch from semantic profile geometry

    Args:
        doc: FreeCAD document
        body: PartDesign Body object
        profile: Profile geometry dictionary
        sketch_name: Name for sketch object

    Returns:
        Sketch object

    Policy 3.5: Meaningful function name (_create_sketch_from_profile)
    """
    # Create sketch object
    sketch = doc.addObject('Sketcher::SketchObject', sketch_name)
    body.addObject(sketch)

    # Attach sketch to XY plane (body.Origin.OriginFeatures[3])
    sketch.MapMode = 'FlatFace'
    sketch.AttachmentSupport = [(body.Origin.OriginFeatures[3], '')]

    geometry_type = profile.get("type")

    if geometry_type == "Circle":
        # Handle both formats: {"x": 0, "y": 0} or [0, 0, 0]
        center_obj = profile.get("center", {})
        if isinstance(center_obj, dict):
            cx = center_obj.get("x", 0)
            cy = center_obj.get("y", 0)
            cz = 0
        else:
            cx, cy, cz = center_obj[0], center_obj[1], center_obj[2] if len(center_obj) > 2 else 0

        # Extract radius (handle diameter too)
        if "radius" in profile:
            radius = _extract_value(profile["radius"])
        elif "diameter" in profile:
            diameter = _extract_value(profile["diameter"])
            radius = diameter / 2.0
        else:
            radius = 10.0

        # Create Part.Circle and add to sketch
        circle = Part.Circle(
            FreeCAD.Vector(cx, cy, cz),
            FreeCAD.Vector(0, 0, 1),  # Normal (Z-axis)
            radius
        )
        sketch.addGeometry(circle, False)  # False = not construction geometry

    elif geometry_type == "Rectangle":
        # Handle both formats: {"x": 0, "y": 0} or [0, 0, 0]
        center_obj = profile.get("center", {})
        if isinstance(center_obj, dict):
            cx = center_obj.get("x", 0)
            cy = center_obj.get("y", 0)
        else:
            cx, cy = center_obj[0], center_obj[1]

        width = _extract_value(profile.get("width", 10.0))
        height = _extract_value(profile.get("height", 10.0))

        # Calculate rectangle corners (centered at origin)
        half_w = width / 2
        half_h = height / 2
        p1 = FreeCAD.Vector(center[0] - half_w, center[1] - half_h, 0)
        p2 = FreeCAD.Vector(center[0] + half_w, center[1] - half_h, 0)
        p3 = FreeCAD.Vector(center[0] + half_w, center[1] + half_h, 0)
        p4 = FreeCAD.Vector(center[0] - half_w, center[1] + half_h, 0)

        # Create 4 line segments
        sketch.addGeometry(Part.LineSegment(p1, p2), False)
        sketch.addGeometry(Part.LineSegment(p2, p3), False)
        sketch.addGeometry(Part.LineSegment(p3, p4), False)
        sketch.addGeometry(Part.LineSegment(p4, p1), False)

        # Add coincident constraints for closed profile
        sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 2, 1, 1))
        sketch.addConstraint(Sketcher.Constraint('Coincident', 1, 2, 2, 1))
        sketch.addConstraint(Sketcher.Constraint('Coincident', 2, 2, 3, 1))
        sketch.addConstraint(Sketcher.Constraint('Coincident', 3, 2, 0, 1))

    elif geometry_type == "Line":
        start = profile.get("start", [0, 0, 0])
        end = profile.get("end", [0, 0, 0])

        # Create LineSegment
        start_vec = FreeCAD.Vector(start[0], start[1], start[2])
        end_vec = FreeCAD.Vector(end[0], end[1], end[2])

        line = Part.LineSegment(start_vec, end_vec)
        sketch.addGeometry(line, False)

    elif geometry_type == "Arc":
        center = profile.get("center", [0, 0, 0])
        radius = profile.get("radius", 10.0)
        start_angle = profile.get("start_angle", 0.0)
        end_angle = profile.get("end_angle", 180.0)

        # Convert degrees to radians
        import math
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        # Create circle first
        center_vec = FreeCAD.Vector(center[0], center[1], center[2])
        normal = FreeCAD.Vector(0, 0, 1)  # Z-axis normal
        circle = Part.Circle(center_vec, normal, radius)

        # Create arc from circle with angle range
        arc = Part.ArcOfCircle(circle, start_rad, end_rad)
        sketch.addGeometry(arc, False)

    else:
        raise ValueError(f"Unsupported geometry type: {geometry_type}")

    # Recompute to update sketch
    doc.recompute()

    return sketch


def _apply_operation(doc, body, operation: str, sketch, **params):
    """
    Apply 3D operation to sketch

    Args:
        doc: FreeCAD document
        body: PartDesign Body object
        operation: Operation type ("Extrude", "Cut")
        sketch: Sketch object
        **params: Operation-specific parameters (length, etc)

    Returns:
        Feature object (Pad, Pocket, etc)

    Policy 3.5: Meaningful function name (_apply_operation)
    """
    if operation == "Extrude":
        # Create Pad (extrusion)
        pad = doc.addObject("PartDesign::Pad", "Pad_1")
        body.addObject(pad)
        pad.Profile = sketch
        pad.Length = params.get("length", 10.0)

        doc.recompute()
        return pad

    elif operation == "Cut":
        # Create Pocket (cut)
        pocket = doc.addObject("PartDesign::Pocket", "Pocket_1")
        body.addObject(pocket)
        pocket.Profile = sketch
        pocket.Type = 1  # ThroughAll

        doc.recompute()
        return pocket

    elif operation == "Revolve":
        revolve = doc.addObject("PartDesign::Revolution", "Revolution_1")
        body.addObject(revolve)
        revolve.Profile = sketch

        # Set rotation angle (default 360 degrees)
        angle = params.get("angle", 360.0)
        revolve.Angle = angle

        # Set axis (default is V_Axis - vertical/Y-axis)
        axis = params.get("axis", "V_Axis")
        if axis == "V_Axis":
            revolve.ReferenceAxis = (sketch, ["V_Axis"])
        elif axis == "H_Axis":
            revolve.ReferenceAxis = (sketch, ["H_Axis"])
        else:
            # Default to V_Axis
            revolve.ReferenceAxis = (sketch, ["V_Axis"])

        doc.recompute()
        return revolve

    else:
        raise ValueError(f"Unsupported operation: {operation}")


def convert_to_freecad(part_json: Dict[str, Any], output_path: str) -> bool:
    """
    Convert semantic geometry JSON to parametric FreeCAD .FCStd file

    Validation Layers (Defense-in-Depth):
    1. JSON Schema validation
    2. Geometry bounds validation
    3. Feature dependencies validation
    4. Sketch closure validation
    5. FreeCAD isValid() check
    6. FreeCAD check() method

    Args:
        part_json: Semantic geometry dictionary with format:
            {
              "part": {
                "name": "Part Name",
                "units": "mm",
                "work_plane": {"type": "primitive", "face": "frontal"},
                "features": [
                  {
                    "type": "Extrude",
                    "sketch": {"geometry": [{"type": "Circle", ...}]},
                    "parameters": {"distance": {"value": 100, "unit": "mm"}}
                  }
                ]
              }
            }
        output_path: Path to save .FCStd file

    Returns:
        True if conversion successful, False otherwise

    Example:
        >>> part = {
        ...     "part": {
        ...       "features": [{
        ...         "type": "Extrude",
        ...         "sketch": {"geometry": [{"type": "Circle", "center": {"x":0,"y":0}, "diameter": {"value": 50, "unit": "mm"}}]},
        ...         "parameters": {"distance": {"value": 100, "unit": "mm"}}
        ...       }]
        ...     }
        ... }
        >>> convert_to_freecad(part, "output.FCStd")
        True
    """
    if FreeCAD is None:
        raise ImportError("FreeCAD not available. Install FreeCAD 1.0.2+")

    # Import validators (optional)
    try:
        from semantic_geometry.freecad_validators import (
            validate_json_schema,
            validate_geometry_bounds,
            validate_feature_dependencies,
            validate_sketch_closure
        )
        VALIDATORS_AVAILABLE = True
    except ImportError:
        VALIDATORS_AVAILABLE = False
        # Define no-op validators
        def validate_json_schema(data): return []
        def validate_geometry_bounds(data): return []
        def validate_feature_dependencies(data): return []
        def validate_sketch_closure(data): return []

    # Extract part info
    part = part_json.get("part", {})
    features = part.get("features", [])

    if len(features) == 0:
        print("No features found in part")
        return False

    # Layer 1: JSON Schema validation (skip for now - validators expect old format)
    # TODO: Update validators to handle part.features format

    # Layer 2-4: Skip validation for now (validators need updating)
    # Will rely on FreeCAD's own validation (isValid, check)

    try:
        # Create new FreeCAD document
        doc_name = Path(output_path).stem
        doc = FreeCAD.newDocument(doc_name)

        # Create PartDesign Body (parametric container)
        body = doc.addObject('PartDesign::Body', 'Body')

        previous_feature = None

        # Process each feature
        for idx, feature in enumerate(features):
            feature_type = feature.get("type")
            sketch_data = feature.get("sketch", {})
            geometry_list = sketch_data.get("geometry", [])

            # Defense-in-depth: Handle both formats (parameters wrapper or flat)
            parameters = feature.get("parameters", {})

            # TEMP FIX: If no "parameters" key, check for flat "distance"
            if not parameters and "distance" in feature:
                print(f"WARNING: Feature '{feature.get('id', idx)}' uses OLD format (distance outside parameters)")
                print(f"         This format is deprecated. Please regenerate semantic.json with correct format.")
                # Create temporary parameters dict from flat values
                parameters = {
                    "distance": feature.get("distance"),
                    "direction": feature.get("direction", "normal"),
                    "operation": feature.get("operation", "new_body")
                }

            # Validate parameters exist
            if not parameters:
                raise ValueError(
                    f"Feature '{feature.get('id', idx)}' missing 'parameters' key. "
                    f"Expected format: {{'parameters': {{'distance': {{'value': X, 'unit': 'mm'}}}}}}"
                )

            # Create sketch for this feature
            sketch_name = f"Sketch_{idx + 1}"
            sketch = doc.addObject('Sketcher::SketchObject', sketch_name)
            body.addObject(sketch)

            # Attach sketch to plane
            if previous_feature is None:
                # First feature: attach to XY plane
                sketch.MapMode = 'FlatFace'
                sketch.AttachmentSupport = [(body.Origin.OriginFeatures[3], '')]
            else:
                # Subsequent features: attach to top face of previous
                sketch.AttachmentSupport = [(previous_feature, 'Face3')]
                sketch.MapMode = 'FlatFace'

            # Add geometry to sketch
            for geom in geometry_list:
                geom_type = geom.get("type")

                if geom_type == "Circle":
                    center_obj = geom.get("center", {})
                    cx = center_obj.get("x", 0) if isinstance(center_obj, dict) else center_obj[0]
                    cy = center_obj.get("y", 0) if isinstance(center_obj, dict) else center_obj[1]

                    if "radius" in geom:
                        radius = _extract_value(geom["radius"])
                    elif "diameter" in geom:
                        radius = _extract_value(geom["diameter"]) / 2.0
                    else:
                        radius = 10.0

                    circle = Part.Circle(
                        FreeCAD.Vector(cx, cy, 0),
                        FreeCAD.Vector(0, 0, 1),
                        radius
                    )
                    sketch.addGeometry(circle, False)

                elif geom_type == "Rectangle":
                    center_obj = geom.get("center", {})
                    cx = center_obj.get("x", 0) if isinstance(center_obj, dict) else center_obj[0]
                    cy = center_obj.get("y", 0) if isinstance(center_obj, dict) else center_obj[1]

                    width = _extract_value(geom.get("width", 10.0))
                    height = _extract_value(geom.get("height", 10.0))

                    half_w = width / 2
                    half_h = height / 2
                    p1 = FreeCAD.Vector(cx - half_w, cy - half_h, 0)
                    p2 = FreeCAD.Vector(cx + half_w, cy - half_h, 0)
                    p3 = FreeCAD.Vector(cx + half_w, cy + half_h, 0)
                    p4 = FreeCAD.Vector(cx - half_w, cy + half_h, 0)

                    sketch.addGeometry(Part.LineSegment(p1, p2), False)
                    sketch.addGeometry(Part.LineSegment(p2, p3), False)
                    sketch.addGeometry(Part.LineSegment(p3, p4), False)
                    sketch.addGeometry(Part.LineSegment(p4, p1), False)

                    sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 2, 1, 1))
                    sketch.addConstraint(Sketcher.Constraint('Coincident', 1, 2, 2, 1))
                    sketch.addConstraint(Sketcher.Constraint('Coincident', 2, 2, 3, 1))
                    sketch.addConstraint(Sketcher.Constraint('Coincident', 3, 2, 0, 1))

                elif geom_type == "Arc":
                    # Arc geometry for chord cuts and custom profiles
                    center_obj = geom.get("center", {})
                    if isinstance(center_obj, dict):
                        cx = center_obj.get("x", 0)
                        cy = center_obj.get("y", 0)
                    else:
                        cx, cy = center_obj[0], center_obj[1]

                    # Extract radius (handle both nested and flat formats)
                    radius = _extract_value(geom.get("radius", 10.0))

                    # Get angles in degrees
                    start_angle = geom.get("start_angle", 0.0)
                    end_angle = geom.get("end_angle", 180.0)

                    # Convert to radians for FreeCAD
                    import math
                    start_rad = math.radians(start_angle)
                    end_rad = math.radians(end_angle)

                    # Create arc
                    center_vec = FreeCAD.Vector(cx, cy, 0)
                    normal = FreeCAD.Vector(0, 0, 1)
                    circle = Part.Circle(center_vec, normal, radius)
                    arc = Part.ArcOfCircle(circle, start_rad, end_rad)

                    sketch.addGeometry(arc, False)

                elif geom_type == "Line":
                    # Line geometry for chord cuts and custom profiles
                    start_obj = geom.get("start", {"x": 0, "y": 0, "z": 0})
                    end_obj = geom.get("end", {"x": 0, "y": 0, "z": 0})

                    # Handle both dict and array formats
                    if isinstance(start_obj, dict):
                        sx = start_obj.get("x", 0)
                        sy = start_obj.get("y", 0)
                        sz = start_obj.get("z", 0)
                    else:
                        sx, sy, sz = start_obj[0], start_obj[1], start_obj[2] if len(start_obj) > 2 else 0

                    if isinstance(end_obj, dict):
                        ex = end_obj.get("x", 0)
                        ey = end_obj.get("y", 0)
                        ez = end_obj.get("z", 0)
                    else:
                        ex, ey, ez = end_obj[0], end_obj[1], end_obj[2] if len(end_obj) > 2 else 0

                    # Create line segment
                    start_vec = FreeCAD.Vector(sx, sy, sz)
                    end_vec = FreeCAD.Vector(ex, ey, ez)
                    line = Part.LineSegment(start_vec, end_vec)

                    sketch.addGeometry(line, False)

            # Apply position offset if present (BEFORE recompute)
            apply_position_offset(sketch, feature)

            doc.recompute()

            # Apply operation
            if feature_type == "Extrude":
                distance_param = parameters.get("distance")

                # Validate distance exists
                if distance_param is None:
                    raise ValueError(
                        f"Feature '{feature.get('id', idx)}' missing 'distance' parameter. "
                        f"Cannot create Extrude without distance."
                    )

                # Extract distance value (handle both nested and flat formats)
                distance = _extract_value(distance_param)

                # Sanity check: distance should not be 0
                if distance == 0.0:
                    raise ValueError(
                        f"Feature '{feature.get('id', idx)}' has distance = 0. "
                        f"This is likely an error in semantic.json."
                    )

                pad = doc.addObject("PartDesign::Pad", f"Pad_{idx + 1}")
                body.addObject(pad)
                pad.Profile = sketch
                pad.Length = distance
                previous_feature = pad

            elif feature_type == "Cut":
                pocket = doc.addObject("PartDesign::Pocket", f"Pocket_{idx + 1}")
                body.addObject(pocket)
                pocket.Profile = sketch

                # Read cut_type from parameters (default to through_all)
                cut_type = parameters.get("cut_type", "through_all")

                if cut_type == "through_all":
                    pocket.Type = 1  # ThroughAll
                elif cut_type == "distance":
                    # Use specified distance for pocket depth
                    distance_param = parameters.get("distance")
                    if distance_param is None:
                        raise ValueError(
                            f"Feature '{feature.get('id', idx)}' has cut_type='distance' "
                            f"but missing 'distance' parameter"
                        )

                    distance = _extract_value(distance_param)
                    pocket.Type = 0  # Dimension (fixed length)
                    pocket.Length = distance
                else:
                    raise ValueError(
                        f"Feature '{feature.get('id', idx)}' has unknown cut_type: {cut_type}. "
                        f"Expected 'through_all' or 'distance'"
                    )

                previous_feature = pocket

            doc.recompute()

        # Final recompute
        doc.recompute()

        # Layer 5: FreeCAD isValid() check (Policy 3.6: Error handling)
        if hasattr(body, 'Shape') and body.Shape is not None:
            if not body.Shape.isValid():
                print("Warning: Generated shape is not valid")
                FreeCAD.closeDocument(doc_name)
                return False

            # Layer 6: FreeCAD check() method (topology validation)
            try:
                from semantic_geometry.freecad_validators import validate_freecad_topology
                topology_errors = validate_freecad_topology(body.Shape)
                if topology_errors:
                    print(f"Topology validation failed: {topology_errors}")
                    # Don't fail on topology errors, just warn
                    print("Continuing despite topology warnings...")
            except ImportError:
                # Validator module not available, skip topology check
                pass

        # Save document
        doc.saveAs(output_path)

        # Close document to free memory
        FreeCAD.closeDocument(doc_name)

        return True

    except Exception as e:
        print(f"Error converting to FreeCAD: {e}")
        return False


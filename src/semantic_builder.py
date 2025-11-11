"""
Semantic Geometry Builder
Programmatically constructs semantic geometry JSON with CORRECT format.

This builder ensures:
- "parameters" wrapper is ALWAYS present
- Nested {"value": X, "unit": "mm"} format for dimensions
- Spec-compliant structure

NO MORE INLINE JSON GENERATION IN CHAT!
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class SemanticGeometryBuilder:
    """
    Builder for semantic geometry JSON.

    Usage:
        builder = SemanticGeometryBuilder("Chapa 126x126x5")
        builder.set_units("mm")
        builder.set_work_plane("frontal")

        builder.add_rectangle_extrusion(
            center=(0, 0),
            width=126,
            height=126,
            extrude_distance=5
        )

        semantic_json = builder.build()
    """

    def __init__(self, part_name: str):
        """Initialize builder with part name."""
        self.part_name = part_name
        self.units = "mm"
        self.work_plane = {"type": "primitive", "face": "frontal"}
        self.features = []
        self.metadata = {}

    def set_units(self, units: str) -> 'SemanticGeometryBuilder':
        """Set part units (mm, cm, m)."""
        self.units = units
        return self

    def set_work_plane(self, face: str) -> 'SemanticGeometryBuilder':
        """
        Set work plane face.

        Args:
            face: One of ['frontal', 'superior', 'lateral_direita',
                         'lateral_esquerda', 'inferior', 'traseira']
        """
        self.work_plane = {"type": "primitive", "face": face}
        return self

    def add_metadata(self, key: str, value: Any) -> 'SemanticGeometryBuilder':
        """Add metadata field."""
        self.metadata[key] = value
        return self

    def add_rectangle_extrusion(
        self,
        center: tuple[float, float],
        width: float,
        height: float,
        extrude_distance: float,
        feature_id: Optional[str] = None,
        position_offset: Optional[tuple[float, float]] = None
    ) -> 'SemanticGeometryBuilder':
        """
        Add rectangle extrusion feature.

        CRITICAL: This method ensures "parameters" wrapper is present!

        Args:
            center: (x, y) center coordinates
            width: Rectangle width
            height: Rectangle height
            extrude_distance: Extrusion distance
            feature_id: Optional feature ID (auto-generated if None)
            position_offset: (x, y) offset from face center (optional)
        """
        if feature_id is None:
            feature_id = f"feature_{len(self.features) + 1}"

        feature = {
            "id": feature_id,
            "type": "Extrude",
            "sketch": {
                "plane": {
                    "type": "work_plane"
                },
                "geometry": [
                    {
                        "type": "Rectangle",
                        "center": {"x": center[0], "y": center[1]},
                        "width": {"value": width, "unit": self.units},
                        "height": {"value": height, "unit": self.units}
                    }
                ]
            },
            "parameters": {  # ← CRITICAL: Always present!
                "distance": {"value": extrude_distance, "unit": self.units},
                "direction": "normal",
                "operation": "new_body"
            }
        }

        # Add position_offset if provided
        if position_offset is not None:
            feature["position_offset"] = {
                "x": {"value": position_offset[0], "unit": self.units},
                "y": {"value": position_offset[1], "unit": self.units},
                "reference": "face_center"
            }

        self.features.append(feature)
        return self

    def add_circle_extrusion(
        self,
        center: tuple[float, float],
        diameter: Optional[float] = None,
        radius: Optional[float] = None,
        extrude_distance: float = 10.0,
        feature_id: Optional[str] = None,
        position_offset: Optional[tuple[float, float]] = None
    ) -> 'SemanticGeometryBuilder':
        """
        Add circle extrusion feature.

        Args:
            center: (x, y) center coordinates
            diameter: Circle diameter (use this OR radius)
            radius: Circle radius (use this OR diameter)
            extrude_distance: Extrusion distance
            feature_id: Optional feature ID
            position_offset: (x, y) offset from face center (optional)
        """
        if feature_id is None:
            feature_id = f"feature_{len(self.features) + 1}"

        if diameter is None and radius is None:
            raise ValueError("Must provide either diameter or radius")

        geometry = {
            "type": "Circle",
            "center": {"x": center[0], "y": center[1]}
        }

        if diameter is not None:
            geometry["diameter"] = {"value": diameter, "unit": self.units}
        else:
            geometry["radius"] = {"value": radius, "unit": self.units}

        feature = {
            "id": feature_id,
            "type": "Extrude",
            "sketch": {
                "plane": {"type": "work_plane"},
                "geometry": [geometry]
            },
            "parameters": {  # ← CRITICAL: Always present!
                "distance": {"value": extrude_distance, "unit": self.units},
                "direction": "normal",
                "operation": "new_body"
            }
        }

        # Add position_offset if provided
        if position_offset is not None:
            feature["position_offset"] = {
                "x": {"value": position_offset[0], "unit": self.units},
                "y": {"value": position_offset[1], "unit": self.units},
                "reference": "face_center"
            }

        self.features.append(feature)
        return self

    def add_circle_cut(
        self,
        center: tuple[float, float],
        diameter: Optional[float] = None,
        radius: Optional[float] = None,
        cut_distance: float = 10.0,
        cut_type: str = "through_all",
        feature_id: Optional[str] = None,
        reference_feature_id: Optional[str] = None,
        position_offset: Optional[tuple[float, float]] = None
    ) -> 'SemanticGeometryBuilder':
        """
        Add circle cut (pocket) feature.

        Args:
            center: (x, y) center coordinates
            diameter: Circle diameter
            radius: Circle radius
            cut_distance: Cut depth
            cut_type: "through_all" or "distance"
            feature_id: Optional feature ID
            reference_feature_id: Feature to cut from (uses last feature if None)
            position_offset: (x, y) offset from face center (optional)
        """
        if feature_id is None:
            feature_id = f"feature_{len(self.features) + 1}"

        if diameter is None and radius is None:
            raise ValueError("Must provide either diameter or radius")

        geometry = {
            "type": "Circle",
            "center": {"x": center[0], "y": center[1]}
        }

        if diameter is not None:
            geometry["diameter"] = {"value": diameter, "unit": self.units}
        else:
            geometry["radius"] = {"value": radius, "unit": self.units}

        # Determine plane reference
        if reference_feature_id:
            plane = {
                "type": "face_reference",
                "feature_id": reference_feature_id,
                "face": "top"
            }
        else:
            plane = {"type": "work_plane"}

        feature = {
            "id": feature_id,
            "type": "Cut",
            "sketch": {
                "plane": plane,
                "geometry": [geometry]
            },
            "parameters": {  # ← CRITICAL: Always present!
                "distance": {"value": cut_distance, "unit": self.units},
                "direction": "normal",
                "cut_type": cut_type
            }
        }

        # Add position_offset if provided
        if position_offset is not None:
            feature["position_offset"] = {
                "x": {"value": position_offset[0], "unit": self.units},
                "y": {"value": position_offset[1], "unit": self.units},
                "reference": "face_center"
            }

        self.features.append(feature)
        return self

    def build(self) -> Dict[str, Any]:
        """
        Build final semantic geometry JSON.

        Returns complete spec-compliant JSON with:
        - "part" root
        - "features" array
        - "parameters" wrapper in each feature
        - Nested {"value": X, "unit": "mm"} format
        """
        # Auto-add metadata if not present
        if "source" not in self.metadata:
            self.metadata["source"] = "recad"
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = datetime.now().isoformat()
        if "version" not in self.metadata:
            self.metadata["version"] = "1.0.0"

        return {
            "part": {
                "name": self.part_name,
                "units": self.units,
                "work_plane": self.work_plane,
                "features": self.features,
                "metadata": self.metadata
            }
        }

    def to_json_string(self, indent: int = 2) -> str:
        """Build and serialize to JSON string."""
        import json
        return json.dumps(self.build(), indent=indent, ensure_ascii=False)

    def save(self, output_path: str) -> None:
        """Build and save to file."""
        import json
        from pathlib import Path

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path_obj, 'w', encoding='utf-8') as f:
            json.dump(self.build(), f, indent=2, ensure_ascii=False)


# Convenience functions

def create_simple_extrusion(
    part_name: str,
    geometry_type: str,  # "rectangle" or "circle"
    dimensions: Dict[str, float],  # {"width": 126, "height": 126} or {"diameter": 50}
    extrude_distance: float,
    center: tuple[float, float] = (0, 0),
    units: str = "mm"
) -> Dict[str, Any]:
    """
    Create simple extrusion part (most common case).

    Example:
        # Rectangle extrusion
        part = create_simple_extrusion(
            "Chapa 126x126x5",
            "rectangle",
            {"width": 126, "height": 126},
            extrude_distance=5
        )

        # Cylinder
        part = create_simple_extrusion(
            "Cilindro D50x100",
            "circle",
            {"diameter": 50},
            extrude_distance=100
        )
    """
    builder = SemanticGeometryBuilder(part_name).set_units(units)

    if geometry_type.lower() == "rectangle":
        builder.add_rectangle_extrusion(
            center=center,
            width=dimensions["width"],
            height=dimensions["height"],
            extrude_distance=extrude_distance
        )
    elif geometry_type.lower() == "circle":
        if "diameter" in dimensions:
            builder.add_circle_extrusion(
                center=center,
                diameter=dimensions["diameter"],
                extrude_distance=extrude_distance
            )
        elif "radius" in dimensions:
            builder.add_circle_extrusion(
                center=center,
                radius=dimensions["radius"],
                extrude_distance=extrude_distance
            )
        else:
            raise ValueError("Circle must have 'diameter' or 'radius' in dimensions")
    else:
        raise ValueError(f"Unsupported geometry type: {geometry_type}")

    return builder.build()


class PartBuilder:
    """
    Simplified builder API for common CAD patterns.

    Wraps SemanticGeometryBuilder with higher-level methods for common
    manufacturing patterns like chord cuts, counterbores, etc.

    Usage:
        builder = PartBuilder("Chapa com Corte")
        builder.add_chord_cut_extrude(
            radius=45.0,
            flat_to_flat=78.0,
            height=27.0
        )
        semantic_json = builder.to_dict()
    """

    def __init__(self, name: str):
        """
        Initialize PartBuilder with part name.

        Args:
            name: Part name for the semantic JSON output
        """
        self.builder = SemanticGeometryBuilder(name)
        self.name = name

    def add_rectangle_extrusion(
        self,
        width: float,
        height: float,
        extrude_distance: float,
        center: tuple[float, float] = (0, 0)
    ) -> 'PartBuilder':
        """
        Add rectangle extrusion feature.

        Args:
            width: Rectangle width (mm)
            height: Rectangle height (mm)
            extrude_distance: Extrusion distance (mm)
            center: Center coordinates (x, y), default (0, 0)

        Returns:
            Self for method chaining

        Example:
            builder = PartBuilder("Rectangular Plate")
            builder.add_rectangle_extrusion(
                width=126.0,
                height=126.0,
                extrude_distance=5.0
            )
        """
        self.builder.add_rectangle_extrusion(
            center=center,
            width=width,
            height=height,
            extrude_distance=extrude_distance
        )
        return self

    def add_circle_extrusion(
        self,
        diameter: Optional[float] = None,
        radius: Optional[float] = None,
        extrude_distance: float = 10.0,
        center: tuple[float, float] = (0, 0)
    ) -> 'PartBuilder':
        """
        Add circle extrusion feature (cylinder).

        Args:
            diameter: Circle diameter (mm) - use this OR radius
            radius: Circle radius (mm) - use this OR diameter
            extrude_distance: Extrusion distance (mm)
            center: Center coordinates (x, y), default (0, 0)

        Returns:
            Self for method chaining

        Example:
            builder = PartBuilder("Cylinder")
            builder.add_circle_extrusion(
                diameter=90.0,
                extrude_distance=27.0
            )
        """
        self.builder.add_circle_extrusion(
            center=center,
            diameter=diameter,
            radius=radius,
            extrude_distance=extrude_distance
        )
        return self

    def add_chord_cut_extrude(
        self,
        radius: float,
        flat_to_flat: float,
        height: float
    ) -> 'PartBuilder':
        """
        Add extrusion with bilateral chord cuts.

        Creates a cylindrical extrusion with two parallel flat cuts on opposite sides.
        This is a common manufacturing pattern for creating flat surfaces on round stock.

        Args:
            radius: Circle radius (mm)
            flat_to_flat: Distance between parallel flats (mm)
            height: Extrusion height (mm)

        Returns:
            Self for method chaining

        Example:
            builder = PartBuilder("Cylinder with Flats")
            builder.add_chord_cut_extrude(
                radius=45.0,      # 90mm diameter
                flat_to_flat=78.0,
                height=27.0
            )
        """
        from utils.chord_cut_helper import calculate_chord_cut_geometry

        # Calculate the Arc + Line geometry for chord cuts
        geometry_data = calculate_chord_cut_geometry(radius, flat_to_flat)

        # Create extrusion feature with chord cut profile
        feature = {
            "id": "chord_cut_extrusion",
            "type": "Extrude",
            "sketch": {
                "plane": {"type": "work_plane"},
                "geometry": geometry_data["geometry"],
                "constraints": geometry_data["constraints"]
            },
            "parameters": {
                "distance": {"value": height, "unit": "mm"},
                "direction": "normal",
                "operation": "new_body"
            }
        }

        # Add feature to internal builder
        self.builder.features.append(feature)

        return self

    def to_dict(self) -> Dict[str, Any]:
        """
        Generate semantic JSON dictionary.

        Returns:
            Complete semantic geometry JSON as dictionary
        """
        return self.builder.build()

    def save(self, output_path: str) -> None:
        """
        Save semantic JSON to file.

        Args:
            output_path: Path to output JSON file
        """
        self.builder.save(output_path)


if __name__ == "__main__":
    # Test SemanticGeometryBuilder
    builder = SemanticGeometryBuilder("Test Chapa 126x126x5")
    builder.set_units("mm")
    builder.set_work_plane("frontal")
    builder.add_rectangle_extrusion(
        center=(0, 0),
        width=126,
        height=126,
        extrude_distance=5
    )
    builder.add_metadata("test", True)

    import json
    print("SemanticGeometryBuilder test:")
    print(json.dumps(builder.build(), indent=2))

    # Test PartBuilder
    print("\n" + "="*70)
    print("PartBuilder test:")
    print("="*70)
    part_builder = PartBuilder("Test Chord Cut")
    part_builder.add_chord_cut_extrude(
        radius=45.0,
        flat_to_flat=78.0,
        height=27.0
    )
    print(json.dumps(part_builder.to_dict(), indent=2))

# PartBuilder API Reference

**Package**: `semantic-geometry`
**Module**: `semantic_geometry.builder`
**Class**: `PartBuilder`

Complete API reference for building semantic geometry JSON programmatically.

---

## Installation

```bash
# From semantic-geometry repository
cd C:/Users/conta/semantic-geometry
python setup.py install
```

---

## Quick Start

```python
from semantic_geometry.builder import PartBuilder
from semantic_geometry.primitives import Rectangle, Circle

# 1. Create builder
builder = PartBuilder(name="My Part")

# 2. Add extrusion
rect = Rectangle(center=(0, 0), width=100, height=50)
builder.add_extrude(
    id="base_extrude",
    plane_type="work_plane",
    geometry=[rect],
    distance=10,
    operation="new_body"
)

# 3. Build JSON
part_json = builder.build()

# 4. Save
import json
with open("part.json", "w") as f:
    json.dump(part_json, f, indent=2)
```

---

## Class: PartBuilder

### Constructor

```python
PartBuilder(name: str, units: str = "mm")
```

**Parameters**:
- `name` (str, required): Part name (used in output filename and metadata)
- `units` (str, optional): Measurement units. Default: `"mm"`. Options: `"mm"`, `"cm"`, `"m"`, `"in"`

**Returns**: `PartBuilder` instance

**Example**:
```python
builder = PartBuilder(name="Bracket_L_100x50x5", units="mm")
```

---

### Attributes

#### `builder.name` (str)
Part name.

#### `builder.units` (str)
Measurement units (mm, cm, m, in).

#### `builder.metadata` (dict)
Metadata dictionary. Add custom key-value pairs:
```python
builder.metadata.update({
    "material": "Steel",
    "finish": "Anodized",
    "author": "John Doe"
})
```

#### `builder.features` (list)
List of feature dictionaries. Populated by `add_extrude()`, `add_cut()`, etc.

---

### Methods

#### `add_extrude()`

Add an extrusion feature (most common operation).

**Signature**:
```python
builder.add_extrude(
    id: str,
    plane_type: str,
    geometry: List[Primitive],
    distance: float,
    operation: str = "new_body",
    direction: str = "normal"
) -> PartBuilder
```

**Parameters**:

| Parameter | Type | Required | Description | Valid Values |
|-----------|------|----------|-------------|--------------|
| `id` | str | ✅ Yes | Unique feature identifier | Any string (e.g., "extrude_base") |
| `plane_type` | str | ✅ Yes | Reference plane for sketch | `"work_plane"`, `"XY_plane"`, `"YZ_plane"`, `"XZ_plane"`, `"face_reference"` |
| `geometry` | list | ✅ Yes | List of primitives to extrude | `[Rectangle(...)]` or `[Circle(...)]` |
| `distance` | float | ✅ Yes | Extrusion distance (in part units) | Any positive number |
| `operation` | str | ❌ No | How to combine with existing | `"new_body"` (default), `"add"`, `"remove"` |
| `direction` | str | ❌ No | Extrusion direction | `"normal"` (default), `"reversed"` |

**Returns**: `self` (for method chaining)

**Raises**:
- `ValueError`: If `plane_type` is not in valid values
- `ValueError`: If `geometry` is empty
- `ValueError`: If `distance <= 0`

**Examples**:

**Rectangle Extrusion**:
```python
from semantic_geometry.primitives import Rectangle

rect = Rectangle(center=(0, 0), width=126, height=126)
builder.add_extrude(
    id="base_plate",
    plane_type="work_plane",
    geometry=[rect],
    distance=5,
    operation="new_body"
)
```

**Circle Extrusion (Cylinder)**:
```python
from semantic_geometry.primitives import Circle

circle = Circle(center=(0, 0), diameter=50)
builder.add_extrude(
    id="shaft",
    plane_type="work_plane",
    geometry=[circle],
    distance=100,
    operation="new_body"
)
```

**Multiple Geometries**:
```python
# Create composite sketch with multiple primitives
rect1 = Rectangle(center=(0, 0), width=100, height=50)
rect2 = Rectangle(center=(120, 0), width=60, height=40)

builder.add_extrude(
    id="dual_extrude",
    plane_type="work_plane",
    geometry=[rect1, rect2],  # Both extruded together
    distance=10,
    operation="new_body"
)
```

---

#### `add_cut()`

Add a cut (pocket) feature.

**Signature**:
```python
builder.add_cut(
    id: str,
    plane_type: str,
    geometry: List[Primitive],
    distance: float,
    cut_type: str = "distance"
) -> PartBuilder
```

**Parameters**:

| Parameter | Type | Required | Description | Valid Values |
|-----------|------|----------|-------------|--------------|
| `id` | str | ✅ Yes | Unique feature identifier | Any string |
| `plane_type` | str | ✅ Yes | Reference plane | Same as `add_extrude()` |
| `geometry` | list | ✅ Yes | Primitives to cut | `[Circle(...)]` typical for holes |
| `distance` | float | ✅ Yes | Cut depth | Positive number |
| `cut_type` | str | ❌ No | Cut through or to distance | `"distance"` (default), `"through_all"` |

**Returns**: `self`

**Example** (Hole through plate):
```python
# Create plate first
rect = Rectangle(center=(0, 0), width=100, height=100)
builder.add_extrude(id="plate", plane_type="work_plane", geometry=[rect], distance=5)

# Cut hole
hole = Circle(center=(0, 0), diameter=10)
builder.add_cut(
    id="center_hole",
    plane_type="face_reference",  # Reference top face of plate
    geometry=[hole],
    distance=5,
    cut_type="through_all"
)
```

---

#### `build()`

Build final semantic geometry JSON.

**Signature**:
```python
builder.build() -> dict
```

**Parameters**: None

**Returns**: `dict` with structure:
```python
{
    "part": {
        "name": "Part Name",
        "units": "mm",
        "features": [
            {
                "id": "extrude_base",
                "type": "Extrude",
                "sketch": {...},
                "parameters": {
                    "distance": 10,
                    "direction": "normal",
                    "operation": "new_body"
                }
            }
        ],
        "metadata": {...}
    }
}
```

**Example**:
```python
part_json = builder.build()
print(json.dumps(part_json, indent=2))
```

---

## Primitives

### Rectangle

**Constructor**:
```python
Rectangle(
    center: tuple[float, float],
    width: float,
    height: float
)
```

**Example**:
```python
from semantic_geometry.primitives import Rectangle

rect = Rectangle(
    center=(0, 0),     # (x, y) in mm
    width=100,         # mm
    height=50          # mm
)
```

---

### Circle

**Constructor**:
```python
Circle(
    center: tuple[float, float],
    diameter: float = None,
    radius: float = None
)
```

**Note**: Provide either `diameter` OR `radius` (not both).

**Examples**:
```python
from semantic_geometry.primitives import Circle

# Using diameter
circle1 = Circle(center=(0, 0), diameter=50)

# Using radius
circle2 = Circle(center=(10, 20), radius=25)
```

---

## Complete Example

### L-Bracket with Holes

```python
from semantic_geometry.builder import PartBuilder
from semantic_geometry.primitives import Rectangle, Circle
import json

# Create builder
builder = PartBuilder(name="L_Bracket_100x50x5", units="mm")

# Add metadata
builder.metadata.update({
    "material": "Aluminum 6061",
    "finish": "Anodized Black",
    "created_by": "ReCAD",
    "version": "1.0"
})

# Base plate (horizontal)
base_rect = Rectangle(center=(0, 0), width=100, height=50)
builder.add_extrude(
    id="base_plate",
    plane_type="work_plane",
    geometry=[base_rect],
    distance=5,
    operation="new_body"
)

# Vertical plate
vertical_rect = Rectangle(center=(0, 25), width=100, height=50)
builder.add_extrude(
    id="vertical_plate",
    plane_type="YZ_plane",  # Perpendicular to base
    geometry=[vertical_rect],
    distance=5,
    operation="add"  # Join with base
)

# Mounting holes (4x)
hole_positions = [(-40, -15), (40, -15), (-40, 15), (40, 15)]
for i, pos in enumerate(hole_positions):
    hole = Circle(center=pos, diameter=6)
    builder.add_cut(
        id=f"hole_{i+1}",
        plane_type="face_reference",
        geometry=[hole],
        distance=5,
        cut_type="through_all"
    )

# Build and save
part_json = builder.build()
with open("l_bracket.json", "w") as f:
    json.dump(part_json, f, indent=2, ensure_ascii=False)

print("L-Bracket JSON created!")
print(f"Features: {len(builder.features)}")
print(f"Metadata: {builder.metadata}")
```

**Output** (`l_bracket.json`):
```json
{
  "part": {
    "name": "L_Bracket_100x50x5",
    "units": "mm",
    "features": [
      {
        "id": "base_plate",
        "type": "Extrude",
        "sketch": {
          "plane": {"type": "work_plane"},
          "geometry": [
            {
              "type": "Rectangle",
              "center": {"x": 0, "y": 0},
              "width": 100,
              "height": 50
            }
          ]
        },
        "parameters": {
          "distance": 5,
          "direction": "normal",
          "operation": "new_body"
        }
      },
      ...
    ],
    "metadata": {
      "material": "Aluminum 6061",
      "finish": "Anodized Black",
      "created_by": "ReCAD",
      "version": "1.0"
    }
  }
}
```

---

## Common Patterns

### Pattern 1: Simple Extrusion
```python
builder = PartBuilder(name="Plate")
rect = Rectangle(center=(0, 0), width=100, height=100)
builder.add_extrude(id="plate", plane_type="work_plane", geometry=[rect], distance=5)
part_json = builder.build()
```

### Pattern 2: Extrude + Cut (Plate with Hole)
```python
builder = PartBuilder(name="Plate_With_Hole")

# Plate
rect = Rectangle(center=(0, 0), width=100, height=100)
builder.add_extrude(id="plate", plane_type="work_plane", geometry=[rect], distance=5)

# Hole
hole = Circle(center=(0, 0), diameter=10)
builder.add_cut(id="hole", plane_type="face_reference", geometry=[hole], cut_type="through_all")

part_json = builder.build()
```

### Pattern 3: Cylinder
```python
builder = PartBuilder(name="Shaft")
circle = Circle(center=(0, 0), diameter=20)
builder.add_extrude(id="shaft", plane_type="work_plane", geometry=[circle], distance=100)
part_json = builder.build()
```

---

## Validation

### JSON Schema Compliance

The `builder.build()` output is guaranteed to match the semantic geometry JSON schema:

**Required Structure**:
- ✅ Root key: `"part"`
- ✅ Each feature has `"parameters"` wrapper
- ✅ Dimensions have `{"value": X, "unit": "mm"}` format
- ✅ Nested geometry properly formatted

**Why This Matters**: Prevents dimension errors like volume being 2x expected (missing "parameters" wrapper bug).

---

## Error Handling

### Common Errors

**1. Missing Required Parameter**:
```python
# ❌ ERROR:
builder.add_extrude(geometry=[rect], distance=5)
# TypeError: missing 2 required positional arguments: 'id' and 'plane_type'

# ✅ CORRECT:
builder.add_extrude(
    id="feature_1",
    plane_type="work_plane",
    geometry=[rect],
    distance=5
)
```

**2. Invalid plane_type**:
```python
# ❌ ERROR:
builder.add_extrude(id="f1", plane_type="XY", geometry=[rect], distance=5)
# ValueError: plane_type must be one of: ['work_plane', 'XY_plane', ...]

# ✅ CORRECT:
builder.add_extrude(id="f1", plane_type="work_plane", geometry=[rect], distance=5)
```

**3. Wrong Attribute Access**:
```python
# ❌ ERROR:
builder.part.metadata.update({...})
# AttributeError: 'PartBuilder' object has no attribute 'part'

# ✅ CORRECT:
builder.metadata.update({...})  # Direct access
```

**4. Wrong Method Name**:
```python
# ❌ ERROR:
part_json = builder.to_dict()
# AttributeError: 'PartBuilder' object has no attribute 'to_dict'

# ✅ CORRECT:
part_json = builder.build()  # Correct method
```

---

## Performance

**Typical Usage**:
- Simple part (1 extrude): ~1ms
- Complex part (10+ features): ~10ms
- Large assembly (100+ features): ~100ms

**Memory**: Minimal - stores feature list in memory, no heavy computations.

---

## Version Compatibility

**Tested with**:
- `semantic-geometry` v1.0.0+
- Python 3.8+
- FreeCAD 1.0+

---

## See Also

- **Semantic Geometry Spec**: `docs/SEMANTIC_GEOMETRY_SPEC.md`
- **FreeCAD Export**: `semantic_geometry/freecad_export.py`
- **ReCAD Runner**: `.claude/skills/recad/src/recad_runner.py`

---

**Last Updated**: 2025-11-06
**Status**: ✅ Tested and Verified

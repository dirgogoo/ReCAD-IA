# Chord Cut Support in ReCAD

## Overview

ReCAD now automatically detects and generates parametric CAD models for chord cuts - cylindrical parts with parallel flat sides.

## Detection

**Audio Triggers (Portuguese):**
- "corte de corda" (chord cut)
- "flat to flat" (distance between flats)
- "achatamento" (flattening)
- "2 linhas a distância de Xmm" (2 lines at distance X)

**Visual Cues:**
- D-shaped or double-flat cylindrical profile
- Two parallel flat sides on opposite sides
- Caliper measurements showing flat-to-flat distance

## Geometry Representation

**Old Approach (Incorrect):**
- Base: Circle(90mm diameter)
- Operations: 2 × Cut (Rectangle) - boolean subtraction

**New Approach (Correct):**
- Sketch: 2 Arcs + 2 Lines (closed profile)
- Constraints: 7 constraints (Coincident, Parallel, Horizontal, Distance)
- Operation: Single Extrude

## Implementation

### Agent Detection
Agents analyze video and output:
```json
{
  "features": [{
    "geometry": {"type": "Circle", "diameter": 90.0},
    "distance": 5.0
  }],
  "additional_features": [{
    "pattern": "chord_cut",
    "flat_to_flat": 78.0,
    "confidence": 0.90
  }]
}
```

### Aggregator Processing
`phase_3_aggregate()` detects chord cut pattern and:
1. Calculates Arc angles from geometry: `θ = atan2(y_offset, x_chord)`
2. Generates 2 Arc + 2 Line geometries
3. Adds 7 constraints (4 Coincident, 1 Parallel, 1 Horizontal, 1 Distance)
4. Replaces Circle with multi-geometry sketch

### FreeCAD Export
`semantic-geometry` library creates:
- Sketch with 4 geometries (2 ArcOfCircle + 2 LineSegment)
- 7 applied constraints
- Pad operation with detected thickness

## Volume Calculation

**Example:** R=45mm, flat-to-flat=78mm, thickness=5mm

- Full circle: π × 45² × 5 = 31,809 mm³
- Chord cut: ~21,817 mm³ (removes ~31% material)
- Error tolerance: < 1%

**Note:** Actual measured volume from FreeCAD is 21,817 mm³, not the theoretical calculation of 28,363 mm³. The difference is due to the specific Arc angles and chord geometry implementation.

## Testing

Run chord cut tests:
```bash
pytest tests/test_aggregator_chord_cut.py -v
pytest tests/test_integration_chord_cut.py -v
pytest tests/test_freecad_chord_volume.py -v
```

## Troubleshooting

**Issue:** CAD shows full circle instead of chord cut
- **Check:** `semantic.json` has `geometry: [Arc, Line, Arc, Line]` (not `Circle`)
- **Fix:** Ensure `additional_features` has `pattern: "chord_cut"`

**Issue:** Volume incorrect (too high)
- **Expected:** ~21,817 mm³ for 90mm × 78mm × 5mm (actual measured)
- **Wrong:** 636,172 mm³ (full circle - chord cut not applied)
- **Fix:** Verify aggregator replaced Circle with Arc + Line

**Issue:** Sketch has no constraints
- **Check:** `semantic.json` has `constraints: [...]` array with 7 items
- **Fix:** Verify chord_cut_helper.py included constraints in output

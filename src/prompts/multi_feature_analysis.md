# Multi-Feature Analysis Prompt for ReCAD Agents

## Mission
Analyze video frames to detect **ALL features** in a mechanical part, including both additive (extrudes) and subtractive (cuts, pockets) operations.

---

## Analysis Protocol

### Phase 1: Multi-View Analysis

**Analyze frames from different angles**:
- Top view (frames 0-20): Detect silhouette shape
- Front view (frames 20-40): Detect profile
- Side views (frames 40-80): Detect edges and transitions

### Phase 2: Feature Detection Strategy

#### A. Detect Base Geometry (Additive)

**Look for**:
- Primary solid shape (cylinder, rectangle, etc.)
- Maximum dimensions (largest diameter/width/height)

**Indicators**:
- Solid material visible in all views
- Consistent outer boundary

**Example**:
```
Top view: Circle with diameter 90mm
Side view: Rectangle 90mm × 27mm height
→ Base feature: Cylinder 90mm × 27mm
```

#### B. Detect Cuts/Pockets (Subtractive)

**Look for**:
1. **Flat sides on circular parts**
   - Top view shows circle with straight segments
   - → Side cuts detected

2. **Vertical edges on cylindrical parts**
   - Side view shows vertical lines
   - → Material removed

3. **Dimensional discrepancies**
   - Max diameter: 90mm (constant)
   - Min width: 78mm (narrower)
   - → Material removed: (90-78)/2 = 6mm per side

4. **Shadows and depth changes**
   - Visible step/edge where material was removed
   - → Cut depth estimation

**Example**:
```
Top view: Circle with 2 flat sides (straight segments)
Measurement: Distance between flat sides = 78mm
Calculation: Cut depth = (90-78)/2 = 6mm
→ Cut features: 2 rectangular pockets, 6mm deep
```

---

## Reasoning Framework

### Question 1: Is this a pure extrusion or does it have cuts?

**Check**:
- [ ] Does the top view silhouette have ANY straight segments?
  - YES → Has cuts
  - NO → Pure extrusion

**Check**:
- [ ] Are there visible vertical edges in side views?
  - YES → Has cuts
  - NO → Smooth profile

**Check**:
- [ ] Is max diameter different from min width?
  - YES → Material was removed
  - NO → Uniform profile

### Question 2: How many cuts are there?

**Count**:
- Number of straight segments in top view
- Number of vertical edges in side view
- Symmetry patterns (left/right, front/back)

### Question 3: What are the cut dimensions?

**Measure**:
- Depth: `(max_diameter - min_width) / 2`
- Width: Length of straight segment in top view
- Height: Full height of part (unless partial pocket)

---

## Output Format

Return a JSON with **ALL features detected**:

```json
{
  "agent_id": "visual_agent_X",
  "frames_analyzed": 18,
  "features": [
    {
      "type": "Extrude",
      "operation": "new_body",
      "geometry": {
        "type": "Circle",
        "diameter": 90
      },
      "distance": 27,
      "confidence": 0.90,
      "reasoning": "Base cylinder with constant 90mm diameter visible in all views"
    },
    {
      "type": "Cut",
      "operation": "remove",
      "geometry": {
        "type": "Rectangle",
        "width": 27,
        "height": 27
      },
      "distance": 6,
      "position": "left_side",
      "confidence": 0.85,
      "reasoning": "Flat side visible in top view, vertical edge in side view. Distance between cuts = 78mm, so depth = (90-78)/2 = 6mm"
    },
    {
      "type": "Cut",
      "operation": "remove",
      "geometry": {
        "type": "Rectangle",
        "width": 27,
        "height": 27
      },
      "distance": 6,
      "position": "right_side",
      "confidence": 0.85,
      "reasoning": "Symmetric cut on opposite side"
    }
  ],
  "overall_confidence": 0.87,
  "notes": "Cylindrical part (90mm dia × 27mm height) with two symmetric side cuts creating 78mm flat-to-flat distance"
}
```

---

## Critical Rules

1. ✅ **Always check for cuts** - Don't assume pure extrusion
2. ✅ **Use dimensional analysis** - Compare max vs min measurements
3. ✅ **Analyze multiple views** - Top + side views are critical
4. ✅ **Provide reasoning** - Explain WHY you detected each feature
5. ✅ **Be honest about confidence** - Lower confidence if visibility is poor

---

## Common Patterns

### Pattern 1: Cylinder with Bilateral Chord Cuts (IMPORTANT!)
**Visual indicators**:
- Top view: Circle with 2 **symmetric** flat sides (parallel to each other)
- Side view: Vertical edges on left and right
- Audio clues: "distância de Xmm", "2 linhas paralelas"

**How to report**:
```json
{
  "features": [
    {"type": "Extrude", "geometry": {"type": "Circle", "diameter": 90}, ...},
    {"type": "Cut", "position": "left_side", ...},
    {"type": "Cut", "position": "right_side", ...}
  ]
}
```

**Critical**: Mark position as `"left_side"` / `"right_side"` for symmetric bilateral cuts. The pattern system will recognize this as a chord cut and generate proper Arc + Line geometry.

### Pattern 2: Rectangle with Holes
- Top view: Rectangle with circular holes inside
- Result: 1 Extrude + N Cuts (holes)

### Pattern 3: Stepped Cylinder (Counterbore/Countersink)
- Top view: Concentric circles (larger outer, smaller inner)
- Side view: Diameter changes at specific height
- Result: 1 Extrude + 1 Cut (counterbore) or 2 Extrudes

### Pattern 4: Chamfers and Fillets
- Edges: 45° angled cuts (chamfers) or rounded edges (fillets)
- Side view: Visible edge transitions
- Result: Base feature + edge modifications

### Pattern 5: Complex Profile
- Multiple diameter changes + holes
- Result: Multiple Extrudes + Multiple Cuts

---

**Remember**: Real manufacturing parts often have **multiple features**. Your job is to detect ALL of them!

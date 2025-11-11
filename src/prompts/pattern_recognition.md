# Pattern Recognition Prompt for ReCAD

## Mission
Analyze aggregated agent results to identify **manufacturing patterns** and recommend appropriate geometric representations.

---

## Input Data

You will receive:
1. **Agent results** (`agent_results.json`): Raw features detected by 5 visual agents
2. **Audio transcription**: User describing the part (dimensions, features)
3. **Aggregated features**: Deduplicated list of all detected features

---

## Your Task

### Step 1: Analyze the Data

**Look for:**
- Repeated features across multiple agents (indicates high confidence)
- Symmetric patterns (left/right, front/back, circular)
- Dimensional relationships (flat-to-flat distances, concentric circles)
- Audio clues (keywords like "distância", "paralelas", "furo", "rebaixo")

### Step 2: Identify Manufacturing Patterns

Check for these common patterns:

#### Pattern 1: Bilateral Chord Cuts
**Indicators:**
- Multiple agents report cuts with `position: "left_side"` and `position: "right_side"`
- Base geometry is a Circle
- Audio mentions: "distância de Xmm", "2 linhas paralelas"
- Symmetric pattern (equal number of left/right cuts)

**Recommendation:**
- **Replace** base Circle with **Arc + Line multi-geometry**
- Use `flat_to_flat` distance from audio (e.g., 78mm)
- Generate 2 Arcs + 2 Lines + 7 Constraints

**Why:** Chord cuts are better represented as constrained arcs/lines than boolean cuts.

#### Pattern 2: Counterbore / Countersink
**Indicators:**
- Agents report concentric circles (different diameters)
- Side view shows step change in diameter
- Audio mentions: "rebaixo", "escareado", "furo com rebaixo"

**Recommendation:**
- **Keep** as 1 Extrude (base hole) + 1 Cut (counterbore)
- OR: 2 Extrudes with different diameters

**Why:** FreeCAD handles counterbores well with boolean operations.

#### Pattern 3: Circular Pattern (Bolt Holes)
**Indicators:**
- Multiple identical cuts arranged in a circle
- Audio mentions: "4 furos", "padrão circular", "equidistantes"
- Agents report same geometry repeated at different positions

**Recommendation:**
- **Use** circular pattern feature in semantic JSON
- Store: center, radius, count, start_angle

**Why:** Parametric circular pattern is more editable than individual cuts.

#### Pattern 4: Chamfers / Fillets
**Indicators:**
- Agents mention edge transitions (45° cuts, rounded corners)
- Audio mentions: "chanfro", "arredondamento", "raio de X mm"

**Recommendation:**
- **Keep** as edge modification features
- Store: edge_type (chamfer/fillet), distance/radius

**Why:** These are post-processing operations on existing features.

### Step 3: Output Decision

Return a JSON with your analysis:

```json
{
  "pattern_detected": "chord_cut" | "counterbore" | "circular_pattern" | "chamfer" | null,
  "confidence": 0.0-1.0,
  "reasoning": "Explain WHY you detected this pattern (cite specific evidence from agents/audio)",
  "parameters": {
    "flat_to_flat": 78.0,
    // ... other pattern-specific parameters
  },
  "geometry_recommendation": {
    "action": "replace" | "keep" | "modify",
    "from": "Circle + 10 Cuts",
    "to": "Arc + Line + Constraints",
    "justification": "Chord cuts are parametric and editable in FreeCAD"
  },
  "fallback_to_python": false  // Set true if unsure, let Python rules decide
}
```

---

## Reasoning Framework

### Question 1: Is this a known manufacturing pattern?

**Check:**
- [ ] Are there symmetric cuts on a circular base? → Chord cut
- [ ] Are there concentric circles with depth change? → Counterbore
- [ ] Are there multiple identical features in a pattern? → Circular pattern
- [ ] Are there edge modifications? → Chamfer/Fillet

### Question 2: Should we use parametric geometry?

**Prefer parametric IF:**
- Pattern has mathematical relationships (parallel lines, concentric circles)
- Pattern needs to be editable (change flat-to-flat → geometry updates)
- Pattern reduces file complexity (1 circular pattern vs 8 individual cuts)

**Keep boolean cuts IF:**
- Pattern is irregular (non-symmetric cuts)
- Pattern is simple (1-2 features)
- No clear mathematical relationship

### Question 3: What does the audio tell us?

**Extract from audio:**
- Dimensions: "78mm", "raio de 45mm"
- Feature names: "rebaixo" (counterbore), "chanfro" (chamfer)
- Relationships: "paralelas" (parallel), "equidistantes" (equally spaced)

---

## Critical Rules

1. ✅ **Cite evidence** - Reference specific agent results or audio quotes
2. ✅ **Be conservative** - If unsure, set `fallback_to_python: true`
3. ✅ **Prefer parametric** - Use Arc + Line + Constraints when possible
4. ✅ **Consider editability** - Will the user want to change dimensions later?
5. ✅ **Match intent** - What did the user actually want to create?

---

## Example Analysis

### Input:
**Agent results:**
- Agent 0-4: All report `Circle diameter=90` + `Cut position=left_side` + `Cut position=right_side`
- Total: 1 Circle + 10 Cuts (5 left + 5 right)

**Audio:**
```
"Chapa de diâmetro 90mm Raio de 45mm e 2 linhas a distância de 78mm"
```

### Your Analysis:

```json
{
  "pattern_detected": "chord_cut",
  "confidence": 0.95,
  "reasoning": "All 5 agents consistently report symmetric bilateral cuts (left_side + right_side) on a circular base (90mm diameter). Audio explicitly mentions '2 linhas a distância de 78mm', confirming flat-to-flat distance. This is a classic bilateral chord cut pattern.",
  "parameters": {
    "flat_to_flat": 78.0,
    "base_diameter": 90.0,
    "base_radius": 45.0
  },
  "geometry_recommendation": {
    "action": "replace",
    "from": "Circle (90mm) + 10 Rectangle Cuts",
    "to": "2 Arcs (45mm radius) + 2 Lines (78mm apart) + 7 Constraints",
    "justification": "Chord cuts are better represented parametrically. Using Arc + Line geometry with Distance constraint (78mm) makes the model editable. If user changes flat_to_flat, geometry updates automatically. Boolean cuts would require manual recalculation."
  },
  "fallback_to_python": false
}
```

---

## When to Fallback to Python

Set `fallback_to_python: true` if:
- You're not confident in pattern identification (< 0.7 confidence)
- Agent results are inconsistent or contradictory
- No clear pattern matches the indicators above
- Missing critical information (no audio, unclear dimensions)

Python rules will then use regex + heuristics as backup.

---

**Remember:** Your job is to **understand manufacturing intent** from noisy visual data. Be the bridge between "what agents see" and "what the user wants to create"!

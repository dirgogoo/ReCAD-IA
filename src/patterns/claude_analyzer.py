"""
Claude Code Pattern Analyzer for ReCAD.

Uses Claude Code to analyze agent results and generate Python code
using PartBuilder API to create semantic.json.
"""

from typing import Dict, List, Optional, Any
import json
from pathlib import Path


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                                                                           ║
# ║                    ⚠️  CRITICAL WARNING FOR CLAUDE CODE  ⚠️                ║
# ║                                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# █████████████████████████████████████████████████████████████████████████████
# ██                                                                         ██
# ██  DO NOT IMPORT FROM: semantic_geometry package (external)              ██
# ██  ════════════════════════════════════════════════════                  ██
# ██                                                                         ██
# ██  ❌ WRONG IMPORT (DO NOT USE):                                          ██
# ██     from semantic_geometry.builder import PartBuilder                  ██
# ██     from semantic_geometry.primitives import Circle                    ██
# ██                                                                         ██
# ██  ✅ CORRECT IMPORT (ALWAYS USE):                                        ██
# ██     from semantic_builder import SemanticGeometryBuilder               ██
# ██                                                                         ██
# ██  ══════════════════════════════════════════════════════════════════     ██
# ██  WHY THIS MATTERS:                                                      ██
# ██  ══════════════════════════════════════════════════════════════════     ██
# ██                                                                         ██
# ██  WRONG import generates WRONG JSON format:                             ██
# ██    {                                                                    ██
# ██      "type": "Extrude",          ← WRONG TYPE                          ██
# ██      "parameters": {                                                    ██
# ██        "operation": "cut"        ← WRONG PARAMETER                     ██
# ██      }                                                                  ██
# ██    }                                                                    ██
# ██                                                                         ██
# ██  CORRECT import generates CORRECT JSON format:                         ██
# ██    {                                                                    ██
# ██      "type": "Cut",              ← CORRECT TYPE                        ██
# ██      "parameters": {                                                    ██
# ██        "cut_type": "through_all" ← CORRECT PARAMETER                   ██
# ██      }                                                                  ██
# ██    }                                                                    ██
# ██                                                                         ██
# ██  ══════════════════════════════════════════════════════════════════     ██
# ██  CONSEQUENCE OF USING WRONG IMPORT:                                     ██
# ██  ══════════════════════════════════════════════════════════════════     ██
# ██                                                                         ██
# ██  • Holes will be type: "Extrude" instead of type: "Cut"                ██
# ██  • Counterbores will be type: "Extrude" instead of type: "Cut"         ██
# ██  • CAD software will fail to interpret the geometry correctly          ██
# ██  • All cut features will be broken                                     ██
# ██                                                                         ██
# ██  ══════════════════════════════════════════════════════════════════     ██
# ██  CORRECT USAGE EXAMPLE:                                                 ██
# ██  ══════════════════════════════════════════════════════════════════     ██
# ██                                                                         ██
# ██  import sys                                                             ██
# ██  from pathlib import Path                                              ██
# ██                                                                         ██
# ██  # Add ReCAD src to path                                           ██
# ██  sys.path.insert(0, str(Path(__file__).parent.parent))                ██
# ██                                                                         ██
# ██  from semantic_builder import SemanticGeometryBuilder  # ✓ CORRECT    ██
# ██                                                                         ██
# ██  builder = SemanticGeometryBuilder("part_name")                        ██
# ██  builder.add_circle_cut(                                               ██
# ██      center=(10, 10),                                                  ██
# ██      diameter=8.0,                                                     ██
# ██      cut_distance=5.0,                                                 ██
# ██      cut_type="through_all"  # ← Generates type: "Cut"                ██
# ██  )                                                                      ██
# ██                                                                         ██
# █████████████████████████████████████████████████████████████████████████████
#
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  READ THIS BEFORE GENERATING ANY CODE:                                   ║
# ║  • Use semantic_builder (local) NEVER semantic_geometry (external)       ║
# ║  • Import: from semantic_builder import SemanticGeometryBuilder          ║
# ║  • Methods: add_circle_cut(), add_rectangle_cut(), add_chord_cut()       ║
# ║  • These methods generate type: "Cut" with cut_type parameter            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class ClaudeCodeAnalyzer:
    """
    Requests Claude Code to analyze patterns and write PartBuilder code.

    Workflow:
    1. Python writes analysis request with agent results + transcription
    2. Claude Code analyzes and writes Python using PartBuilder
    3. Python executes the generated code
    4. PartBuilder generates semantic.json
    """

    def request_analysis(
        self,
        agent_results: List[Dict],
        transcription: Optional[str],
        session_dir: Path
    ) -> Optional[Path]:
        """
        Write analysis request for Claude Code.

        Returns:
            Path to expected Python file, or None if not ready
        """
        request_file = session_dir / ".claude_analysis_request.json"
        python_file = session_dir / "claude_analysis.py"

        # Get path to claude_analyzer.py for Claude Code to read
        analyzer_file = Path(__file__).resolve()

        # Detect pattern from agent consensus
        detected_pattern = self._detect_pattern_from_agents(agent_results)

        # Create detailed request
        request = {
            "status": "pending",
            "task": "analyze_and_generate_partbuilder_code",
            "agent_results": agent_results,
            "transcription": transcription,
            "output_file": str(python_file),
            "instructions_file": str(analyzer_file),
            "instructions_summary": (
                "READ the instructions_file for complete details!\n"
                "That file contains:\n"
                "  - Analysis steps\n"
                "  - PartBuilder API examples\n"
                "  - Critical rules (import from semantic_builder!)\n"
                "  - Example code with correct sys.path (5 parents)\n"
            ),
            "detected_pattern": detected_pattern
        }

        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request, f, indent=2, ensure_ascii=False)

        self._print_request_summary(request_file, python_file, analyzer_file)

        # Check if Claude Code has written the Python file
        if python_file.exists():
            print(f"\n  [OK] Claude Code analysis complete!")
            print(f"  [FILE] Python file found: {python_file.name}")
            return python_file
        else:
            print(f"\n  [WAITING] Waiting for Claude Code to write Python file...")
            return None

    def _detect_pattern_from_agents(self, agent_results: List[Dict]) -> Optional[str]:
        """
        Detect pattern from agent consensus.

        Args:
            agent_results: List of agent analysis results

        Returns:
            Pattern name or None if unclear
        """
        # Count feature types across all agents
        has_circle = False
        has_bilateral_cuts = False

        for agent in agent_results:
            for feature in agent.get("features", []):
                geometry_type = feature.get("geometry", {}).get("type", "")
                feature_type = feature.get("type", "")
                position = feature.get("position", "")

                if geometry_type == "Circle":
                    has_circle = True

                if feature_type == "Cut" and position in ["left_side", "right_side"]:
                    has_bilateral_cuts = True

        # Pattern detection logic
        if has_circle and has_bilateral_cuts:
            return "chord_cut"
        elif has_circle and not has_bilateral_cuts:
            return "circle_extrude"

        return None

    def _get_instructions(self) -> str:
        return """
# Task: Analyze Patterns and Generate PartBuilder Code

## Your Mission
Analyze the agent results and audio transcription, then write Python code using PartBuilder API.

## Analysis Steps:

### 1. Review Agent Data
- All agents report the same features? → High confidence pattern
- Check agent reasoning fields for explanations
- Look for position markers: "left_side", "right_side", etc.

### 2. Extract Parameters from Agent Results
- Get dimensions from agent_results[*].geometry (diameter, width, height, etc.)
- Get distances from agent_results[*].distance
- Audio transcription is context only, not a measurement source

### 3. Identify Pattern
- Bilateral cuts (left + right) → chord_cut
- Concentric circles → counterbore
- Multiple identical cuts → circular_pattern

### 4. Write Builder Code

Example 1: chord_cut (bilateral cuts)

```python
#!/usr/bin/env python3
\"\"\"
Generated by Claude Code Pattern Analyzer
Pattern: chord_cut
Confidence: 0.95

Analysis:
- All 5 agents report Circle(diameter=90mm) + bilateral cuts
- Audio: "2 linhas a distância de 78mm"
- Pattern: Bilateral chord cuts on cylindrical part
\"\"\"

import sys
import json
from pathlib import Path

# Add recad src directory to path for imports
# Path structure: .../recad/src/docs/outputs/recad/SESSION_ID/claude_analysis.py
# We need: .../recad/src/ (5 parents up)
recad_src = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(recad_src))

from semantic_builder import PartBuilder

# Extracted parameters from agent results
diameter = 90.0  # From agent_results[*].features[*].geometry.diameter
height = 27.0  # From agent_results[*].features[*].distance
radius = diameter / 2  # 45.0mm

# Calculate flat_to_flat from geometry
# For chord_cut: look for cuts or use audio context
flat_to_flat = 78.0  # From audio context or calculated from cut positions

# Create part using PartBuilder
builder = PartBuilder("chapa_circle_90mm")

# Add chord cut extrude
builder.add_chord_cut_extrude(
    radius=radius,
    flat_to_flat=flat_to_flat,
    height=height
)

# Generate semantic JSON
semantic = builder.to_dict()

# Write to file
output_file = Path(__file__).parent / "semantic.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(semantic, f, indent=2, ensure_ascii=False)

print(f"[OK] Semantic JSON generated: {output_file}")
print(f"   Pattern: chord_cut")
print(f"   Parameters: radius={radius}mm, flat_to_flat={flat_to_flat}mm, height={height}mm")
```

Example 2: rectangle extrusion

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

recad_src = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(recad_src))

from semantic_builder import PartBuilder

# Extract from agent_results
width = 126.0   # From agent_results[*].features[*].geometry.width
height = 126.0  # From agent_results[*].features[*].geometry.height
depth = 5.0     # From agent_results[*].features[*].distance

# Create part
builder = PartBuilder("chapa_retangular_126x126x5")
builder.add_rectangle_extrusion(
    width=width,
    height=height,
    extrude_distance=depth
)

semantic = builder.to_dict()

output_file = Path(__file__).parent / "semantic.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(semantic, f, indent=2, ensure_ascii=False)

print(f"[OK] Semantic JSON generated: {output_file}")
```

Example 3: circle extrusion (cylinder)

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

recad_src = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(recad_src))

from semantic_builder import PartBuilder

# Extract from agent_results
diameter = 90.0  # From agent_results[*].features[*].geometry.diameter
height = 27.0    # From agent_results[*].features[*].distance

builder = PartBuilder("cilindro_90x27")
builder.add_circle_extrusion(
    diameter=diameter,
    extrude_distance=height
)

semantic = builder.to_dict()

output_file = Path(__file__).parent / "semantic.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(semantic, f, indent=2, ensure_ascii=False)

print(f"[OK] Semantic JSON generated: {output_file}")
```

Example 4: circular hole (through-hole)

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

recad_src = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(recad_src))

from semantic_builder import PartBuilder

# Extract from agent_results
base_diameter = 50.0  # From base Extrude feature
base_height = 10.0
hole_diameter = 8.0   # From Cut feature with Circle geometry
hole_center = (20, 20)  # From geometry.center

# Create part with base + hole
builder = PartBuilder("plate_with_hole")

# Base extrusion
builder.add_circle_extrusion(
    diameter=base_diameter,
    extrude_distance=base_height
)

# Add through-hole
builder.add_circle_cut(
    diameter=hole_diameter,
    cut_type="through_all",
    center=hole_center
)

semantic = builder.to_dict()

output_file = Path(__file__).parent / "semantic.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(semantic, f, indent=2, ensure_ascii=False)

print(f"[OK] Semantic JSON generated: {output_file}")
print(f"   Pattern: hole (through-hole)")
print(f"   Parameters: diameter={hole_diameter}mm at center={hole_center}")
```

Example 5: blind hole (with depth)

```python
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

recad_src = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(recad_src))

from semantic_builder import PartBuilder

# Extract from agent_results
width = 100.0
height = 100.0
thickness = 20.0
hole_diameter = 12.0
hole_depth = 15.0  # From parameters.distance
hole_center = (30, 30)

# Create part
builder = PartBuilder("plate_with_blind_hole")

# Base rectangle
builder.add_rectangle_extrusion(
    width=width,
    height=height,
    extrude_distance=thickness
)

# Add blind hole
builder.add_circle_cut(
    diameter=hole_diameter,
    cut_type="distance",
    cut_distance=hole_depth,
    center=hole_center
)

semantic = builder.to_dict()

output_file = Path(__file__).parent / "semantic.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(semantic, f, indent=2, ensure_ascii=False)

print(f"[OK] Semantic JSON generated: {output_file}")
print(f"   Pattern: hole (blind)")
print(f"   Parameters: diameter={hole_diameter}mm, depth={hole_depth}mm")
```

Example 6: polar hole pattern (circular arrangement)

```python
#!/usr/bin/env python3
\"\"\"
Generated by Claude Code Pattern Analyzer
Pattern: polar_hole_pattern
Confidence: 0.92

Analysis:
- All 6 agents report 6 identical holes (diameter=8mm) in circular arrangement
- Audio: "6 furos em círculo com raio de 30mm"
- Pattern: Polar hole pattern (bolt circle)
- Geometry: 6 holes evenly spaced at 60° intervals
\"\"\"

import sys
import json
from pathlib import Path

recad_src = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(recad_src))

from semantic_builder import PartBuilder

# Extract from agent_results
base_diameter = 100.0
base_height = 10.0
hole_diameter = 8.0
pattern_radius = 30.0
hole_count = 6

# Create part
builder = PartBuilder("flange_with_bolt_circle")

# Base disc
builder.add_circle_extrusion(
    diameter=base_diameter,
    extrude_distance=base_height
)

# Add holes in polar pattern (6 holes at 60° intervals)
import math
for i in range(hole_count):
    angle_deg = i * (360.0 / hole_count)  # 0°, 60°, 120°, 180°, 240°, 300°
    angle_rad = math.radians(angle_deg)

    x = pattern_radius * math.cos(angle_rad)
    y = pattern_radius * math.sin(angle_rad)

    builder.add_circle_cut(
        diameter=hole_diameter,
        cut_type="through_all",
        center=(round(x, 2), round(y, 2))
    )

semantic = builder.to_dict()

output_file = Path(__file__).parent / "semantic.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(semantic, f, indent=2, ensure_ascii=False)

print(f"[OK] Semantic JSON generated: {output_file}")
print(f"   Pattern: polar_hole_pattern")
print(f"   Parameters: {hole_count} holes, diameter={hole_diameter}mm, radius={pattern_radius}mm")
```

Example 7: counterbore (two-stage hole for flush-mount fastener)

```python
#!/usr/bin/env python3
\"\"\"
Pattern: counterbore
Confidence: 0.93
Analysis: Two-stage hole - 12mm outer (4mm deep) for screw head, 6mm inner (12mm deep) for shaft
\"\"\"
import sys
import json
from pathlib import Path

# Add semantic_builder to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from semantic_builder import PartBuilder

# Build mounting plate with counterbore
builder = PartBuilder("plate_with_counterbore")

# Base plate: 60x60x10mm
builder.add_rectangle_extrusion(
    width=60.0,
    height=60.0,
    extrude_distance=10.0
)

# Counterbore at center: 12mm outer (4mm deep), 6mm inner (12mm total depth)
# Outer cut (for screw head)
builder.add_circle_cut(
    diameter=12.0,
    cut_type="distance",
    cut_distance=4.0,
    center=(0, 0)
)

# Inner cut (for screw shaft) - depth relative to outer cut bottom
builder.add_circle_cut(
    diameter=6.0,
    cut_type="distance",
    cut_distance=8.0,  # 12mm total - 4mm outer = 8mm deeper
    center=(0, 0)
)

# Build and save
semantic_json = builder.to_dict()
output_path = "semantic.json"
with open(output_path, "w") as f:
    json.dump(semantic_json, f, indent=2)

print(f"[OK] Semantic geometry saved to {output_path}")
```

Example 8: countersink (conical two-stage hole for flat-head screw)

```python
#!/usr/bin/env python3
\"\"\"
Pattern: countersink
Confidence: 0.94
Analysis: Conical two-stage hole - 16mm outer (82° angle, 5mm deep) for flat-head screw, 8mm inner (15mm total depth) for shaft
\"\"\"
import sys
import json
from pathlib import Path

# Add semantic_builder to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from semantic_builder import PartBuilder

# Build mounting plate with countersink
builder = PartBuilder("plate_with_countersink")

# Base plate: 80x80x15mm
builder.add_rectangle_extrusion(
    width=80.0,
    height=80.0,
    extrude_distance=15.0
)

# Countersink at center: 16mm outer (82° angle, 5mm deep), 8mm inner (15mm total depth)
# Outer cut (for flat-head screw - conical)
builder.add_countersink_cut(
    outer_diameter=16.0,
    inner_diameter=8.0,
    angle=82.0,
    outer_depth=5.0,
    inner_depth=15.0,
    center=(0, 0)
)

# Build and save
semantic_json = builder.to_dict()
output_path = "semantic.json"
with open(output_path, "w") as f:
    json.dump(semantic_json, f, indent=2)

print(f"[OK] Semantic geometry saved to {output_path}")
print(f"   Pattern: countersink")
print(f"   Parameters: outer_diameter=16mm, inner_diameter=8mm, angle=82°")
```

### Example 9: Slot Detection (Elongated Rectangular Groove)

**Pattern**: Slot
**Confidence**: 0.92
**Method**: `builder.add_slot_cut()`

**Visual Analysis**:
- Rectangular cavity elongated in one direction
- Width 10mm (narrow dimension)
- Length 50mm (long dimension)
- Aspect ratio 5:1 (length/width)
- Depth 5mm cut from top surface
- Horizontal orientation (0°)

**Audio Cues**: "rasgo de 10 por 50 milímetros, profundidade 5"

**Code**:
```python
#!/usr/bin/env python3
\"\"\"
Pattern: slot
Confidence: 0.92
Analysis: Elongated rectangular groove - 10mm x 50mm x 5mm deep for sliding guide
\"\"\"
import sys
import json
from pathlib import Path

# Add semantic_builder to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from semantic_builder import PartBuilder

# Build plate with slot
builder = PartBuilder("plate_with_slot")

# Base plate: 100x80x15mm
builder.add_rectangle_extrusion(
    width=100.0,
    height=80.0,
    extrude_distance=15.0
)

# Slot for sliding guide: 10mm x 50mm x 5mm deep
builder.add_slot_cut(
    width=10.0,          # Narrow dimension (perpendicular to slot)
    length=50.0,         # Long dimension (parallel to slot)
    depth=5.0,           # Cut depth from surface
    center=(0, 0),       # Center position
    orientation=0.0      # 0° = horizontal, 90° = vertical
)

# Build and save
semantic_json = builder.to_dict()
output_path = "semantic.json"
with open(output_path, "w") as f:
    json.dump(semantic_json, f, indent=2)

print(f"[OK] Semantic geometry saved to {output_path}")
print(f"   Pattern: slot")
print(f"   Parameters: width=10mm, length=50mm, depth=5mm, orientation=0°")
```

## Available PartBuilder Methods:

**IMPORTANT**: Use ONLY PartBuilder for everything! Import: `from semantic_builder import PartBuilder`

```python
from semantic_builder import PartBuilder

builder = PartBuilder("part_name")

# 1. Rectangle extrusion
builder.add_rectangle_extrusion(
    width=126.0,
    height=126.0,
    extrude_distance=5.0,
    center=(0, 0)  # Optional, defaults to (0, 0)
)

# 2. Circle extrusion (cylinder)
builder.add_circle_extrusion(
    diameter=90.0,  # Use diameter= OR radius= (not both)
    extrude_distance=27.0,
    center=(0, 0)  # Optional
)

# 3. Chord cut extrusion (cylinder with bilateral cuts)
builder.add_chord_cut_extrude(
    radius=45.0,          # Circle radius (NOT diameter!)
    flat_to_flat=78.0,    # Distance between parallel flats
    height=27.0
)

# 4. Circular hole (cut)
builder.add_circle_cut(
    diameter=8.0,           # Hole diameter
    cut_type="through_all", # Or "distance" for blind holes
    cut_distance=15.0,      # Required if cut_type="distance"
    center=(20, 20)         # Hole center position
)

# 5. Polar hole pattern (circular arrangement)
# See Example 6 for complete implementation with math.cos/sin

# 6. Counterbore (two-stage hole)
# Outer cut (larger diameter, shallow)
builder.add_circle_cut(
    diameter=12.0,
    cut_type="distance",
    cut_distance=4.0,
    center=(0, 0)
)
# Inner cut (smaller diameter, deeper) - depth is relative!
builder.add_circle_cut(
    diameter=6.0,
    cut_type="distance",
    cut_distance=8.0,  # Total 12mm - Outer 4mm = 8mm deeper
    center=(0, 0)
)

# 7. Countersink (conical two-stage hole for flat-head screws)
builder.add_countersink_cut(
    outer_diameter=16.0,    # Outer diameter at top surface
    inner_diameter=8.0,     # Inner hole diameter
    angle=82.0,             # Countersink angle (82°, 90°, 100°, or 120°)
    outer_depth=5.0,        # Depth of conical section
    inner_depth=15.0,       # Total depth (conical + cylindrical)
    center=(0, 0)           # Center position
)

# 8. Slot (elongated rectangular groove for guides/adjustments)
builder.add_slot_cut(
    width=10.0,          # Narrow dimension (perpendicular to slot direction)
    length=50.0,         # Long dimension (parallel to slot direction)
    depth=5.0,           # Cut depth
    center=(0, 0),       # Center position
    orientation=0.0      # Angle from horizontal (0° = horizontal, 90° = vertical)
)

# Generate semantic JSON
semantic = builder.to_dict()
```

## Critical Rules:

0. [CRITICAL] ALWAYS use PartBuilder for everything!
   - ✅ CORRECT: `from semantic_builder import PartBuilder`
   - ❌ WRONG: `from semantic_geometry.builder import ...` (NEVER import from semantic_geometry!)
   - ❌ WRONG: `from semantic_builder import SemanticGeometryBuilder` (Use PartBuilder only!)

1. [REQUIRED] Extract ALL parameters from agent_results (NOT audio!)
   - Get dimensions from: `agent_results[*].features[*].geometry`
   - Get distances from: `agent_results[*].features[*].distance`
   - Audio is context only, NOT measurement source

2. [REQUIRED] Choose the right PartBuilder method based on detected pattern:
   - **rectangle** → `builder.add_rectangle_extrusion(width, height, extrude_distance)`
   - **circle/cylinder** → `builder.add_circle_extrusion(diameter, extrude_distance)`
   - **chord_cut** → `builder.add_chord_cut_extrude(radius, flat_to_flat, height)`
   - **hole (through-hole)** → `builder.add_circle_cut(diameter, cut_type="through_all", center=(x, y))`
   - **hole (blind)** → `builder.add_circle_cut(diameter, cut_type="distance", cut_distance=depth, center=(x, y))`
   - **polar_hole_pattern** → Loop through holes and call `builder.add_circle_cut()` for each with calculated center
   - **counterbore** → Two `add_circle_cut()` calls at same center (INNER FIRST, then outer shallow)
   - **countersink** → `builder.add_countersink_cut(outer_diameter, inner_diameter, angle, outer_depth, inner_depth, center=(x, y))`
   - **slot** → `builder.add_slot_cut(width, length, depth, center=(x, y), orientation=angle)`

3. [REQUIRED] Use correct parameter names:
   - Rectangle: `width`, `height`, `extrude_distance`
   - Circle: `diameter` (or `radius`), `extrude_distance`
   - Chord cut: `radius` (NOT diameter!), `flat_to_flat`, `height`

4. [REQUIRED] Add detailed docstring explaining your analysis
5. [REQUIRED] Use exact values from agent data (don't round or estimate)
6. [REQUIRED] Call `builder.to_dict()` to generate semantic JSON
7. [REQUIRED] Write semantic.json to session directory
8. **Counterbores**: Two sequential `add_circle_cut()` at SAME center
   - **ORDER CRITICAL**: Inner (small) FIRST, then Outer (large) SECOND!
   - Inner cut: Smaller diameter (screw shaft), through_all or total depth
   - Outer cut: Larger diameter (screw head), shallow depth only
   - Example for M8 counterbore (Ø9mm hole, Ø15mm x 9mm counterbore):
     ```python
     # Step 1: Through-hole (Ø9mm) - FIRST!
     builder.add_circle_cut(diameter=9, cut_type="through_all", center=(x, y))
     # Step 2: Counterbore (Ø15mm x 9mm depth) - SECOND!
     builder.add_circle_cut(diameter=15, cut_type="distance", cut_distance=9, center=(x, y))
     ```
   - NEVER reverse this order or the large hole will become through_all!
9. **Countersinks**: Use `add_countersink_cut()` for conical flat-head screw holes
   - Conical profile with standard angles (82°, 90°, 100°, or 120°)
   - outer_diameter: Diameter at top surface (conical section)
   - inner_diameter: Cylindrical hole diameter
   - angle: Countersink angle (typically 82° for flat-head screws)
   - outer_depth: Depth of conical section
   - inner_depth: Total depth (conical + cylindrical sections)
   - Look for keywords: "flat-head", "countersink", "conical", angle measurements
10. **Slots**: Elongated rectangular grooves with aspect ratio > 2:1
   - Width = smaller dimension (perpendicular to slot direction)
   - Length = larger dimension (parallel to slot direction)
   - Orientation = 0° for horizontal, 90° for vertical, any angle supported
   - Keywords: "slot", "rasgo", "ranhura", "canal", "groove", "keyway"
   - Distinguish from rectangular pockets (aspect ratio < 2:1)
   - Use `add_slot_cut(width, length, depth, center, orientation)`
11. [REQUIRED] Make the file executable (add shebang)

## Output File:

Write complete Python code to: claude_analysis.py
"""

    def _print_request_summary(self, request_file: Path, python_file: Path, analyzer_file: Path):
        print(f"\n{'='*70}")
        print(f"  [REQUEST] Claude Code Analysis Request")
        print(f"{'='*70}")
        print(f"  Request: {request_file.name}")
        print(f"  Expected output: {python_file.name}")
        print(f"\n  [TASK] YOUR TASK (Claude Code):")
        print(f"  1. Read {request_file.name}")
        print(f"  2. Read {analyzer_file} (instructions_file)")
        print(f"  3. Analyze agent results + transcription")
        print(f"  4. Identify pattern (chord_cut, counterbore, etc.)")
        print(f"  5. Extract parameters from data")
        print(f"  6. Write Python code using PartBuilder")
        print(f"  7. Save to {python_file.name}")
        print(f"{'='*70}\n")


def get_analyzer() -> ClaudeCodeAnalyzer:
    """Get Claude Code analyzer instance."""
    return ClaudeCodeAnalyzer()

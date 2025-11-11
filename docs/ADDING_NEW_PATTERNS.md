# Adding New Patterns to ReCAD

**Audience:** Claude Code (AI assistant helping developers)
**Purpose:** Step-by-step guide to add new geometric pattern recognition
**Time:** ~20-30 minutes per pattern

---

## Quick Start

When user says: **"Add [pattern_name] pattern to ReCAD"**

1. Read this guide completely
2. Follow the 7-step checklist below
3. Use `chord_cut.py` as reference template
4. Test with TDD (RED → GREEN → REFACTOR)

---

## Prerequisites

Before starting, verify:
- [ ] `patterns/base.py` exists with `GeometricPattern` ABC
- [ ] `patterns/__init__.py` exists with registry system
- [ ] At least one example pattern exists (e.g., `chord_cut.py`)
- [ ] User has described what the pattern looks like (visual + audio cues)

---

## 7-Step Implementation Checklist

### Step 1: Gather Pattern Information

Ask the user (if not provided):

1. **Pattern Name:** What should it be called? (e.g., "counterbore", "chamfer")
2. **Priority:** How complex is it?
   - 150-200: Complex multi-geometry (chord cuts, keyways)
   - 100-149: Medium (counterbores, slots)
   - 50-99: Simple (chamfers, fillets)
3. **Detection Cues:**
   - Audio keywords (Portuguese): e.g., "rebaixo", "escareado"
   - Visual indicators: What do agents see? (circular cuts, angled edges)
   - Feature types: Cut? Extrude? Multiple features?
4. **Parameters Needed:**
   - What measurements? (diameter, depth, angle, etc.)
   - Where do they come from? (audio, visual analysis, both)
5. **Geometry Output:**
   - What primitives? (Circles, Arcs, Lines)
   - What constraints? (Concentric, Tangent, Distance)
   - Does it need base geometry? (like chord_cut needs base Circle)

**Example conversation:**
```
User: "Add counterbore pattern"
Claude: "I need to understand the counterbore pattern better:
1. What audio keywords indicate a counterbore? (e.g., 'rebaixo', 'counterbore')
2. Visually, how do agents detect it? (circular cut within a hole?)
3. What parameters are needed? (hole diameter, counterbore diameter, depth?)
4. Does it modify an existing hole or create new geometry?"
```

---

### Step 2: Create Pattern File

**File:** `patterns/[pattern_name].py`

**Template:**
```python
"""
[Pattern Name] Pattern Detection and Geometry Generation

Description: [Brief description of what this pattern represents]

Detection:
  - Audio: [Keywords in Portuguese/English]
  - Visual: [What agents look for in frames]
  - Features: [Feature types that indicate this pattern]

Parameters:
  - [param1]: [description and unit]
  - [param2]: [description and unit]

Geometry:
  - [List of primitives generated]
  - [List of constraints applied]

Priority: [number] ([Low/Medium/High] complexity)
"""

import re
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base import GeometricPattern, PatternMatch, register_pattern

@register_pattern
class [PatternName]Pattern(GeometricPattern):
    """
    Detects and generates geometry for [pattern description].

    Example: [Brief example of when this pattern is used]
    """

    @property
    def name(self) -> str:
        return "[pattern_name]"  # Lowercase, underscores

    @property
    def priority(self) -> int:
        return [number]  # See priority guidelines in PATTERN_SYSTEM_DESIGN.md

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect [pattern_name] in agent results.

        Detection strategy:
        1. [First detection method]
        2. [Fallback detection method]
        3. [Alternative detection method]

        Returns:
            PatternMatch with extracted parameters, or None if not detected
        """

        # Strategy 1: Check additional_features (if agents support it)
        for result in agent_results:
            for feature in result.get("additional_features", []):
                if feature.get("pattern") == self.name:
                    return PatternMatch(
                        pattern_name=self.name,
                        confidence=feature.get("confidence", 0.9),
                        parameters={
                            # Extract parameters from feature
                        },
                        source="additional_features"
                    )

        # Strategy 2: Detect from Cut/Extrude operations
        for result in agent_results:
            for feature in result.get("features", []):
                # Check if feature matches pattern criteria
                if self._matches_pattern(feature):
                    params = self._extract_parameters(feature, transcription)
                    if params:
                        return PatternMatch(
                            pattern_name=self.name,
                            confidence=feature.get("confidence", 0.85),
                            parameters=params,
                            source="feature_analysis"
                        )

        # Strategy 3: Audio-only detection (if visual ambiguous)
        if transcription:
            params = self._extract_from_audio(transcription)
            if params:
                return PatternMatch(
                    pattern_name=self.name,
                    confidence=0.80,  # Lower confidence for audio-only
                    parameters=params,
                    source="audio_transcription"
                )

        return None

    def _matches_pattern(self, feature: Dict) -> bool:
        """Check if feature matches this pattern's criteria"""
        # Example: Counterbore = Cut with circular geometry inside another cut
        # Implement pattern-specific logic
        pass

    def _extract_parameters(self,
                           feature: Dict,
                           transcription: Optional[str]) -> Optional[Dict]:
        """Extract pattern parameters from feature and audio"""
        # Example for counterbore:
        # - hole_diameter from feature geometry
        # - counterbore_diameter from nested cut
        # - depth from audio ("rebaixo de 3mm")
        pass

    def _extract_from_audio(self, transcription: str) -> Optional[Dict]:
        """Extract parameters from audio transcription only"""
        # Use regex patterns with encoding tolerance
        # Example: r'rebaixo de (\d+)\s*mm'
        pass

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate geometry for [pattern_name].

        Args:
            match: Pattern match with parameters

        Returns:
            Geometry specification (see two formats below)
        """

        # FORMAT 1: Needs base geometry (like chord_cut)
        # Use this if pattern modifies existing Circle/Rectangle
        return {
            "needs_base_circle": True,  # or needs_base_rectangle
            "param1": match.parameters["param1"],
            "param2": match.parameters["param2"],
            # Aggregator will call helper function with base geometry
        }

        # FORMAT 2: Complete geometry (self-contained)
        # Use this if pattern generates all primitives
        return {
            "geometry": [
                {
                    "type": "Circle",  # or Arc, Line, Rectangle
                    "center": {"x": 0, "y": 0},
                    "diameter": {"value": match.parameters["diameter"], "unit": "mm"}
                },
                # ... more geometries
            ],
            "constraints": [
                {
                    "type": "Concentric",  # or Distance, Tangent, etc.
                    "geo1": 0,
                    "geo2": 1
                },
                # ... more constraints
            ]
        }

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove features that conflict with this pattern.

        Args:
            all_features: All detected features
            match: Pattern match information

        Returns:
            Filtered feature list
        """

        # Example 1: Remove specific Cut operations (like chord_cut does)
        return [f for f in all_features if f.get("type") != "Cut"]

        # Example 2: Remove only matching cuts (more selective)
        return [f for f in all_features
                if not (f.get("type") == "Cut" and
                       self._is_pattern_cut(f, match))]

        # Example 3: No filtering needed (pattern adds to existing)
        return all_features

    def _is_pattern_cut(self, feature: Dict, match: PatternMatch) -> bool:
        """Check if a Cut feature belongs to this pattern"""
        # Pattern-specific logic to identify related cuts
        pass
```

---

### Step 3: Register Pattern

**File:** `patterns/__init__.py`

Add import for new pattern:
```python
from .base import GeometricPattern, PatternMatch, register_pattern

_PATTERN_REGISTRY: List[GeometricPattern] = []

def register_pattern(cls):
    _PATTERN_REGISTRY.append(cls())
    return cls

def get_registered_patterns() -> List[GeometricPattern]:
    return sorted(_PATTERN_REGISTRY, key=lambda p: p.priority, reverse=True)

# Import all patterns (triggers @register_pattern decorator)
from .chord_cut import ChordCutPattern
from .[pattern_name] import [PatternName]Pattern  # ← ADD THIS LINE
```

---

### Step 4: Create Helper Function (if needed)

If pattern needs complex geometry calculation (like chord_cut_helper):

**File:** `utils/[pattern_name]_helper.py`

```python
"""
Helper functions for [pattern_name] geometry calculations.

Mathematical formulas and geometry generation logic.
"""

from typing import Dict, Any

def calculate_[pattern_name]_geometry(param1: float,
                                       param2: float,
                                       **kwargs) -> Dict[str, Any]:
    """
    Calculate Arc+Line+Constraints for [pattern_name].

    Args:
        param1: [Description with unit]
        param2: [Description with unit]

    Returns:
        {
            "geometry": [list of primitives],
            "constraints": [list of constraints]
        }

    Raises:
        ValueError: If parameters are invalid

    Example:
        >>> result = calculate_[pattern_name]_geometry(10.0, 5.0)
        >>> len(result["geometry"])
        2
        >>> result["constraints"][0]["type"]
        'Concentric'
    """

    # Input validation
    if param1 <= 0:
        raise ValueError(f"param1 must be positive, got {param1}")

    # Geometry calculation
    geometry = [
        # ... build primitives
    ]

    constraints = [
        # ... build constraints
    ]

    return {
        "geometry": geometry,
        "constraints": constraints
    }
```

**Then update pattern's `generate_geometry()`:**
```python
def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
    from utils.[pattern_name]_helper import calculate_[pattern_name]_geometry

    # If needs base geometry
    if needs_base:
        return {
            "needs_base_circle": True,
            "param1": match.parameters["param1"],
            "helper_function": calculate_[pattern_name]_geometry
        }

    # If self-contained
    return calculate_[pattern_name]_geometry(
        param1=match.parameters["param1"],
        param2=match.parameters["param2"]
    )
```

---

### Step 5: Write Tests (TDD)

**File:** `tests/test_[pattern_name]_pattern.py`

```python
import pytest
from pathlib import Path
import json

from patterns.[pattern_name] import [PatternName]Pattern
from patterns.base import PatternMatch

class Test[PatternName]Detection:
    """Test pattern detection logic"""

    def test_detects_from_additional_features(self):
        """Should detect pattern from additional_features"""
        pattern = [PatternName]Pattern()

        agent_results = [{
            "additional_features": [{
                "pattern": "[pattern_name]",
                "confidence": 0.92,
                "param1": 10.0,
                "param2": 5.0
            }]
        }]

        match = pattern.detect(agent_results)

        assert match is not None
        assert match.pattern_name == "[pattern_name]"
        assert match.confidence == 0.92
        assert match.parameters["param1"] == 10.0

    def test_detects_from_cut_operations(self):
        """Should detect pattern from Cut feature analysis"""
        pattern = [PatternName]Pattern()

        agent_results = [{
            "features": [{
                "type": "Cut",
                "geometry": {"type": "Circle", "diameter": 10},
                # ... pattern-specific indicators
            }]
        }]

        transcription = "[audio keywords that indicate pattern]"
        match = pattern.detect(agent_results, transcription)

        assert match is not None
        assert match.source == "feature_analysis"

    def test_detects_from_audio_only(self):
        """Should detect pattern from audio transcription"""
        pattern = [PatternName]Pattern()

        transcription = "[Pattern keyword] de 10mm com [param2] de 5mm"
        match = pattern.detect([], transcription)

        assert match is not None
        assert match.parameters["param1"] == 10.0
        assert match.confidence < 0.9  # Lower confidence for audio-only

    def test_no_detection_when_absent(self):
        """Should return None when pattern not present"""
        pattern = [PatternName]Pattern()

        agent_results = [{"features": [{"type": "Extrude"}]}]
        match = pattern.detect(agent_results)

        assert match is None

class Test[PatternName]Geometry:
    """Test geometry generation"""

    def test_generates_correct_geometry(self):
        """Should generate valid geometry from parameters"""
        pattern = [PatternName]Pattern()

        match = PatternMatch(
            pattern_name="[pattern_name]",
            confidence=0.9,
            parameters={"param1": 10.0, "param2": 5.0},
            source="test"
        )

        result = pattern.generate_geometry(match)

        # Verify structure
        if "needs_base_circle" in result:
            assert result["param1"] == 10.0
        else:
            assert "geometry" in result
            assert "constraints" in result
            assert len(result["geometry"]) > 0

    def test_geometry_validation(self):
        """Should validate parameter constraints"""
        pattern = [PatternName]Pattern()

        # Invalid parameters (e.g., param1 > param2 when shouldn't be)
        match = PatternMatch(
            pattern_name="[pattern_name]",
            confidence=0.9,
            parameters={"param1": 5.0, "param2": 10.0},  # Invalid order
            source="test"
        )

        with pytest.raises(ValueError):
            pattern.generate_geometry(match)

class Test[PatternName]Filtering:
    """Test feature filtering"""

    def test_filters_conflicting_features(self):
        """Should remove features that conflict with pattern"""
        pattern = [PatternName]Pattern()

        all_features = [
            {"type": "Extrude", "id": "base"},
            {"type": "Cut", "id": "cut1"},  # Should be filtered
            {"type": "Cut", "id": "cut2"},  # Should be filtered
        ]

        match = PatternMatch(
            pattern_name="[pattern_name]",
            confidence=0.9,
            parameters={},
            source="test"
        )

        filtered = pattern.filter_features(all_features, match)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "base"

# Integration test (optional but recommended)
class Test[PatternName]Integration:
    """Test full pipeline integration"""

    @pytest.mark.integration
    def test_full_pipeline_with_real_video(self):
        """Test pattern detection with real video data"""
        # This test requires actual agent_results.json from video processing
        # Skip if file doesn't exist
        agent_results_path = Path("test_data/[pattern_name]_example.json")

        if not agent_results_path.exists():
            pytest.skip("Test data not available")

        with open(agent_results_path) as f:
            agent_results = json.load(f)

        pattern = [PatternName]Pattern()
        match = pattern.detect(agent_results)

        assert match is not None
        # Verify expected parameters from known test video
```

**Run tests:**
```bash
pytest tests/test_[pattern_name]_pattern.py -v
```

---

### Step 6: Integration Test

Test the complete flow with ReCAD runner:

1. **Prepare test video** (if available):
   - Video showing the pattern
   - Audio describing the pattern in Portuguese

2. **Run ReCAD:**
```bash
cd src
python recad_runner.py "path/to/test/video.mp4"
```

3. **Verify output:**
   - Check console: `[OK] Pattern detected: [pattern_name]`
   - Check `semantic.json`: Has correct geometry
   - Export to FreeCAD: `freecadcmd.exe` (validate volume/geometry)

4. **If issues:**
   - Check pattern priority (might be overridden by higher priority)
   - Debug `detect()` method (add print statements)
   - Verify regex patterns match actual transcription

---

### Step 7: Document and Commit

1. **Update pattern list in docs:**

Edit `docs/PATTERN_SYSTEM_DESIGN.md`:
```markdown
### Pattern Types Expected
- Chord cuts (implemented) - Priority: 100
- [Pattern name] (implemented) - Priority: [number]  ← ADD THIS
- Counterbores and countersinks
- Chamfers and fillets
...
```

2. **Add example to README:**

Edit `recad/README.md`:
```markdown
### Supported Patterns

- **Chord Cuts:** Bilateral flattening on cylinders
  - Audio: "corte de corda", "flat to flat"
  - Priority: 100

- **[Pattern Name]:** [Brief description]  ← ADD THIS
  - Audio: "[keywords]"
  - Priority: [number]
```

3. **Commit changes:**
```bash
git add patterns/[pattern_name].py
git add tests/test_[pattern_name]_pattern.py
git add utils/[pattern_name]_helper.py  # if created
git add patterns/__init__.py
git add docs/PATTERN_SYSTEM_DESIGN.md
git add recad/README.md

git commit -m "feat: add [pattern_name] pattern detection

- Implements [PatternName]Pattern with priority [number]
- Detects from [detection sources]
- Generates [geometry description]
- All tests passing ([X]/[X])
"
```

---

## Common Patterns Reference

### Pattern Detection Strategies

**1. Audio Keyword Detection:**
```python
# Encoding-tolerant regex
match = re.search(r'[keyword].{0,20}(\d+)\s*mm', transcription)
# Use . to match any character (handles â, ã, etc.)
```

**2. Cut Operation Analysis:**
```python
if (feature.get("type") == "Cut" and
    feature.get("geometry", {}).get("type") == "Circle"):
    # This is a circular cut - could be counterbore/hole
```

**3. Position Indicators:**
```python
position = feature.get("position", "")
if "concentric" in position or "center" in position:
    # Feature is centered - relevant for many patterns
```

### Geometry Generation Patterns

**1. Concentric Circles (counterbore, countersink):**
```python
{
    "geometry": [
        {"type": "Circle", "diameter": outer_dia, "center": (0, 0)},
        {"type": "Circle", "diameter": inner_dia, "center": (0, 0)}
    ],
    "constraints": [
        {"type": "Concentric", "geo1": 0, "geo2": 1}
    ]
}
```

**2. Angled Lines (chamfer):**
```python
{
    "geometry": [
        {"type": "Line", "start": (x1, y1), "end": (x2, y2), "angle": 45}
    ],
    "constraints": [
        {"type": "Angle", "geo1": 0, "value": 45}
    ]
}
```

**3. Arc + Line (fillet):**
```python
{
    "geometry": [
        {"type": "Arc", "radius": fillet_radius, "start_angle": 0, "end_angle": 90},
        {"type": "Line", ...}
    ],
    "constraints": [
        {"type": "Tangent", "geo1": 0, "geo2": 1}
    ]
}
```

---

## Troubleshooting

### Pattern Not Detected

**Check:**
1. Pattern priority too low? (another pattern matching first)
2. Regex not matching transcription? (encoding issues)
3. Feature type mismatch? (looking for Cut but agents report Extrude)
4. Print debug info in `detect()` method

### Wrong Geometry Generated

**Check:**
1. Parameter extraction correct? (print `match.parameters`)
2. Helper function called with right values?
3. Base geometry available? (if `needs_base_circle: True`)
4. Coordinate system correct? (origin, orientation)

### Tests Failing

**Check:**
1. Mock data structure matches actual agent output?
2. Transcription encoding in test? (use raw strings)
3. Import paths correct? (`from patterns.[name]` works?)
4. pytest discovering tests? (`test_` prefix, `Test` class prefix)

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ Adding New Pattern - Quick Checklist                   │
├─────────────────────────────────────────────────────────┤
│ □ Create patterns/[name].py with @register_pattern     │
│ □ Implement 3 methods: detect, generate, filter        │
│ □ Add import to patterns/__init__.py                   │
│ □ Create helper in utils/ (if needed)                  │
│ □ Write tests/test_[name]_pattern.py                   │
│ □ Run: pytest tests/test_[name]_pattern.py -v          │
│ □ Integration test with real video                     │
│ □ Update docs + commit                                 │
│                                                         │
│ Priority Guide:                                         │
│   150-200 = Complex (chord cuts, keyways)              │
│   100-149 = Medium (counterbores, slots)               │
│    50-99  = Simple (chamfers, fillets)                 │
│                                                         │
│ Time estimate: 20-30 minutes with Claude Code          │
└─────────────────────────────────────────────────────────┘
```

---

## Example: Complete Counterbore Pattern

See `patterns/chord_cut.py` for full working example.

**Key differences for counterbore:**
- Detects concentric circular cuts (not bilateral flats)
- Audio: "rebaixo", "counterbore", "escareado"
- Geometry: 2 concentric circles (outer + inner)
- Constraint: Concentric
- No base geometry needed (self-contained)

---

**Last updated:** 2025-11-06
**Maintainer:** Claude Code
**Questions?** Check `docs/PATTERN_SYSTEM_DESIGN.md` for architecture details

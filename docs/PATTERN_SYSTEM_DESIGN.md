# ReCAD Pattern System - Design Document

**Date:** 2025-11-06
**Status:** Approved Design
**Purpose:** Scalable architecture for detecting and converting geometric patterns in ReCAD

---

## Problem Statement

The ReCAD aggregator was accumulating hardcoded logic for each geometric pattern (chord cuts, counterbores, chamfers, etc.), leading to:
- Increasing code complexity in `recad_runner.py`
- Difficulty maintaining pattern-specific logic
- Risk of AI getting lost in growing conditional branches
- Hard to add new patterns without touching core aggregator

**Current state:** Chord cut logic hardcoded in aggregator with if/elif chains.

**Desired state:** Plugin-based registry where adding a pattern = creating 1 new file.

---

## Design Decisions

### Who Adds Patterns?
**Decision:** Developer (using Claude Code)
**Rationale:** Since patterns are added via Claude Code, we can use Python directly instead of complex DSL.

### Pattern Types Expected
- Chord cuts (implemented)
- Counterbores and countersinks
- Chamfers and fillets
- Slots and keyways
- Circular patterns

### Architecture Choice
**Selected:** Plugin Pattern Registry
**Alternatives considered:**
- JSON + Python Hybrid (rejected: two places to maintain)
- Declarative YAML DSL (rejected: unnecessary complexity for developer-only use)

**Why Plugin Registry:**
- Type-safe Python code
- Easy debugging with IDE support
- Zero changes to aggregator when adding patterns
- Natural fit for Claude Code workflow

---

## Architecture Overview

### Directory Structure
```
recad/src/
├── patterns/
│   ├── __init__.py          # Pattern registry + get_registered_patterns()
│   ├── base.py              # GeometricPattern ABC + PatternMatch dataclass
│   ├── claude_analyzer.py   # Claude LLM pattern analyzer (Phase 3.5)
│   ├── chord_cut.py         # ChordCutPattern implementation
│   ├── counterbore.py       # Future: CounterborePattern
│   ├── chamfer.py           # Future: ChamferPattern
│   └── ...
├── recad_runner.py      # Uses registry (pattern-agnostic)
└── utils/
    └── chord_cut_helper.py  # Keep existing helper functions
```

---

## Claude LLM Integration (Phase 3.5)

**Added:** 2025-11-06

### Overview

Three-layer hybrid pattern detection system providing intelligent analysis with deterministic fallback.

**Workflow:**
1. Aggregator calls `_claude_pattern_recognition(agent_results, transcription)`
2. Claude analyzes results against `get_pattern_catalog()`
3. Returns: `{pattern_detected, confidence, reasoning, parameters, fallback_to_python}`
4. If confidence >= 0.7 and no fallback → use Claude result
5. Else → fallback to Python registry detection

### Why Claude?

**Benefits:**
- Understands context (visual + audio + patterns)
- Tolerant to agent reporting variations
- Extracts parameters from natural language
- Provides reasoning (debuggable)
- Temperature=0.0 for ~99% determinism

**Example:**
```python
# Claude analyzes: 5 agents reporting Circle + left_side/right_side Cuts
# Audio: "2 linhas a distância de 78mm"
# Output:
{
  "pattern_detected": "chord_cut",
  "confidence": 0.95,
  "reasoning": "All 5 agents report Circle + left_side/right_side Cuts. Audio mentions '2 linhas a distância de 78mm'. Clear bilateral chord cut pattern.",
  "parameters": {
    "flat_to_flat": 78.0,
    "base_diameter": 90.0,
    "base_radius": 45.0
  },
  "fallback_to_python": false
}
```

### Why Python Fallback?

**Benefits:**
- 100% deterministic (same inputs → same outputs)
- No API dependency (offline support)
- Fast (<1ms vs 500-2000ms for Claude)
- Battle-tested regex and rule-based logic

**When Fallback Occurs:**
- No API key configured
- API errors or timeouts
- Claude confidence < 0.7
- Claude requests fallback explicitly

### Implementation Details

**Pattern Catalog Export:**
```python
# patterns/__init__.py
def get_pattern_catalog() -> List[Dict[str, Any]]:
    """Export all patterns for Claude analysis"""
    patterns = get_registered_patterns()
    return [
        {
            "name": p.name,
            "priority": p.priority,
            "description": p.description,  # Human-readable explanation
            "indicators": p.detection_indicators  # Visual/audio/feature clues
        }
        for p in patterns
    ]
```

**Claude Analyzer:**
```python
# patterns/claude_analyzer.py
class ClaudePatternAnalyzer:
    def analyze(self, agent_results, transcription, pattern_catalog):
        # Build structured prompt with pattern catalog
        prompt = self._build_prompt(agent_results, transcription, pattern_catalog)

        # Call Claude API (temperature=0.0 for determinism)
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        return json.loads(response.content[0].text)
```

**Integration in Aggregator:**
```python
# recad_runner.py - Phase 3.5
def _claude_pattern_recognition(self, agent_results, transcription):
    from patterns import get_pattern_catalog
    from patterns.claude_analyzer import ClaudePatternAnalyzer

    analyzer = ClaudePatternAnalyzer()
    catalog = get_pattern_catalog()

    result = analyzer.analyze(agent_results, transcription, catalog)

    # If high confidence, return Claude result
    # Else, return None to trigger Python fallback
    if result and result.get("confidence", 0) >= 0.7:
        return result
    return None
```

### Configuration

**Set API Key:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

If not set, system automatically falls back to Python rules (no errors).

### Adding New Patterns

When adding a new pattern, implement these methods for Claude integration:

```python
@register_pattern
class NewPattern(GeometricPattern):
    @property
    def description(self) -> str:
        """Human-readable description for Claude"""
        return """
        Pattern description explaining:
        - Visual indicators (what agents would report)
        - Audio clues (keywords in transcription)
        - Expected feature structure
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        """Structured indicators for pattern detection"""
        return {
            "visual": ["visual clues agents report"],
            "audio": ["keywords in transcription"],
            "features": ["expected feature types"]
        }
```

Claude automatically sees new patterns in catalog - zero configuration needed!

### Debugging

**Check Claude Analysis:**
```python
from patterns.claude_analyzer import ClaudePatternAnalyzer
analyzer = ClaudePatternAnalyzer()
result = analyzer.analyze(agent_results, transcription, catalog)
print(result['reasoning'])  # See Claude's thought process
```

**Force Python Fallback:**
```bash
ANTHROPIC_API_KEY="" python recad_runner.py ...
```

**See Full Documentation:**
- `docs/CLAUDE_PATTERN_DETECTOR.md` - Comprehensive guide
- `tests/test_claude_analyzer.py` - Integration tests

---

### Key Components

**1. Base Interface (`patterns/base.py`):**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class PatternMatch:
    """Result of pattern detection"""
    pattern_name: str          # "chord_cut"
    confidence: float          # 0.0-1.0
    parameters: Dict[str, Any] # {"flat_to_flat": 78, "radius": 45}
    source: str                # "bilateral_cut_operation", "audio_transcript"

class GeometricPattern(ABC):
    """Base class for all geometric patterns"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique pattern identifier (e.g., 'chord_cut')"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Detection priority (higher = checked first). Range: 0-200"""
        pass

    @abstractmethod
    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect if this pattern is present in agent results.

        Args:
            agent_results: List of agent analysis results
            transcription: Audio transcription text (optional)

        Returns:
            PatternMatch if detected, None otherwise
        """
        pass

    @abstractmethod
    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate Arc+Line+Constraints geometry from detected parameters.

        Args:
            match: Detection result with parameters

        Returns:
            {
                "geometry": [Arc, Line, Arc, Line, ...],
                "constraints": [Coincident, Parallel, ...]
            }

            OR (for patterns needing base geometry):
            {
                "needs_base_circle": True,
                "flat_to_flat": 78.0,
                ...
            }
        """
        pass

    @abstractmethod
    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove features that conflict with this pattern.

        Example: Chord cut removes all Cut operations.

        Args:
            all_features: All detected features from agents
            match: Pattern match information

        Returns:
            Filtered list of features (without conflicts)
        """
        pass
```

**2. Registry System (`patterns/__init__.py`):**
```python
from typing import List
from .base import GeometricPattern

_PATTERN_REGISTRY: List[GeometricPattern] = []

def register_pattern(cls):
    """Decorator to auto-register pattern classes"""
    _PATTERN_REGISTRY.append(cls())
    return cls

def get_registered_patterns() -> List[GeometricPattern]:
    """Get all patterns sorted by priority (highest first)"""
    return sorted(_PATTERN_REGISTRY, key=lambda p: p.priority, reverse=True)

# Import all patterns to trigger registration
from .chord_cut import ChordCutPattern
# from .counterbore import CounterborePattern  # Future
```

**3. Aggregator Integration (`recad_runner.py`):**
```python
from patterns import get_registered_patterns

def phase_3_aggregate(self, agent_results_path):
    # ... existing setup code ...

    # Load transcription for pattern detection
    transcription = self._load_transcription()

    # Detect pattern using registry (auto-sorted by priority)
    detected_pattern = None
    for pattern in get_registered_patterns():
        match = pattern.detect(agent_results, transcription)
        if match:
            detected_pattern = (pattern, match)
            print(f"  [OK] Pattern detected: {match.pattern_name}")
            print(f"       Parameters: {match.parameters}")
            print(f"       Confidence: {match.confidence:.2f}")
            break  # Use first match (highest priority)

    # Extract features from agent results
    all_features = []
    for result in agent_results:
        if "features" in result:
            all_features.extend(result["features"])

    # Filter features if pattern detected
    if detected_pattern:
        pattern_obj, match = detected_pattern
        original_count = len(all_features)
        all_features = pattern_obj.filter_features(all_features, match)
        removed = original_count - len(all_features)
        if removed > 0:
            print(f"  [OK] Filtered {removed} conflicting features")

    # Aggregate features
    aggregated = self._aggregate_multi_features(all_features)

    # Build semantic JSON with pattern geometry
    for i, feature in enumerate(aggregated):
        if detected_pattern and feature.get("type") == "Extrude":
            pattern_obj, match = detected_pattern
            geometry_spec = pattern_obj.generate_geometry(match)

            # Handle patterns that need base geometry
            if geometry_spec.get("needs_base_circle"):
                # Extract radius from base Circle
                base_geom = feature.get("geometry", {})
                if base_geom.get("type") == "Circle":
                    radius = base_geom.get("diameter", 0) / 2

                    # Use existing helper (e.g., chord_cut_helper)
                    from utils.chord_cut_helper import calculate_chord_cut_geometry
                    result = calculate_chord_cut_geometry(
                        radius=radius,
                        flat_to_flat=geometry_spec["flat_to_flat"]
                    )

                    # Replace base Circle with pattern geometry
                    sketch = {
                        "plane": {"type": "work_plane"},
                        "geometry": result["geometry"],
                        "constraints": result["constraints"]
                    }

                    feature_dict = {
                        "id": f"extrude_{i}",
                        "type": "Extrude",
                        "sketch": sketch,
                        "parameters": {
                            "distance": {"value": feature.get("distance", 5), "unit": "mm"},
                            "direction": "normal",
                            "operation": "new_body"
                        }
                    }
                    builder.features.append(feature_dict)
            else:
                # Pattern provides complete geometry directly
                sketch = {
                    "plane": {"type": "work_plane"},
                    "geometry": geometry_spec["geometry"],
                    "constraints": geometry_spec.get("constraints", [])
                }
                # ... build feature_dict ...

    # ... rest of aggregation ...
```

---

## Pattern Priority Guidelines

**Priority Ranges:**
- **150-200:** Complex multi-geometry patterns (chord cuts, keyways)
- **100-149:** Medium complexity (counterbores, slots)
- **50-99:** Simple features (chamfers, fillets)
- **0-49:** Fallback/generic patterns

**Rationale:** More complex patterns should be detected first to prevent simpler patterns from matching incorrectly.

---

## Benefits

### Scalability
- **10 patterns = 10 files, 0 aggregator changes**
- Each pattern is isolated and independent
- Registry automatically manages priority and execution order

### Maintainability
- Bug in chord_cut? Only touch `patterns/chord_cut.py`
- Clear separation of concerns
- Self-documenting code (class name = pattern name)

### Testability
- Each pattern testable in isolation
- Mock `PatternMatch` for geometry tests
- Integration tests validate registry behavior

### AI Collaboration
- Claude Code workflow: "Add counterbore pattern"
- Template-based implementation (copy chord_cut.py structure)
- Type hints guide implementation
- Zero risk of breaking existing patterns

---

## Migration Path

### Phase 1: Extract ChordCutPattern
1. Create `patterns/base.py` with `GeometricPattern` ABC
2. Create `patterns/chord_cut.py` implementing the interface
3. Update `recad_runner.py` to use registry
4. Test with existing chord cut videos
5. Remove hardcoded chord cut logic from aggregator

### Phase 2: Add Documentation
1. Create `ADDING_NEW_PATTERNS.md` guide
2. Document template and examples
3. Add inline comments for Claude Code

### Phase 3: Future Patterns
1. Counterbore (priority: 110)
2. Chamfer (priority: 80)
3. Circular pattern (priority: 120)
4. ... (as needed)

---

## File Locations

- **Design Doc:** `docs/PATTERN_SYSTEM_DESIGN.md` (this file)
- **Developer Guide:** `docs/ADDING_NEW_PATTERNS.md` (for Claude Code)
- **Base Classes:** `src/patterns/base.py`
- **Registry:** `src/patterns/__init__.py`
- **Example:** `src/patterns/chord_cut.py`

---

## Success Metrics

- ✅ Time to add new pattern: < 30 minutes (with Claude Code)
- ✅ Lines of code in aggregator: No increase per pattern
- ✅ Test isolation: Each pattern independently testable
- ✅ Zero regressions: Existing patterns unaffected by new additions

---

## Appendix: Pattern Lifecycle

```
1. Pattern Request
   ↓
2. Create patterns/new_pattern.py
   ↓
3. Implement GeometricPattern interface
   ↓
4. Add @register_pattern decorator
   ↓
5. Import in patterns/__init__.py
   ↓
6. Write tests (test_new_pattern.py)
   ↓
7. Run integration test with real video
   ↓
8. Commit and document
```

**Estimated time per pattern:** 20-30 minutes with Claude Code assistance.

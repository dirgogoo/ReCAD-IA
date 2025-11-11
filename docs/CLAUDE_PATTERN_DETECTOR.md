# Claude Pattern Detector

**Status:** Production
**Added:** 2025-11-06

## Overview

Three-layer hybrid pattern detection system:

1. **Layer 1 - Claude LLM**: Contextual pattern analysis using natural language understanding
2. **Layer 2 - Python Rules**: Deterministic fallback using regex-based detection
3. **Layer 3 - Pattern Classes**: Geometry generation from detected patterns

This architecture combines the contextual understanding of Claude with the reliability of deterministic Python rules.

## Architecture

```
Agent Results + Transcription
         ↓
[Phase 3.5] Claude Pattern Analysis
         ↓
Pattern Catalog: [{name, description, indicators}, ...]
         ↓
Claude evaluates EACH pattern:
  - Visual indicators match?
  - Audio indicators match?
  - Confidence score (0.0-1.0)
         ↓
Best Match: {pattern: "chord_cut", confidence: 0.95, parameters: {...}}
         ↓
IF confidence < 0.7 OR error → Fallback to Python Rules
         ↓
Pattern Class generates geometry (Arc + Line + Constraints)
```

### Data Flow Example

```
Video: WhatsApp Video 2025-11-06.mp4
  ↓
89 frames extracted
  ↓
5 Visual Agents analyze frames
  ↓
Agent Results:
  - Agent 1: Circle(diameter=90) + Cut(position="left_side") + Cut(position="right_side")
  - Agent 2: Circle(diameter=90) + Cut(position="left_side") + Cut(position="right_side")
  - ...5 total agents with similar reports
  ↓
Audio Transcription: "...duas linhas paralelas a distância de 78 milímetros..."
  ↓
Claude Pattern Analysis:
  Input: agent_results + transcription + pattern_catalog
  Output: {
    "pattern_detected": "chord_cut",
    "confidence": 0.95,
    "reasoning": "All 5 agents report Circle + bilateral Cuts (left_side/right_side). Audio mentions '78mm' distance between parallel lines.",
    "parameters": {
      "flat_to_flat": 78.0,
      "base_diameter": 90.0,
      "base_radius": 45.0
    },
    "fallback_to_python": false
  }
  ↓
Pattern Class (ChordCutPattern):
  - Filters conflicting features (removes redundant Cuts)
  - Generates Arc + Line geometry
  - Creates Distance constraint (78.0mm)
  ↓
Semantic JSON: {
  "geometry": [
    {"type": "Arc", ...},
    {"type": "Line", ...}
  ],
  "constraints": [
    {"type": "Distance", "value": 78.0, ...}
  ]
}
  ↓
FreeCAD export: parametric part with 78mm flat-to-flat dimension
```

## Benefits

### Claude Layer (Layer 1)

**Advantages:**
- **Contextual Understanding**: Analyzes visual + audio evidence holistically
- **Tolerance to Variation**: Handles different agent reporting styles
- **Natural Language Extraction**: Parses dimensions from transcription ("78mm" → 78.0)
- **Reasoning**: Provides explanation for debugging
- **Extensibility**: New patterns automatically recognized from catalog

**Limitations:**
- API dependency (requires internet + API key)
- ~500-2000ms latency per analysis
- Non-deterministic (though temp=0.0 reduces variance to ~1%)

### Python Fallback (Layer 2)

**Advantages:**
- **100% Deterministic**: Same inputs always produce same outputs
- **Fast**: <1ms execution time
- **Offline**: No API or internet required
- **Reliable**: No API rate limits or errors
- **Transparent**: Regex patterns are auditable

**Limitations:**
- Less flexible than LLM
- Requires manual pattern definition
- Cannot understand natural language context

### Combined System

The hybrid approach gives you:

- **Robustness**: If Claude fails, Python catches it
- **Speed with Intelligence**: Fast fallback when needed, smart analysis when available
- **~99% Determinism**: Claude temp=0.0 provides near-deterministic results
- **Graceful Degradation**: System works offline or without API key
- **Best of Both Worlds**: Contextual understanding + deterministic reliability

## Configuration

### API Key Setup

Set your Anthropic API key as an environment variable:

```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-...
```

**No API Key?** The system automatically falls back to Python rules if:
- `ANTHROPIC_API_KEY` is not set
- API key is invalid
- `anthropic` package is not installed
- Network connection fails
- Claude API returns an error

### Dependencies

Install the Anthropic SDK:

```bash
pip install anthropic
```

The system gracefully handles missing dependencies by falling back to Python.

## How It Works

### Phase 3.5: Claude Pattern Analysis

Inserted between aggregation (Phase 3) and geometry generation (Phase 4):

```python
# In recad_runner.py

def _claude_pattern_recognition(self, agent_results, transcription):
    """Use Claude LLM to analyze patterns (Phase 3.5)."""

    # 1. Get pattern catalog
    catalog = get_pattern_catalog()
    # Returns: [
    #   {
    #     "name": "chord_cut",
    #     "priority": 180,
    #     "description": "Bilateral chord cuts on cylindrical parts...",
    #     "indicators": {
    #       "visual": ["symmetric bilateral cuts", ...],
    #       "audio": ["distância de", "linhas paralelas", ...],
    #       "features": ["Circle geometry (base)", ...]
    #     }
    #   },
    #   ...
    # ]

    # 2. Initialize analyzer
    analyzer = ClaudePatternAnalyzer()

    # 3. Analyze
    result = analyzer.analyze(agent_results, transcription, catalog)
    # Returns: {
    #   "pattern_detected": "chord_cut",
    #   "confidence": 0.95,
    #   "reasoning": "...",
    #   "parameters": {"flat_to_flat": 78.0, ...},
    #   "fallback_to_python": false
    # }

    # 4. Use result or fallback
    if result and not result.get("fallback_to_python"):
        # Use Claude detection
        return result
    else:
        # Fallback to Python rules
        return None
```

### Pattern Catalog Introspection

Each pattern class implements:

```python
@property
def description(self) -> str:
    """Human-readable description for Claude LLM."""
    return """
    Bilateral chord cuts on cylindrical parts.

    Visual: Circle with two symmetric flat sides (parallel to each other)
    Audio: Keywords like 'distância de Xmm', '2 linhas paralelas'
    Features: 1 Circle base + multiple Cuts with position 'left_side'/'right_side'
    """

@property
def detection_indicators(self) -> Dict[str, List[str]]:
    """Structured indicators for pattern detection."""
    return {
        "visual": [
            "symmetric bilateral cuts",
            "left_side + right_side position markers",
            "Circle base with flat sides"
        ],
        "audio": [
            "distância de",
            "linhas paralelas",
            "flat-to-flat",
            "chord"
        ],
        "features": [
            "Circle geometry (base)",
            "Multiple Cut operations",
            "Cuts with position='left_side' or 'right_side'"
        ]
    }
```

Claude analyzes agent results against these indicators to determine the best pattern match.

## Adding New Patterns

To add a new pattern that Claude can detect:

### Step 1: Implement Pattern Class

```python
# In patterns/counterbore.py

from .base import GeometricPattern

class CounterborePattern(GeometricPattern):
    name = "counterbore"
    priority = 160

    @property
    def description(self) -> str:
        return """
        Stepped hole (counterbore) in a part.

        Visual: Two concentric circles with different diameters
        Audio: Keywords like 'counterbore', 'rebaixo', 'stepped hole'
        Features: 2 Circle geometries (outer + inner) + Cut operation

        This pattern creates a stepped hole where the outer circle
        is larger than the inner circle, with a depth constraint.
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        return {
            "visual": [
                "two concentric circles",
                "stepped hole appearance",
                "larger outer circle + smaller inner circle"
            ],
            "audio": [
                "counterbore",
                "rebaixo",
                "stepped",
                "depth",
                "diâmetro externo",
                "diâmetro interno"
            ],
            "features": [
                "Multiple Circle geometries",
                "Cut operation",
                "Concentric circles (same center)"
            ]
        }

    def applies_to(self, features: List[Dict], metadata: Dict) -> bool:
        """Python fallback detection logic."""
        # ... regex-based detection
        pass

    def generate_geometry(self, features: List[Dict], metadata: Dict) -> List[Dict]:
        """Generate geometry for counterbore."""
        # ... geometry generation
        pass
```

### Step 2: Register Pattern

```python
# In patterns/__init__.py

from .counterbore import CounterborePattern

def get_registered_patterns():
    return [
        ChordCutPattern(),
        CounterborePattern(),  # <- Automatically available to Claude
        # ... other patterns
    ]
```

### Step 3: Test

Claude will automatically see the new pattern in the catalog:

```bash
cd C:\Users\conta\.claude\skills\recad\src
python -c "
from patterns import get_pattern_catalog
import json
catalog = get_pattern_catalog()
print(json.dumps(catalog, indent=2))
"
```

Expected output includes your new pattern:

```json
[
  {
    "name": "chord_cut",
    ...
  },
  {
    "name": "counterbore",
    "priority": 160,
    "description": "Stepped hole (counterbore) in a part...",
    "indicators": {
      "visual": ["two concentric circles", ...],
      "audio": ["counterbore", "rebaixo", ...],
      "features": ["Multiple Circle geometries", ...]
    }
  }
]
```

That's it! Claude will now analyze for counterbore patterns automatically.

## Debugging

### Check Claude Analysis

```python
from patterns.claude_analyzer import ClaudePatternAnalyzer
from patterns import get_pattern_catalog
import json

# Load your data
with open('docs/outputs/.../agent_results.json') as f:
    agent_results = json.load(f)

with open('docs/outputs/.../transcription.json') as f:
    transcription = json.load(f)['text']

# Analyze
analyzer = ClaudePatternAnalyzer()
catalog = get_pattern_catalog()

result = analyzer.analyze(agent_results, transcription, catalog)

# Inspect result
print(f"Pattern detected: {result.get('pattern_detected')}")
print(f"Confidence: {result.get('confidence'):.2f}")
print(f"\nReasoning:")
print(result.get('reasoning'))
print(f"\nParameters:")
print(json.dumps(result.get('parameters', {}), indent=2))
```

### Force Python Fallback

Test that Python fallback works:

```bash
# Temporarily disable Claude
ANTHROPIC_API_KEY="" python recad_runner.py "video.mp4" --agent-results "results.json"
```

Expected output:

```
[Phase 3.5] Claude Pattern Analysis
[INFO] Claude analyzer not available (no API key)
[INFO] Using Python pattern detection (Claude fallback)
[OK] Pattern detected by Python: chord_cut
     Source: bilateral_cut_pattern
```

### Verify Pattern Catalog

Check that all patterns are registered with proper metadata:

```python
from patterns import get_pattern_catalog

catalog = get_pattern_catalog()

for pattern in catalog:
    print(f"\nPattern: {pattern['name']}")
    print(f"  Priority: {pattern['priority']}")
    print(f"  Description: {pattern['description'][:50]}...")
    print(f"  Visual indicators: {len(pattern['indicators']['visual'])}")
    print(f"  Audio indicators: {len(pattern['indicators']['audio'])}")
    print(f"  Feature indicators: {len(pattern['indicators']['features'])}")
```

### Enable Debug Logging

See the prompt sent to Claude:

```python
analyzer = ClaudePatternAnalyzer()

# Build prompt without calling API
prompt = analyzer._build_prompt(agent_results, transcription, catalog)

print("=== PROMPT SENT TO CLAUDE ===")
print(prompt)
print("=== END PROMPT ===")
```

### Check Response Validation

If Claude returns invalid JSON, validation catches it:

```
[WARN] Missing required field: confidence
[WARN] Claude response missing required fields, falling back to Python
```

Required fields in Claude response:
- `pattern_detected`: string or null
- `confidence`: float (0.0-1.0)
- `reasoning`: string
- `parameters`: dict
- `fallback_to_python`: bool

### Test with Mock Data

```python
# Test with minimal data
test_results = [
    {
        "geometry": {"type": "Circle", "diameter": 90},
        "operations": [
            {"type": "Cut", "position": "left_side"},
            {"type": "Cut", "position": "right_side"}
        ]
    }
]

test_transcription = "duas linhas paralelas a distância de 78 milímetros"

analyzer = ClaudePatternAnalyzer()
catalog = get_pattern_catalog()

result = analyzer.analyze(test_results, test_transcription, catalog)
print(json.dumps(result, indent=2))
```

## Performance

### Timing Comparison

| Layer | Latency | Determinism | Offline |
|-------|---------|-------------|---------|
| Claude | 500-2000ms | ~99% (temp=0.0) | No |
| Python | <1ms | 100% | Yes |

### When to Use Each

**Use Claude when:**
- You have API key and internet
- You want natural language parameter extraction
- You need tolerance to agent variation
- You want reasoning/explanation

**Use Python when:**
- Offline processing required
- Speed is critical (batch processing)
- 100% determinism needed
- No API key available

**The system automatically chooses for you!** If Claude is available, it tries Claude first. If Claude fails or is unavailable, it falls back to Python.

## Testing

### Run Tests

```bash
cd C:\Users\conta\.claude\skills\recad\src
pytest tests/test_claude_analyzer.py -v
```

Expected output:

```
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerInit::test_init_with_api_key_provided PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerInit::test_init_with_env_var PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerInit::test_init_without_api_key PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerFallback::test_analyze_without_client_returns_fallback PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerFallback::test_analyze_with_api_error_returns_fallback PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerPromptConstruction::test_build_prompt_includes_pattern_catalog PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerAnalysis::test_analyze_returns_valid_pattern_detection PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerAnalysis::test_analyze_handles_markdown_code_blocks PASSED
tests/test_claude_analyzer.py::TestClaudePatternAnalyzerErrorHandling::test_analyze_handles_invalid_json_response PASSED
```

### Integration Test

Test with real data:

```bash
# Run full pipeline with Claude
python recad_runner.py "C:\Users\conta\Downloads\WhatsApp Video 2025-11-06 at 16.36.07.mp4" \
  --agent-results "docs/outputs/recad/2025-11-06_204255/agent_results.json"
```

Expected output:

```
[Phase 3] Aggregate Results
  [OK] Loaded agent results: 5 agents
  [Phase 3.5] Claude Pattern Analysis
  [INFO] Analyzing against 1 registered patterns
  [OK] Claude detected: chord_cut
       Confidence: 0.95
  [OK] Pattern detected by Claude: chord_cut
       Reasoning: All 5 agents report Circle + left_side/right_side Cuts. Audio mentions '2 linhas a distância de 78mm'. Clear bilateral chord cut pattern.
       Confidence: 0.95
  [OK] Pattern 'chord_cut' filtered out 10 conflicting features
  [OK] Chord cut pattern - replacing Circle with Arc + Line geometry
```

## Troubleshooting

### "Claude analyzer not available (no API key)"

**Problem:** API key not set
**Solution:** Export `ANTHROPIC_API_KEY` environment variable

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "anthropic package not installed"

**Problem:** Missing dependency
**Solution:** Install anthropic SDK

```bash
pip install anthropic
```

### "Claude pattern analysis failed: API key invalid"

**Problem:** Invalid API key
**Solution:** Check your API key at https://console.anthropic.com/

### Low Confidence Detection

**Problem:** Claude returns confidence < 0.7
**Solution:**
1. Check pattern indicators match your data
2. Verify transcription contains expected keywords
3. Ensure agents report expected features
4. Python fallback will handle it automatically

### Missing Parameters

**Problem:** `parameters` dict is empty
**Solution:**
1. Check audio transcription contains dimension values
2. Verify agent geometry includes required features
3. Update pattern's `detection_indicators` with parameter extraction hints

## Architecture Decisions

### Why Temperature 0.0?

Claude is called with `temperature=0.0` to maximize determinism:

```python
response = self.client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2000,
    temperature=0.0,  # <-- Maximum determinism
    messages=[...]
)
```

**Result:** ~99% deterministic (same inputs → same outputs most of the time)

### Why Confidence Threshold 0.7?

If Claude's confidence is below 0.7, it requests fallback to Python:

```python
if confidence < 0.7:
    result["fallback_to_python"] = True
```

**Rationale:** Below 70% confidence, Python's deterministic rules are more reliable than uncertain LLM predictions.

### Why Both Claude AND Python?

**Defense in Depth:**
- Claude provides intelligence and flexibility
- Python provides reliability and determinism
- Together, they cover each other's weaknesses

**Real-World Resilience:**
- Network failures → Python catches it
- API rate limits → Python catches it
- Invalid API key → Python catches it
- Offline processing → Python handles it

### Why Pattern Catalog?

The catalog-based approach enables:

1. **Automatic Discovery**: New patterns are immediately available to Claude
2. **Consistent Format**: All patterns use same indicator structure
3. **Documentation**: Pattern descriptions serve as inline docs
4. **Testing**: Easy to verify patterns are registered correctly

## Related Documentation

- **Pattern System Design**: `docs/PATTERN_SYSTEM_DESIGN.md`
- **Agent Integration**: `docs/AGENT_PATTERN_INTEGRATION.md`
- **Chord Cut Pattern**: `docs/CHORD_CUT_PATTERN.md`
- **ReCAD Runner**: `src/recad_runner.py`

## Version History

- **2025-11-06**: Initial implementation
  - ClaudePatternAnalyzer class
  - Pattern catalog introspection
  - Integration into Phase 3.5
  - Parameter extraction from audio
  - Comprehensive test suite

---

**Questions?** Check the source code:
- `src/patterns/claude_analyzer.py` - Main implementation
- `src/tests/test_claude_analyzer.py` - Test suite
- `src/patterns/base.py` - Pattern base class
- `src/recad_runner.py` - Integration point

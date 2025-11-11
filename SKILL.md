---
name: recad
description: Video-to-CAD reconstruction skill. Analyzes video of physical parts, extracts geometry, and generates parametric CAD models. Consolidated workflow using recad_runner.py for optimized execution.
---

# ReCAD - Video to CAD Reconstruction

Transforms videos of physical parts into parametric CAD models (.FCStd).

## When to Invoke

**Use this skill when:**
- User provides video of a physical part for CAD reconstruction
- Keywords: "reconstrução", "reconstruction", "video to CAD", "geometria", "geometry"
- User wants to convert physical measurements to 3D model
- User asks to analyze part dimensions from video

**Do NOT use for:**
- Static images (use different workflow)
- Text/document analysis
- General video analysis without CAD intent

## How It Works

**Hybrid Architecture**:
```
Python (Deterministic)          Claude (Multimodal)
- Extract frames (FFmpeg)      → Analyze frames (Read tool)
- Extract audio (FFmpeg)         Identify geometry
- Transcribe (Whisper)           Extract measurements
- Aggregate (PartBuilder)        Correlate audio+visual
- Report
                                FreeCAD (CAD Operations)
                                → Export .FCStd
                                → Validate volume
```

**Pipeline** (6 phases):
0. **Setup**: Create session directories, metadata
1. **Extract**: Frames (@1.5 FPS) + Audio transcription (Whisper)
2. **Analyze**: 5 parallel Claude agents analyze frames for geometry
3. **Aggregate**: Build semantic JSON using **PartBuilder** (correct class name!)
4. **Export**: Convert to FreeCAD parametric model (.FCStd)
5. **Validate**: Check volume, dimensions, topology
6. **Report**: Generate summary with results

---

## Workflow Execution (UPDATED - Consolidated Runner)

### Quick Start

```bash
cd C:/Users/conta/.claude/skills/recad/src
python recad_runner.py "C:/path/to/video.mp4" --fps 1.5
```

**That's it!** Runner handles Phases 0, 1 and prepares handoff for Claude.

---

### Detailed Workflow

When invoked, follow these steps:

#### Phase 0-1: Python Runner (Automated)

```bash
cd C:/Users/conta/.claude/skills/recad/src
python recad_runner.py "C:/path/to/video.mp4" --fps 1.5
```

**What it does**:
- ✅ Creates session directory (`docs/outputs/recad/2025-11-06_HHMMSS/`)
- ✅ Extracts frames @ 1.5 FPS using FFmpeg
- ✅ Extracts audio and transcribes with Whisper (uses API key from config.py)
- ✅ Saves `claude_handoff.json` with batched frame assignments
- ⏸️ **PAUSES** awaiting Claude analysis

**Output**:
```
[Phase 0] Setup ✅
  Session: 2025-11-06_153425

[Phase 1] Extract ✅
  Frames: 56 @ 1.5 FPS
  Audio: audio.wav
  Transcription: "Chapa retangular 126x126x5mm..."

[Phase 2] HANDOFF TO CLAUDE
  [ACTION REQUIRED] Claude should now:
    1. Read: claude_handoff.json
    2. Dispatch 5 Task agents in parallel
    3. Each agent analyzes ~11 frames
    4. Save results to: agent_results.json
```

---

#### Phase 2: Claude Parallel Agent Analysis

**IMPORTANT**: This phase MUST use Claude Task tool!

Read the handoff file to get frame assignments:
```python
import json
with open("docs/outputs/recad/2025-11-06_HHMMSS/claude_handoff.json") as f:
    handoff = json.load(f)

frame_paths = handoff["frame_paths"]
transcription = handoff["transcription"]
num_agents = handoff["num_agents"]  # 5
batch_size = handoff["batch_size"]  # ~11 frames each
```

**Dispatch 5 Task agents in parallel**:

```python
# Agent 0: frames 0-10
Task(
    description="Analyze batch 0 frames",
    prompt=f"""
Analyze frames 0-10 for geometric reconstruction.

Frames: {frame_paths[0:11]}
Audio transcription: "{transcription['text']}"

Your task:
1. Read each frame (use Read tool) - frames show part with measuring tools
2. Identify base shape: Rectangle, Circle, or Polygon
3. Extract dimensions from visual measurements (calipers showing mm)
4. Correlate visual measurements with audio mentions
5. Return JSON with detected geometry

Return format:
{{
  "batch_id": "batch_0",
  "frames_analyzed": 11,
  "geometry": {{
    "type": "Rectangle",  // or "Circle"
    "dimensions": {{
      "width": 126,  // mm (from caliper reading)
      "height": 126,
      "thickness": 5
    }},
    "confidence": 0.95
  }},
  "measurements_source": "caliper visual + audio correlation"
}}
    """,
    subagent_type="general-purpose"
)

# Repeat for agents 1-4 with their respective frame batches
```

**Each agent analyzes** its batch of frames:
- Read frames using Read tool (multimodal!)
- Identify geometry (circle, rectangle, polygon)
- Extract dimensions from calipers/rulers
- Correlate with audio timestamps

**Aggregate agent results**:
```python
import json

# Collect all agent results
agent_results = [agent0_result, agent1_result, agent2_result, agent3_result, agent4_result]

# Save for Phase 3
with open("docs/outputs/recad/2025-11-06_HHMMSS/agent_results.json", "w") as f:
    json.dump(agent_results, f, indent=2)
```

---

#### Phase 3-6: Resume Python Runner

**IMPORTANT: Session Auto-Detection**
The runner now automatically detects and reuses the existing session from the `--agent-results` path!

```bash
cd C:/Users/conta/.claude/skills/recad/src
python recad_runner.py "C:/path/to/video.mp4" \
  --agent-results "docs/outputs/recad/2025-11-06_HHMMSS/agent_results.json"
```

**What happens:**
- ✅ Auto-detects session ID from agent_results path (2025-11-06_HHMMSS)
- ✅ Reuses existing session directory (skips Phase 0-1)
- ✅ All outputs saved to same session folder
- ✅ No duplicate sessions created!

**What it does**:
- ✅ Reads agent results
- ✅ Aggregates geometry detections (most common type)
- ✅ Builds semantic JSON using **PartBuilder** (from semantic-geometry)
- ✅ Validates "parameters" wrapper is present (prevents dimension errors!)
- ✅ Saves `semantic.json`
- ✅ Prepares `freecad_handoff.json`
- ⏸️ **PAUSES** awaiting FreeCAD export

**Output**:
```
[Phase 3] Aggregate ✅
  Geometry: Rectangle
  Dimensions: 126x126x5 mm
  Confidence: 0.91
  [OK] semantic.json saved
  [OK] Parameters wrapper present!

[Phase 4-5] HANDOFF TO FREECAD
  [ACTION REQUIRED] Execute freecadcmd with:
    Input: semantic.json
    Output: chapa_retangular_126x126x5.FCStd
```

---

#### Phase 4-5: FreeCAD Export + Validation

Execute via freecadcmd (FreeCAD Python environment):

```bash
"/c/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecadcmd.exe" -c "
import sys
sys.path.insert(0, 'C:/Users/conta/semantic-geometry')

from pathlib import Path
from semantic_geometry.freecad_export import convert_to_freecad
import json

# Load semantic JSON
session_dir = Path('docs/outputs/recad/2025-11-06_HHMMSS')
semantic_path = session_dir / 'semantic.json'
cad_path = session_dir / 'chapa_retangular_126x126x5.FCStd'

with open(semantic_path) as f:
    part_json = json.load(f)

print('Converting semantic JSON to FreeCAD...')

# Convert to FreeCAD
success = convert_to_freecad(
    part_json=part_json,
    output_path=str(cad_path)
)

if success:
    print(f'[OK] CAD file created: {cad_path.name}')
else:
    print('[ERROR] CAD conversion failed')
"
```

**Validate volume**:
```bash
"/c/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecadcmd.exe" -c "
import FreeCAD

doc = FreeCAD.openDocument('docs/outputs/recad/2025-11-06_HHMMSS/chapa_retangular_126x126x5.FCStd')
body = doc.getObject('Body')

if body and hasattr(body, 'Shape'):
    volume_mm3 = body.Shape.Volume
    print(f'Volume: {volume_mm3:.2f} cubic mm')

    # Expected: 126 × 126 × 5 = 79,380 mm³
    expected = 126 * 126 * 5
    print(f'Expected: {expected:.2f} cubic mm')

    if abs(volume_mm3 - expected) < 100:
        print('[OK] Volume is CORRECT!')
    else:
        print(f'[ERROR] Volume mismatch: {abs(volume_mm3 - expected):.2f} mm³ difference')

FreeCAD.closeDocument('chapa_retangular_126x126x5')
"
```

---

## Key Files

```
recad/
├── SKILL.md                    # This file
├── README.md                   # User guide
├── src/
│   ├── recad_runner.py    # ⭐ CONSOLIDATED RUNNER (Phases 0,1,3,6)
│   ├── config.py               # API keys, settings
│   ├── extract_frames.py       # FFmpeg frame extraction
│   ├── extract_audio.py        # Audio + Whisper transcription
│   ├── audio_utils.py          # Convenience wrappers
│   └── __init__.py
└── examples/
    ├── simple_cylinder.json    # Example output
    ├── hollow_cylinder.json    # Multi-feature example
    └── l_bracket.json          # Complex geometry
```

---

## Configuration

**Default settings** (config.py):
```python
# OpenAI API Key for Whisper
OPENAI_API_KEY = "sk-proj-..."

# FreeCAD Installation
FREECAD_PATH = "C:/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecadcmd.exe"

# Extraction settings
DEFAULT_FPS = 1.5  # Frames per second
DEFAULT_NUM_AGENTS = 5  # Parallel agents
DEFAULT_UNITS = "mm"  # Measurement units

# Output directories
OUTPUT_BASE_DIR = "docs/outputs/recad"
```

---

## CRITICAL: Use PartBuilder, NOT SemanticGeometryBuilder!

**WRONG** (outdated docs):
```python
from semantic_geometry.semantic_builder import SemanticGeometryBuilder  # ❌ Module doesn't exist!
builder = SemanticGeometryBuilder("Part Name")  # ❌ Class doesn't exist!
```

**CORRECT** (actual implementation):
```python
from semantic_geometry.builder import PartBuilder  # ✅ Correct module
from semantic_geometry.primitives import Rectangle, Circle  # ✅ Needed for geometry

builder = PartBuilder(name="Part Name")  # ✅ Correct class

# Add extrude with Rectangle primitive
rect = Rectangle(center=(0, 0), width=126, height=126)
builder.add_extrude(
    geometry=[rect],  # ✅ Pass primitive directly (no .to_dict()!)
    distance=5,
    operation="new_body"
)

# Get JSON
part_json = builder.to_dict()  # ✅ Correct method
```

**Why This Matters**:
- ❌ Wrong imports cause `ModuleNotFoundError`
- ❌ Wrong class causes `ImportError: cannot import name`
- ❌ `.to_dict()` on primitives causes `AttributeError`
- ✅ Correct usage in `recad_runner.py:phase_3_aggregate()`

---

## Error Handling

### Common Issues

**1. Type Mismatch (str vs Path)**
- **Cause**: Functions received string path but expected Path object
- **Fix**: All functions now accept `Union[str, Path]` and normalize immediately
- **Prevention**: Use recad_runner.py (handles normalization)

**2. API Key Not Found**
- **Cause**: OPENAI_API_KEY not in environment
- **Fix**: Set in `config.py` (already done!)
- **Prevention**: Runner uses config.py automatically

**3. Wrong Volume (2x expected)**
- **Cause**: Missing "parameters" wrapper in semantic.json
- **Fix**: Use PartBuilder (guarantees correct format)
- **Prevention**: Runner uses PartBuilder, validates wrapper presence

**4. FreeCAD Import Error**
- **Cause**: Running in standard Python (not FreeCAD environment)
- **Fix**: Use freecadcmd.exe for CAD operations
- **Prevention**: Runner clearly marks FreeCAD handoff points

**5. Unicode Encoding Errors**
- **Cause**: Special characters (³, ×) in bash inline commands
- **Fix**: Use ASCII only, or create separate .py file
- **Prevention**: Runner uses pure Python (no inline bash strings)

---

## Success Criteria

- ✅ Semantic JSON validates against spec
- ✅ "parameters" wrapper present in all features
- ✅ Volume matches expected (±1% tolerance)
- ✅ CAD file opens in FreeCAD
- ✅ Dimensions are parametric (editable)

---

## Output Directory Structure

```
docs/outputs/recad/
└── 2025-11-06_153425/
    ├── metadata.json          # Session info
    ├── transcription.json     # Whisper output
    ├── claude_handoff.json    # Frame batches for agents
    ├── agent_results.json     # Aggregated detections
    ├── semantic.json          # Semantic geometry (PartBuilder!)
    ├── freecad_handoff.json   # CAD export instructions
    ├── chapa_126x126x5.FCStd  # FreeCAD parametric model
    ├── summary.json           # Processing summary
    └── frames/                # Extracted frames (56 .png files)
```

---

## Performance Metrics

**Before (inline bash commands)**:
- 47+ separate `python -c "..."` commands
- ~35s overhead (process spawning)
- ~328s total (5m 28s)

**After (consolidated runner)**:
- 1 runner command + 2 handoffs
- ~1s overhead
- ~294s total (4m 54s)
- **34s saved (10% faster)**

---

## Example Usage

```
User: "Analyze this video and create CAD: C:/path/to/part_video.mp4"

Claude:
1. Runs: python recad_runner.py "C:/path/to/part_video.mp4"
   → Extracts 56 frames @ 1.5 FPS
   → Transcribes: "Rectangular plate, 126mm x 126mm, 5mm thick"
   → Prepares claude_handoff.json

2. Reads handoff, dispatches 5 agents in parallel (Task tool)
   → Agent 0-4 analyze frames 0-10, 11-21, 22-32, 33-43, 44-55
   → Each identifies: Rectangle 126x126mm with 5mm extrusion
   → Saves agent_results.json

3. Resumes: python recad_runner.py --agent-results agent_results.json
   → Aggregates: Rectangle 126x126x5 (confidence 0.91)
   → Builds semantic.json with PartBuilder
   → Validates "parameters" wrapper ✓

4. Executes freecadcmd to export CAD
   → Creates chapa_retangular_126x126x5.FCStd
   → Validates volume: 79,380 mm³ ✓ CORRECT!

5. Presents results to user:
   ✅ Semantic JSON: semantic.json
   ✅ CAD Model: chapa_retangular_126x126x5.FCStd
   ✅ Volume: 79,380 mm³ (100% accurate)
   ✅ Session: docs/outputs/recad/2025-11-06_153425/
```

---

## Version

**v2.1.0** - Session Reuse + Auto-Detection
- ✅ Auto-detects session ID from `--agent-results` path
- ✅ Reuses existing session (no duplicate directories)
- ✅ All outputs consolidated in single session folder
- ✅ Skips Phase 0-1 when resuming from agent results
- ✅ New `--session-id` argument for manual session reuse

**v2.0.0** - Consolidated Runner + Optimization
- ✅ recad_runner.py consolidates Phases 0, 1, 3, 6
- ✅ 47 commands → 1 command (95% reduction)
- ✅ Type safety (Union[str, Path] throughout)
- ✅ Correct imports (PartBuilder, not SemanticGeometryBuilder)
- ✅ 34s faster execution (10% improvement)
- ✅ Zero type mismatch errors

---

CLAUDE.MD ATIVO

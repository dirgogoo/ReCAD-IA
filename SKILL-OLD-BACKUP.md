---
name: recad
description: Video-to-CAD reconstruction skill. Analyzes video of physical parts, extracts geometry, and generates parametric CAD models. Unified skill combining video analysis + semantic geometry + CAD export.
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

**Pipeline** (5 phases):
1. **Extract**: Frames (@1.5 FPS) + Audio transcription (Whisper)
2. **Analyze**: 5 parallel Claude agents analyze frames for geometry
3. **Aggregate**: Build semantic JSON using SemanticGeometryBuilder (NO inline JSON!)
4. **Export**: Convert to FreeCAD parametric model (.FCStd)
5. **Validate**: Check volume, dimensions, topology

## Invocation

**Simple command**:
```
recad <video_path>
```

**With options**:
```
recad <video_path> --fps 1.5 --output <dir>
```

## Workflow Execution

When invoked, follow these steps:

### Phase 0: Setup

```bash
# Create session directories
python src/setup.py <video_path>
```

Returns session info for subsequent phases.

### Phase 1: Extract Video Data

```bash
# Extract frames + audio
python -c "
from extract_frames import extract_frames_at_fps
from extract_audio import extract_audio_from_video, transcribe_audio_with_whisper

frames = extract_frames_at_fps(video_path, output_dir, fps=1.5)
audio_path = extract_audio_from_video(video_path, output_dir)
transcription = transcribe_audio_with_whisper(audio_path, language='pt')
"
```

**Output**: Frame paths + transcription text

### Phase 2: Parallel Agent Analysis

**IMPORTANT**: This phase MUST use Claude Task tool!

1. **Batch frames** (divide into 5 batches)
2. **Dispatch 5 agents in parallel** using Task tool
3. **Each agent analyzes** its batch of frames:
   - Read frames using Read tool
   - Identify geometry (circle, rectangle, etc.)
   - Extract dimensions from calipers/rulers
   - Correlate with audio timestamps
4. **Each agent returns** detected geometry + measurements

**Agent Prompt Template**:
```
Analyze frames {start}-{end} for geometric reconstruction.

Frames: {frame_paths}
Audio: "{transcription_text}"

Your task:
1. Read each frame (use Read tool)
2. Identify shapes: circle, rectangle, polygon
3. Extract dimensions from measuring tools (calipers, rulers)
4. Correlate visual measurements with audio mentions
5. Return JSON with detected geometry

Return format:
{
  "batch_id": "batch_0",
  "frames_analyzed": 4,
  "geometry": {
    "type": "Rectangle",  // or "Circle"
    "dimensions": {
      "width": 126,  // mm
      "height": 126,
      "thickness": 5
    },
    "confidence": 0.95
  },
  "measurements_source": "caliper + audio correlation"
}
```

### Phase 3: Aggregate with Builder

**CRITICAL**: Use SemanticGeometryBuilder, NOT inline JSON!

```python
from semantic_builder import SemanticGeometryBuilder

# Aggregate agent results
all_results = [agent1_result, agent2_result, ...] # From Task outputs

# Determine most common geometry
geometry_type = most_common([r["geometry"]["type"] for r in all_results])
dimensions = aggregate_dimensions(all_results)

# Build semantic JSON using Builder
builder = SemanticGeometryBuilder(part_name)
builder.set_units("mm")
builder.set_work_plane("frontal")

if geometry_type == "Rectangle":
    builder.add_rectangle_extrusion(
        center=(0, 0),
        width=dimensions["width"],
        height=dimensions["height"],
        extrude_distance=dimensions["thickness"]
    )
elif geometry_type == "Circle":
    builder.add_circle_extrusion(
        center=(0, 0),
        diameter=dimensions["diameter"],
        extrude_distance=dimensions["length"]
    )

# Add metadata
builder.add_metadata("video_file", video_path)
builder.add_metadata("frames_analyzed", total_frames)
builder.add_metadata("audio_transcription", transcription_text)
builder.add_metadata("visual_confidence", avg_confidence)

# Save
builder.save(f"{session_dir}/semantic.json")
```

**Why Builder**:
- ✅ Guarantees "parameters" wrapper is present
- ✅ Ensures nested {"value": X, "unit": "mm"} format
- ✅ Prevents format errors that cause wrong dimensions
- ✅ No more 158,760 mm³ when expecting 79,380 mm³!

### Phase 4: Export to CAD

```python
from cad_export import convert_to_freecad

success = convert_to_freecad(
    part_json=semantic_json,  # From builder
    output_path=f"{session_dir}/part.FCStd"
)

# Validate volume
import FreeCAD
doc = FreeCAD.openDocument(cad_path)
body = doc.getObject("Body")
volume = body.Shape.Volume  # Should match expected!
```

### Phase 5: Report

Present to user:
- ✅ Semantic JSON path
- ✅ CAD file path (.FCStd)
- ✅ Volume (mm³)
- ✅ Dimensions summary
- ✅ Confidence scores

## Key Files

```
recad/
├── SKILL.md                  # This file
├── src/
│   ├── semantic_builder.py  # 🔥 Builder (prevents format errors!)
│   ├── extract_frames.py    # ffmpeg frame extraction
│   ├── extract_audio.py     # Audio + Whisper transcription
│   ├── cad_export.py         # FreeCAD .FCStd generation
│   └── setup.py              # Session initialization
├── examples/
│   ├── simple_cylinder.json  # Example output
│   ├── hollow_cylinder.json  # Multi-feature example
│   └── l_bracket.json        # Complex geometry
└── docs/
    └── SEMANTIC_GEOMETRY_SPEC.md  # JSON format spec
```

## Configuration

**Default settings**:
```yaml
fps: 1.5  # Frames per second (good for geometric capture)
agents: 5  # Parallel analysis agents
units: mm  # Default units
freecad_path: "C:/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecadcmd.exe"
```

## Error Handling

**Common issues**:

1. **Wrong volume** (e.g., 2x expected)
   - **Cause**: Inline JSON missing "parameters" wrapper
   - **Fix**: ALWAYS use SemanticGeometryBuilder!

2. **FreeCAD import error**
   - **Cause**: FreeCAD path incorrect
   - **Fix**: Update freecad_path in config

3. **Whisper transcription fails**
   - **Cause**: No API key
   - **Fix**: Set OPENAI_API_KEY env var

4. **Agent analysis incomplete**
   - **Cause**: Frames too many or unclear
   - **Fix**: Reduce FPS or improve video quality

## Output Directory Structure

```
docs/outputs/recad/
└── 2025-11-06_143045/
    ├── metadata.json          # Session info
    ├── semantic.json          # Semantic geometry (from Builder!)
    ├── part.FCStd             # FreeCAD parametric model
    ├── summary.json           # Processing summary
    └── frames/                # Extracted frames (temp, deleted after)
```

## Success Criteria

- ✅ Semantic JSON validates against spec
- ✅ "parameters" wrapper present in all features
- ✅ Volume matches expected (±1% tolerance)
- ✅ CAD file opens in FreeCAD
- ✅ Dimensions are parametric (editable)

## Example Usage

```
User: "Analyze this video and create CAD: C:/path/to/part_video.mp4"

Claude:
1. Invokes ReCAD skill
2. Extracts 36 frames @ 1.5 FPS
3. Transcribes audio: "Rectangular plate, 126mm x 126mm, 5mm thick"
4. Dispatches 5 agents to analyze frames in parallel
5. Agents identify: Rectangle 126x126mm with 5mm extrusion
6. Uses SemanticGeometryBuilder to create correct JSON
7. Exports to part.FCStd (79,380 mm³ volume ✓)
8. Presents results to user
```

## Version

**v1.0.0** - Initial unified ReCAD skill
- Consolidated from video-interpreter + semantic-geometry
- SemanticGeometryBuilder prevents format errors
- Simplified invocation

---

CLAUDE.MD ATIVO

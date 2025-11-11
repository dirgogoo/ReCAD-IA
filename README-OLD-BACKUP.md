# ReCAD - Video to CAD Reconstruction

**Unified skill** for converting videos of physical parts into parametric CAD models.

## Quick Start

```
recad C:/path/to/part_video.mp4
```

## What It Does

1. **Extracts** frames (@1.5 FPS) + audio transcription
2. **Analyzes** geometry using 5 parallel Claude agents
3. **Builds** semantic JSON using SemanticGeometryBuilder (prevents format errors!)
4. **Exports** to FreeCAD parametric model (.FCStd)
5. **Validates** dimensions and volume

## Features

- ✅ **Unified**: All code in one place (no scattered dependencies)
- ✅ **Builder Pattern**: Guarantees correct JSON format
- ✅ **Parallel Processing**: 5 agents analyze simultaneously
- ✅ **Audio Correlation**: Matches spoken measurements with visual
- ✅ **Parametric CAD**: Generated models are fully editable

## Requirements

- **Python 3.8+**
- **FFmpeg** (for frame/audio extraction)
- **OpenAI API Key** (for Whisper transcription)
- **FreeCAD 1.0+** (for CAD export)

## Output

```
docs/outputs/recad/2025-11-06_143045/
├── semantic.json    # Semantic geometry (spec-compliant)
├── part.FCStd       # FreeCAD parametric model
├── metadata.json    # Session info
└── summary.json     # Processing report
```

## Examples

See `examples/` for sample semantic JSON:
- `simple_cylinder.json` - Basic extrusion
- `hollow_cylinder.json` - Multi-feature (extrude + cut)
- `l_bracket.json` - Complex geometry

## Documentation

- **SKILL.md** - Complete skill documentation (read by Claude)
- **docs/SEMANTIC_GEOMETRY_SPEC.md** - JSON format specification

## Version

**v1.0.0** - Initial release
- Consolidated from video-interpreter + semantic-geometry projects
- SemanticGeometryBuilder ensures format correctness
- Simplified, unified workflow

## License

MIT


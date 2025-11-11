# Phase 2: Claude Agent Analysis - Complete Instructions

## Overview

Phase 2 is where **Claude dispatches 5 parallel agents** to analyze video frames and detect geometric features. This phase MUST be executed correctly to ensure proper CAD generation.

---

## Step-by-Step Workflow

### 1. **Runner Pauses After Phase 1**

When you run:
```bash
python recad_runner.py video.mp4 --fps 1.5
```

Runner completes Phase 0-1, then **PAUSES** with message:
```
[Phase 2] HANDOFF TO CLAUDE
  [ACTION REQUIRED] Claude should now:
    1. Read: claude_handoff.json
    2. Dispatch 5 Task agents in parallel using prompts/multi_feature_analysis.md
    3. Each agent analyzes ~18 frames
    4. Collect agent outputs and call save_agent_results()
    5. Results will be saved to: agent_results.json
```

---

### 2. **Claude Reads Handoff Data**

```python
# Read handoff instructions
handoff_path = "path/to/session/claude_handoff.json"
with open(handoff_path) as f:
    handoff = json.load(f)

# Handoff contains:
{
  "frames_dir": "/absolute/path/to/frames",
  "frame_count": 89,
  "frame_paths": [...],
  "transcription": {"text": "..."},
  "num_agents": 5,
  "batch_size": 18
}
```

---

### 3. **Dispatch 5 Agents in Parallel**

**CRITICAL**: Use the multi-feature analysis prompt located at:
`C:\Users\conta\.claude\skills\recad\src\prompts\multi_feature_analysis.md`

**Load the prompt**:
```python
prompt_path = Path("prompts/multi_feature_analysis.md")
with open(prompt_path) as f:
    base_prompt = f.read()
```

**Dispatch 5 agents** (use single message with 5 Task calls):

```python
# Agent 1: Frames 0-17
task1 = Task(
    subagent_type="general-purpose",
    description="Analyze frames batch 1",
    prompt=f"{base_prompt}\n\n**Your Assignment**: Analyze frames 0-17\n**Frames**: {frames[0:18]}"
)

# Agent 2: Frames 18-35
task2 = Task(...)

# Agent 3: Frames 36-53
task3 = Task(...)

# Agent 4: Frames 54-71
task4 = Task(...)

# Agent 5: Frames 72-88
task5 = Task(...)
```

**Agents return multi-feature format**:
```json
{
  "agent_id": "visual_agent_1",
  "features": [
    {
      "type": "Extrude",
      "operation": "new_body",
      "geometry": {"type": "Circle", "diameter": 90},
      "distance": 27,
      "confidence": 0.90
    },
    {
      "type": "Cut",
      "operation": "remove",
      "geometry": {"type": "Rectangle", "width": 27, "height": 27},
      "distance": 6,
      "confidence": 0.85
    }
  ]
}
```

---

### 4. **Save Agent Results** ← **CRITICAL STEP**

After all 5 agents complete, **YOU MUST SAVE** the results:

**Option A: Use runner's save_agent_results() method**:

```python
from recad_runner import ReCADRunner

# Reconstruct runner instance
runner = ReCADRunner(video_path="...", output_dir="...")
runner.session_dir = Path("path/to/session")

# Collect agent outputs
agent_outputs = [
    agent1_result,  # Raw text output from Task tool
    agent2_result,
    agent3_result,
    agent4_result,
    agent5_result
]

# Save automatically (parses JSON and saves)
runner.save_agent_results(agent_outputs)
```

**Option B: Manual save with Write tool**:

```python
import json

# Parse agent outputs to JSON objects
agent_results = []
for output in agent_outputs:
    # Extract JSON from output text
    json_data = json.loads(output)  # or extract with regex
    agent_results.append(json_data)

# Save to session directory
output_path = Path("session_dir/agent_results.json")
with open(output_path, 'w') as f:
    json.dump(agent_results, f, indent=2)
```

---

### 5. **Continue Workflow**

After saving `agent_results.json`, continue the workflow:

```bash
python recad_runner.py video.mp4 --agent-results path/to/agent_results.json
```

Runner will:
- Load agent_results.json
- Detect multi-feature format automatically
- Aggregate features (extrudes + cuts)
- Generate semantic.json with PartBuilder
- Create CAD file

---

## Common Mistakes to Avoid

### ❌ **Mistake 1**: Not saving agent_results.json
**Symptom**: Runner fails with "Agent results not found"
**Fix**: Always call `save_agent_results()` or use Write tool

### ❌ **Mistake 2**: Saving in wrong location
**Symptom**: Runner can't find file
**Fix**: Save to `session_dir/agent_results.json` (exact path from handoff)

### ❌ **Mistake 3**: Using legacy single-geometry format
**Symptom**: System only detects one feature (misses cuts)
**Fix**: Use `multi_feature_analysis.md` prompt (returns list of features)

### ❌ **Mistake 4**: Not dispatching agents in parallel
**Symptom**: Slow execution (~5x slower)
**Fix**: Use **single message** with 5 Task calls (parallel execution)

---

## Validation Checklist

Before continuing to Phase 3, verify:

- [ ] ✅ `agent_results.json` exists in session directory
- [ ] ✅ File contains array of 5 agent results
- [ ] ✅ Each agent result has `"features"` array (multi-feature format)
- [ ] ✅ Features include both "Extrude" and "Cut" types (if applicable)
- [ ] ✅ Confidence values are reasonable (0.7-0.95)

---

## Example Complete Execution

```python
# 1. Read handoff
handoff_path = "C:/Users/conta/.claude/skills/recad/src/docs/outputs/recad/2025-11-06_180000/claude_handoff.json"
with open(handoff_path) as f:
    handoff = json.load(f)

# 2. Load multi-feature prompt
prompt_path = Path("C:/Users/conta/.claude/skills/recad/src/prompts/multi_feature_analysis.md")
with open(prompt_path) as f:
    base_prompt = f.read()

# 3. Dispatch 5 agents (in parallel - single message!)
agents = []
for i in range(5):
    start_frame = i * 18
    end_frame = min((i+1) * 18, handoff["frame_count"])

    agent_prompt = f"{base_prompt}\n\n**Your Assignment**: Analyze frames {start_frame}-{end_frame}"

    agents.append(Task(
        subagent_type="general-purpose",
        description=f"Analyze batch {i+1}",
        prompt=agent_prompt
    ))

# Wait for all agents to complete (automatic with parallel Task calls)

# 4. Save results
from recad_runner import ReCADRunner
runner = ReCADRunner(video_path=handoff["frames_dir"], ...)
runner.session_dir = Path(handoff_path).parent
runner.save_agent_results([agent1.output, agent2.output, ...])

# 5. Continue workflow
# python recad_runner.py video.mp4 --agent-results path/to/agent_results.json
```

---

## Troubleshooting

### Issue: "Agent results not found"
**Cause**: `agent_results.json` not saved
**Solution**: Call `save_agent_results()` after agents complete

### Issue: "No features found in agent results"
**Cause**: Agents returned legacy format (single geometry)
**Solution**: Use `multi_feature_analysis.md` prompt

### Issue: "Visual confidence too low"
**Cause**: Agents didn't analyze images (returned defaults)
**Solution**: Check frame paths are correct, agents have multimodal access

---

**Last Updated**: 2025-11-06
**Status**: ✅ Tested and Working

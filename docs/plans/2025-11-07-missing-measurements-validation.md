# Missing Measurements Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Detect missing critical measurements from audio transcription and halt execution to request them from the user.

**Architecture:** Add validation layer that analyzes transcription text and agent consensus to identify missing dimensional parameters. If critical measurements are absent, raise interactive error that prompts user for specific missing values before continuing.

**Tech Stack:** Python, regex/NLP for dimension extraction, interactive CLI prompts

---

## Task 1: Create Measurement Extractor Module

**Files:**
- Create: `C:\Users\conta\.claude\skills\recad\src\utils\measurement_extractor.py`
- Test: `C:\Users\conta\.claude\skills\recad\src\tests\test_measurement_extractor.py`

**Step 1: Write the failing test**

Create test file with basic extraction test:

```python
"""Tests for measurement extraction from transcription."""
import pytest
from utils.measurement_extractor import MeasurementExtractor, MissingMeasurementError


def test_extract_diameter_from_transcription():
    """Should extract diameter measurement from Portuguese text."""
    extractor = MeasurementExtractor()

    text = "Chapa de diâmetro 90mm"
    measurements = extractor.extract_measurements(text)

    assert "diameter" in measurements
    assert measurements["diameter"] == 90.0


def test_missing_diameter_raises_error():
    """Should raise error when diameter is mentioned but value is missing."""
    extractor = MeasurementExtractor()

    text = "Chapa circular com furos"  # No diameter value

    with pytest.raises(MissingMeasurementError) as exc_info:
        extractor.validate_required_measurements(text, required=["diameter"])

    assert "diameter" in str(exc_info.value).lower()
```

**Step 2: Run test to verify it fails**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_measurement_extractor.py::test_extract_diameter_from_transcription -v`

Expected: FAIL with "No module named 'utils.measurement_extractor'"

**Step 3: Write minimal implementation**

Create `utils/measurement_extractor.py`:

```python
"""
Extracts dimensional measurements from audio transcription text.

Detects missing critical measurements and raises errors to request them.
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


class MissingMeasurementError(Exception):
    """Raised when a critical measurement is missing from transcription."""

    def __init__(self, missing_measurements: List[str], transcription_text: str):
        self.missing_measurements = missing_measurements
        self.transcription_text = transcription_text

        measurements_str = ", ".join(missing_measurements)
        super().__init__(
            f"Missing critical measurements: {measurements_str}\n"
            f"Transcription: '{transcription_text}'\n"
            f"Please provide these measurements to continue."
        )


@dataclass
class Measurement:
    """Represents an extracted measurement."""
    name: str
    value: float
    unit: str
    confidence: float  # 0.0 to 1.0


class MeasurementExtractor:
    """Extracts measurements from transcription text."""

    # Regex patterns for common measurements (Portuguese)
    PATTERNS = {
        "diameter": [
            r"diâmetro\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"diâmetro\s+(?:de\s+)?(\d+(?:\.\d+)?)",
        ],
        "radius": [
            r"raio\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"raio\s+(?:de\s+)?(\d+(?:\.\d+)?)",
        ],
        "height": [
            r"altura\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"espessura\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
        ],
        "width": [
            r"largura\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"comprimento\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
        ],
        "distance": [
            r"distância\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"(\d+)\s*mm\s+de\s+distância",
        ],
        "flat_to_flat": [
            r"(\d+)\s*mm\s+de\s+(?:distância|espaçamento)",
            r"2\s+linhas.*?(\d+(?:\.\d+)?)\s*mm",
        ]
    }

    def extract_measurements(self, text: str) -> Dict[str, float]:
        """
        Extract all measurements from transcription text.

        Args:
            text: Transcription text (Portuguese)

        Returns:
            Dict mapping measurement names to values (in mm)
        """
        measurements = {}
        text_lower = text.lower()

        for measurement_name, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        measurements[measurement_name] = value
                        break  # Found match for this measurement
                    except (ValueError, IndexError):
                        continue

        return measurements

    def validate_required_measurements(
        self,
        text: str,
        required: List[str]
    ) -> Dict[str, float]:
        """
        Validate that all required measurements are present.

        Args:
            text: Transcription text
            required: List of required measurement names

        Returns:
            Dict of extracted measurements

        Raises:
            MissingMeasurementError: If any required measurements are missing
        """
        measurements = self.extract_measurements(text)
        missing = [name for name in required if name not in measurements]

        if missing:
            raise MissingMeasurementError(missing, text)

        return measurements
```

**Step 4: Run test to verify it passes**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_measurement_extractor.py -v`

Expected: 2 tests PASS

**Step 5: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/utils/measurement_extractor.py src/tests/test_measurement_extractor.py
git commit -m "feat: add measurement extraction from transcription

- Extract dimensional measurements using regex patterns
- Support Portuguese measurement keywords
- Raise MissingMeasurementError when critical measurements absent
- TDD: 2 tests pass"
```

---

## Task 2: Add Pattern-Specific Measurement Requirements

**Files:**
- Modify: `C:\Users\conta\.claude\skills\recad\src\patterns\base.py:1-50`
- Test: `C:\Users\conta\.claude\skills\recad\src\tests\test_measurement_requirements.py`

**Step 1: Write the failing test**

Create test file:

```python
"""Tests for pattern-specific measurement requirements."""
import pytest
from patterns.base import get_required_measurements_for_pattern


def test_chord_cut_requires_diameter_and_flat_to_flat():
    """Chord cut pattern requires diameter and flat_to_flat measurements."""
    required = get_required_measurements_for_pattern("chord_cut")

    assert "diameter" in required or "radius" in required
    assert "flat_to_flat" in required or "distance" in required


def test_circle_extrude_requires_diameter_and_height():
    """Circle extrude requires diameter and height."""
    required = get_required_measurements_for_pattern("circle_extrude")

    assert "diameter" in required or "radius" in required
    assert "height" in required
```

**Step 2: Run test to verify it fails**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_measurement_requirements.py -v`

Expected: FAIL with "cannot import name 'get_required_measurements_for_pattern'"

**Step 3: Write minimal implementation**

Modify `patterns/base.py` to add at the end:

```python
# Pattern-specific measurement requirements
PATTERN_REQUIREMENTS = {
    "chord_cut": ["diameter", "flat_to_flat", "height"],
    "circle_extrude": ["diameter", "height"],
    "rectangle_extrude": ["width", "height", "depth"],
    "circular_hole": ["diameter", "depth"],
}


def get_required_measurements_for_pattern(pattern_name: str) -> List[str]:
    """
    Get list of required measurements for a pattern.

    Args:
        pattern_name: Pattern identifier (e.g., "chord_cut")

    Returns:
        List of required measurement names

    Raises:
        ValueError: If pattern is unknown
    """
    if pattern_name not in PATTERN_REQUIREMENTS:
        raise ValueError(f"Unknown pattern: {pattern_name}")

    return PATTERN_REQUIREMENTS[pattern_name]
```

Add import at top of file:

```python
from typing import List, Dict, Any, Optional
```

**Step 4: Run test to verify it passes**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_measurement_requirements.py -v`

Expected: 2 tests PASS

**Step 5: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/patterns/base.py src/tests/test_measurement_requirements.py
git commit -m "feat: define pattern-specific measurement requirements

- Add PATTERN_REQUIREMENTS dict mapping patterns to required measurements
- Add get_required_measurements_for_pattern() function
- Support chord_cut, circle_extrude, rectangle_extrude, circular_hole
- TDD: 2 tests pass"
```

---

## Task 3: Integrate Validation into Claude Code Analyzer

**Files:**
- Modify: `C:\Users\conta\.claude\skills\recad\src\patterns\claude_analyzer.py:63-90`
- Test: `C:\Users\conta\.claude\skills\recad\src\tests\test_claude_analyzer_validation.py`

**Step 1: Write the failing test**

Create test file:

```python
"""Tests for measurement validation in Claude analyzer."""
import pytest
from pathlib import Path
from patterns.claude_analyzer import ClaudeCodeAnalyzer
from utils.measurement_extractor import MissingMeasurementError


def test_analyzer_detects_missing_measurements(tmp_path):
    """Analyzer should detect missing measurements and include in instructions."""
    analyzer = ClaudeCodeAnalyzer()

    # Mock data with missing flat_to_flat measurement
    agent_results = [
        {
            "agent_id": "test",
            "features": [
                {
                    "type": "Extrude",
                    "geometry": {"type": "Circle", "diameter": 90},
                    "distance": 27
                },
                {
                    "type": "Cut",
                    "position": "left_side"
                }
            ]
        }
    ]

    # Transcription mentions cuts but no flat_to_flat distance
    transcription = "Chapa de diâmetro 90mm com cortes laterais"

    # This should detect chord_cut pattern but missing flat_to_flat
    request_path = analyzer.request_analysis(
        agent_results=agent_results,
        transcription=transcription,
        session_dir=tmp_path
    )

    # Should create request with warning about missing measurement
    request_file = tmp_path / ".claude_analysis_request.json"
    assert request_file.exists()

    import json
    with open(request_file) as f:
        request = json.load(f)

    # Should include warning about missing measurement
    assert "missing_measurements" in request or "warnings" in request
```

**Step 2: Run test to verify it fails**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_claude_analyzer_validation.py -v`

Expected: FAIL - missing_measurements not in request

**Step 3: Write minimal implementation**

Modify `patterns/claude_analyzer.py` in the `request_analysis` method (around line 24):

```python
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

    # NEW: Detect pattern and validate measurements
    from utils.measurement_extractor import MeasurementExtractor, MissingMeasurementError
    from patterns.base import get_required_measurements_for_pattern

    detected_pattern = self._detect_pattern_from_agents(agent_results)
    measurement_warnings = []

    if detected_pattern and transcription:
        try:
            required = get_required_measurements_for_pattern(detected_pattern)
            extractor = MeasurementExtractor()
            extractor.validate_required_measurements(transcription, required)
        except MissingMeasurementError as e:
            measurement_warnings = e.missing_measurements
        except ValueError:
            # Unknown pattern, skip validation
            pass

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
        "detected_pattern": detected_pattern,
        "missing_measurements": measurement_warnings
    }

    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(request, f, indent=2, ensure_ascii=False)

    self._print_request_summary(request_file, python_file, analyzer_file)

    # NEW: If measurements are missing, print warning but continue
    if measurement_warnings:
        print(f"\n  [WARNING] Missing measurements detected: {', '.join(measurement_warnings)}")
        print(f"  [WARNING] Claude Code may need to prompt user for these values")

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
```

Add import at top of file:

```python
import json
```

**Step 4: Run test to verify it passes**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_claude_analyzer_validation.py -v`

Expected: 1 test PASS

**Step 5: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/patterns/claude_analyzer.py src/tests/test_claude_analyzer_validation.py
git commit -m "feat: integrate measurement validation into analyzer

- Detect pattern from agent results
- Validate required measurements against transcription
- Include missing_measurements in request JSON
- Print warnings when measurements are missing
- TDD: 1 test passes"
```

---

## Task 4: Add Interactive Prompt for Missing Measurements

**Files:**
- Create: `C:\Users\conta\.claude\skills\recad\src\utils\interactive_prompt.py`
- Modify: `C:\Users\conta\.claude\skills\recad\src\recad_runner.py:475-485`
- Test: `C:\Users\conta\.claude\skills\recad\src\tests\test_interactive_prompt.py`

**Step 1: Write the failing test**

Create test file:

```python
"""Tests for interactive measurement prompts."""
import pytest
from unittest.mock import patch
from utils.interactive_prompt import prompt_for_missing_measurements


def test_prompt_for_single_measurement():
    """Should prompt user for single missing measurement."""
    with patch('builtins.input', return_value='78'):
        result = prompt_for_missing_measurements(["flat_to_flat"])

    assert result["flat_to_flat"] == 78.0


def test_prompt_for_multiple_measurements():
    """Should prompt for each missing measurement."""
    with patch('builtins.input', side_effect=['90', '27']):
        result = prompt_for_missing_measurements(["diameter", "height"])

    assert result["diameter"] == 90.0
    assert result["height"] == 27.0


def test_prompt_handles_invalid_input():
    """Should re-prompt on invalid input."""
    with patch('builtins.input', side_effect=['invalid', '78']):
        result = prompt_for_missing_measurements(["flat_to_flat"])

    assert result["flat_to_flat"] == 78.0
```

**Step 2: Run test to verify it fails**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_interactive_prompt.py -v`

Expected: FAIL with "No module named 'utils.interactive_prompt'"

**Step 3: Write minimal implementation**

Create `utils/interactive_prompt.py`:

```python
"""
Interactive CLI prompts for missing measurements.
"""
from typing import Dict, List


# Portuguese measurement name translations
MEASUREMENT_NAMES_PT = {
    "diameter": "diâmetro",
    "radius": "raio",
    "height": "altura",
    "width": "largura",
    "depth": "profundidade",
    "distance": "distância",
    "flat_to_flat": "distância entre linhas paralelas (flat-to-flat)",
}


def prompt_for_missing_measurements(missing: List[str]) -> Dict[str, float]:
    """
    Prompt user for missing measurements via CLI.

    Args:
        missing: List of missing measurement names

    Returns:
        Dict mapping measurement names to user-provided values
    """
    print(f"\n{'='*70}")
    print(f"  [INPUT REQUIRED] Missing Measurements")
    print(f"{'='*70}\n")
    print(f"  The audio transcription is missing {len(missing)} critical measurement(s).")
    print(f"  Please provide the following values (in mm):\n")

    measurements = {}

    for measurement_name in missing:
        # Get Portuguese name if available
        display_name = MEASUREMENT_NAMES_PT.get(measurement_name, measurement_name)

        while True:
            try:
                value_str = input(f"  {display_name} (mm): ").strip()
                value = float(value_str)

                if value <= 0:
                    print(f"    [ERROR] Value must be positive. Try again.")
                    continue

                measurements[measurement_name] = value
                break

            except ValueError:
                print(f"    [ERROR] Invalid number. Please enter a numeric value.")
            except (KeyboardInterrupt, EOFError):
                print(f"\n  [CANCELLED] User cancelled input.")
                raise RuntimeError("User cancelled measurement input")

    print(f"\n{'='*70}")
    print(f"  [OK] All measurements provided. Continuing...")
    print(f"{'='*70}\n")

    return measurements


def format_measurement_prompt(
    missing: List[str],
    transcription: str,
    detected_pattern: str
) -> str:
    """
    Format a helpful prompt message for missing measurements.

    Args:
        missing: List of missing measurement names
        transcription: Original transcription text
        detected_pattern: Detected pattern name

    Returns:
        Formatted message string
    """
    msg = (
        f"Pattern: {detected_pattern}\n"
        f"Transcription: \"{transcription}\"\n\n"
        f"Missing measurements: {', '.join(missing)}\n\n"
        f"The system detected a {detected_pattern} pattern but could not extract "
        f"the following measurements from your audio:\n"
    )

    for measurement_name in missing:
        display_name = MEASUREMENT_NAMES_PT.get(measurement_name, measurement_name)
        msg += f"  - {display_name}\n"

    return msg
```

**Step 4: Run test to verify it passes**

Run: `cd C:\Users\conta\.claude\skills\recad\src && pytest tests/test_interactive_prompt.py -v`

Expected: 3 tests PASS

**Step 5: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/utils/interactive_prompt.py src/tests/test_interactive_prompt.py
git commit -m "feat: add interactive CLI prompts for missing measurements

- Prompt user for each missing measurement
- Display Portuguese measurement names
- Validate numeric input and retry on errors
- Handle Ctrl+C gracefully
- TDD: 3 tests pass"
```

---

## Task 5: Integrate Interactive Prompts into Main Runner

**Files:**
- Modify: `C:\Users\conta\.claude\skills\recad\src\recad_runner.py:475-490`
- Test: Manual integration test

**Step 1: Add import at top of file**

```python
from utils.interactive_prompt import prompt_for_missing_measurements, format_measurement_prompt
```

**Step 2: Modify phase_3_aggregate method**

Find the section where `analyzer.request_analysis()` is called (around line 481) and modify:

```python
# NEW: Try Claude Code + PartBuilder first
# ========================================
from patterns.claude_analyzer import get_analyzer
import subprocess

analyzer = get_analyzer()
python_file = analyzer.request_analysis(
    agent_results=agent_results,
    transcription=transcription,
    session_dir=self.session_dir
)

# NEW: Check if measurements are missing
request_file = self.session_dir / ".claude_analysis_request.json"
if request_file.exists():
    with open(request_file, 'r', encoding='utf-8') as f:
        request_data = json.load(f)

    missing = request_data.get("missing_measurements", [])
    detected_pattern = request_data.get("detected_pattern")

    if missing:
        print(f"\n{'='*70}")
        print(f"  [VALIDATION ERROR] Missing Critical Measurements")
        print(f"{'='*70}\n")

        # Show helpful context
        if detected_pattern:
            print(f"  Detected pattern: {detected_pattern}")
        if transcription:
            print(f"  Transcription: \"{transcription}\"")
        print(f"  Missing: {', '.join(missing)}\n")

        # Prompt user for measurements
        try:
            user_measurements = prompt_for_missing_measurements(missing)

            # Update transcription with provided measurements
            # Format: "diameter=90mm, flat_to_flat=78mm"
            measurement_str = ", ".join(
                f"{name}={value}mm"
                for name, value in user_measurements.items()
            )

            # Append to transcription
            updated_transcription = f"{transcription or ''} [Medições fornecidas: {measurement_str}]"

            print(f"  [OK] Updated transcription with measurements")
            print(f"  [OK] New transcription: \"{updated_transcription}\"")

            # Re-run analysis with updated transcription
            python_file = analyzer.request_analysis(
                agent_results=agent_results,
                transcription=updated_transcription,
                session_dir=self.session_dir
            )

        except RuntimeError as e:
            raise RuntimeError(
                f"Cannot continue without required measurements.\n"
                f"Missing: {', '.join(missing)}"
            ) from e

if python_file:
    # Execute Claude Code's Python file
    print(f"\n  [OK] Executing Claude Code analysis...")
    # ... rest of execution code
```

**Step 3: Manual integration test**

Create test video without mentioning all measurements in audio, run:

```bash
cd C:\Users\conta\.claude\skills\recad\src
python recad_runner.py "test_video.mp4" --fps 1.5
```

Expected behavior:
1. System detects missing measurements
2. Prompts user for values
3. Continues with user-provided values
4. Generates correct semantic.json

**Step 4: Verify test passes**

Check:
- [ ] System detects missing measurement
- [ ] User is prompted interactively
- [ ] Provided value is used in generation
- [ ] semantic.json has correct values

**Step 5: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/recad_runner.py
git commit -m "feat: integrate interactive prompts into main workflow

- Check for missing_measurements in analysis request
- Prompt user interactively when measurements are missing
- Update transcription with user-provided values
- Re-run analysis with complete data
- Halt execution if user cancels input

Fixes issue where agents would guess measurements when not specified in audio."
```

---

## Task 6: Update Instructions for Claude Code

**Files:**
- Modify: `C:\Users\conta\.claude\skills\recad\src\patterns\claude_analyzer.py:65-90`

**Step 1: Add instructions about missing measurements**

In the `_get_instructions()` method, add a new section after "### 2. Extract Parameters from Audio":

```python
### 2.5. Check for Missing Measurements

**IMPORTANT**: If the request includes `missing_measurements`, the user has already been prompted!

```python
# In claude_analysis.py - check if measurements were provided by user
import json
from pathlib import Path

request_file = Path(__file__).parent / ".claude_analysis_request.json"
with open(request_file) as f:
    request = json.load(f)

# User-provided measurements are appended to transcription
# Look for: "[Medições fornecidas: diameter=90mm, flat_to_flat=78mm]"
transcription = request.get("transcription", "")
if "[Medições fornecidas:" in transcription:
    # Extract user-provided measurements
    import re
    match = re.search(r'\[Medições fornecidas: (.*?)\]', transcription)
    if match:
        measurements_str = match.group(1)
        # Parse: "diameter=90mm, flat_to_flat=78mm"
        for item in measurements_str.split(','):
            name, value = item.strip().split('=')
            value_num = float(value.replace('mm', ''))
            print(f"  [USER PROVIDED] {name} = {value_num}mm")
```
```

**Step 2: Add to Critical Rules section**

Add as new rule:

```markdown
7. [REQUIRED] Use user-provided measurements when available
   - Check transcription for "[Medições fornecidas: ...]"
   - These measurements were interactively collected from the user
   - They override any agent estimates or guesses
```

**Step 3: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/patterns/claude_analyzer.py
git commit -m "docs: add instructions for user-provided measurements

- Explain missing_measurements field in request
- Show how to extract user-provided values from transcription
- Add critical rule to prioritize user-provided measurements
- Ensures Claude Code uses interactive values correctly"
```

---

## Task 7: Add Test Mode Flag

**Files:**
- Modify: `C:\Users\conta\.claude\skills\recad\src\recad_runner.py:35-45`
- Modify: `C:\Users\conta\.claude\skills\recad\src\recad_runner.py:475-490`

**Step 1: Add --no-interactive flag to CLI**

Modify the argument parser (around line 1090):

```python
parser.add_argument(
    '--no-interactive',
    action='store_true',
    help='Disable interactive prompts (use mock measurements for testing)'
)
```

**Step 2: Pass flag to runner**

Modify runner initialization:

```python
def __init__(
    self,
    video_path: Union[str, Path],
    output_dir: Optional[str] = None,
    fps: float = DEFAULT_FPS,
    session_id: Optional[str] = None,
    interactive: bool = True  # NEW parameter
):
    """
    Initialize ReCAD runner.

    Args:
        video_path: Path to video file (accepts str or Path)
        output_dir: Optional output directory (defaults to OUTPUT_BASE_DIR)
        fps: Frames per second for extraction (default: 1.5)
        session_id: Optional session ID to reuse existing session (defaults to new session)
        interactive: Enable interactive prompts for missing measurements (default: True)
    """
    # ... existing initialization code ...
    self.interactive = interactive
```

**Step 3: Skip prompts in non-interactive mode**

Modify the missing measurements check:

```python
if missing:
    if self.interactive:
        # Interactive mode: prompt user
        user_measurements = prompt_for_missing_measurements(missing)
        # ... rest of interactive code ...
    else:
        # Non-interactive mode: use mock measurements
        print(f"  [WARNING] Missing measurements but running in non-interactive mode")
        print(f"  [WARNING] Using mock measurements for testing")

        # Generate reasonable mock values
        mock_measurements = {
            "diameter": 90.0,
            "radius": 45.0,
            "height": 27.0,
            "flat_to_flat": 78.0,
            "width": 100.0,
            "depth": 10.0,
            "distance": 50.0
        }

        user_measurements = {
            name: mock_measurements.get(name, 50.0)
            for name in missing
        }
```

**Step 4: Test both modes**

Test interactive mode:
```bash
python recad_runner.py "test.mp4" --fps 1.5
```

Test non-interactive mode:
```bash
python recad_runner.py "test.mp4" --fps 1.5 --no-interactive
```

**Step 5: Commit**

```bash
cd C:\Users\conta\.claude\skills\recad
git add src/recad_runner.py
git commit -m "feat: add --no-interactive flag for automated testing

- Add interactive parameter to ReCADRunner
- Add --no-interactive CLI flag
- Use mock measurements when interactive=False
- Allows automated tests to run without user input
- Preserves interactive prompts for production use"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] `pytest src/tests/test_measurement_extractor.py -v` - all pass
- [ ] `pytest src/tests/test_measurement_requirements.py -v` - all pass
- [ ] `pytest src/tests/test_claude_analyzer_validation.py -v` - all pass
- [ ] `pytest src/tests/test_interactive_prompt.py -v` - all pass
- [ ] Manual test: Run with incomplete audio → prompts for measurements
- [ ] Manual test: Run with complete audio → no prompts
- [ ] Manual test: Run with `--no-interactive` → uses mocks without prompting
- [ ] All commits follow conventional commit format
- [ ] Code follows DRY, YAGNI, TDD principles

---

## Plan complete and saved to `docs/plans/2025-11-07-missing-measurements-validation.md`.

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**

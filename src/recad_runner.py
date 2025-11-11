#!/usr/bin/env python3
"""
ReCAD Runner - Consolidated Python Workflow
Consolidates phases 0, 1, 3, 6 into single Python script.

Phases that remain external:
- Phase 2: Claude Task tool (parallel frame analysis - multimodal)
- Phase 4-5: FreeCAD (CAD export + validation - requires freecadcmd)

Usage:
    python recad_runner.py <video_path> [--output-dir DIR] [--fps FPS]

Example:
    python recad_runner.py "C:/path/to/video.mp4" --fps 1.5
"""
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union


class ValidationError(Exception):
    """Raised when generated code validation fails."""
    pass

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import ReCAD modules
from extract_frames import extract_frames_at_fps
from extract_audio import extract_audio_from_video, transcribe_audio_with_whisper
from config import OPENAI_API_KEY, DEFAULT_FPS, OUTPUT_BASE_DIR, TEMP_BASE_DIR
from utils.chord_cut_helper import calculate_chord_cut_geometry


class ReCADRunner:
    """Main runner class for ReCAD workflow."""

    def __init__(self, video_path: Union[str, Path], output_dir: Optional[str] = None, fps: float = DEFAULT_FPS, session_id: Optional[str] = None):
        """
        Initialize ReCAD runner.

        Args:
            video_path: Path to video file (accepts str or Path)
            output_dir: Optional output directory (defaults to OUTPUT_BASE_DIR)
            fps: Frames per second for extraction (default: 1.5)
            session_id: Optional session ID to reuse existing session (defaults to new session)
        """
        # Normalize paths immediately (prevents str vs Path errors)
        self.video_path = Path(video_path)
        self.fps = fps

        # Validate video exists
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        # Create or reuse session directories
        base_dir = Path(output_dir) if output_dir else Path(OUTPUT_BASE_DIR)

        if session_id:
            # REUSE existing session
            self.session_id = session_id
            self.session_dir = base_dir / self.session_id

            if not self.session_dir.exists():
                raise FileNotFoundError(f"Session directory not found: {self.session_dir}")

            # Load existing metadata if available
            metadata_path = self.session_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, encoding='utf-8') as f:
                    self.metadata = json.load(f)
            else:
                # Create new metadata for existing session
                self.metadata = {
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "video_path": str(self.video_path.absolute()),
                    "video_size_mb": self.video_path.stat().st_size / (1024 * 1024),
                    "fps": self.fps,
                    "version": "2.0.0-consolidated"
                }
        else:
            # CREATE new session
            self.session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self.session_dir = base_dir / self.session_id
            self.session_dir.mkdir(parents=True, exist_ok=True)

            # Metadata
            self.metadata = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "video_path": str(self.video_path.absolute()),
                "video_size_mb": self.video_path.stat().st_size / (1024 * 1024),
                "fps": self.fps,
                "version": "2.0.0-consolidated"
            }

        # Create subdirectories (handles both new and existing sessions)
        self.frames_dir = self.session_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)

        # Results storage
        self.results = {
            "frames_extracted": 0,
            "audio_transcription": None,
            "agent_results": None,
            "semantic_json_path": None,
            "cad_file_path": None
        }

    def _validate_generated_code(self, python_file: Path) -> bool:
        """
        Validate that generated Python code uses correct imports.

        Args:
            python_file: Path to generated Python file

        Returns:
            True if valid, False if using wrong imports

        Raises:
            ValidationError: If forbidden imports are detected
        """
        with open(python_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for forbidden imports
        forbidden_imports = [
            "from semantic_geometry",
            "import semantic_geometry"
        ]

        for forbidden in forbidden_imports:
            if forbidden in content:
                error_msg = (
                    f"\n{'='*70}\n"
                    f"  [ERROR] VALIDATION ERROR: Wrong imports detected!\n"
                    f"{'='*70}\n\n"
                    f"  Found forbidden import:\n"
                    f"    {forbidden}\n\n"
                    f"  This will generate WRONG JSON format:\n"
                    f"    type: 'Extrude', operation: 'cut'  [WRONG]\n\n"
                    f"  Expected import:\n"
                    f"    from semantic_builder import SemanticGeometryBuilder  [CORRECT]\n\n"
                    f"  This generates CORRECT JSON format:\n"
                    f"    type: 'Cut', cut_type: 'through_all'  [CORRECT]\n\n"
                    f"  [FILE] {python_file}\n"
                    f"  [FIX] Claude Code must re-read instructions in claude_analyzer.py\n"
                    f"{'='*70}\n"
                )
                print(error_msg)
                raise ValidationError(error_msg)

        # Check for correct import (accept both SemanticGeometryBuilder and PartBuilder)
        correct_imports = [
            "from semantic_builder import SemanticGeometryBuilder",
            "from semantic_builder import PartBuilder"
        ]

        has_correct_import = any(imp in content for imp in correct_imports)

        if not has_correct_import:
            warning_msg = (
                f"\n{'='*70}\n"
                f"  WARNING: Missing correct import\n"
                f"{'='*70}\n\n"
                f"  Expected one of:\n"
                f"    from semantic_builder import SemanticGeometryBuilder\n"
                f"    from semantic_builder import PartBuilder\n\n"
                f"  [FILE] {python_file}\n"
                f"{'='*70}\n"
            )
            print(warning_msg)
            return False

        print(f"\n  [OK] Generated code uses correct import (semantic_builder)")
        return True

    def phase_0_setup(self) -> Dict[str, Any]:
        """
        Phase 0: Setup session directories and metadata.

        Returns:
            Dict with session info
        """
        print("=" * 60)
        print("ReCAD Runner - Consolidated Workflow")
        print("=" * 60)
        print(f"\n[Phase 0] Setup")
        print(f"  Session ID: {self.session_id}")
        print(f"  Video: {self.video_path.name} ({self.metadata['video_size_mb']:.2f} MB)")
        print(f"  Output: {self.session_dir}")
        print(f"  FPS: {self.fps}")

        # Save metadata
        metadata_path = self.session_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

        print(f"  [OK] Metadata saved: {metadata_path.name}")

        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "metadata_path": str(metadata_path)
        }

    def phase_1_extract(self) -> Dict[str, Any]:
        """
        Phase 1: Extract frames and audio, transcribe with Whisper.

        Returns:
            Dict with extraction results
        """
        print(f"\n[Phase 1] Extract Video Data")

        # 1.1: Extract frames
        print(f"  Extracting frames @ {self.fps} FPS...")
        try:
            frame_paths = extract_frames_at_fps(
                video_path=self.video_path,  # Now Path object
                output_dir=self.frames_dir,
                fps=self.fps
            )
            self.results["frames_extracted"] = len(frame_paths)
            print(f"  [OK] Frames extracted: {len(frame_paths)}")
        except Exception as e:
            print(f"  [ERROR] Frame extraction failed: {e}")
            raise

        # 1.2: Extract audio
        audio_path = self.session_dir / "audio.wav"
        print(f"  Extracting audio to {audio_path.name}...")
        try:
            extract_audio_from_video(
                video_path=self.video_path,
                output_path=audio_path  # Full file path, not directory!
            )
            print(f"  [OK] Audio extracted: {audio_path.name}")
        except Exception as e:
            print(f"  [WARN] Audio extraction failed: {e}")
            print(f"  [WARN] Continuing without audio...")
            audio_path = None

        # 1.3: Transcribe audio
        transcription_result = None
        if audio_path and audio_path.exists():
            print(f"  Transcribing audio with Whisper...")
            try:
                transcription_result = transcribe_audio_with_whisper(
                    audio_path=audio_path,
                    language="pt",
                    granularity="segment",
                    api_key=OPENAI_API_KEY  # From config.py
                )
                self.results["audio_transcription"] = transcription_result

                # Save transcription
                transcription_path = self.session_dir / "transcription.json"
                with open(transcription_path, 'w', encoding='utf-8') as f:
                    json.dump(transcription_result, f, indent=2, ensure_ascii=False)

                print(f"  [OK] Transcription complete")
                print(f"  [OK] Text: \"{transcription_result.get('text', '')[:100]}...\"")
                print(f"  [OK] Saved: {transcription_path.name}")

            except Exception as e:
                print(f"  [WARN] Transcription failed: {e}")
                print(f"  [WARN] Continuing without transcription...")

        return {
            "frames_extracted": len(frame_paths),
            "frame_paths": [str(Path(p).absolute()) for p in frame_paths],
            "audio_path": str(audio_path.absolute()) if audio_path else None,
            "transcription": transcription_result
        }

    def phase_2_generate_mock_results(self, extraction_results: Dict[str, Any]) -> str:
        """
        Phase 2 TEST MODE: Generate mock agent results for testing.

        This bypasses Claude analysis and generates synthetic results.
        Useful for automated testing of the pipeline.

        Args:
            extraction_results: Results from phase 1

        Returns:
            Path to generated agent_results.json
        """
        print(f"\n[Phase 2] GENERATE MOCK RESULTS (Test Mode)")
        print(f"  Generating synthetic agent results for testing...")

        # Create realistic mock results
        num_frames = extraction_results["frames_extracted"]
        mock_results = []

        for i in range(5):  # 5 mock agents
            mock_results.append({
                "agent_id": f"visual_agent_{i}",
                "frames_analyzed": num_frames // 5,
                "features": [
                    {
                        "type": "Extrude",
                        "operation": "new_body",
                        "geometry": {
                            "type": "Circle",
                            "diameter": 90
                        },
                        "distance": 27,
                        "confidence": 0.92,
                        "reasoning": "Base cylinder clearly visible with diameter 90mm and height 27mm (mock data)"
                    },
                    {
                        "type": "Cut",
                        "operation": "remove",
                        "geometry": {
                            "type": "Rectangle",
                            "width": 27,
                            "height": 27
                        },
                        "distance": 6,
                        "position": "left_side",
                        "confidence": 0.88,
                        "reasoning": "Left chord cut detected. Flat-to-flat distance 78mm, depth=(90-78)/2=6mm (mock data)"
                    },
                    {
                        "type": "Cut",
                        "operation": "remove",
                        "geometry": {
                            "type": "Rectangle",
                            "width": 27,
                            "height": 27
                        },
                        "distance": 6,
                        "position": "right_side",
                        "confidence": 0.88,
                        "reasoning": "Right chord cut symmetric to left cut (mock data)"
                    }
                ],
                "overall_confidence": 0.89,
                "notes": "Mock result for automated testing: Cylinder 90mm x 27mm with bilateral chord cuts (78mm flat-to-flat)"
            })

        # Save mock results
        agent_results_path = self.session_dir / "agent_results.json"
        with open(agent_results_path, 'w', encoding='utf-8') as f:
            json.dump(mock_results, f, indent=2)

        print(f"  [OK] Mock results generated: {agent_results_path.name}")
        print(f"  [OK] Mock pattern: Cylinder 90mm x 27mm with chord cuts (78mm flat-to-flat)")
        print(f"  [OK] Format: Multi-feature (Extrude + 2 Cuts)")

        return str(agent_results_path.absolute())

    def phase_2_handoff_to_claude(self, extraction_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: HANDOFF TO CLAUDE - Prepare data for parallel agent analysis.

        This phase CANNOT be done in Python (requires Claude multimodal analysis).
        Saves necessary data and returns instructions for Claude.

        Args:
            extraction_results: Results from phase 1

        Returns:
            Dict with handoff instructions
        """
        print(f"\n[Phase 2] HANDOFF TO CLAUDE")
        print(f"  This phase requires Claude Task tool (multimodal frame analysis)")

        # Prepare handoff data
        handoff_data = {
            "frames_dir": str(self.frames_dir.absolute()),
            "frame_count": extraction_results["frames_extracted"],
            "frame_paths": extraction_results["frame_paths"],
            "transcription": extraction_results.get("transcription"),
            "num_agents": 5,
            "batch_size": extraction_results["frames_extracted"] // 5
        }

        # Save handoff data for Claude to read
        handoff_path = self.session_dir / "claude_handoff.json"
        with open(handoff_path, 'w', encoding='utf-8') as f:
            json.dump(handoff_data, f, indent=2, ensure_ascii=False)

        print(f"  [OK] Handoff data prepared: {handoff_path.name}")
        print(f"  [OK] Total frames: {handoff_data['frame_count']}")
        print(f"  [OK] Agents to dispatch: {handoff_data['num_agents']}")
        print(f"\n  [ACTION REQUIRED] Claude should now:")
        print(f"    1. Read: {handoff_path}")
        print(f"    2. Dispatch 5 Task agents in parallel using prompts/multi_feature_analysis.md")
        print(f"    3. Each agent analyzes ~{handoff_data['batch_size']} frames")
        print(f"    4. Collect agent outputs and call save_agent_results()")
        print(f"    5. Results will be saved to: {self.session_dir / 'agent_results.json'}")

        return {
            "handoff_path": str(handoff_path.absolute()),
            "status": "awaiting_claude_analysis",
            "expected_output": str((self.session_dir / "agent_results.json").absolute())
        }

    def save_agent_results(self, agent_outputs: List[str], output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Save agent analysis results to JSON file.

        This method should be called by Claude after dispatching agents.
        It collects the raw text outputs from agents and saves them as JSON.

        Args:
            agent_outputs: List of raw JSON strings returned by each agent
            output_path: Optional path to save (defaults to session_dir/agent_results.json)

        Returns:
            Path to saved agent_results.json

        Example:
            # After dispatching 5 agents
            agent_outputs = [
                agent1_output,  # Raw JSON string from Task tool
                agent2_output,
                agent3_output,
                agent4_output,
                agent5_output
            ]
            runner.save_agent_results(agent_outputs)
        """
        if output_path is None:
            output_path = self.session_dir / "agent_results.json"
        else:
            output_path = Path(output_path)

        # Parse JSON from each agent output
        agent_results = []
        for i, output in enumerate(agent_outputs):
            try:
                # Extract JSON from agent output (may contain extra text)
                # Look for JSON block in the output
                import re
                json_match = re.search(r'\{[\s\S]*\}', output)
                if json_match:
                    result = json.loads(json_match.group())
                    agent_results.append(result)
                else:
                    print(f"  [WARN] Agent {i+1} output does not contain valid JSON")
            except json.JSONDecodeError as e:
                print(f"  [ERROR] Failed to parse agent {i+1} output: {e}")
                continue

        # Save aggregated results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(agent_results, f, indent=2, ensure_ascii=False)

        print(f"  [OK] Saved {len(agent_results)} agent results to: {output_path.name}")

        return output_path.absolute()

    def _claude_pattern_recognition(
        self,
        agent_results: List[Dict],
        transcription: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Use Claude LLM to analyze patterns (Phase 3.5).

        Args:
            agent_results: Raw features from visual agents
            transcription: Audio transcription text

        Returns:
            Pattern analysis result or None if unavailable
        """
        try:
            from patterns import get_pattern_catalog
            from patterns.claude_analyzer import ClaudePatternAnalyzer

            print(f"  [Phase 3.5] Claude Pattern Analysis")

            # Get pattern catalog
            catalog = get_pattern_catalog()
            print(f"  [INFO] Analyzing against {len(catalog)} registered patterns")

            # Initialize analyzer
            analyzer = ClaudePatternAnalyzer()

            # Analyze
            result = analyzer.analyze(agent_results, transcription, catalog)

            if result and result.get("pattern_detected"):
                print(f"  [OK] Claude detected: {result['pattern_detected']}")
                print(f"       Confidence: {result.get('confidence', 0):.2f}")
            else:
                print(f"  [INFO] Claude requested fallback to Python rules")

            return result

        except ImportError as e:
            print(f"  [WARN] Claude analyzer not available (missing dependencies: {e})")
            return None
        except Exception as e:
            print(f"  [WARN] Claude pattern analysis error: {e}")
            return None

    def phase_3_aggregate(self, agent_results_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Phase 3: Aggregate agent results and build semantic JSON.

        NEW WORKFLOW:
        1. Request Claude Code analysis
        2. Execute generated Python code using PartBuilder
        3. Fallback to Python pattern detection if unavailable

        Args:
            agent_results_path: Path to agent_results.json from Claude

        Returns:
            Dict with aggregation results
        """
        print(f"\n[Phase 3] Aggregate Results")

        # Normalize path
        agent_results_path = Path(agent_results_path)

        if not agent_results_path.exists():
            raise FileNotFoundError(
                f"Agent results not found: {agent_results_path}\n"
                f"Did Claude complete Phase 2?"
            )

        # Load agent results
        with open(agent_results_path, 'r', encoding='utf-8') as f:
            agent_results = json.load(f)

        print(f"  [OK] Loaded agent results: {len(agent_results)} agents")

        # Load transcription for pattern detection
        transcription = None
        transcription_file = self.session_dir / "transcription.json"
        if transcription_file.exists():
            with open(transcription_file) as f:
                trans_data = json.load(f)
            transcription = trans_data.get("text", "")

        # ========================================
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

        if python_file:
            # Validate before executing
            print(f"\n  [VALIDATION] Checking generated code for correct imports...")
            try:
                if not self._validate_generated_code(python_file):
                    error_msg = (
                        f"\n{'='*70}\n"
                        f"  [BLOCKED] Generated code validation failed!\n"
                        f"{'='*70}\n\n"
                        f"  The generated Python file does not use the correct imports.\n"
                        f"  Execution has been blocked to prevent generating wrong JSON format.\n\n"
                        f"  [ACTION] Ask Claude Code to regenerate using semantic_builder\n"
                        f"  [FILE] {python_file}\n"
                        f"{'='*70}\n"
                    )
                    print(error_msg)
                    raise RuntimeError(error_msg)
            except ValidationError as e:
                # ValidationError means forbidden imports found - this is a hard failure
                raise RuntimeError(str(e))

            # Execute Claude Code's Python file
            print(f"\n  [OK] Validation passed - Executing Claude Code analysis...")
            try:
                result = subprocess.run(
                    [sys.executable, python_file.name],  # Use filename only since cwd is set
                    cwd=str(self.session_dir),
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    # Print Claude Code output
                    if result.stdout:
                        print(result.stdout)

                    # Verify semantic.json was created
                    semantic_path = self.session_dir / "semantic.json"
                    if semantic_path.exists():
                        print(f"  [OK] Claude Code generated semantic.json successfully")

                        # Load semantic JSON to extract metadata for return value
                        with open(semantic_path, 'r', encoding='utf-8') as f:
                            semantic_data = json.load(f)

                        part_name = semantic_data.get("part", {}).get("name", "unknown")

                        return {
                            "semantic_json_path": str(semantic_path),
                            "part_name": part_name,
                            "confidence": 0.95,  # High confidence from Claude Code analysis
                            "source": "claude_code_partbuilder"
                        }
                    else:
                        raise RuntimeError(
                            f"Claude Code execution succeeded but semantic.json not found!\n"
                            f"Expected: {semantic_path}\n"
                            f"Please check the generated Python code."
                        )
                else:
                    raise RuntimeError(
                        f"Claude Code Python execution failed!\n"
                        f"Error output:\n{result.stderr}\n"
                        f"Please fix the generated Python code and try again."
                    )

            except subprocess.TimeoutExpired:
                raise RuntimeError(
                    f"Claude Code execution timeout (30s)!\n"
                    f"The generated Python code is taking too long.\n"
                    f"Please check: {python_file}"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Error executing Claude Code: {e}\n"
                    f"Please check the generated Python code."
                )
        else:
            # Claude Code hasn't written the Python file yet
            raise RuntimeError(
                f"\n{'='*70}\n"
                f"  [BLOCKED] Waiting for Claude Code to write analysis!\n"
                f"{'='*70}\n\n"
                f"  Claude Code must write: {self.session_dir / 'claude_analysis.py'}\n\n"
                f"  Instructions:\n"
                f"  1. Read the analysis request:\n"
                f"     {self.session_dir / '.claude_analysis_request.json'}\n\n"
                f"  2. Analyze agent results + transcription\n\n"
                f"  3. Write Python code using PartBuilder to:\n"
                f"     {self.session_dir / 'claude_analysis.py'}\n\n"
                f"  4. Re-run the aggregation phase\n\n"
                f"{'='*70}\n"
                f"  NO FALLBACK: Claude Code + PartBuilder is REQUIRED!\n"
                f"{'='*70}\n"
            )

    def _fallback_aggregation(
        self,
        agent_results: List[Dict],
        transcription: Optional[str]
    ) -> Dict[str, Any]:
        """
        Fallback to Python pattern detection if Claude Code unavailable.

        This is the original aggregator logic (backward compatibility).

        Args:
            agent_results: Raw agent results
            transcription: Audio transcription text

        Returns:
            Dict with aggregation results
        """
        print(f"\n  [Fallback] Using Python pattern detection")

        # Check for new multi-feature format or legacy single-geometry format
        has_multi_feature_format = any("features" in result for result in agent_results)

        # ========================================
        # PATTERN DETECTION using Hybrid System
        # ========================================
        # Layer 1: Claude LLM analysis (contextual understanding)
        # Layer 2: Python Registry (fallback rules)
        from patterns import get_registered_patterns

        # Python pattern detection (no Claude LLM calls in fallback)
        detected_pattern = None
        pattern_match = None

        if True:  # Always use Python patterns in fallback
            print(f"  [INFO] Using Python pattern detection (Claude fallback or unavailable)")
            for pattern in get_registered_patterns():
                match = pattern.detect(agent_results, transcription)
                if match:
                    detected_pattern = pattern
                    pattern_match = match
                    print(f"  [OK] Pattern detected by Python: {match.pattern_name}")
                    print(f"       Source: {match.source}")
                    print(f"       Parameters: {match.parameters}")
                    print(f"       Confidence: {match.confidence:.2f}")
                    break  # Use first match (highest priority)

        # Legacy compatibility: Store chord_cut info in old format for now
        # TODO: Remove this once all references to chord_cut_info are migrated
        chord_cut_info = None
        if pattern_match and pattern_match.pattern_name == "chord_cut":
            chord_cut_info = {
                "flat_to_flat": pattern_match.parameters.get("flat_to_flat"),
                "confidence": pattern_match.confidence,
                "detected": True,
                "source": pattern_match.source
            }

        if has_multi_feature_format:
            # NEW FORMAT: Each agent returns list of features
            print(f"  [OK] Multi-feature format detected")
            all_features = []
            all_confidences = []

            for result in agent_results:
                if "features" in result:
                    all_features.extend(result["features"])
                    # Use overall confidence or average of feature confidences
                    result_confidence = result.get("overall_confidence") or result.get("confidence", 0.0)
                    all_confidences.append(result_confidence)

            if not all_features:
                raise ValueError(
                    f"[ERROR] No features found in agent results!\n"
                    f"  Phase 2 (Claude visual analysis) may have failed.\n"
                    f"  File: {agent_results_path}"
                )

            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            if avg_confidence < 0.1:
                raise ValueError(
                    f"[ERROR] Visual confidence too low ({avg_confidence:.2f})!\n"
                    f"  Expected: 0.7-0.95, Actual: {avg_confidence:.2f}"
                )

            # Filter features using pattern registry
            if detected_pattern and pattern_match:
                original_count = len(all_features)
                all_features = detected_pattern.filter_features(all_features, pattern_match)
                removed_count = original_count - len(all_features)
                if removed_count > 0:
                    print(f"  [OK] Pattern '{pattern_match.pattern_name}' filtered out {removed_count} conflicting features")

            print(f"  [OK] Total features detected: {len(all_features)}")
            print(f"  [OK] Average confidence: {avg_confidence:.2f}")

        else:
            # LEGACY FORMAT: Single geometry per agent (backward compatibility)
            print(f"  [OK] Legacy single-geometry format detected")
            geometries = []
            confidences = []

            for result in agent_results:
                if "geometry" in result:
                    geometries.append(result["geometry"])
                    confidences.append(result.get("confidence", 0.0))

            if not geometries:
                raise ValueError(
                    f"[ERROR] No geometry data found in agent results!\n"
                    f"  Phase 2 (Claude visual analysis) may have failed.\n"
                    f"  File: {agent_results_path}\n"
                    f"  Agent count: {len(agent_results)}"
                )

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            if avg_confidence < 0.1:
                raise ValueError(
                    f"[ERROR] Visual confidence too low ({avg_confidence:.2f})!\n"
                    f"  This indicates Claude agents did not analyze frames visually.\n"
                    f"  Expected confidence: 0.7-0.95\n"
                    f"  Actual confidence: {avg_confidence:.2f}\n"
                    f"  Cannot proceed with unreliable data."
                )

        # Import semantic-geometry builder
        sys.path.insert(0, str(Path.home() / "semantic-geometry"))
        from semantic_geometry.builder import PartBuilder
        from semantic_geometry.primitives import Rectangle, Circle

        # Process features based on format
        if has_multi_feature_format:
            # NEW FORMAT: Process multiple features (extrudes + cuts)
            aggregated_features = self._aggregate_multi_features(all_features)
            part_name = self._generate_part_name_from_features(aggregated_features)

            print(f"  Building semantic JSON with {len(aggregated_features)} features...")
            builder = PartBuilder(name=part_name)

            # Build each feature
            for i, feature in enumerate(aggregated_features):
                feature_type = feature.get("type")
                geometry_data = feature.get("geometry", {})
                operation = feature.get("operation", "new_body")
                distance = feature.get("distance", 0)
                constraints = feature.get("constraints", [])

                # Check if multi-geometry (list) or single geometry (dict)
                if isinstance(geometry_data, list):
                    # NEW FORMAT: Multi-geometry sketch (Arc + Line array)
                    print(f"  [OK] Multi-geometry sketch detected: {len(geometry_data)} geometries")

                    # Build semantic JSON structure directly (bypass PartBuilder primitives)
                    # PartBuilder doesn't have Arc/Line primitives, so we use raw dict format
                    sketch = {
                        "plane": {"type": "work_plane"},
                        "geometry": geometry_data  # Pass through as-is (Arc + Line dicts)
                    }

                    # Add constraints if present
                    if constraints:
                        sketch["constraints"] = constraints
                        print(f"  [OK] Preserved {len(constraints)} constraints")

                    # Build feature dict manually (PartBuilder format)
                    feature_dict = {
                        "id": f"{feature_type.lower()}_{i}",
                        "type": feature_type,
                        "sketch": sketch,
                        "parameters": {
                            "distance": {"value": distance, "unit": "mm"},
                            "direction": "normal",
                            "operation": operation if feature_type == "Extrude" else None
                        }
                    }

                    # Remove None values
                    if feature_dict["parameters"]["operation"] is None:
                        del feature_dict["parameters"]["operation"]

                    # Add to builder's internal feature list
                    builder.features.append(feature_dict)

                    geom_types = [g.get("type") for g in geometry_data]
                    print(f"  [OK] Added {feature_type}: {', '.join(geom_types)} {distance}mm ({operation})")

                    # Validate chord cut pattern if detected (pattern-specific validation)
                    if pattern_match and pattern_match.pattern_name == "chord_cut" and len(geometry_data) == 4:
                        arc_count = sum(1 for g in geometry_data if g.get("type") == "Arc")
                        line_count = sum(1 for g in geometry_data if g.get("type") == "Line")

                        if arc_count == 2 and line_count == 2:
                            print(f"  [OK] Chord cut geometry validated: 2 Arcs + 2 Lines")

                            # Check for required constraints
                            constraint_types = [c.get("type") for c in constraints]
                            required = ["Coincident", "Parallel", "Horizontal", "Distance"]
                            missing = [r for r in required if r not in constraint_types]

                            if missing:
                                print(f"  [WARN] Chord cut missing constraints: {', '.join(missing)}")
                            else:
                                print(f"  [OK] Chord cut constraints complete: {len(constraints)} constraints")
                        else:
                            print(f"  [WARN] Chord cut pattern incomplete: {arc_count} Arcs, {line_count} Lines (expected 2+2)")
                    elif pattern_match and pattern_match.pattern_name == "chord_cut" and len(geometry_data) != 4:
                        print(f"  [WARN] Chord cut detected but geometry count = {len(geometry_data)} (expected 4)")

                elif chord_cut_info and isinstance(geometry_data, dict) and geometry_data.get("type") == "Circle":
                    # PATTERN-BASED GEOMETRY REPLACEMENT
                    # Pattern detected by registry, geometry generated via helper
                    print(f"  [OK] Chord cut pattern - replacing Circle with Arc + Line geometry")

                    # Extract radius from Circle
                    diameter = geometry_data.get("diameter", 0)
                    radius = diameter / 2 if diameter else 0
                    flat_to_flat = chord_cut_info.get("flat_to_flat", 0)

                    # Calculate Arc + Line geometry using helper function
                    chord_geometry = calculate_chord_cut_geometry(
                        radius=radius,
                        flat_to_flat=flat_to_flat
                    )

                    # Build sketch with multi-geometry
                    sketch = {
                        "plane": {"type": "work_plane"},
                        "geometry": chord_geometry["geometry"]  # 2 Arcs + 2 Lines
                    }

                    # Add constraints
                    sketch["constraints"] = chord_geometry["constraints"]  # 7 constraints
                    print(f"  [OK] Chord cut geometry: {len(chord_geometry['geometry'])} geometries, {len(chord_geometry['constraints'])} constraints")

                    # Build feature dict manually (PartBuilder format)
                    feature_dict = {
                        "id": f"{feature_type.lower()}_{i}",
                        "type": feature_type,
                        "sketch": sketch,
                        "parameters": {
                            "distance": {"value": distance, "unit": "mm"},
                            "direction": "normal",
                            "operation": operation if feature_type == "Extrude" else None
                        }
                    }

                    # Remove None values
                    if feature_dict["parameters"]["operation"] is None:
                        del feature_dict["parameters"]["operation"]

                    # Add to builder's internal feature list
                    builder.features.append(feature_dict)

                    geom_types = [g.get("type") for g in chord_geometry["geometry"]]
                    print(f"  [OK] Added {feature_type}: {', '.join(geom_types)} {distance}mm ({operation})")

                else:
                    # LEGACY FORMAT: Single geometry (Circle or Rectangle)
                    geom_type = geometry_data.get("type")

                    if geom_type == "Circle":
                        geometry = Circle(
                            center=(0, 0),
                            diameter=geometry_data.get("diameter", 50)
                        )
                    elif geom_type == "Rectangle":
                        geometry = Rectangle(
                            center=(0, 0),
                            width=geometry_data.get("width", 100),
                            height=geometry_data.get("height", 100)
                        )
                    else:
                        print(f"  [WARN] Unknown geometry type: {geom_type}, skipping feature {i}")
                        continue

                    # Add feature to builder (uses PartBuilder methods)
                    if feature_type == "Extrude":
                        builder.add_extrude(
                            id=f"extrude_{i}",
                            plane_type="work_plane",
                            geometry=[geometry],
                            distance=distance,
                            operation=operation
                        )
                        print(f"  [OK] Added Extrude: {geom_type} {distance}mm ({operation})")

                    elif feature_type == "Cut":
                        builder.add_cut(
                            id=f"cut_{i}",
                            plane_type="work_plane",
                            geometry=[geometry],
                            distance=distance,
                            cut_type="distance"
                        )
                        print(f"  [OK] Added Cut: {geom_type} {distance}mm depth")

        else:
            # LEGACY FORMAT: Single geometry (backward compatibility)
            geometry_types = [g.get("type") for g in geometries if "type" in g]
            most_common_type = max(set(geometry_types), key=geometry_types.count) if geometry_types else "Rectangle"

            # Average dimensions
            avg_dimensions = {}
            for geom in geometries:
                if "dimensions" in geom:
                    for key, value in geom["dimensions"].items():
                        if key not in avg_dimensions:
                            avg_dimensions[key] = []
                        avg_dimensions[key].append(value)

            for key in avg_dimensions:
                avg_dimensions[key] = sum(avg_dimensions[key]) / len(avg_dimensions[key])

            print(f"  [OK] Geometry detected: {most_common_type}")
            print(f"  [OK] Dimensions: {avg_dimensions}")

            part_name = f"chapa_{most_common_type.lower()}_{int(avg_dimensions.get('width', 0))}x{int(avg_dimensions.get('height', 0))}x{int(avg_dimensions.get('thickness', 0))}"
            builder = PartBuilder(name=part_name)

            # Add single feature
            if most_common_type == "Rectangle":
                rect = Rectangle(
                    center=(0, 0),
                    width=avg_dimensions.get("width", 100),
                    height=avg_dimensions.get("height", 100)
                )
                builder.add_extrude(
                    id="extrude_base",
                    plane_type="work_plane",
                    geometry=[rect],
                    distance=avg_dimensions.get("thickness", 5),
                    operation="new_body"
                )
            elif most_common_type == "Circle":
                circle = Circle(
                    center=(0, 0),
                    diameter=avg_dimensions.get("diameter", 50)
                )
                builder.add_extrude(
                    id="extrude_base",
                    plane_type="work_plane",
                    geometry=[circle],
                    distance=avg_dimensions.get("length", 100),
                    operation="new_body"
                )

        print(f"  [OK] Average confidence: {avg_confidence:.2f}")

        # Add metadata
        audio_transcription = self.results.get("audio_transcription") or {}
        builder.metadata.update({
            "video_file": str(self.video_path),
            "frames_analyzed": self.results["frames_extracted"],
            "visual_confidence": avg_confidence,
            "audio_transcription": audio_transcription.get("text", ""),
            "created_with": "recad_runner.py"
        })

        # Save semantic JSON
        semantic_json_path = self.session_dir / "semantic.json"
        part_json = builder.build()

        with open(semantic_json_path, 'w', encoding='utf-8') as f:
            json.dump(part_json, f, indent=2, ensure_ascii=False)

        self.results["semantic_json_path"] = semantic_json_path

        print(f"  [OK] Semantic JSON saved: {semantic_json_path.name}")
        print(f"  [OK] Part name: {part_name}")

        # Verify "parameters" wrapper is present
        first_feature = part_json["part"]["features"][0]
        if "parameters" in first_feature:
            print(f"  [OK] Parameters wrapper present (format correct!)")
        else:
            print(f"  [WARN] Parameters wrapper missing (may cause dimension errors)")

        # Return results (compatible with both formats)
        result = {
            "semantic_json_path": str(semantic_json_path),
            "part_name": part_name,
            "confidence": avg_confidence
        }

        # Add format-specific fields
        if has_multi_feature_format:
            result["geometry_type"] = "multi_feature"
            result["features_count"] = len(aggregated_features)
            result["dimensions"] = {}  # Multiple features, no single dimension
        else:
            result["geometry_type"] = most_common_type
            result["dimensions"] = avg_dimensions

        # Add pattern detection information to result
        if pattern_match:
            result[f"{pattern_match.pattern_name}_detected"] = True
            # Add pattern-specific parameters
            for key, value in pattern_match.parameters.items():
                result[key] = value

        return result

    def phase_4_5_handoff_to_freecad(self, semantic_json_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Phase 4-5: HANDOFF TO FREECAD - CAD export and validation.

        This phase CANNOT be done in standard Python (requires FreeCAD environment).
        Returns instructions for freecadcmd execution.

        Args:
            semantic_json_path: Path to semantic.json

        Returns:
            Dict with handoff instructions
        """
        print(f"\n[Phase 4-5] HANDOFF TO FREECAD")
        print(f"  This phase requires freecadcmd.exe (FreeCAD Python environment)")

        # Normalize path
        semantic_json_path = Path(semantic_json_path)

        # Prepare CAD output path
        cad_output_path = self.session_dir / f"{semantic_json_path.stem}.FCStd"

        # Prepare handoff instructions
        handoff_instructions = {
            "semantic_json": str(semantic_json_path.absolute()),
            "cad_output": str(cad_output_path.absolute()),
            "freecadcmd_path": "C:/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecadcmd.exe"
        }

        # Save handoff data
        handoff_path = self.session_dir / "freecad_handoff.json"
        with open(handoff_path, 'w', encoding='utf-8') as f:
            json.dump(handoff_instructions, f, indent=2)

        print(f"  [OK] Handoff data prepared: {handoff_path.name}")
        print(f"\n  [ACTION REQUIRED] Execute freecadcmd with:")
        print(f"    Input: {semantic_json_path.name}")
        print(f"    Output: {cad_output_path.name}")
        print(f"\n  Example command:")
        print(f"    freecadcmd -c \"")
        print(f"      import sys")
        print(f"      sys.path.insert(0, 'C:/Users/conta/semantic-geometry')")
        print(f"      from semantic_geometry.freecad_export import convert_to_freecad")
        print(f"      # Load semantic.json and convert")
        print(f"    \"")

        return {
            "handoff_path": str(handoff_path.absolute()),
            "status": "awaiting_freecad_export",
            "expected_output": str(cad_output_path.absolute())
        }

    def phase_6_report(self, aggregate_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 6: Generate final summary report.

        Args:
            aggregate_results: Results from phase 3

        Returns:
            Dict with summary
        """
        print(f"\n[Phase 6] Generate Report")

        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.metadata["timestamp"])
        processing_time = (end_time - start_time).total_seconds()

        summary = {
            "session_id": self.session_id,
            "status": "success",
            "processing_time_seconds": processing_time,
            "video": {
                "path": str(self.video_path),
                "size_mb": self.metadata["video_size_mb"],
                "frames_analyzed": self.results["frames_extracted"]
            },
            "part": {
                "name": aggregate_results.get("part_name"),
                "geometry_type": aggregate_results.get("geometry_type"),
                "dimensions": aggregate_results.get("dimensions"),
                "confidence": aggregate_results.get("confidence")
            },
            "outputs": {
                "semantic_json": aggregate_results.get("semantic_json_path"),
                "session_dir": str(self.session_dir)
            }
        }

        summary_path = self.session_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"  [OK] Summary saved: {summary_path.name}")
        print(f"\n" + "=" * 60)
        print(f"ReCAD Runner - Phases 0, 1, 3, 6 Complete!")
        print(f"=" * 60)
        print(f"\nSession: {self.session_dir}")
        print(f"Processing time: {processing_time:.1f}s")
        print(f"\nPart Details:")
        print(f"  Name: {aggregate_results.get('part_name')}")
        print(f"  Type: {aggregate_results.get('geometry_type')}")
        print(f"  Confidence: {aggregate_results.get('confidence', 0):.2f}")
        print(f"\nNext Steps:")
        print(f"  1. Claude: Complete Phase 2 (agent analysis)")
        print(f"  2. FreeCAD: Complete Phase 4-5 (CAD export + validation)")
        print(f"=" * 60)

        return summary

    def _aggregate_multi_features(self, all_features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate features from multiple agents, preserving distinct features.

        POLICY 3.3 (SRP): This method aggregates features.
        POLICY 13.2 (Fallback): Returns individual features if clustering fails.
        POLICY 3.6 (Error Handling): Explicit error messages for failures.

        Args:
            all_features: List of all features detected by all agents

        Returns:
            List of aggregated features (preserves multiple cuts/extrudes)
        """
        try:
            # Policy 3.3: Extract clustering logic to separate method
            feature_clusters = self._cluster_similar_features(all_features)

            # Average dimensions within each cluster
            aggregated = []
            for cluster in feature_clusters:
                geometries = [f.get("geometry", {}) for f in cluster]
                distances = [f.get("distance", 0) for f in cluster if "distance" in f]
                constraints = [f.get("constraints", []) for f in cluster]

                # Check if multi-geometry (list)
                if geometries and isinstance(geometries[0], list):
                    # Multi-geometry sketch: Preserve as-is (no averaging makes sense)
                    # Use first agent's geometry (assume agents agree on multi-geometry)
                    avg_geometry = geometries[0]
                    avg_constraints = constraints[0] if constraints else []
                else:
                    # Single geometry: Average dimensions across agents
                    avg_geometry = self._average_geometry_dimensions(geometries)
                    avg_constraints = []

                avg_distance = sum(distances) / len(distances) if distances else 0

                aggregated_feature = {
                    "type": cluster[0].get("type"),
                    "operation": cluster[0].get("operation", "new_body"),
                    "geometry": avg_geometry,
                    "constraints": avg_constraints,
                    "distance": round(avg_distance, 1),
                    "confidence": sum(f.get("confidence", 0) for f in cluster) / len(cluster),
                    "count": len(cluster)
                }

                aggregated.append(aggregated_feature)

            # Sort: Extrudes first (additive), then Cuts (subtractive)
            aggregated.sort(key=lambda f: (f["type"] != "Extrude", f["type"]))

            return aggregated

        except Exception as e:
            # Policy 13.2 (Fallback): Return individual features on failure
            # Policy 3.6 (Error Handling): Log error with context
            print(f"  [WARNING] Feature clustering failed: {e}")
            print(f"  [FALLBACK] Returning {len(all_features)} individual features")
            return all_features

    def _average_geometry_dimensions(self, geometries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average dimensions across multiple geometry detections."""
        if not geometries:
            return {}

        # Determine geometry type (most common)
        geom_types = [g.get("type") for g in geometries if "type" in g]
        if not geom_types:
            return {}

        most_common_type = max(set(geom_types), key=geom_types.count)

        # Collect all dimension values
        dimension_values = {}
        for geom in geometries:
            if geom.get("type") == most_common_type:
                for key, value in geom.items():
                    if key != "type" and isinstance(value, (int, float)):
                        if key not in dimension_values:
                            dimension_values[key] = []
                        dimension_values[key].append(value)

        # Average each dimension
        avg_geometry = {"type": most_common_type}
        for key, values in dimension_values.items():
            avg_geometry[key] = round(sum(values) / len(values), 1)

        return avg_geometry

    def _cluster_similar_features(self, all_features: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Cluster features by type + operation, but detect DISTINCT features.

        POLICY 3.3 (SRP): Dedicated method for clustering logic.
        POLICY 3.6 (Error Handling): Validates inputs.

        Strategy:
        - Extrudes: Should be 1 cluster (base geometry)
        - Cuts: Count how many DISTINCT cuts agents detected
          - If 3 agents report 2 cuts each => 2 cuts total (not 1 averaged cut)
          - If 2 agents report 1 cut, 3 report 2 cuts => 2 cuts (consensus)

        Args:
            all_features: All features from all agents

        Returns:
            List of clusters (each cluster = list of similar features)
        """
        # Policy 3.6: Validate inputs
        if not all_features:
            print("  [WARNING] _cluster_similar_features: No features to cluster")
            return []

        # Separate by type first
        extrudes = [f for f in all_features if f.get("type") == "Extrude"]
        cuts = [f for f in all_features if f.get("type") == "Cut"]

        clusters = []

        # Cluster extrudes (typically 1 base body)
        if extrudes:
            # Group by operation
            by_operation = {}
            for e in extrudes:
                op = e.get("operation", "new_body")
                if op not in by_operation:
                    by_operation[op] = []
                by_operation[op].append(e)

            # Each operation type = 1 cluster
            for op_features in by_operation.values():
                clusters.append(op_features)

        # Cluster cuts - detect DISTINCT cuts from agent consensus
        if cuts:
            # Count how many cuts each agent reported
            cuts_per_agent = {}
            for cut in cuts:
                agent_id = cut.get("agent_id", "unknown")
                if agent_id not in cuts_per_agent:
                    cuts_per_agent[agent_id] = []
                cuts_per_agent[agent_id].append(cut)

            # Consensus: How many distinct cuts?
            cuts_counts = [len(cuts) for cuts in cuts_per_agent.values()]
            if cuts_counts:
                # Use median count (robust to outliers)
                cuts_counts.sort()
                median_cuts = cuts_counts[len(cuts_counts) // 2]

                print(f"  [CLUSTERING] Agents reported cuts: {cuts_counts} -> Consensus: {median_cuts} distinct cuts")

                # Divide all cuts into N clusters (N = median_cuts)
                cuts_per_cluster = max(1, len(cuts) // median_cuts)

                for i in range(median_cuts):
                    cluster_cuts = cuts[i * cuts_per_cluster:(i + 1) * cuts_per_cluster]
                    if cluster_cuts:
                        clusters.append(cluster_cuts)

        print(f"  [CLUSTERING] Created {len(clusters)} feature clusters from {len(all_features)} total features")

        return clusters

    def _generate_part_name_from_features(self, features: List[Dict[str, Any]]) -> str:
        """Generate descriptive part name from features."""
        # Find base extrude
        base_extrudes = [f for f in features if f.get("type") == "Extrude" and f.get("operation") == "new_body"]
        if not base_extrudes:
            return "part_unknown"

        base = base_extrudes[0]
        geom = base.get("geometry", {})

        # Check if multi-geometry (list)
        if isinstance(geom, list):
            # Multi-geometry sketch (Arc + Line, etc.)
            geom_types = [g.get("type", "unknown") for g in geom]
            arc_count = geom_types.count("Arc")
            line_count = geom_types.count("Line")

            distance = int(base.get("distance", 0))

            if arc_count == 2 and line_count == 2:
                # Chord cut pattern
                name = f"chord_cut_{distance}mm"
            else:
                # Generic multi-geometry
                type_str = "_".join(sorted(set(geom_types)))
                name = f"profile_{type_str}_{distance}mm"
        else:
            # Single geometry
            geom_type = geom.get("type", "unknown").lower()

            # Build name based on geometry
            if geom_type == "circle":
                diameter = int(geom.get("diameter", 0))
                height = int(base.get("distance", 0))
                name = f"cylinder_{diameter}x{height}"
            elif geom_type == "rectangle":
                width = int(geom.get("width", 0))
                height = int(geom.get("height", 0))
                depth = int(base.get("distance", 0))
                name = f"block_{width}x{height}x{depth}"
            else:
                name = f"{geom_type}_part"

        # Add suffix for cuts
        num_cuts = sum(1 for f in features if f.get("type") == "Cut")
        if num_cuts > 0:
            name += f"_with_{num_cuts}cuts"

        return name


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="ReCAD Runner - Consolidated Python Workflow")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("--output-dir", help="Output directory (default: from config.py)")
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS, help=f"Frames per second (default: {DEFAULT_FPS})")
    parser.add_argument("--session-id", help="Session ID to reuse existing session (auto-detected from --agent-results)")
    parser.add_argument("--agent-results", help="Path to agent_results.json (if Phase 2 already complete)")
    parser.add_argument("--test", action="store_true", help="Test mode: Generate mock agent results (bypasses Claude)")

    args = parser.parse_args()

    try:
        # Auto-detect session ID from agent-results path if not provided
        session_id = args.session_id
        if args.agent_results and not session_id:
            # Extract session ID from agent_results path
            # Example: "docs/outputs/recad/2025-11-06_192547/agent_results.json" -> "2025-11-06_192547"
            agent_results_path = Path(args.agent_results)
            if agent_results_path.exists():
                # Get parent directory name (should be session ID)
                session_id = agent_results_path.parent.name
                print(f"\n[AUTO-DETECT] Reusing session: {session_id}")

        # Initialize runner
        runner = ReCADRunner(
            video_path=args.video_path,
            output_dir=args.output_dir,
            fps=args.fps,
            session_id=session_id
        )

        # Phase 0: Setup (or skip if reusing session)
        if not session_id:
            runner.phase_0_setup()
        else:
            print("=" * 60)
            print("ReCAD Runner - Consolidated Workflow")
            print("=" * 60)
            print(f"\n[Phase 0] REUSING existing session")
            print(f"  Session ID: {runner.session_id}")
            print(f"  Session Dir: {runner.session_dir}")

        # Phase 1: Extract (or skip if reusing session)
        if not session_id:
            extraction_results = runner.phase_1_extract()
        else:
            print(f"\n[Phase 1] SKIPPED (session already has frames/audio)")
            extraction_results = None

        # Phase 2: Handoff to Claude (or skip if agent results provided, or use test mode)
        if args.agent_results:
            print(f"\n[Phase 2] SKIPPED (using provided agent results)")
            agent_results_path = args.agent_results
        elif args.test:
            # Test mode: Generate mock results automatically
            agent_results_path = runner.phase_2_generate_mock_results(extraction_results)
            print(f"  [TEST MODE] Continuing automatically with mock results...")
        else:
            handoff_results = runner.phase_2_handoff_to_claude(extraction_results)
            print(f"\n[PAUSED] Waiting for Claude to complete Phase 2...")
            print(f"Expected output: {handoff_results['expected_output']}")
            print(f"\nTo continue after Claude completes Phase 2, run:")
            print(f"  python {__file__} {args.video_path} --agent-results <path_to_agent_results.json>")
            print(f"\nOr run in test mode:")
            print(f"  python {__file__} {args.video_path} --test")
            return

        # Phase 3: Aggregate
        aggregate_results = runner.phase_3_aggregate(agent_results_path)

        # Phase 4-5: Handoff to FreeCAD
        runner.phase_4_5_handoff_to_freecad(aggregate_results["semantic_json_path"])

        # Phase 6: Report
        runner.phase_6_report(aggregate_results)

        print(f"\n[OK] Runner complete! Session: {runner.session_id}")

    except Exception as e:
        print(f"\n[ERROR] Runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

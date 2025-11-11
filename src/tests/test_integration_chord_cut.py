import pytest
import json
from pathlib import Path
from recad_runner import ReCADRunner

@pytest.mark.integration
def test_full_pipeline_chord_cut_video():
    """Integration test: Full pipeline with real chord cut video"""
    # ARRANGE
    video_path = Path("C:/Users/conta/Downloads/WhatsApp Video 2025-11-06 at 16.36.07.mp4")

    if not video_path.exists():
        pytest.skip("Test video not found")

    # ACT: Run extraction phases
    runner = ReCADRunner(str(video_path))

    # Phase 0: Setup
    setup_result = runner.phase_0_setup()
    assert setup_result["session_id"] is not None

    # Phase 1: Extract frames and audio
    extraction_result = runner.phase_1_extract()
    assert extraction_result["frames_extracted"] > 0

    # Check if transcription contains dimensional info
    transcription = runner.results.get("audio_transcription", {})
    if transcription:
        text = transcription.get("text", "")
        # Check for dimension mentions (90mm diameter, 78mm flat-to-flat, or 45mm radius)
        has_dimensions = "90" in text or "45" in text or "78" in text
        if has_dimensions:
            print(f"  [OK] Transcription contains dimensions: {text[:100]}...")

    # Phase 3: Aggregate with mock agent results (since real agents not run yet)
    # Create mock agent results that simulate chord cut detection
    agent_results = [{
        "features": [{
            "type": "Extrude",
            "geometry": {
                "type": "Circle",
                "diameter": 90.0
            },
            "distance": 5.0,
            "operation": "new_body"
        }],
        "additional_features": [{
            "pattern": "chord_cut",
            "flat_to_flat": 78.0,
            "confidence": 0.90
        }],
        "overall_confidence": 0.95
    }]

    # Save mock agent results
    agent_results_path = runner.session_dir / "agent_results.json"
    with open(agent_results_path, 'w') as f:
        json.dump(agent_results, f, indent=2)

    # Run aggregator
    result = runner.phase_3_aggregate(agent_results_path)

    # ASSERT: Verify chord cut was detected and applied
    assert result.get("chord_cut_detected") is True, "Chord cut should be detected"

    semantic_json_path = result.get("semantic_json_path")
    assert semantic_json_path is not None, "semantic.json should be created"

    with open(semantic_json_path) as f:
        semantic = json.load(f)

    # Verify multi-geometry (Arc + Line)
    geometry = semantic["part"]["features"][0]["sketch"]["geometry"]
    assert isinstance(geometry, list), "Geometry should be list (multi-geometry)"
    assert len(geometry) == 4, f"Should have 4 geometries (2 Arc + 2 Line), got {len(geometry)}"

    # Verify geometry types
    assert geometry[0]["type"] == "Arc", "First geometry should be Arc"
    assert geometry[1]["type"] == "Line", "Second geometry should be Line"
    assert geometry[2]["type"] == "Arc", "Third geometry should be Arc"
    assert geometry[3]["type"] == "Line", "Fourth geometry should be Line"

    # Verify constraints
    constraints = semantic["part"]["features"][0]["sketch"].get("constraints", [])
    assert len(constraints) == 7, f"Should have 7 constraints, got {len(constraints)}"

    # Verify thickness
    distance = semantic["part"]["features"][0]["parameters"]["distance"]["value"]
    assert 4.0 <= distance <= 6.0, f"Thickness should be 4-6mm, got {distance}mm"

    print(f"[OK] Integration test passed!")
    print(f"   Video: {video_path.name}")
    print(f"   Session: {runner.session_id}")
    print(f"   Frames extracted: {extraction_result['frames_extracted']}")
    print(f"   Geometry: {len(geometry)} items (Arc + Line)")
    print(f"   Constraints: {len(constraints)} items")
    print(f"   Thickness: {distance}mm")
    print(f"   semantic.json: {semantic_json_path}")

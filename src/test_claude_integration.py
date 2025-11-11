#!/usr/bin/env python3
"""
Quick test to verify Claude pattern detector integration.
"""
import json
from pathlib import Path
from patterns.claude_analyzer import ClaudePatternAnalyzer
from patterns import get_pattern_catalog

# Load agent results from recent session
session_dir = Path("docs/outputs/recad/2025-11-06_215239")
agent_results_path = session_dir / "agent_results.json"
transcription_path = session_dir / "transcription.json"

print("=" * 60)
print("Testing Claude Pattern Detector Integration")
print("=" * 60)

# Load data
with open(agent_results_path) as f:
    agent_results = json.load(f)

with open(transcription_path) as f:
    transcription_data = json.load(f)
    transcription = transcription_data.get("text", "")

print(f"\n[INFO] Loaded {len(agent_results)} agent results")
print(f"[INFO] Transcription: {transcription[:80]}...")

# Get pattern catalog
catalog = get_pattern_catalog()
print(f"\n[INFO] Pattern catalog has {len(catalog)} patterns:")
for p in catalog:
    print(f"  - {p['name']} (priority: {p['priority']})")

# Initialize Claude analyzer
print("\n[INFO] Initializing ClaudePatternAnalyzer...")
analyzer = ClaudePatternAnalyzer()

if analyzer.use_claude_code:
    print("[OK] Using Claude Code direct analysis (no API key needed)")
elif not analyzer.client:
    print("[WARN] No Anthropic API key found - Claude will fallback to Python")
    print("       Set ANTHROPIC_API_KEY environment variable to test Claude")
else:
    print("[OK] Claude API client initialized")

# Analyze
print("\n[Phase 3.5] Running Claude pattern analysis...")
result = analyzer.analyze(agent_results, transcription, catalog)

print("\n" + "=" * 60)
print("Results:")
print("=" * 60)
print(json.dumps(result, indent=2))

if result.get("fallback_to_python"):
    print("\n[INFO] Claude requested fallback to Python")
elif result.get("pattern_detected"):
    print(f"\n[OK] Claude detected pattern: {result['pattern_detected']}")
    print(f"     Confidence: {result.get('confidence', 0):.2f}")
    print(f"     Reasoning: {result.get('reasoning', 'N/A')[:100]}...")
else:
    print("\n[INFO] No pattern detected by Claude")

print("\n" + "=" * 60)

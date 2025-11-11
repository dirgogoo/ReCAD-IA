"""
Base classes for ReCAD geometric pattern detection system.

This module defines the abstract interface that all pattern detectors must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """
    Result of pattern detection.

    Attributes:
        pattern_name: Unique identifier for the pattern (e.g., "chord_cut")
        confidence: Detection confidence score (0.0-1.0)
        parameters: Pattern-specific parameters extracted from detection
        source: Where the pattern was detected from (e.g., "bilateral_cut_operation", "audio_transcript")
    """
    pattern_name: str
    confidence: float
    parameters: Dict[str, Any]
    source: str


class GeometricPattern(ABC):
    """
    Abstract base class for all geometric pattern detectors.

    Each pattern implements detection logic, geometry generation, and feature filtering.
    Patterns are automatically registered and executed in priority order.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique pattern identifier.

        Returns:
            String identifier (e.g., 'chord_cut', 'counterbore')
        """
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Detection priority - higher values are checked first.

        Priority Guidelines:
        - 150-200: Complex multi-geometry patterns (chord cuts, keyways)
        - 100-149: Medium complexity (counterbores, slots)
        - 50-99: Simple features (chamfers, fillets)
        - 0-49: Fallback/generic patterns

        Returns:
            Integer priority value (0-200)
        """
        pass

    @abstractmethod
    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect if this pattern is present in agent results.

        Args:
            agent_results: List of agent analysis results from Phase 2
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if pattern detected, None otherwise
        """
        pass

    @abstractmethod
    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate Arc+Line+Constraints geometry from detected parameters.

        Two return formats are supported:

        FORMAT 1: Needs base geometry (e.g., chord cut needs base Circle radius)
        {
            "needs_base_circle": True,
            "flat_to_flat": 78.0,
            ... other pattern parameters ...
        }

        FORMAT 2: Complete geometry (pattern doesn't need base geometry)
        {
            "geometry": [Arc(...), Line(...), ...],
            "constraints": [Coincident(...), Parallel(...), ...]
        }

        Args:
            match: Detection result with parameters

        Returns:
            Dictionary with geometry specification (see formats above)
        """
        pass

    @abstractmethod
    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove features that conflict with this pattern.

        Example: Chord cut removes all Cut operations since the pattern
        replaces them with Arc + Line geometry.

        Args:
            all_features: All detected features from agents
            match: Pattern match information

        Returns:
            Filtered list of features (without conflicts)
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of this pattern for Claude LLM.

        Should describe:
        - Visual indicators (what agents would report)
        - Audio clues (keywords in transcription)
        - Expected feature structure

        Returns:
            String description for pattern recognition
        """
        pass

    @property
    @abstractmethod
    def detection_indicators(self) -> Dict[str, List[str]]:
        """
        Structured indicators for pattern detection.

        Returns:
            {
                "visual": ["symmetric cuts", "left_side + right_side"],
                "audio": ["distância", "paralelas", "2 linhas"],
                "features": ["Circle base", "multiple Cuts"]
            }
        """
        pass


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

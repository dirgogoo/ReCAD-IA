"""
Base classes for ReCAD geometric pattern detection system.

This module defines the abstract interface that all pattern detectors must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import math


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

    # === Protected Helper Methods (shared across patterns) ===

    def _extract_value(self, obj: Any) -> Optional[float]:
        """
        Extract numeric value from dict or return as-is.

        Handles both direct values and dict format: {"value": X, "unit": "mm"}

        Args:
            obj: Value to extract (can be float, dict, or None)

        Returns:
            Extracted float value or None

        Examples:
            >>> self._extract_value(10.5)
            10.5
            >>> self._extract_value({"value": 10.5, "unit": "mm"})
            10.5
            >>> self._extract_value(None)
            None
        """
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get("value")
        return float(obj)

    def _extract_center(self, feature: Dict) -> tuple:
        """
        Extract center coordinates from feature geometry.

        Args:
            feature: Feature dict with geometry.center = {x: X, y: Y}

        Returns:
            Tuple (x, y) with default (0, 0) if not found

        Example:
            >>> feature = {"geometry": {"center": {"x": 10, "y": 20}}}
            >>> self._extract_center(feature)
            (10, 20)
        """
        center_obj = feature.get("geometry", {}).get("center", {"x": 0, "y": 0})
        return (center_obj.get("x", 0), center_obj.get("y", 0))

    def _distance(self, p1: tuple, p2: tuple) -> float:
        """
        Calculate Euclidean distance between two 2D points.

        Args:
            p1: First point (x, y)
            p2: Second point (x, y)

        Returns:
            Distance in same units as input coordinates

        Example:
            >>> self._distance((0, 0), (3, 4))
            5.0
        """
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _extract_depth(self, feature: Dict) -> Optional[float]:
        """
        Extract depth from Cut feature parameters.

        Handles both "depth" (for chamfer) and "distance" (for circle cuts).

        Args:
            feature: Feature dict with parameters.depth or parameters.distance

        Returns:
            Extracted depth value or None

        Example:
            >>> feature = {"parameters": {"distance": {"value": 10}}}
            >>> self._extract_depth(feature)
            10.0
        """
        params = feature.get("parameters", {})
        # Could be "depth" (for chamfer) or "distance" (for circle)
        depth = params.get("depth") or params.get("distance")
        return self._extract_value(depth)


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

"""
Chord cut pattern detector for ReCAD.

Detects bilateral chord cuts (flat sides on cylindrical parts) from:
1. additional_features in agent results
2. Cut operations with bilateral/chord position markers
3. Audio transcription keywords
"""

import re
from typing import Dict, List, Optional, Any
from .base import GeometricPattern, PatternMatch
from . import register_pattern


@register_pattern
class ChordCutPattern(GeometricPattern):
    """
    Detects bilateral chord cuts on cylindrical parts.

    A chord cut is characterized by two parallel flat sides on a cylinder,
    resulting in a geometry with 2 arcs + 2 lines.

    Priority: 180 (high - complex multi-geometry pattern)
    """

    @property
    def name(self) -> str:
        return "chord_cut"

    @property
    def priority(self) -> int:
        return 180  # High priority - complex pattern should be detected first

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect chord cuts from multiple sources.

        Detection strategies:
        1. Check for additional_features with "chord_cut" type
        2. Detect Cut operations with bilateral/chord position markers
        3. Extract parameters from audio transcription

        Args:
            agent_results: List of agent analysis results
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if chord cut detected, None otherwise
        """
        # Strategy 1: Check additional_features
        for result in agent_results:
            additional = result.get("additional_features", [])
            for feature in additional:
                if feature.get("type") == "chord_cut":
                    flat_to_flat = feature.get("flat_to_flat")
                    if flat_to_flat:
                        return PatternMatch(
                            pattern_name=self.name,
                            confidence=feature.get("confidence", 0.95),
                            parameters={"flat_to_flat": flat_to_flat},
                            source="additional_features"
                        )

        # Strategy 2: Detect from Cut operations with bilateral/left/right position
        # Count cuts by position to detect bilateral pattern
        left_cuts = 0
        right_cuts = 0
        bilateral_cuts = 0

        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut" and feature.get("operation") == "remove":
                    position = feature.get("position", "")
                    if "bilateral" in position or "chord" in position:
                        bilateral_cuts += 1
                    elif "left" in position:
                        left_cuts += 1
                    elif "right" in position:
                        right_cuts += 1

        # Detect bilateral chord cut if we have matching left/right cuts or explicit bilateral
        if bilateral_cuts > 0 or (left_cuts > 0 and right_cuts > 0):
            # Try to extract flat_to_flat from transcription
            flat_to_flat = self._extract_flat_to_flat(transcription)
            if flat_to_flat:
                return PatternMatch(
                    pattern_name=self.name,
                    confidence=0.92,
                    parameters={"flat_to_flat": flat_to_flat},
                    source="bilateral_cut_pattern"
                )

        return None

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate Arc + Line geometry for chord cut.

        This pattern needs the base Circle radius to calculate the geometry,
        so it returns a "needs_base_circle" flag and lets the aggregator
        handle geometry generation via chord_cut_helper.

        Args:
            match: Detection result with flat_to_flat parameter

        Returns:
            Dictionary indicating need for base circle and flat_to_flat value
        """
        return {
            "needs_base_circle": True,
            "flat_to_flat": match.parameters["flat_to_flat"]
        }

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove Cut operations when chord cut is detected.

        Chord cuts replace Cut operations with Arc + Line geometry,
        so all Cut operations should be filtered out.

        Args:
            all_features: All detected features from agents
            match: Pattern match information

        Returns:
            Features without Cut operations
        """
        return [f for f in all_features if f.get("type") != "Cut"]

    @property
    def description(self) -> str:
        return """
    Bilateral chord cuts on cylindrical parts.

    Visual: Circle with two symmetric flat sides (parallel to each other)
    Audio: Keywords like 'distância de Xmm', '2 linhas paralelas'
    Features: 1 Circle base + multiple Cuts with position 'left_side'/'right_side'

    This pattern creates a cylinder with flat sides, resulting in a
    flat-to-flat distance smaller than the diameter. Better represented
    as Arc + Line geometry than boolean cuts.
    """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        return {
            "visual": [
                "symmetric bilateral cuts",
                "left_side + right_side position markers",
                "Circle base with flat sides"
            ],
            "audio": [
                "distância de",
                "linhas paralelas",
                "flat-to-flat",
                "chord"
            ],
            "features": [
                "Circle geometry (base)",
                "Multiple Cut operations",
                "Cuts with position='left_side' or 'right_side'"
            ]
        }

    def _extract_flat_to_flat(self, transcription: Optional[str]) -> Optional[float]:
        """
        Extract flat-to-flat distance from audio transcription.

        Tries multiple regex patterns to handle encoding variations:
        - "distância de XXmm" (direct distance mention)
        - "2 linhas... XXmm" (two lines with distance)

        Args:
            transcription: Audio transcription text

        Returns:
            Flat-to-flat distance in mm, or None if not found
        """
        if not transcription:
            return None

        # Pattern 1: "distância de XXmm" (use . to handle encoding variations)
        match = re.search(r'dist.ncia de (\d+)\s*mm', transcription)
        if match:
            return float(match.group(1))

        # Pattern 2: "2 linhas... XXmm" (fallback)
        match = re.search(r'2 linhas.*?(\d+)\s*mm', transcription)
        if match:
            return float(match.group(1))

        return None

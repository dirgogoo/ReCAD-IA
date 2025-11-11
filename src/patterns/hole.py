"""
Hole pattern detector for ReCAD.

Detects circular cuts (through-holes and blind holes) from:
1. Cut operations with Circle geometry from agents
2. Audio transcription for depth cues
"""

import re
from typing import Dict, List, Optional, Any
from .base import GeometricPattern, PatternMatch
from . import register_pattern


@register_pattern
class HolePattern(GeometricPattern):
    """
    Detects holes (circular cuts) in parts.

    A hole is characterized by a Cut operation with Circle geometry.
    Can be through-hole (cut_type="through_all") or blind hole (cut_type="distance").

    Priority: 150 (medium-high - common feature but simpler than chord cuts)
    """

    @property
    def name(self) -> str:
        return "hole"

    @property
    def priority(self) -> int:
        return 150  # Medium-high priority - detect before generic patterns

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect holes from Cut operations with Circle geometry.

        Args:
            agent_results: List of agent analysis results
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if hole detected, None otherwise
        """
        # Look for Cut operations with Circle geometry
        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut":
                    geometry = feature.get("geometry", {})
                    if geometry.get("type") == "Circle":
                        # Extract parameters
                        diameter_obj = geometry.get("diameter", {})
                        diameter = diameter_obj.get("value") if isinstance(diameter_obj, dict) else diameter_obj

                        center_obj = geometry.get("center", {"x": 0, "y": 0})
                        center = (center_obj.get("x", 0), center_obj.get("y", 0))

                        parameters_obj = feature.get("parameters", {})
                        cut_type = parameters_obj.get("cut_type", "through_all")

                        depth = None
                        if cut_type == "distance":
                            distance_obj = parameters_obj.get("distance", {})
                            depth = distance_obj.get("value") if isinstance(distance_obj, dict) else distance_obj

                        # Build parameters
                        params = {
                            "diameter": diameter,
                            "cut_type": cut_type,
                            "center": center,
                            "depth": depth
                        }

                        # Calculate confidence
                        confidence = 0.90  # High confidence for clear Cut + Circle
                        if transcription and self._has_depth_cues(transcription):
                            confidence = 0.95

                        return PatternMatch(
                            pattern_name=self.name,
                            confidence=confidence,
                            parameters=params,
                            source="agent_results"
                        )

        return None

    def _has_depth_cues(self, transcription: str) -> bool:
        """Check if audio mentions depth/profundidade."""
        depth_keywords = [
            "profundidade",
            "fundo",
            "depth",
            "blind hole",
            "furo cego"
        ]
        lower_text = transcription.lower()
        return any(keyword in lower_text for keyword in depth_keywords)

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate geometry data for PartBuilder.add_circle_cut().

        Returns parameters that can be directly passed to PartBuilder.add_circle_cut():
        - center: (x, y) tuple
        - diameter: float
        - cut_type: "through_all" or "distance"
        - cut_distance: float (depth for blind holes)

        Args:
            match: Pattern match with hole parameters

        Returns:
            Dict with parameters matching PartBuilder.add_circle_cut() signature
        """
        params = match.parameters
        result = {
            "center": params["center"],
            "diameter": params["diameter"],
            "cut_type": params["cut_type"]
        }

        # Add cut_distance for blind holes
        if params["cut_type"] == "distance" and params.get("depth"):
            result["cut_distance"] = params["depth"]

        return result

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove Cut features that were detected as holes.

        Args:
            all_features: All detected features
            match: Pattern match information

        Returns:
            Filtered list without Cut operations
        """
        return [
            f for f in all_features
            if f.get("type") != "Cut"
        ]

    @property
    def description(self) -> str:
        """Human-readable description for Claude LLM."""
        return """
        Holes (Circular Cuts):
        - Visual: Circular cutouts/pockets in base geometry
        - Audio: "furo", "hole", "profundidade de X mm"
        - Types: Through-hole (cut_type="through_all") or Blind hole (with depth)
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        """Structured indicators for pattern detection."""
        return {
            "visual": ["circular cutout", "hole", "pocket", "circular Cut operation"],
            "audio": ["furo", "hole", "profundidade", "depth", "furo passante", "through-hole", "blind hole"],
            "features": ["Cut operation", "Circle geometry", "cut_type parameter"]
        }

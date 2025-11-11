"""
Counterbore pattern detector for ReCAD.

Detects two-stage holes (counterbores and countersinks) from:
1. Direct Counterbore geometry from agents
2. Two sequential Circle cuts at same center (larger → smaller)
3. Audio transcription for confirmation
"""

import math
from typing import Dict, List, Optional, Any
from .base import GeometricPattern, PatternMatch
from . import register_pattern


@register_pattern
class CounterborePattern(GeometricPattern):
    """
    Detects counterbores (two-stage holes) in parts.

    A counterbore consists of:
    - Outer cut: Larger diameter, shallow depth (for screw head)
    - Inner cut: Smaller diameter, deeper depth (for screw shaft)

    Priority: 155 (between polar_hole_pattern 160 and hole 150)
    """

    @property
    def name(self) -> str:
        return "counterbore"

    @property
    def priority(self) -> int:
        return 155  # Between polar patterns (160) and individual holes (150)

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect counterbores from agent results.

        Strategy:
        1. Look for direct Counterbore geometry
        2. Look for two Circle cuts at same center (different diameters)
        3. Validate: outer_diameter > inner_diameter

        Args:
            agent_results: List of agent analysis results
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if counterbore detected, None otherwise
        """
        # Strategy 1: Look for direct Counterbore geometry
        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut":
                    geometry = feature.get("geometry", {})
                    if geometry.get("type") == "Counterbore":
                        return self._detect_from_counterbore_geometry(feature, transcription)

        # Strategy 2: Look for two Circle cuts at same center
        for result in agent_results:
            features = result.get("features", [])
            circular_cuts = [
                f for f in features
                if f.get("type") == "Cut" and f.get("geometry", {}).get("type") == "Circle"
            ]

            if len(circular_cuts) >= 2:
                match = self._detect_from_two_cuts(circular_cuts, transcription)
                if match:
                    return match

        return None

    def _detect_from_counterbore_geometry(
        self,
        feature: Dict,
        transcription: Optional[str]
    ) -> Optional[PatternMatch]:
        """Detect from direct Counterbore geometry."""
        geometry = feature.get("geometry", {})
        parameters = feature.get("parameters", {})

        # Extract parameters
        outer_diameter = self._extract_value(geometry.get("outer_diameter"))
        inner_diameter = self._extract_value(geometry.get("inner_diameter"))
        outer_depth = self._extract_value(parameters.get("outer_depth"))
        inner_depth = self._extract_value(parameters.get("inner_depth"))

        center_obj = geometry.get("center", {"x": 0, "y": 0})
        center = (center_obj.get("x", 0), center_obj.get("y", 0))

        # Validate
        if not self._validate_counterbore(outer_diameter, inner_diameter, outer_depth, inner_depth):
            return None

        # Calculate confidence
        confidence = 0.90  # High confidence for direct geometry
        if transcription and self._has_counterbore_cues(transcription):
            confidence = 0.95

        return PatternMatch(
            pattern_name=self.name,
            confidence=confidence,
            parameters={
                "outer_diameter": outer_diameter,
                "inner_diameter": inner_diameter,
                "outer_depth": outer_depth,
                "inner_depth": inner_depth,
                "center": center
            },
            source="agent_results"
        )

    def _detect_from_two_cuts(
        self,
        cuts: List[Dict],
        transcription: Optional[str]
    ) -> Optional[PatternMatch]:
        """Detect from two Circle cuts at same center."""
        # Find all pairs of cuts at same center
        for i, cut1 in enumerate(cuts):
            for cut2 in cuts[i+1:]:
                center1 = self._extract_center(cut1)
                center2 = self._extract_center(cut2)

                # Check if centers match (within 0.5mm tolerance)
                if self._distance(center1, center2) > 0.5:
                    continue

                # Extract diameters and depths
                d1 = self._extract_value(cut1.get("geometry", {}).get("diameter"))
                d2 = self._extract_value(cut2.get("geometry", {}).get("diameter"))
                depth1 = self._extract_depth(cut1)
                depth2 = self._extract_depth(cut2)

                # Determine which is outer (larger) and inner (smaller)
                if d1 > d2:
                    outer_d, inner_d = d1, d2
                    outer_depth, inner_depth = depth1, depth2
                elif d2 > d1:
                    outer_d, inner_d = d2, d1
                    outer_depth, inner_depth = depth2, depth1
                else:
                    continue  # Same diameter = not counterbore

                # Validate
                if not self._validate_counterbore(outer_d, inner_d, outer_depth, inner_depth):
                    continue

                # Calculate confidence
                confidence = 0.85  # Good confidence for inferred pattern
                if transcription and self._has_counterbore_cues(transcription):
                    confidence = 0.95

                return PatternMatch(
                    pattern_name=self.name,
                    confidence=confidence,
                    parameters={
                        "outer_diameter": outer_d,
                        "inner_diameter": inner_d,
                        "outer_depth": outer_depth,
                        "inner_depth": inner_depth,
                        "center": center1
                    },
                    source="agent_results"
                )

        return None

    def _validate_counterbore(
        self,
        outer_d: float,
        inner_d: float,
        outer_depth: float,
        inner_depth: float
    ) -> bool:
        """Validate counterbore parameters."""
        if outer_d is None or inner_d is None:
            return False
        if outer_depth is None or inner_depth is None:
            return False
        if outer_d <= inner_d:  # Outer must be larger
            return False
        if outer_depth >= inner_depth:  # Outer should be shallower
            return False
        return True

    def _extract_value(self, obj: Any) -> Optional[float]:
        """Extract numeric value from dict or return as-is."""
        if isinstance(obj, dict):
            return obj.get("value")
        return obj

    def _extract_center(self, feature: Dict) -> tuple:
        """Extract center coordinates from feature."""
        center_obj = feature.get("geometry", {}).get("center", {"x": 0, "y": 0})
        return (center_obj.get("x", 0), center_obj.get("y", 0))

    def _extract_depth(self, feature: Dict) -> Optional[float]:
        """Extract depth from Cut feature."""
        params = feature.get("parameters", {})
        distance = params.get("distance")
        return self._extract_value(distance)

    def _distance(self, p1: tuple, p2: tuple) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _has_counterbore_cues(self, transcription: str) -> bool:
        """Check if audio mentions counterbore."""
        keywords = [
            "counterbore",
            "counter bore",
            "escareado",
            "furo escalonado",
            "two stage",
            "dois estágios"
        ]
        lower_text = transcription.lower()
        return any(keyword in lower_text for keyword in keywords)

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate geometry for two PartBuilder.add_circle_cut() calls.

        Returns dict with "outer_cut" and "inner_cut" parameters.

        Args:
            match: Pattern match with counterbore parameters

        Returns:
            {
                "outer_cut": {diameter, cut_distance, center},
                "inner_cut": {diameter, cut_distance, center}
            }
        """
        params = match.parameters

        # Outer cut (shallow, larger diameter)
        outer_cut = {
            "center": params["center"],
            "diameter": params["outer_diameter"],
            "cut_type": "distance",
            "cut_distance": params["outer_depth"]
        }

        # Inner cut (deeper, smaller diameter, relative depth)
        inner_depth_relative = params["inner_depth"] - params["outer_depth"]
        inner_cut = {
            "center": params["center"],
            "diameter": params["inner_diameter"],
            "cut_type": "distance",
            "cut_distance": inner_depth_relative
        }

        return {
            "outer_cut": outer_cut,
            "inner_cut": inner_cut
        }

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove Cut features that were detected as counterbore.

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
        Counterbores (Two-Stage Holes):
        - Visual: Two concentric circles (larger → smaller), step visible from side
        - Audio: "counterbore", "escareado", "furo escalonado", "dois estágios"
        - Structure: Outer cut (screw head) + Inner cut (screw shaft)
        - Usage: Flush-mount fasteners, recessed bolt heads
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        """Structured indicators for pattern detection."""
        return {
            "visual": [
                "two concentric circles",
                "stepped hole",
                "larger hole → smaller hole",
                "counterbore profile"
            ],
            "audio": [
                "counterbore",
                "counter bore",
                "escareado",
                "furo escalonado",
                "dois estágios",
                "two stage"
            ],
            "features": [
                "Counterbore geometry",
                "two Circle cuts same center",
                "different diameters",
                "different depths"
            ]
        }

"""
Countersink pattern detector for ReCAD.

Detects countersinks (conical counterbores) from:
1. Direct Countersink geometry from agents
2. Chamfer cut + Circle cut at same center
3. Audio transcription for confirmation
"""

import math
from typing import Dict, List, Optional, Any
from .base import GeometricPattern, PatternMatch
from . import register_pattern


@register_pattern
class CountersinkPattern(GeometricPattern):
    """
    Detects countersinks (conical two-stage holes) in parts.

    A countersink consists of:
    - Outer cut: Conical (chamfer), larger diameter (for flat-head screw)
    - Inner cut: Cylindrical (circle), smaller diameter (for screw shaft)

    Priority: 154 (between counterbore 155 and hole 150)
    """

    # Standard countersink angles (ISO, DIN standards)
    VALID_ANGLES = [82.0, 90.0, 100.0, 120.0]
    ANGLE_TOLERANCE = 2.0  # ±2° tolerance

    @property
    def name(self) -> str:
        return "countersink"

    @property
    def priority(self) -> int:
        return 154  # Between counterbore (155) and hole (150)

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect countersinks from agent results.

        Strategy:
        1. Look for direct Countersink geometry
        2. Look for Chamfer cut + Circle cut at same center
        3. Validate: outer_diameter > inner_diameter
        4. Validate: cone angle in valid range

        Args:
            agent_results: List of agent analysis results
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if countersink detected, None otherwise
        """
        # Strategy 1: Look for direct Countersink geometry
        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut":
                    geometry = feature.get("geometry", {})
                    if geometry.get("type") == "Countersink":
                        return self._detect_from_countersink_geometry(feature, transcription)

        # Strategy 2: Look for Chamfer + Circle at same center
        for result in agent_results:
            features = result.get("features", [])

            chamfer_cuts = [
                f for f in features
                if f.get("type") == "Cut" and f.get("geometry", {}).get("type") == "Chamfer"
            ]

            circular_cuts = [
                f for f in features
                if f.get("type") == "Cut" and f.get("geometry", {}).get("type") == "Circle"
            ]

            if chamfer_cuts and circular_cuts:
                match = self._detect_from_chamfer_and_circle(chamfer_cuts, circular_cuts, transcription)
                if match:
                    return match

        return None

    def _detect_from_countersink_geometry(
        self,
        feature: Dict,
        transcription: Optional[str]
    ) -> Optional[PatternMatch]:
        """Detect from direct Countersink geometry."""
        geometry = feature.get("geometry", {})
        parameters = feature.get("parameters", {})

        # Extract parameters
        outer_diameter = self._extract_value(geometry.get("outer_diameter"))
        inner_diameter = self._extract_value(geometry.get("inner_diameter"))
        angle = self._extract_value(geometry.get("angle"))
        outer_depth = self._extract_value(parameters.get("outer_depth"))
        inner_depth = self._extract_value(parameters.get("inner_depth"))

        center_obj = geometry.get("center", {"x": 0, "y": 0})
        center = (center_obj.get("x", 0), center_obj.get("y", 0))

        # Validate
        if not self._validate_countersink(outer_diameter, inner_diameter, angle, outer_depth, inner_depth):
            return None

        # Calculate confidence
        confidence = 0.90  # High confidence for direct geometry
        if transcription and self._has_countersink_cues(transcription):
            confidence = 0.95

        return PatternMatch(
            pattern_name=self.name,
            confidence=confidence,
            parameters={
                "outer_diameter": outer_diameter,
                "inner_diameter": inner_diameter,
                "angle": angle,
                "outer_depth": outer_depth,
                "inner_depth": inner_depth,
                "center": center
            },
            source="agent_results"
        )

    def _detect_from_chamfer_and_circle(
        self,
        chamfer_cuts: List[Dict],
        circular_cuts: List[Dict],
        transcription: Optional[str]
    ) -> Optional[PatternMatch]:
        """Detect from Chamfer cut + Circle cut at same center."""
        # Find chamfer + circle pairs at same center
        for chamfer in chamfer_cuts:
            for circle in circular_cuts:
                center_chamfer = self._extract_center(chamfer)
                center_circle = self._extract_center(circle)

                # Check if centers match (within 0.5mm tolerance)
                if self._distance(center_chamfer, center_circle) > 0.5:
                    continue

                # Extract parameters
                outer_d = self._extract_value(chamfer.get("geometry", {}).get("diameter"))
                inner_d = self._extract_value(circle.get("geometry", {}).get("diameter"))
                angle = self._extract_value(chamfer.get("geometry", {}).get("angle"))
                outer_depth = self._extract_depth(chamfer)
                inner_depth = self._extract_depth(circle)

                # Validate
                if not self._validate_countersink(outer_d, inner_d, angle, outer_depth, inner_depth):
                    continue

                # Calculate confidence
                confidence = 0.85  # Good confidence for inferred pattern
                if transcription and self._has_countersink_cues(transcription):
                    confidence = 0.95

                return PatternMatch(
                    pattern_name=self.name,
                    confidence=confidence,
                    parameters={
                        "outer_diameter": outer_d,
                        "inner_diameter": inner_d,
                        "angle": angle,
                        "outer_depth": outer_depth,
                        "inner_depth": inner_depth,
                        "center": center_chamfer
                    },
                    source="agent_results"
                )

        return None

    def _validate_countersink(
        self,
        outer_d: float,
        inner_d: float,
        angle: float,
        outer_depth: float,
        inner_depth: float
    ) -> bool:
        """Validate countersink parameters."""
        if outer_d is None or inner_d is None or angle is None:
            return False
        if outer_depth is None or inner_depth is None:
            return False
        if outer_d <= inner_d:  # Outer must be larger
            return False
        if outer_depth >= inner_depth:  # Outer should be shallower
            return False

        # Validate angle is one of standard values
        if not self._is_valid_angle(angle):
            return False

        return True

    def _is_valid_angle(self, angle: float) -> bool:
        """Check if angle is one of the standard countersink angles."""
        for valid_angle in self.VALID_ANGLES:
            if abs(angle - valid_angle) <= self.ANGLE_TOLERANCE:
                return True
        return False

    def _has_countersink_cues(self, transcription: str) -> bool:
        """Check if audio mentions countersink."""
        keywords = [
            "countersink",
            "counter sink",
            "escareado cônico",
            "escareado",
            "flat head",
            "cabeça chata",
            "cabeça embutida",
            "conical counterbore"
        ]
        lower_text = transcription.lower()
        return any(keyword in lower_text for keyword in keywords)

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate geometry for chamfer cut + circle cut.

        Returns dict with "chamfer_cut" and "circle_cut" parameters.

        Args:
            match: Pattern match with countersink parameters

        Returns:
            {
                "chamfer_cut": {diameter, angle, depth, center},
                "circle_cut": {diameter, cut_distance, center}
            }
        """
        params = match.parameters

        # Chamfer cut (conical outer)
        chamfer_cut = {
            "center": params["center"],
            "diameter": params["outer_diameter"],
            "angle": params["angle"],
            "depth": params["outer_depth"]
        }

        # Circle cut (cylindrical inner, relative depth)
        inner_depth_relative = params["inner_depth"] - params["outer_depth"]
        circle_cut = {
            "center": params["center"],
            "diameter": params["inner_diameter"],
            "cut_type": "distance",
            "cut_distance": inner_depth_relative
        }

        return {
            "chamfer_cut": chamfer_cut,
            "circle_cut": circle_cut
        }

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove Cut features that were detected as countersink.

        Args:
            all_features: All detected features
            match: Pattern match information

        Returns:
            Filtered list without chamfer and circle cuts
        """
        return [
            f for f in all_features
            if f.get("type") != "Cut"
        ]

    @property
    def description(self) -> str:
        """Human-readable description for Claude LLM."""
        return """
        Countersinks (Conical Counterbores):
        - Visual: Conical transition (cone-shaped) + cylindrical hole, flat-head screw profile
        - Audio: "countersink", "escareado cônico", "flat head", "cabeça chata"
        - Structure: Chamfer/Cone cut (outer) + Circle cut (inner)
        - Angles: 82° (ISO standard), 90° (common), 100°, 120° (rare)
        - Usage: Flat-head screws, flush-mount fasteners, smooth surfaces
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        """Structured indicators for pattern detection."""
        return {
            "visual": [
                "conical transition",
                "cone-shaped outer hole",
                "flat-head screw profile",
                "chamfered edge",
                "V-shaped cut"
            ],
            "audio": [
                "countersink",
                "counter sink",
                "escareado cônico",
                "escareado",
                "flat head",
                "cabeça chata",
                "cabeça embutida",
                "conical counterbore"
            ],
            "features": [
                "Countersink geometry",
                "Chamfer cut + Circle cut same center",
                "cone angle 82° or 90° or 100°",
                "different diameters",
                "different depths"
            ]
        }

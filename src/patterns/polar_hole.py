"""
Polar hole pattern detector for ReCAD.

Detects circular arrangements of holes (bolt circles, mounting patterns) from:
1. Multiple Cut operations with same diameter
2. Equal angular spacing around center point
3. Audio transcription with pattern cues
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from .base import GeometricPattern, PatternMatch
from . import register_pattern


@register_pattern
class PolarHolePattern(GeometricPattern):
    """
    Detects polar hole patterns (circular arrangements).

    A polar pattern is characterized by N holes of same diameter arranged
    at equal angular intervals around a center point.

    Priority: 160 (high - should detect before individual holes)
    """

    @property
    def name(self) -> str:
        return "polar_hole_pattern"

    @property
    def priority(self) -> int:
        return 160  # Higher than individual holes (150) to match patterns first

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect polar hole patterns from multiple Cut operations.

        Algorithm:
        1. Extract all circular cuts (holes)
        2. Group by diameter
        3. For each diameter group with 3+ holes:
           - Calculate center point (centroid of hole centers)
           - Calculate radius from center to each hole
           - Check if radii are consistent (tolerance 5%)
           - Calculate angles between holes
           - Check if angles are evenly spaced (tolerance 5%)
        4. Return first valid pattern found

        Args:
            agent_results: List of agent analysis results
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if polar pattern detected, None otherwise
        """
        # Step 1: Extract all circular cuts
        holes = []
        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut":
                    geometry = feature.get("geometry", {})
                    if geometry.get("type") == "Circle":
                        diameter_obj = geometry.get("diameter", {})
                        diameter = diameter_obj.get("value") if isinstance(diameter_obj, dict) else diameter_obj

                        center_obj = geometry.get("center", {"x": 0, "y": 0})
                        center = (center_obj.get("x", 0), center_obj.get("y", 0))

                        parameters_obj = feature.get("parameters", {})
                        cut_type = parameters_obj.get("cut_type", "through_all")

                        holes.append({
                            "diameter": diameter,
                            "center": center,
                            "cut_type": cut_type
                        })

        if len(holes) < 3:
            return None  # Need at least 3 holes for circular pattern

        # Step 2: Group by diameter
        diameter_groups = {}
        for hole in holes:
            d = hole["diameter"]
            if d not in diameter_groups:
                diameter_groups[d] = []
            diameter_groups[d].append(hole)

        # Step 3: Check each group for polar pattern
        for diameter, group_holes in diameter_groups.items():
            if len(group_holes) < 3:
                continue  # Need at least 3 holes

            # Calculate pattern center (centroid)
            pattern_center = self._calculate_centroid([h["center"] for h in group_holes])

            # Calculate radius from center to each hole
            radii = [self._distance(pattern_center, h["center"]) for h in group_holes]
            avg_radius = sum(radii) / len(radii)

            # Check if radii are consistent (tolerance 5%)
            if not self._are_radii_consistent(radii, avg_radius, tolerance=0.05):
                continue

            # Calculate angles
            angles = [self._angle_from_center(pattern_center, h["center"]) for h in group_holes]
            angles = sorted(angles)  # Sort for angle difference calculation

            # Calculate expected angle step
            expected_angle_step = 360.0 / len(group_holes)

            # Check if angles are evenly spaced
            if not self._are_angles_evenly_spaced(angles, expected_angle_step, tolerance=5.0):
                continue

            # Pattern found!
            cut_type = group_holes[0]["cut_type"]

            # Calculate confidence
            confidence = 0.85  # Base confidence
            if transcription and self._has_pattern_cues(transcription):
                confidence = 0.95

            return PatternMatch(
                pattern_name=self.name,
                confidence=confidence,
                parameters={
                    "count": len(group_holes),
                    "diameter": diameter,
                    "radius": avg_radius,
                    "angle_step": expected_angle_step,
                    "center": pattern_center,
                    "cut_type": cut_type,
                    "start_angle": angles[0]  # First hole angle
                },
                source="agent_results"
            )

        return None

    def _calculate_centroid(self, points: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate geometric center of points."""
        x_sum = sum(p[0] for p in points)
        y_sum = sum(p[1] for p in points)
        count = len(points)
        return (x_sum / count, y_sum / count)

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def _angle_from_center(self, center: Tuple[float, float], point: Tuple[float, float]) -> float:
        """Calculate angle in degrees from center to point (0° = +X axis)."""
        dx = point[0] - center[0]
        dy = point[1] - center[1]
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        # Normalize to 0-360 range
        return angle_deg if angle_deg >= 0 else angle_deg + 360

    def _are_radii_consistent(self, radii: List[float], avg_radius: float, tolerance: float) -> bool:
        """Check if all radii are within tolerance of average."""
        for r in radii:
            if abs(r - avg_radius) / avg_radius > tolerance:
                return False
        return True

    def _are_angles_evenly_spaced(self, angles: List[float], expected_step: float, tolerance: float) -> bool:
        """Check if angles are evenly spaced with given tolerance (degrees)."""
        for i in range(len(angles)):
            next_i = (i + 1) % len(angles)
            angle_diff = angles[next_i] - angles[i]
            if angle_diff < 0:
                angle_diff += 360  # Handle wraparound

            if abs(angle_diff - expected_step) > tolerance:
                return False
        return True

    def _has_pattern_cues(self, transcription: str) -> bool:
        """Check if audio mentions pattern keywords."""
        pattern_keywords = [
            "círculo",
            "circular",
            "bolt circle",
            "padrão",
            "pattern",
            "em volta",
            "ao redor",
            "igualmente espaçados",
            "equally spaced"
        ]
        lower_text = transcription.lower()
        return any(keyword in lower_text for keyword in pattern_keywords)

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate geometry data for multiple holes in polar pattern.

        Returns list of hole parameters, one per hole in pattern.
        Each hole can be created with add_circle_cut().

        Args:
            match: Pattern match with polar pattern parameters

        Returns:
            Dict with list of holes and their individual parameters
        """
        params = match.parameters
        count = params["count"]
        diameter = params["diameter"]
        radius = params["radius"]
        angle_step = params["angle_step"]
        start_angle = params.get("start_angle", 0.0)
        center = params.get("center", (0.0, 0.0))  # Default to origin if not provided
        cut_type = params["cut_type"]

        holes = []
        for i in range(count):
            angle_deg = start_angle + (i * angle_step)
            angle_rad = math.radians(angle_deg)

            # Calculate hole center
            x = center[0] + radius * math.cos(angle_rad)
            y = center[1] + radius * math.sin(angle_rad)

            holes.append({
                "center": (round(x, 2), round(y, 2)),
                "diameter": diameter,
                "cut_type": cut_type
            })

        return {"holes": holes}

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove individual hole Cut features that are part of pattern.

        Args:
            all_features: All detected features
            match: Pattern match information

        Returns:
            Filtered list without individual hole Cuts
        """
        # Remove ALL Cut features (holes in pattern)
        return [f for f in all_features if f.get("type") != "Cut"]

    @property
    def description(self) -> str:
        """Human-readable description for Claude LLM."""
        return """
        Polar Hole Patterns (Circular Arrangements):
        - Visual: Multiple identical holes arranged in circle
        - Audio: "furos em círculo", "bolt circle", "padrão circular"
        - Characteristics: Same diameter, equal angular spacing, consistent radius
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        """Structured indicators for pattern detection."""
        return {
            "visual": [
                "multiple identical holes",
                "circular arrangement",
                "equal spacing around center",
                "bolt circle pattern"
            ],
            "audio": [
                "furos em círculo",
                "circular",
                "bolt circle",
                "padrão circular",
                "igualmente espaçados",
                "ao redor do centro"
            ],
            "features": [
                "3+ Cut operations",
                "same diameter",
                "equal radii from center",
                "evenly spaced angles"
            ]
        }

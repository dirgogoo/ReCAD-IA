"""
Slot pattern detector for ReCAD.

Detects rectangular grooves (slots) from:
1. Direct Slot geometry from agents
2. Elongated Rectangle cuts (aspect ratio > 2.0)
3. Audio transcription for confirmation
"""

import math
from typing import Dict, List, Optional, Any
from .base import GeometricPattern, PatternMatch
from . import register_pattern


@register_pattern
class SlotPattern(GeometricPattern):
    """
    Detects slots (elongated rectangular grooves) in parts.

    A slot consists of:
    - Width: narrow dimension (perpendicular to slot direction)
    - Length: long dimension (parallel to slot direction)
    - Orientation: angle of slot axis from horizontal
    - Depth: cut depth

    Priority: 145 (between countersink 154 and hole 150)
    """

    MIN_ASPECT_RATIO = 2.0  # length/width must be > 2.0 to be a slot

    @property
    def name(self) -> str:
        return "slot"

    @property
    def priority(self) -> int:
        return 145  # Between countersink (154) and hole (150)

    def detect(self,
               agent_results: List[Dict],
               transcription: Optional[str] = None) -> Optional[PatternMatch]:
        """
        Detect slots from agent results.

        Strategy:
        1. Look for direct Slot geometry
        2. Look for elongated Rectangle cuts (aspect ratio > 2.0)
        3. Validate: width > 0, length > 0, length > width

        Args:
            agent_results: List of agent analysis results
            transcription: Optional audio transcription text

        Returns:
            PatternMatch if slot detected, None otherwise
        """
        # Strategy 1: Look for direct Slot geometry
        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut":
                    geometry = feature.get("geometry", {})
                    if geometry.get("type") == "Slot":
                        return self._detect_from_slot_geometry(feature, transcription)

        # Strategy 2: Look for elongated Rectangle cuts
        for result in agent_results:
            features = result.get("features", [])
            for feature in features:
                if feature.get("type") == "Cut":
                    geometry = feature.get("geometry", {})
                    if geometry.get("type") == "Rectangle":
                        match = self._detect_from_rectangle(feature, transcription)
                        if match:
                            return match

        return None

    def _detect_from_slot_geometry(
        self,
        feature: Dict,
        transcription: Optional[str]
    ) -> Optional[PatternMatch]:
        """Detect from direct Slot geometry."""
        geometry = feature.get("geometry", {})
        parameters = feature.get("parameters", {})

        # Extract parameters
        width = self._extract_value(geometry.get("width"))
        length = self._extract_value(geometry.get("length"))
        depth = self._extract_value(parameters.get("depth"))

        center_obj = geometry.get("center", {"x": 0, "y": 0})
        center = (center_obj.get("x", 0), center_obj.get("y", 0))

        orientation = self._extract_value(geometry.get("orientation", 0.0))

        # Validate
        if not self._validate_slot(width, length, depth):
            return None

        # Calculate confidence
        confidence = 0.90  # High confidence for direct geometry
        if transcription and self._has_slot_cues(transcription):
            confidence = 0.95

        return PatternMatch(
            pattern_name=self.name,
            confidence=confidence,
            parameters={
                "width": width,
                "length": length,
                "depth": depth,
                "center": center,
                "orientation": orientation
            },
            source="agent_results"
        )

    def _detect_from_rectangle(
        self,
        feature: Dict,
        transcription: Optional[str]
    ) -> Optional[PatternMatch]:
        """Detect from elongated Rectangle cut (aspect ratio > 2.0)."""
        geometry = feature.get("geometry", {})
        parameters = feature.get("parameters", {})

        # Extract dimensions
        rect_width = self._extract_value(geometry.get("width"))
        rect_height = self._extract_value(geometry.get("height"))
        depth = self._extract_value(parameters.get("distance"))

        center_obj = geometry.get("center", {"x": 0, "y": 0})
        center = (center_obj.get("x", 0), center_obj.get("y", 0))

        if rect_width is None or rect_height is None or depth is None:
            return None

        # Determine which is width (smaller) and length (larger)
        if rect_width < rect_height:
            width = rect_width
            length = rect_height
            orientation = 90.0  # Vertical slot
        else:
            width = rect_height
            length = rect_width
            orientation = 0.0  # Horizontal slot

        # Check aspect ratio
        aspect_ratio = length / width if width > 0 else 0
        if aspect_ratio < self.MIN_ASPECT_RATIO:
            return None  # Not elongated enough to be a slot

        # Validate
        if not self._validate_slot(width, length, depth):
            return None

        # Calculate confidence
        confidence = 0.85  # Good confidence for inferred pattern
        if transcription and self._has_slot_cues(transcription):
            confidence = 0.95

        return PatternMatch(
            pattern_name=self.name,
            confidence=confidence,
            parameters={
                "width": width,
                "length": length,
                "depth": depth,
                "center": center,
                "orientation": orientation
            },
            source="agent_results"
        )

    def _validate_slot(
        self,
        width: Optional[float],
        length: Optional[float],
        depth: Optional[float]
    ) -> bool:
        """Validate slot parameters."""
        if width is None or length is None or depth is None:
            return False
        if width <= 0 or length <= 0 or depth <= 0:
            return False
        if length <= width:  # Length must be greater than width
            return False
        return True

    def _has_slot_cues(self, transcription: str) -> bool:
        """Check if audio mentions slot."""
        keywords = [
            "slot",
            "rasgo",
            "ranhura",
            "canal",
            "groove",
            "keyway",
            "guia"
        ]
        lower_text = transcription.lower()
        return any(keyword in lower_text for keyword in keywords)

    def generate_geometry(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Generate geometry for PartBuilder.add_slot_cut() call.

        Args:
            match: Pattern match with slot parameters

        Returns:
            {
                "width": float,
                "length": float,
                "cut_type": "distance",
                "cut_distance": float,
                "center": tuple,
                "orientation": float
            }
        """
        params = match.parameters

        return {
            "center": params["center"],
            "width": params["width"],
            "length": params["length"],
            "cut_type": "distance",
            "cut_distance": params["depth"],
            "orientation": params.get("orientation", 0.0)
        }

    def filter_features(self,
                       all_features: List[Dict],
                       match: PatternMatch) -> List[Dict]:
        """
        Remove Cut features that were detected as slot.

        Args:
            all_features: All detected features
            match: Pattern match information

        Returns:
            Filtered list without the slot Cut operation
        """
        # Remove the Rectangle or Slot cut that was detected
        return [
            f for f in all_features
            if not (f.get("type") == "Cut" and
                   f.get("geometry", {}).get("type") in ["Slot", "Rectangle"])
        ]

    @property
    def description(self) -> str:
        """Human-readable description for Claude LLM."""
        return """
        Slots (Elongated Rectangular Grooves):
        - Visual: Rectangular cavity with length >> width (aspect ratio > 2:1)
        - Audio: "slot", "rasgo", "ranhura", "canal", "groove"
        - Structure: Width (narrow) x Length (long) x Depth
        - Usage: Sliding guides, T-slots, keyways, adjustment tracks
        - Orientation: Angle from horizontal (0° = horizontal, 90° = vertical)
        """

    @property
    def detection_indicators(self) -> Dict[str, List[str]]:
        """Structured indicators for pattern detection."""
        return {
            "visual": [
                "elongated rectangular cavity",
                "slot profile",
                "groove or channel",
                "aspect ratio > 2:1"
            ],
            "audio": [
                "slot",
                "rasgo",
                "ranhura",
                "canal",
                "groove",
                "keyway",
                "guia"
            ],
            "features": [
                "Slot geometry",
                "elongated Rectangle cut",
                "aspect ratio > 2.0",
                "width < length"
            ]
        }

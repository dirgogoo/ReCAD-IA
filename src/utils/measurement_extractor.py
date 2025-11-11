"""
Extracts dimensional measurements from audio transcription text.

Detects missing critical measurements and raises errors to request them.
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


class MissingMeasurementError(Exception):
    """Raised when a critical measurement is missing from transcription."""

    def __init__(self, missing_measurements: List[str], transcription_text: str):
        self.missing_measurements = missing_measurements
        self.transcription_text = transcription_text

        measurements_str = ", ".join(missing_measurements)
        super().__init__(
            f"Missing critical measurements: {measurements_str}\n"
            f"Transcription: '{transcription_text}'\n"
            f"Please provide these measurements to continue."
        )


@dataclass
class Measurement:
    """Represents an extracted measurement."""
    name: str
    value: float
    unit: str
    confidence: float  # 0.0 to 1.0


class MeasurementExtractor:
    """Extracts measurements from transcription text."""

    # Regex patterns for common measurements (Portuguese)
    PATTERNS = {
        "diameter": [
            r"diâmetro\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"diâmetro\s+(?:de\s+)?(\d+(?:\.\d+)?)",
        ],
        "radius": [
            r"raio\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"raio\s+(?:de\s+)?(\d+(?:\.\d+)?)",
        ],
        "height": [
            r"altura\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"espessura\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
        ],
        "width": [
            r"largura\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"comprimento\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
        ],
        "distance": [
            r"distância\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*mm",
            r"(\d+)\s*mm\s+de\s+distância",
        ],
        "flat_to_flat": [
            r"(\d+)\s*mm\s+de\s+(?:distância|espaçamento)",
            r"2\s+linhas.*?(\d+(?:\.\d+)?)\s*mm",
        ]
    }

    def extract_measurements(self, text: str) -> Dict[str, float]:
        """
        Extract all measurements from transcription text.

        Args:
            text: Transcription text (Portuguese)

        Returns:
            Dict mapping measurement names to values (in mm)
        """
        measurements = {}
        text_lower = text.lower()

        for measurement_name, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        measurements[measurement_name] = value
                        break  # Found match for this measurement
                    except (ValueError, IndexError):
                        continue

        return measurements

    def validate_required_measurements(
        self,
        text: str,
        required: List[str]
    ) -> Dict[str, float]:
        """
        Validate that all required measurements are present.

        Args:
            text: Transcription text
            required: List of required measurement names

        Returns:
            Dict of extracted measurements

        Raises:
            MissingMeasurementError: If any required measurements are missing
        """
        measurements = self.extract_measurements(text)
        missing = [name for name in required if name not in measurements]

        if missing:
            raise MissingMeasurementError(missing, text)

        return measurements

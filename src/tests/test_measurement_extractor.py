"""Tests for measurement extraction from transcription."""
import pytest
from utils.measurement_extractor import MeasurementExtractor, MissingMeasurementError


def test_extract_diameter_from_transcription():
    """Should extract diameter measurement from Portuguese text."""
    extractor = MeasurementExtractor()

    text = "Chapa de diâmetro 90mm"
    measurements = extractor.extract_measurements(text)

    assert "diameter" in measurements
    assert measurements["diameter"] == 90.0


def test_missing_diameter_raises_error():
    """Should raise error when diameter is mentioned but value is missing."""
    extractor = MeasurementExtractor()

    text = "Chapa circular com furos"  # No diameter value

    with pytest.raises(MissingMeasurementError) as exc_info:
        extractor.validate_required_measurements(text, required=["diameter"])

    assert "diameter" in str(exc_info.value).lower()

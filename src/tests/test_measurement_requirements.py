"""Tests for pattern-specific measurement requirements."""
import pytest
from patterns.base import get_required_measurements_for_pattern


def test_chord_cut_requires_diameter_and_flat_to_flat():
    """Chord cut pattern requires diameter and flat_to_flat measurements."""
    required = get_required_measurements_for_pattern("chord_cut")

    assert "diameter" in required or "radius" in required
    assert "flat_to_flat" in required or "distance" in required


def test_circle_extrude_requires_diameter_and_height():
    """Circle extrude requires diameter and height."""
    required = get_required_measurements_for_pattern("circle_extrude")

    assert "diameter" in required or "radius" in required
    assert "height" in required

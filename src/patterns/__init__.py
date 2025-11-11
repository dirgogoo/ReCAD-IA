"""
Pattern registry system for ReCAD geometric pattern detection.

This module provides the auto-registration mechanism for pattern detectors.
New patterns are automatically registered when their module is imported.
"""

from typing import List, Dict, Any
from .base import GeometricPattern, PatternMatch

# Global registry of all pattern detectors
_PATTERN_REGISTRY: List[GeometricPattern] = []


def register_pattern(cls):
    """
    Decorator to automatically register pattern classes.

    Usage:
        @register_pattern
        class MyPattern(GeometricPattern):
            ...

    Args:
        cls: Pattern class to register

    Returns:
        The same class (decorator doesn't modify it)
    """
    _PATTERN_REGISTRY.append(cls())
    return cls


def get_registered_patterns() -> List[GeometricPattern]:
    """
    Get all registered patterns sorted by priority (highest first).

    Returns:
        List of GeometricPattern instances in priority order
    """
    return sorted(_PATTERN_REGISTRY, key=lambda p: p.priority, reverse=True)


def get_pattern_catalog() -> List[Dict[str, Any]]:
    """
    Get catalog of all registered patterns for Claude LLM analysis.

    Returns:
        List of pattern metadata dicts with name, priority, description, indicators
    """
    patterns = get_registered_patterns()
    return [
        {
            "name": p.name,
            "priority": p.priority,
            "description": p.description,
            "indicators": p.detection_indicators
        }
        for p in patterns
    ]


# Import all pattern implementations to trigger auto-registration
# Add new imports here as new patterns are created
from .chord_cut import ChordCutPattern
from .hole import HolePattern
from .polar_hole import PolarHolePattern
from .counterbore import CounterborePattern
from .countersink import CountersinkPattern
from .slot import SlotPattern

# Export public API
__all__ = [
    'GeometricPattern',
    'PatternMatch',
    'register_pattern',
    'get_registered_patterns',
    'get_pattern_catalog',
    'ChordCutPattern',
    'HolePattern',
    'PolarHolePattern',
    'CounterborePattern',
    'CountersinkPattern',
    'SlotPattern',
]

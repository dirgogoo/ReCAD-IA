"""Tests for interactive measurement prompts."""
import pytest
from unittest.mock import patch
from utils.interactive_prompt import prompt_for_missing_measurements


def test_prompt_for_single_measurement():
    """Should prompt user for single missing measurement."""
    with patch('builtins.input', return_value='78'):
        result = prompt_for_missing_measurements(["flat_to_flat"])

    assert result["flat_to_flat"] == 78.0


def test_prompt_for_multiple_measurements():
    """Should prompt for each missing measurement."""
    with patch('builtins.input', side_effect=['90', '27']):
        result = prompt_for_missing_measurements(["diameter", "height"])

    assert result["diameter"] == 90.0
    assert result["height"] == 27.0


def test_prompt_handles_invalid_input():
    """Should re-prompt on invalid input."""
    with patch('builtins.input', side_effect=['invalid', '78']):
        result = prompt_for_missing_measurements(["flat_to_flat"])

    assert result["flat_to_flat"] == 78.0

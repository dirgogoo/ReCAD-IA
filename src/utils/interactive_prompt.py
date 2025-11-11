"""
Interactive CLI prompts for missing measurements.
"""
from typing import Dict, List


# Portuguese measurement name translations
MEASUREMENT_NAMES_PT = {
    "diameter": "diâmetro",
    "radius": "raio",
    "height": "altura",
    "width": "largura",
    "depth": "profundidade",
    "distance": "distância",
    "flat_to_flat": "distância entre linhas paralelas (flat-to-flat)",
}


def prompt_for_missing_measurements(missing: List[str]) -> Dict[str, float]:
    """
    Prompt user for missing measurements via CLI.

    Args:
        missing: List of missing measurement names

    Returns:
        Dict mapping measurement names to user-provided values
    """
    print(f"\n{'='*70}")
    print(f"  [INPUT REQUIRED] Missing Measurements")
    print(f"{'='*70}\n")
    print(f"  The audio transcription is missing {len(missing)} critical measurement(s).")
    print(f"  Please provide the following values (in mm):\n")

    measurements = {}

    for measurement_name in missing:
        # Get Portuguese name if available
        display_name = MEASUREMENT_NAMES_PT.get(measurement_name, measurement_name)

        while True:
            try:
                value_str = input(f"  {display_name} (mm): ").strip()
                value = float(value_str)

                if value <= 0:
                    print(f"    [ERROR] Value must be positive. Try again.")
                    continue

                measurements[measurement_name] = value
                break

            except ValueError:
                print(f"    [ERROR] Invalid number. Please enter a numeric value.")
            except (KeyboardInterrupt, EOFError):
                print(f"\n  [CANCELLED] User cancelled input.")
                raise RuntimeError("User cancelled measurement input")

    print(f"\n{'='*70}")
    print(f"  [OK] All measurements provided. Continuing...")
    print(f"{'='*70}\n")

    return measurements


def format_measurement_prompt(
    missing: List[str],
    transcription: str,
    detected_pattern: str
) -> str:
    """
    Format a helpful prompt message for missing measurements.

    Args:
        missing: List of missing measurement names
        transcription: Original transcription text
        detected_pattern: Detected pattern name

    Returns:
        Formatted message string
    """
    msg = (
        f"Pattern: {detected_pattern}\n"
        f"Transcription: \"{transcription}\"\n\n"
        f"Missing measurements: {', '.join(missing)}\n\n"
        f"The system detected a {detected_pattern} pattern but could not extract "
        f"the following measurements from your audio:\n"
    )

    for measurement_name in missing:
        display_name = MEASUREMENT_NAMES_PT.get(measurement_name, measurement_name)
        msg += f"  - {display_name}\n"

    return msg

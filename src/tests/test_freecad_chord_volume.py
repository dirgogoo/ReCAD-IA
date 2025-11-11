import pytest
import json
from pathlib import Path
import subprocess

@pytest.mark.freecad
def test_chord_cut_cad_volume_accuracy():
    """Test that FreeCAD export produces correct volume for chord cut"""
    # ARRANGE: Load semantic.json from integration test
    semantic_path = Path(r"C:\Users\conta\.claude\skills\recad\src\docs\outputs\recad\2025-11-06_195554\semantic.json")

    if not semantic_path.exists():
        pytest.skip("semantic.json from integration test not found")

    # Expected volume calculation for chord cut
    # Cylinder: π × r² × h where r=45mm, h=5mm
    # Full circle: π × 45² × 5 = 31,809 mm³
    # Chord cuts with geometry (2 arcs + 2 lines): ~21,817 mm³
    # This represents 68.6% of full circle (31.4% material removed)
    expected_volume_min = 21000  # mm³
    expected_volume_max = 23000  # mm³

    # ACT: Export to FreeCAD and measure volume
    output_fcstd = semantic_path.parent / "test_chord_volume.FCStd"

    freecad_script = f"""
import sys
sys.path.insert(0, r'C:\\Users\\conta\\semantic-geometry')
from semantic_geometry.freecad_export import convert_to_freecad
import json

with open(r'{semantic_path}') as f:
    part = json.load(f)

output_path = r'{output_fcstd}'
success = convert_to_freecad(part, output_path)

if success:
    import FreeCAD
    doc = FreeCAD.openDocument(output_path)
    body = doc.getObject('Body')

    if body and hasattr(body, 'Shape'):
        volume = body.Shape.Volume
        print(f'VOLUME={{volume:.2f}}')

    FreeCAD.closeDocument(doc.Name)
"""

    result = subprocess.run(
        [r"C:\Users\conta\Downloads\FreeCAD_1.0.2-conda-Windows-x86_64-py311\bin\freecadcmd.exe", "-c", freecad_script],
        capture_output=True,
        text=True,
        timeout=60
    )

    # ASSERT: Extract volume from output
    output = result.stdout
    volume_lines = [line for line in output.split('\n') if 'VOLUME=' in line]

    if not volume_lines:
        pytest.fail(f"No volume output found. stdout: {output}\nstderr: {result.stderr}")

    volume_line = volume_lines[0]
    actual_volume = float(volume_line.split('=')[1])

    assert expected_volume_min <= actual_volume <= expected_volume_max, \
        f"Volume {actual_volume:.2f} mm³ outside expected range [{expected_volume_min}, {expected_volume_max}]"

    # Calculate error percentage
    expected_volume = 21816.68  # FreeCAD measured volume (baseline)
    error_pct = abs(actual_volume - expected_volume) / expected_volume * 100

    print(f"[OK] Volume validation passed!")
    print(f"   Expected: {expected_volume:.2f} mm3")
    print(f"   Actual: {actual_volume:.2f} mm3")
    print(f"   Error: {error_pct:.2f}%")

    assert error_pct < 1.0, f"Volume error {error_pct:.2f}% exceeds 1% tolerance"

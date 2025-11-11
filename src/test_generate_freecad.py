#!/usr/bin/env python
"""Test FreeCAD generation with fixed counterbore handling"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from cad_export import convert_to_freecad

# Load semantic.json
semantic_file = Path(__file__).parent / 'docs/outputs/recad/2025-11-10_160705/semantic.json'
output_file = Path(__file__).parent / 'docs/outputs/recad/2025-11-10_160705/test_fixed_counterbore.FCStd'

print(f"Loading semantic.json from: {semantic_file}")
with open(semantic_file, 'r') as f:
    semantic_json = json.load(f)

# Show Cut features
cuts = [f for f in semantic_json['part']['features'] if f['type'] == 'Cut']
print(f'\n[INFO] Found {len(cuts)} Cut features:')
for cut in cuts:
    cut_id = cut.get('id')
    diameter = cut['sketch']['geometry'][0]['diameter']['value']
    cut_type = cut['parameters'].get('cut_type', 'unknown')
    distance = cut['parameters'].get('distance', {}).get('value', 'N/A')
    print(f'  - {cut_id}: Ø{diameter}mm, cut_type={cut_type}, distance={distance}mm')

print(f"\nGenerating FreeCAD file: {output_file}")
success = convert_to_freecad(semantic_json, str(output_file))

if success:
    print('\n[OK] FreeCAD file generated successfully!')
    print(f'[OK] File saved to: {output_file}')
else:
    print('\n[ERROR] FreeCAD generation failed!')
    sys.exit(1)

#!/usr/bin/env python
"""Direct FreeCAD test - no complex imports"""
import sys
import json
from pathlib import Path

# Add FreeCAD to path
FREECAD_PATH = "C:/Users/conta/Downloads/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin"
if FREECAD_PATH not in sys.path:
    sys.path.append(FREECAD_PATH)

import FreeCAD
import Part
import Sketcher

# Load semantic.json
semantic_file = Path(r'C:\Users\conta\.claude\skills\recad\src\docs\outputs\recad\2025-11-10_160705\semantic.json')
output_file = Path(r'C:\Users\conta\.claude\skills\recad\src\docs\outputs\recad\2025-11-10_160705\test_fixed_counterbore.FCStd')

print(f"Loading: {semantic_file}")
with open(semantic_file, 'r') as f:
    data = json.load(f)

part_data = data['part']
features = part_data['features']

# Show Cut features
cuts = [f for f in features if f['type'] == 'Cut']
print(f'\nFound {len(cuts)} Cut features:')
for cut in cuts:
    cut_id = cut.get('id')
    diameter = cut['sketch']['geometry'][0]['diameter']['value']
    cut_type = cut['parameters'].get('cut_type', 'unknown')
    distance = cut['parameters'].get('distance', {}).get('value', 'N/A')
    print(f'  {cut_id}: O{diameter}mm, cut_type={cut_type}, distance={distance}mm')

# Create FreeCAD document
doc_name = "test_counterbore"
doc = FreeCAD.newDocument(doc_name)
body = doc.addObject("PartDesign::Body", "Body")

print(f"\nGenerating FreeCAD model...")

previous_feature = None

for idx, feature in enumerate(features):
    feature_type = feature.get('type')
    parameters = feature.get('parameters', {})
    sketch_data = feature.get('sketch', {})
    geometry_list = sketch_data.get('geometry', [])

    # Create sketch
    sketch = doc.addObject("Sketcher::SketchObject", f"Sketch_{idx + 1}")
    body.addObject(sketch)

    # Attach to previous feature or work plane
    if previous_feature:
        sketch.MapMode = 'FlatFace'
        sketch.Support = [(previous_feature, 'Face1')]

    # Add geometry
    for geom in geometry_list:
        geom_type = geom.get('type')

        if geom_type == 'Circle':
            center = geom.get('center', {'x': 0, 'y': 0})
            cx = center.get('x', 0)
            cy = center.get('y', 0)

            diameter_obj = geom.get('diameter')
            if diameter_obj:
                if isinstance(diameter_obj, dict):
                    diameter = diameter_obj.get('value')
                else:
                    diameter = diameter_obj
                radius = diameter / 2.0
            else:
                radius_obj = geom.get('radius')
                if isinstance(radius_obj, dict):
                    radius = radius_obj.get('value')
                else:
                    radius = radius_obj

            circle = Part.Circle(FreeCAD.Vector(cx, cy, 0), FreeCAD.Vector(0, 0, 1), radius)
            sketch.addGeometry(circle, False)

    doc.recompute()

    # Apply operation
    if feature_type == "Extrude":
        distance_param = parameters.get('distance')
        if isinstance(distance_param, dict):
            distance = distance_param.get('value')
        else:
            distance = distance_param

        pad = doc.addObject("PartDesign::Pad", f"Pad_{idx + 1}")
        body.addObject(pad)
        pad.Profile = sketch
        pad.Length = distance
        previous_feature = pad
        print(f"  Created Pad: {distance}mm")

    elif feature_type == "Cut":
        pocket = doc.addObject("PartDesign::Pocket", f"Pocket_{idx + 1}")
        body.addObject(pocket)
        pocket.Profile = sketch

        # THIS IS THE FIX!
        cut_type = parameters.get("cut_type", "through_all")

        if cut_type == "through_all":
            pocket.Type = 1  # ThroughAll
            print(f"  Created Pocket: ThroughAll")
        elif cut_type == "distance":
            distance_param = parameters.get("distance")
            if isinstance(distance_param, dict):
                distance = distance_param.get('value')
            else:
                distance = distance_param

            pocket.Type = 0  # Dimension
            pocket.Length = distance
            print(f"  Created Pocket: {distance}mm depth (FIXED!)")

        previous_feature = pocket

    doc.recompute()

# Final recompute
doc.recompute()

# Save
print(f"\nSaving to: {output_file}")
doc.saveAs(str(output_file))
FreeCAD.closeDocument(doc_name)

print("\n[OK] FreeCAD file generated successfully!")
print(f"[OK] Open in FreeCAD: {output_file}")

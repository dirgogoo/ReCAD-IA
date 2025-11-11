import sys
sys.path.insert(0, r'C:\Users\conta\semantic-geometry')
from semantic_geometry.freecad_export import convert_to_freecad
import json

semantic_path = r'C:\Users\conta\.claude\skills\recad\src\docs\outputs\recad\2025-11-06_195554\semantic.json'

with open(semantic_path) as f:
    part = json.load(f)

output_path = r'C:\Users\conta\.claude\skills\recad\src\docs\outputs\recad\2025-11-06_195554\test_chord_volume.FCStd'
success = convert_to_freecad(part, output_path)

if success:
    import FreeCAD
    doc = FreeCAD.openDocument(output_path)
    body = doc.getObject('Body')

    if body and hasattr(body, 'Shape'):
        shape = body.Shape
        print(f'Volume: {shape.Volume:.2f} mm³')
        print(f'Surface Area: {shape.Area:.2f} mm²')
        
        # Get bounding box
        bb = shape.BoundBox
        print(f'BoundBox: X=[{bb.XMin:.2f}, {bb.XMax:.2f}], Y=[{bb.YMin:.2f}, {bb.YMax:.2f}], Z=[{bb.ZMin:.2f}, {bb.ZMax:.2f}]')
        print(f'Dimensions: {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f} mm')
        
        # Check if it's a solid
        print(f'Is Solid: {shape.isSolid()}')
        print(f'Is Valid: {shape.isValid()}')

    FreeCAD.closeDocument(doc.Name)

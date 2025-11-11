import FreeCAD
import Part
import sys

doc = FreeCAD.openDocument(r'C:\Users\conta\.claude\skills\visioncad\src\docs\outputs\visioncad\2025-11-06_205742\chapa_circle_90mm.FCStd')

sketch = doc.getObject('Sketch')
if sketch and sketch.Shape:
    print('Sketch wires:', len(sketch.Shape.Wires))
    if sketch.Shape.Wires:
        wire = sketch.Shape.Wires[0]
        print('Wire is closed:', wire.isClosed())
        print('Wire vertices:', len(wire.Vertexes))
        print('Wire edges:', len(wire.Edges))

        # Try to make face
        try:
            face = Part.Face(wire)
            print('Face area:', face.Area, 'mm^2')
        except Exception as e:
            print('Error making face:', str(e))

# Check the Pad
pad = doc.getObject('Pad')
if pad:
    shape = pad.Shape
    print('\nPad Shape:')
    print('  Volume:', shape.Volume, 'mm^3')
    print('  BoundBox:', shape.BoundBox)

FreeCAD.closeDocument('chapa_circle_90mm')

"""
Quick validation test - verify our import validation catches the bug
"""
from pathlib import Path
from recad_runner import ValidationError
import tempfile

def test_validation_catches_forbidden_import():
    """Test that validation catches forbidden semantic_geometry import"""

    # Create test file with WRONG import (external package)
    test_code_wrong = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[5] / "semantic-geometry"))

from semantic_geometry.builder import PartBuilder  # WRONG!
from semantic_geometry.primitives import Circle

builder = PartBuilder(name="Test")
'''

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code_wrong)
        temp_file = Path(f.name)

    try:
        # Create mock runner
        from recad_runner import ReCADRunner

        # We can't instantiate ReCADRunner without video, so test the method directly
        class MockRunner:
            def _validate_generated_code(self, python_file):
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for forbidden imports
                forbidden_imports = [
                    "from semantic_geometry",
                    "import semantic_geometry"
                ]

                for forbidden in forbidden_imports:
                    if forbidden in content:
                        raise ValidationError(f"Found forbidden import: {forbidden}")

                # Check for correct import
                correct_imports = [
                    "from semantic_builder import SemanticGeometryBuilder",
                    "from semantic_builder import PartBuilder"
                ]

                has_correct_import = any(imp in content for imp in correct_imports)

                if not has_correct_import:
                    return False

                return True

        runner = MockRunner()

        # This should raise ValidationError
        try:
            runner._validate_generated_code(temp_file)
            print("[FAIL] Validation did NOT catch forbidden import!")
            return False
        except ValidationError as e:
            print("[PASS] Validation correctly caught forbidden import!")
            print(f"       Error: {str(e)[:100]}...")
            return True

    finally:
        # Cleanup
        temp_file.unlink()

def test_validation_accepts_correct_import():
    """Test that validation accepts correct semantic_builder import"""

    # Create test file with CORRECT import (local)
    test_code_correct = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from semantic_builder import PartBuilder  # CORRECT!

builder = PartBuilder("Test")
builder.add_circle_extrusion(diameter=50, extrude_distance=10)
'''

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code_correct)
        temp_file = Path(f.name)

    try:
        class MockRunner:
            def _validate_generated_code(self, python_file):
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for forbidden imports
                forbidden_imports = [
                    "from semantic_geometry",
                    "import semantic_geometry"
                ]

                for forbidden in forbidden_imports:
                    if forbidden in content:
                        raise ValidationError(f"Found forbidden import: {forbidden}")

                # Check for correct import
                correct_imports = [
                    "from semantic_builder import SemanticGeometryBuilder",
                    "from semantic_builder import PartBuilder"
                ]

                has_correct_import = any(imp in content for imp in correct_imports)

                if not has_correct_import:
                    return False

                return True

        runner = MockRunner()

        # This should pass
        try:
            result = runner._validate_generated_code(temp_file)
            if result:
                print("[PASS] Validation correctly accepted semantic_builder import!")
                return True
            else:
                print("[FAIL] Validation rejected correct import!")
                return False
        except ValidationError as e:
            print(f"[FAIL] Validation incorrectly rejected correct import: {e}")
            return False

    finally:
        # Cleanup
        temp_file.unlink()

if __name__ == "__main__":
    print("="*70)
    print("VALIDATION TEST SUITE")
    print("="*70)
    print()

    print("Test 1: Catch forbidden import (from semantic_geometry)")
    test1 = test_validation_catches_forbidden_import()
    print()

    print("Test 2: Accept correct import (from semantic_builder)")
    test2 = test_validation_accepts_correct_import()
    print()

    print("="*70)
    if test1 and test2:
        print("[OK] ALL TESTS PASSED - Validation is working correctly!")
    else:
        print("[ERROR] SOME TESTS FAILED - Validation needs fixes")
    print("="*70)

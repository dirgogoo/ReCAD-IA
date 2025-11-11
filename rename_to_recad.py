#!/usr/bin/env python3
"""
Script to rename all occurrences of visioncad to recad in the visioncad directory.
Does NOT rename the directory itself - that will be done manually later.
"""

import os
import re
from pathlib import Path

# Directory to process
BASE_DIR = Path(__file__).parent

# Directories to exclude
EXCLUDE_DIRS = {
    '.git',
    'outputs',
    '__pycache__'
}

# File extensions to exclude
EXCLUDE_EXTENSIONS = {
    '.png', '.mp4', '.FCStd', '.pyc', '.pyo', '.so', '.dll', '.exe'
}

def should_process_file(file_path):
    """Check if file should be processed."""
    # Skip excluded directories
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False

    # Skip excluded extensions
    if file_path.suffix in EXCLUDE_EXTENSIONS:
        return False

    # Skip this script itself
    if file_path.name == 'rename_to_recad.py':
        return False

    return True

def replace_in_file(file_path):
    """Replace all visioncad variants with recad in a file."""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original_content = content

        # Perform replacements
        # Order matters: do case-sensitive replacements first
        content = content.replace('VISIONCAD', 'RECAD')
        content = content.replace('VisionCAD', 'ReCAD')
        content = content.replace('visioncad', 'recad')

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all files."""
    files_changed = 0
    files_processed = 0

    print("Starting replacement: visioncad -> recad")
    print("=" * 60)

    # Walk through all files
    for file_path in BASE_DIR.rglob('*'):
        if not file_path.is_file():
            continue

        if not should_process_file(file_path):
            continue

        files_processed += 1

        # Process file
        if replace_in_file(file_path):
            files_changed += 1
            rel_path = file_path.relative_to(BASE_DIR)
            print(f"[OK] {rel_path}")

    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Files processed: {files_processed}")
    print(f"  Files changed: {files_changed}")
    print(f"\nReplacements made:")
    print(f"  VISIONCAD -> RECAD")
    print(f"  VisionCAD -> ReCAD")
    print(f"  visioncad -> recad")
    print(f"\nDirectory NOT renamed (do this manually later)")

if __name__ == '__main__':
    main()

"""Nyaya AI — Reports Directory Cleanup Script.

Recursively deletes the 'tests/fixtures/reports/' directory and all files inside it.
"""

import shutil
from pathlib import Path

def main():
    root_dir = Path(__file__).parent.absolute()
    reports_dir = root_dir / "tests" / "fixtures" / "reports"
    
    if reports_dir.exists() and reports_dir.is_dir():
        try:
            shutil.rmtree(reports_dir)
            print(f"✓ Successfully deleted directory: {reports_dir}")
        except Exception as e:
            print(f"✗ Failed to delete directory {reports_dir}: {e}")
    else:
        print(f"- Skipped: Directory {reports_dir} does not exist.")

if __name__ == "__main__":
    main()

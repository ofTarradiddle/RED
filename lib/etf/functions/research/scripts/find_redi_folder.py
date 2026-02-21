"""
Helper script to find the REDI folder on external drive
"""

import sys
from pathlib import Path
import os

print("="*70)
print("Finding REDI Folder on External Drive")
print("="*70)

# Check common locations
possible_locations = [
    Path('/Volumes/My Passport/REDI'),
    Path('/Volumes/My Passport/redi'),
    Path('/Volumes/Passport/REDI'),
    Path('/Volumes/Passport/redi'),
]

print("\nChecking common locations:")
found = False
for loc in possible_locations:
    if loc.exists():
        print(f"✓ Found: {loc}")
        # Test write
        test_file = loc / '.test_write'
        try:
            test_file.write_text('test')
            test_file.unlink()
            print(f"  ✓ Write permissions: OK")
            print(f"\nUse this path in fetch_financial_data.py:")
            print(f"  EXTERNAL_DRIVE_PATH = Path('{loc}')")
            found = True
            break
        except Exception as e:
            print(f"  ✗ Write permissions: {e}")

if not found:
    print("\nREDI folder not found in common locations.")
    print("\nPlease provide the exact path where you created the REDI folder.")
    print("Or update EXTERNAL_DRIVE_PATH in fetch_financial_data.py")


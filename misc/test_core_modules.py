# 
import sys
import os
from pathlib import Path

# Print Python path
print("Python path:")
for p in sys.path:
    print(f"  {p}")

# Check directory structure
project_root = Path(__file__).parent
core_path = project_root / "app" / "core" / "db_operations"
print(f"\nChecking path: {core_path}")
print(f"Path exists: {core_path.exists()}")

# List directories
print("\nDirectories in app:")
app_path = project_root / "app"
if app_path.exists():
    for item in app_path.iterdir():
        if item.is_dir():
            print(f"  {item.name}/")
else:
    print("  app/ directory not found")

# Try importing from settings.py for debugging
print("\nTrying to import settings:")
try:
    from app.config.settings import settings
    print(f"  Settings import successful!")
    print(f"  Flask env: {settings.FLASK_ENV}")
    print(f"  Database URL: {settings.DATABASE_URL}")
except Exception as e:
    print(f"  Error importing settings: {e}")

# Try creating the directory structure
try:
    os.makedirs(core_path, exist_ok=True)
    print(f"\nCreated directory structure: {core_path}")
except Exception as e:
    print(f"\nError creating directories: {e}")
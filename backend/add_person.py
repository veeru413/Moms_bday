"""
add_person.py — Helper script to add a new family member's photos.

Usage:
  python add_person.py "Priya" /path/to/photo1.jpg /path/to/photo2.jpg

This copies the photos into known_faces/Priya/ and then retrains the model
by calling the /api/retrain endpoint.
"""

import sys
import shutil
import requests
from pathlib import Path

API = "http://localhost:8000"
KNOWN_DIR = Path(__file__).parent / "known_faces"

def add_person(name: str, photo_paths: list[str]):
    person_dir = KNOWN_DIR / name
    person_dir.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(photo_paths):
        src_path = Path(src)
        if not src_path.exists():
            print(f"  ⚠ File not found: {src}")
            continue
        ext = src_path.suffix.lower()
        dst = person_dir / f"photo_{i+1}{ext}"
        shutil.copy2(src_path, dst)
        print(f"  ✓ Copied {src_path.name} → {dst}")

    print(f"\n✅ Added {len(photo_paths)} photo(s) for '{name}'")
    print("   Retraining recognizer via API…")

    try:
        res = requests.post(f"{API}/api/retrain", timeout=30)
        data = res.json()
        if data["success"]:
            print(f"   ✅ Retrained. People in DB: {', '.join(data['people'])}")
        else:
            print("   ⚠ Retraining returned no data — check known_faces/ directory.")
    except Exception as e:
        print(f"   ⚠ Could not reach API ({e}). Start the server and run:\n"
              f"      curl -X POST {API}/api/retrain")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_person.py \"Name\" photo1.jpg [photo2.jpg ...]")
        sys.exit(1)
    name   = sys.argv[1]
    photos = sys.argv[2:]
    add_person(name, photos)

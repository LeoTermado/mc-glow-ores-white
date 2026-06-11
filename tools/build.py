#!/usr/bin/env python3
"""Package the resource pack into a distributable zip.

The zip contains the CONTENTS of pack/ at its root: pack.mcmeta and assets/
sit at the top level, not nested inside a pack/ folder. System junk
(.DS_Store, Thumbs.db) and __pycache__ are excluded.

Usage:
    python build.py
"""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = ROOT / "pack"
DIST_DIR = ROOT / "dist"
OUTPUT = DIST_DIR / "glow-ores-v1.0.0.zip"

EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDE_DIRS = {"__pycache__"}


def included(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return False
    if any(part in EXCLUDE_DIRS for part in path.relative_to(PACK_DIR).parts):
        return False
    return True


def main():
    if not PACK_DIR.is_dir():
        raise SystemExit(f"pack/ directory not found at {PACK_DIR}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACK_DIR.rglob("*")):
            if not path.is_file() or not included(path):
                continue
            # arcname is relative to pack/ so its CONTENTS land at the zip root.
            arcname = path.relative_to(PACK_DIR)
            zf.write(path, arcname)
            count += 1

    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({count} files)")


if __name__ == "__main__":
    main()

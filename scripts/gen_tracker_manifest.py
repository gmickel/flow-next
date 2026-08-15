#!/usr/bin/env python3
"""Regenerate flowctl_tracker/MANIFEST.json (fn-139.5, R1/R2).

The manifest is the integrity contract installers verify AFTER copying -
integrity is checked where it can actually run (the installer), never per
command (rejected: it would tax every invocation to catch what installers
already cover). `test_tracker_distribution.py` fails CI whenever the manifest
is stale, which is what keeps this file honest.

Usage: python3 scripts/gen_tracker_manifest.py [--check]
  --check  exit 1 if the manifest on disk is stale (no write)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "plugins" / "flow-next" / "scripts" / "flowctl_tracker"
MANIFEST = PKG / "MANIFEST.json"


def compute(pkg: Path = PKG) -> dict:
    # The manifest REPLACED the old single-file SOURCE_SHA256 pin (fn-139.5):
    # it covers flowctl.py itself plus every package file. Installers verify
    # all of it post-copy; the bootstrap consults only the flowctl.py entry to
    # authenticate its static-help fast path.
    files = [{
        "path": "flowctl.py",
        "sha256": hashlib.sha256((pkg.parent / "flowctl.py").read_bytes()).hexdigest(),
    }]
    for path in sorted(pkg.rglob("*.py")):
        rel = path.relative_to(pkg).as_posix()
        files.append({
            "path": f"flowctl_tracker/{rel}",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return {
        "package": "flowctl_tracker",
        "generated_by": "scripts/gen_tracker_manifest.py",
        "files": files,
    }


def main() -> int:
    current = compute()
    rendered = json.dumps(current, indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv[1:]:
        on_disk = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if on_disk != rendered:
            print("MANIFEST.json is stale; run scripts/gen_tracker_manifest.py",
                  file=sys.stderr)
            return 1
        print("MANIFEST.json is current")
        return 0
    MANIFEST.write_text(rendered, encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(REPO)} ({len(current['files'])} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

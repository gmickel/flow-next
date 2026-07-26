#!/usr/bin/env python3
"""Post-copy flowctl_tracker manifest verification (fn-139.5, R1).

Called by every installer (install-codex.sh, install-cursor.sh, copy-mode
setup, ralph-init) AFTER copying, with the directory that should contain
`flowctl_tracker/` as argv[1]. Integrity is verified where it can actually
run - the installer - and fails loudly there, instead of surfacing later as
an ImportError mid-command. There is deliberately NO per-command hashing.

Exit 0: verified. Exit 1: mismatch/missing (the copy is corrupt).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_tracker_manifest.py <dir-containing-flowctl_tracker>",
              file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    manifest_path = root / "flowctl_tracker" / "MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"flowctl_tracker manifest unreadable at {manifest_path}: {exc}",
              file=sys.stderr)
        return 1
    bad = []
    for entry in manifest.get("files", []):
        target = root / entry["path"]
        if not target.is_file():
            bad.append(f"{entry['path']} (missing)")
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            bad.append(f"{entry['path']} (hash mismatch)")
    if bad:
        print("flowctl_tracker manifest verification FAILED:\n  "
              + "\n  ".join(bad), file=sys.stderr)
        return 1
    print(f"flowctl_tracker package verified ({len(manifest.get('files', []))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

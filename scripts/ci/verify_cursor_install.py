#!/usr/bin/env python3
"""Verify a Cursor local-install produced by install-cursor.sh / install-cursor.ps1.

CI-only smoke helper (NOT part of the unittest suite — it reads the real
~/.cursor/plugins/local/flow-next that the installer just wrote, so it must not
run as part of a developer's local `unittest discover`).

The CI workflow runs the platform's installer, then runs this. It asserts the
install is COMPLETE and CLEAN by comparing against the source tree instead of
hardcoding counts (so adding a skill/command/agent doesn't break the smoke):

  - the .cursor-plugin/plugin.json manifest is present;
  - dest skill dirs / command files / agent files match the source 1:1;
  - the excluded payload (codex/, tests/, *.pyc) did NOT leak into the install.

Exit 0 on success; exit 1 with a diagnostic on any mismatch.

Usage:
    python scripts/ci/verify_cursor_install.py [--dest <path>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]                       # repo root (scripts/ci/ -> ../../)
SRC = REPO_ROOT / "plugins" / "flow-next"


def _skill_dirs(root: Path) -> set[str]:
    base = root / "skills"
    if not base.is_dir():
        return set()
    return {p.name for p in base.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}


def _command_files(root: Path) -> set[str]:
    base = root / "commands" / "flow-next"
    if not base.is_dir():
        return set()
    return {p.name for p in base.glob("*.md")}


def _agent_files(root: Path) -> set[str]:
    base = root / "agents"
    if not base.is_dir():
        return set()
    return {p.name for p in base.glob("*.md")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dest",
        default=str(Path.home() / ".cursor" / "plugins" / "local" / "flow-next"),
        help="install destination (default: ~/.cursor/plugins/local/flow-next)",
    )
    args = parser.parse_args()
    dest = Path(args.dest)

    errors: list[str] = []

    if not dest.is_dir():
        print(f"FAIL: install dest does not exist: {dest}", file=sys.stderr)
        return 1
    if dest.is_symlink():
        errors.append(f"dest is a symlink (Cursor rejects these): {dest}")

    # Manifest present.
    if not (dest / ".cursor-plugin" / "plugin.json").is_file():
        errors.append("missing .cursor-plugin/plugin.json manifest")

    # Completeness: dest must match source 1:1 for the copied component trees.
    for label, fn in (
        ("skills", _skill_dirs),
        ("commands", _command_files),
        ("agents", _agent_files),
    ):
        src_set, dst_set = fn(SRC), fn(dest)
        if not src_set:
            errors.append(f"source has no {label} — cannot verify (check SRC path)")
            continue
        missing = src_set - dst_set
        extra = dst_set - src_set
        if missing:
            errors.append(f"{label}: {len(missing)} missing in install: {sorted(missing)[:5]}")
        if extra:
            errors.append(f"{label}: {len(extra)} unexpected in install: {sorted(extra)[:5]}")

    # Cleanliness: excluded payload must NOT have leaked in.
    if (dest / "codex").exists():
        errors.append("codex/ mirror leaked into the install (should be excluded)")
    if (dest / "tests").exists():
        errors.append("tests/ leaked into the install (should be excluded)")
    pyc = next(dest.rglob("*.pyc"), None)
    if pyc is not None:
        errors.append(f"*.pyc leaked into the install (should be excluded): {pyc}")

    if errors:
        print("FAIL: Cursor install verification found problems:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"OK: Cursor install verified at {dest}\n"
        f"    skills={len(_skill_dirs(dest))} "
        f"commands={len(_command_files(dest))} "
        f"agents={len(_agent_files(dest))}; "
        f"excludes honored (no codex/ tests/ *.pyc)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

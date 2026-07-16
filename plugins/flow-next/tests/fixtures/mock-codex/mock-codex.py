#!/usr/bin/env python3
"""Mock-codex fixture (fn-55.4) — a deterministic stub standing in for a real
``codex exec`` delegation run, so the classification + rollback-path tests have
canned ``result-batch-*.json`` + exit codes for each of the 5 classification
rows (plus the malformed / missing variants) WITHOUT a real model.

It does not pretend to be the full ``codex exec`` CLI — it only emits the
proof-of-work artifacts the deterministic flowctl helpers
(``codex classify-result`` / ``codex rollback-plan``) consume: a result JSON file
and a process exit code. The classifier + rollback computations are pure, so this
fixture is sufficient to drive every branch.

Usage::

    mock-codex.py --row <row> --out <result-file> [--create-file <path> ...]

``--row`` selects the canned outcome:

    completed        → status:"completed", exit 0  (success → commit)
    partial          → status:"partial",   exit 0  (partial → finish_locally)
    failed           → status:"failed",    exit 0  (task_failure → rollback)
    malformed        → invalid JSON,        exit 0  (task_failure → rollback)
    missing          → NO result file,      exit 0  (task_failure → rollback)
    cli_failure      → status:"completed", exit 1  (cli_failure → rollback_and_disable)

``--create-file`` optionally creates untracked files on disk (relative to CWD),
simulating Codex having written code — used by the rollback-path tests to build a
realistic post-snapshot. Repeatable. Parent directories are created.

This is a fixture, never shipped to consumers — it lives under tests/fixtures/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Canned result bodies keyed by row. ``files_modified`` mirrors any --create-file
# paths the caller passes so the trust cross-check has something to chew on.
_ROWS = {
    "completed": ("completed", 0, True),
    "partial": ("partial", 0, True),
    "failed": ("failed", 0, True),
    "cli_failure": ("completed", 1, True),  # status irrelevant — exit wins
    "malformed": (None, 0, "malformed"),
    "missing": (None, 0, "missing"),
}


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Mock codex delegation stub")
    ap.add_argument("--row", required=True, choices=sorted(_ROWS))
    ap.add_argument("--out", required=True, help="Result JSON output path")
    ap.add_argument(
        "--create-file",
        action="append",
        default=[],
        help="Untracked file(s) to create (relative to CWD), repeatable",
    )
    args = ap.parse_args(argv)

    # Simulate Codex writing code (untracked files for the rollback snapshot).
    created = []
    for rel in args.create_file:
        p = Path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("// codex-written\n", encoding="utf-8")
        created.append(rel)

    status, exit_code, body = _ROWS[args.row]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if body == "missing":
        # Emit nothing — classifier must treat absent file as malformed.
        pass
    elif body == "malformed":
        out.write_text("not valid json {", encoding="utf-8")
    else:
        result = {
            "status": status,
            "files_modified": created,
            "issues": [] if status == "completed" else ["follow-up"],
            "summary": f"mock {args.row}",
            "verification_summary": "mock verification",
        }
        out.write_text(json.dumps(result), encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Build the fn-141 tracker prose-teardown candidate delta artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import character


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
B1_ROOT = HERE / "fixtures" / "b1"
B1_INDEX = B1_ROOT / "INDEX.json"
DEFAULT_OUTPUT = HERE / "tracker-teardown-candidate.json"
TASK_ID = "fn-141-tracker-determinism-c-prose-teardown.5"


def _stable_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _git_text(commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_commit(commit: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{commit}}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_artifact(source_commit: str) -> dict[str, Any]:
    """Measure candidate bytes against every immutable B1 tracker fixture."""
    candidate_commit = _git_commit(source_commit)
    index = json.loads(B1_INDEX.read_text(encoding="utf-8"))
    tracker_rows = sorted(
        (row for row in index["fixtures"] if row["cluster"] == "tracker"),
        key=lambda row: row["fixture_id"],
    )
    fixtures: list[dict[str, Any]] = []

    for row in tracker_rows:
        manifest = json.loads((HERE / row["path"]).read_text(encoding="utf-8"))
        activated_paths = manifest["required_reads"]
        root_path, *reference_paths = activated_paths
        metrics = character.compute_reached_path(
            root_skill_text=_git_text(candidate_commit, root_path),
            root_skill_path=root_path,
            activated=[
                (path, _git_text(candidate_commit, path))
                for path in reference_paths
            ],
        )
        before_chars = manifest["metrics"]["reached_path_chars"]
        after_chars = metrics["reached_path_chars"]
        fixtures.append(
            {
                "fixture_id": manifest["fixture_id"],
                "b1_manifest": row["path"],
                "b1_fixture_hash": manifest["fixture_hash"],
                "activated_paths": activated_paths,
                "before_reached_path_chars": before_chars,
                "after_reached_path_chars": after_chars,
                "reduction_chars": before_chars - after_chars,
                "reduction_percent": round(
                    100 * (before_chars - after_chars) / before_chars, 2
                ),
                "candidate_prompt_hashes": {
                    item["path"]: item["content_hash"] for item in metrics["files"]
                },
            }
        )

    return {
        "schema_version": 1,
        "task": TASK_ID,
        "classification": "CANDIDATE",
        "b2_introduced": False,
        "lineage": {
            "baseline": "V1/B1",
            "baseline_commit": index["baseline_commit"],
            "baseline_index_sha256": _sha256(B1_INDEX),
            "candidate_source_commit": candidate_commit,
            "rule": (
                "B1 is immutable; candidate compares the same activated-file "
                "inventory to post-teardown source bytes"
            ),
        },
        "measurement": {
            "algorithm": index["algorithm"],
            "fixture_count": len(fixtures),
            "command": (
                "python3 optimization/reached-path/tracker_candidate.py "
                f"--source-commit {candidate_commit} --check"
            ),
            "backend_telemetry": None,
        },
        "rationale": (
            "Reduction by design, not regression: fn-141 moved deterministic "
            "tracker transport out of agent instructions while preserving the "
            "B1 fixture inventory and reached behavior."
        ),
        "fixtures": fixtures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = _stable_json(build_artifact(args.source_commit))
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"missing candidate artifact: {args.output}")
        if args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"candidate artifact is stale: {args.output}")
        print(f"OK: {args.output.relative_to(REPO_ROOT)} is reproducible")
        return 0

    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

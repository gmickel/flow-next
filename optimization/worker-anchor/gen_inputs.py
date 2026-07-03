#!/usr/bin/env python3
"""Freeze the comprehension-eval inputs for the worker-anchor harness (fn-83.3).

For each frozen task this writes, under ``inputs/<short-id>/``:

- ``bundle.md``    — ``flowctl anchor <task-id> --md`` (the bundle arm)
- ``statusquo.md`` — a worker Phase-1 transcript: each read the worker runs
  today (agents/worker.md:21-68, same order), rendered as ``$ <command>``
  followed by its verbatim output (the status-quo arm)

plus ``inputs/manifest.json`` recording the generation SHA/date. Both arms
are generated back-to-back from the SAME working-tree state, so the only
difference between them is PACKAGING — which is exactly what the eval
measures. Inputs are FROZEN once committed: regenerate only to add NEW
tasks (append-only, like every optimization/ corpus).

Run from the repo root:  python3 optimization/worker-anchor/gen_inputs.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
FLOWCTL = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"

# Frozen task set — varied size, three different specs, all with deps.
TASKS = {
    "fn-64.3": {
        "task_id": "fn-64-tracker-sync-project-flow-spec.3",
        "spec_id": "fn-64-tracker-sync-project-flow-spec",
    },
    "fn-74.2": {
        "task_id": "fn-74-cursor-review-backend-cursor-agent-cli.2",
        "spec_id": "fn-74-cursor-review-backend-cursor-agent-cli",
    },
    "fn-81.2": {
        "task_id": "fn-81-skill-runtime-token-plumbing-single.2",
        "spec_id": "fn-81-skill-runtime-token-plumbing-single",
    },
}


def _run(argv: list) -> str:
    result = subprocess.run(
        argv, cwd=str(REPO_ROOT), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"{result.stderr}"
        )
    return result.stdout


def _flowctl(*args: str) -> str:
    return _run([sys.executable, str(FLOWCTL)] + list(args))


def _statusquo_transcript(task_id: str, spec_id: str) -> str:
    """The worker Phase-1 reads exactly as worker.md:21-68 runs them."""
    reads = [
        (f"flowctl show {task_id} --json", ("show", task_id, "--json")),
        (f"flowctl cat {task_id}", ("cat", task_id)),
        (f"flowctl show {spec_id} --json", ("show", spec_id, "--json")),
        (f"flowctl cat {spec_id}", ("cat", spec_id)),
    ]
    chunks = []
    for label, argv in reads:
        chunks.append(f"$ {label}\n{_flowctl(*argv)}")
    chunks.append("$ git status\n" + _run(["git", "status"]))
    chunks.append(
        "$ git log -5 --oneline\n" + _run(["git", "log", "-5", "--oneline"])
    )
    chunks.append(
        "$ flowctl config get memory.enabled --json\n"
        + _flowctl("config", "get", "memory.enabled", "--json")
    )
    chunks.append(
        "$ flowctl memory list --json\n" + _flowctl("memory", "list", "--json")
    )
    chunks.append(
        "$ flowctl glossary list --json\n"
        + _flowctl("glossary", "list", "--json")
    )
    return "\n".join(chunks)


def main() -> None:
    inputs = HERE / "inputs"
    manifest = {
        "generated": date.today().isoformat(),
        "head": _run(["git", "rev-parse", "HEAD"]).strip(),
        "tasks": TASKS,
    }
    for short, ids in TASKS.items():
        out_dir = inputs / short
        out_dir.mkdir(parents=True, exist_ok=True)
        bundle = _flowctl("anchor", ids["task_id"], "--md")
        statusquo = _statusquo_transcript(ids["task_id"], ids["spec_id"])
        (out_dir / "bundle.md").write_text(bundle, encoding="utf-8")
        (out_dir / "statusquo.md").write_text(statusquo, encoding="utf-8")
        print(
            f"{short}: bundle {len(bundle)} chars, statusquo "
            f"{len(statusquo)} chars"
        )
    (inputs / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest @ {manifest['head'][:12]}")


if __name__ == "__main__":
    main()

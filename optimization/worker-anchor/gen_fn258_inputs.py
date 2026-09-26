#!/usr/bin/env python3
"""Freeze the fn-258 R1 parity inputs: current bundle vs lean bundle.

fn-258 R1 changes what the anchor bundle carries (text memory index, glossary
entries matching the task, spec record without its review/tracker ledgers,
short git status). Its merge gate is this harness's comprehension key, re-run
on two arms generated back-to-back from ONE working-tree state:

- ``bundle-current.md`` — ``flowctl anchor <id> --md`` from the pre-change
  flowctl (``--base-flowctl``: the fn-258 base commit's ``flowctl.py``)
- ``bundle-lean.md``    — the same call from this checkout's flowctl

Both arms read the same ``.flow/`` state (cwd = this repo root), so the only
difference is what the bundle carries. The frozen fn-83 inputs and the answer
key are untouched (append-only).

Run from the repo root:
  python3 optimization/worker-anchor/gen_fn258_inputs.py --base-flowctl <path>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
LEAN_FLOWCTL = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"
KEY = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))


def _anchor(flowctl: Path, task_id: str) -> str:
    result = subprocess.run(
        [sys.executable, str(flowctl), "anchor", task_id, "--md"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"anchor failed ({flowctl}): {result.stderr}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-flowctl", type=Path, required=True)
    args = parser.parse_args()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    for short, entry in KEY["tasks"].items():
        out_dir = HERE / "inputs" / short
        for arm, flowctl in (
            ("bundle-current", args.base_flowctl),
            ("bundle-lean", LEAN_FLOWCTL),
        ):
            text = _anchor(flowctl, entry["task_id"])
            (out_dir / f"{arm}.md").write_text(text, encoding="utf-8")
            print(f"{short} {arm}: {len(text)} chars")
    (HERE / "inputs" / "manifest-fn258.json").write_text(
        json.dumps(
            {"generated": date.today().isoformat(), "head": head,
             "arms": ["bundle-current", "bundle-lean"]},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

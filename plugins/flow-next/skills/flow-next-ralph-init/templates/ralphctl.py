#!/usr/bin/env python3
"""Ralph run control CLI (repo-local after /flow-next:ralph-init).

Commands: pause, resume, stop, status. Operates on scripts/ralph/runs/
sentinels (PAUSE / STOP) and progress.txt.

Installed under scripts/ralph/ by /flow-next:ralph-init. Not part of
flowctl core (fn-114 extraction). flowctl status soft-probes the runs
directory for display only; control lives here.

Usage:
    ./scripts/ralph/ralphctl.py status [--run <id>] [--json]
    ./scripts/ralph/ralphctl.py pause  [--run <id>] [--json]
    ./scripts/ralph/ralphctl.py resume [--run <id>] [--json]
    ./scripts/ralph/ralphctl.py stop   [--run <id>] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_repo_root() -> Path:
    """Find git repo root; fall back to cwd."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def json_output(data: dict, success: bool = True) -> None:
    result = {"success": success, **data}
    print(json.dumps(result, indent=2, default=str))


def error_exit(message: str, code: int = 1, use_json: bool = True) -> None:
    if use_json:
        json_output({"error": message}, success=False)
    else:
        print(f"Error: {message}", file=sys.stderr)
    sys.exit(code)


def find_active_runs() -> list[dict]:
    """
    Find active Ralph runs by scanning scripts/ralph/runs/*/progress.txt.
    A run is active if progress.txt exists AND does NOT contain both
    completion_reason= and promise=COMPLETE.
    Returns list of dicts with run info.
    """
    repo_root = get_repo_root()
    runs_dir = repo_root / "scripts" / "ralph" / "runs"
    active_runs: list[dict] = []

    if not runs_dir.exists():
        return active_runs

    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        progress_file = run_dir / "progress.txt"
        if not progress_file.exists():
            continue

        content = progress_file.read_text(encoding="utf-8", errors="replace")

        # Require both completion_reason= AND promise=COMPLETE to avoid
        # false positives from per-iteration promise= logging
        if "completion_reason=" in content and "promise=COMPLETE" in content:
            continue

        run_info = {
            "id": run_dir.name,
            "path": str(run_dir),
            "iteration": None,
            "current_epic": None,
            "current_task": None,
            "paused": (run_dir / "PAUSE").exists(),
            "stopped": (run_dir / "STOP").exists(),
        }

        iter_match = re.search(r"iteration[:\s]+(\d+)", content, re.IGNORECASE)
        if iter_match:
            run_info["iteration"] = int(iter_match.group(1))

        epic_match = re.search(r"epic[:\s]+(fn-[\w-]+)", content, re.IGNORECASE)
        if epic_match:
            run_info["current_epic"] = epic_match.group(1)

        task_match = re.search(r"task[:\s]+(fn-[\w.-]+\.\d+)", content, re.IGNORECASE)
        if task_match:
            run_info["current_task"] = task_match.group(1)

        active_runs.append(run_info)

    return active_runs


def find_active_run(
    run_id: Optional[str] = None, use_json: bool = False
) -> tuple[str, Path]:
    """
    Find a single active run. Auto-detect if run_id is None.
    Returns (run_id, run_dir) tuple.
    """
    runs = find_active_runs()
    if run_id:
        matches = [r for r in runs if r["id"] == run_id]
        if not matches:
            error_exit(f"Run {run_id} not found or not active", use_json=use_json)
        return matches[0]["id"], Path(matches[0]["path"])
    if len(runs) == 0:
        error_exit("No active runs", use_json=use_json)
    if len(runs) > 1:
        ids = ", ".join(r["id"] for r in runs)
        error_exit(f"Multiple active runs, specify --run: {ids}", use_json=use_json)
    return runs[0]["id"], Path(runs[0]["path"])


def cmd_pause(args: argparse.Namespace) -> None:
    """Pause a Ralph run."""
    run_id, run_dir = find_active_run(args.run, use_json=args.json)
    (run_dir / "PAUSE").touch()
    if args.json:
        json_output({"run": run_id, "action": "paused"})
    else:
        print(f"Paused {run_id}")


def cmd_resume(args: argparse.Namespace) -> None:
    """Resume a paused Ralph run."""
    run_id, run_dir = find_active_run(args.run, use_json=args.json)
    (run_dir / "PAUSE").unlink(missing_ok=True)
    if args.json:
        json_output({"run": run_id, "action": "resumed"})
    else:
        print(f"Resumed {run_id}")


def cmd_stop(args: argparse.Namespace) -> None:
    """Request a Ralph run to stop."""
    run_id, run_dir = find_active_run(args.run, use_json=args.json)
    (run_dir / "STOP").touch()
    if args.json:
        json_output({"run": run_id, "action": "stop_requested"})
    else:
        print(f"Stop requested for {run_id}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show Ralph run status."""
    run_id, run_dir = find_active_run(args.run, use_json=args.json)
    paused = (run_dir / "PAUSE").exists()
    stopped = (run_dir / "STOP").exists()

    progress_file = run_dir / "progress.txt"
    iteration = None
    current_epic = None
    current_task = None

    if progress_file.exists():
        content = progress_file.read_text(encoding="utf-8", errors="replace")
        iter_match = re.search(r"iteration[:\s]+(\d+)", content, re.IGNORECASE)
        if iter_match:
            iteration = int(iter_match.group(1))
        epic_match = re.search(r"epic[:\s]+(fn-[\w-]+)", content, re.IGNORECASE)
        if epic_match:
            current_epic = epic_match.group(1)
        task_match = re.search(r"task[:\s]+(fn-[\w.-]+\.\d+)", content, re.IGNORECASE)
        if task_match:
            current_task = task_match.group(1)

    if args.json:
        json_output(
            {
                "run": run_id,
                "iteration": iteration,
                "current_spec": current_epic,
                "current_task": current_task,
                "paused": paused,
                "stopped": stopped,
            }
        )
    else:
        state = []
        if paused:
            state.append("PAUSED")
        if stopped:
            state.append("STOPPED")
        state_str = f" [{', '.join(state)}]" if state else " [running]"
        task_info = ""
        if current_task:
            task_info = f", working on {current_task}"
        elif current_epic:
            task_info = f", epic {current_epic}"
        iter_info = f"iteration {iteration}" if iteration else "starting"
        print(f"{run_id} ({iter_info}{task_info}){state_str}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ralphctl",
        description="Ralph run control (pause/resume/stop/status)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, help_text, func in (
        ("pause", "Pause a Ralph run", cmd_pause),
        ("resume", "Resume a paused Ralph run", cmd_resume),
        ("stop", "Request a Ralph run to stop", cmd_stop),
        ("status", "Show Ralph run status", cmd_status),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--run", help="Run ID (auto-detect if single)")
        p.add_argument("--json", action="store_true", help="JSON output")
        p.set_defaults(func=func)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

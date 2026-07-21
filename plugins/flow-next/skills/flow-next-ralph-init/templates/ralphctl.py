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


def parse_progress_kv(content: str) -> dict[str, str]:
    """Parse progress.txt key=value contract lines (last assignment wins).

    Contract (written by ralph.sh append_progress / write_completion_marker):
      iteration=<n>
      spec=<spec-id>
      task=<task-id>
      promise=<value>          # per-iteration; COMPLETE only at end
      completion_reason=<why>  # only on terminal write
    Lines that are not pure key=value (headers, prose tails) are ignored.
    """
    result: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # Reject multi-token left-hand sides (prose / multi-kv residue)
        if not key or any(c.isspace() for c in key):
            continue
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        result[key] = val.strip()
    return result


def find_active_runs() -> list[dict]:
    """
    Find active Ralph runs by scanning scripts/ralph/runs/*/progress.txt.
    A run is active if progress.txt exists AND does NOT have both
    completion_reason= and promise=COMPLETE key=value contract lines.
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
        kv = parse_progress_kv(content)

        # Terminal marker: both completion_reason= and promise=COMPLETE present
        if "completion_reason" in kv and kv.get("promise") == "COMPLETE":
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

        raw_iter = kv.get("iteration", "")
        if raw_iter.isdigit():
            run_info["iteration"] = int(raw_iter)

        epic = kv.get("spec") or kv.get("epic") or ""
        if epic:
            run_info["current_epic"] = epic

        task = kv.get("task") or ""
        if task:
            run_info["current_task"] = task

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
        kv = parse_progress_kv(content)
        raw_iter = kv.get("iteration", "")
        if raw_iter.isdigit():
            iteration = int(raw_iter)
        current_epic = kv.get("spec") or kv.get("epic") or None
        current_task = kv.get("task") or None

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

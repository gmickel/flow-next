"""Shared test support for tests that spawn the edge CLI."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOWCTL_SCRIPT = HERE.parents[1] / "plugins" / "flow" / "skills" / "flow" / "scripts" / "edge.py"
RUNNER = HERE / "flowctl_runner.py"
if not RUNNER.is_file():
    raise FileNotFoundError(f"edge test runner not found: {RUNNER}")

FLOWCTL_CMD = (sys.executable, str(RUNNER))


def git(cwd: Path, *args: str, check: bool = True) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed ({res.returncode}): {res.stderr}")
    return res.stdout.strip()

"""`flowctl pilot strikes list|clear` over the pilot skill's ledger (fn-184.1, #325).

The ledger is the pilot skill's EXISTING contract, verbatim:
`$(git rev-parse --git-common-dir)/flow-next/pilot-strikes.json` holding
`{"<spec-id>": {"count": n, "stage": str, "reason": str, "ts": iso8601}}`.
flowctl owns READ + CLEAR; the skill keeps its jq write sites.

Pinned here:
  * `list` is empty-safe (missing file / empty file / non-git all exit 0) and
    its `--json` shape is stable.
  * `clear <spec-id>` removes exactly one entry and leaves every other entry
    byte-identical; `clear --all` empties the ledger to `{}`.
  * An unknown spec id is a DISTINCT not-found (exit 3) naming the known keys -
    never silent success, never a traceback.
  * The write is atomic: a failure at the rename leaves the original ledger
    intact and no stray temp file behind.
  * A linked worktree's `.git` FILE resolves through to the shared common dir,
    so a clear from a worktree edits the same ledger the main tree reads.
  * R2: clearing a strike NEVER mutates spec readiness in either direction.

Run:
    python3 -m unittest test_pilot_strikes -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

ROOT = Path(__file__).resolve().parents[1]
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"

_spec = importlib.util.spec_from_file_location("flowctl_pilot_strikes", FLOWCTL_PY)
flowctl = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = flowctl
_spec.loader.exec_module(flowctl)

ENTRY_A = {
    "count": 2,
    "stage": "work",
    "reason": "no advancement (worker returned no diff)",
    "ts": "2026-08-10T09:00:00Z",
}
ENTRY_B = {
    "count": 1,
    "stage": "plan",
    "reason": "plan-review found no ready task",
    "ts": "2026-08-10T10:30:00Z",
}


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    )


class PilotStrikesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.repo = self.tmpdir / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@example.com")
        _git(self.repo, "config", "user.name", "T")
        (self.repo / "README.md").write_text("x\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        self.ledger = self.repo / ".git" / "flow-next" / "pilot-strikes.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_ledger(self, data: dict) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_ledger(self) -> dict:
        return json.loads(self.ledger.read_text(encoding="utf-8"))

    # --- list -----------------------------------------------------------

    def test_list_missing_ledger_is_empty_and_exits_zero(self) -> None:
        res = _run(self.repo, "pilot", "strikes", "list")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("No pilot strikes", res.stdout)

        res = _run(self.repo, "pilot", "strikes", "list", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["success"], True)
        self.assertEqual(payload["strikes"], {})
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["note"], None)
        self.assertTrue(payload["ledger"].endswith("flow-next/pilot-strikes.json"))

    def test_list_empty_file_is_tolerated(self) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text("", encoding="utf-8")
        res = _run(self.repo, "pilot", "strikes", "list", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["strikes"], {})

    def test_list_populated_json_and_human(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A, "fn-2-beta": ENTRY_B})

        res = _run(self.repo, "pilot", "strikes", "list", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["strikes"]["fn-1-alpha"], ENTRY_A)
        self.assertEqual(payload["strikes"]["fn-2-beta"], ENTRY_B)

        res = _run(self.repo, "pilot", "strikes", "list")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("fn-1-alpha", res.stdout)
        self.assertIn("strike 2/2", res.stdout)
        self.assertIn("stage=work", res.stdout)
        self.assertIn("flowctl pilot strikes clear", res.stdout)

    def test_list_malformed_ledger_errors_cleanly(self) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text("not json", encoding="utf-8")
        res = _run(self.repo, "pilot", "strikes", "list", "--json")
        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn("Traceback", res.stderr)
        self.assertIn("not valid JSON", json.loads(res.stdout)["error"])

    # --- clear ----------------------------------------------------------

    def test_clear_one_leaves_other_entries_untouched(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A, "fn-2-beta": ENTRY_B})
        res = _run(self.repo, "pilot", "strikes", "clear", "fn-1-alpha", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["cleared"], ["fn-1-alpha"])
        self.assertEqual(payload["remaining"], 1)
        self.assertEqual(self._read_ledger(), {"fn-2-beta": ENTRY_B})

    def test_clear_all_empties_the_ledger(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A, "fn-2-beta": ENTRY_B})
        res = _run(self.repo, "pilot", "strikes", "clear", "--all", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["cleared"], ["fn-1-alpha", "fn-2-beta"])
        self.assertEqual(payload["remaining"], 0)
        self.assertEqual(self._read_ledger(), {})

    def test_clear_unknown_spec_is_distinct_not_found(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A})
        res = _run(self.repo, "pilot", "strikes", "clear", "fn-9-nope", "--json")
        self.assertEqual(res.returncode, 3, res.stdout + res.stderr)
        self.assertNotIn("Traceback", res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["success"], False)
        self.assertIn("fn-9-nope", payload["error"])
        self.assertIn("fn-1-alpha", payload["error"])  # names the known keys
        # Not a silent success: the ledger is untouched.
        self.assertEqual(self._read_ledger(), {"fn-1-alpha": ENTRY_A})

    def test_clear_requires_exactly_one_of_id_or_all(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A})
        both = _run(
            self.repo, "pilot", "strikes", "clear", "fn-1-alpha", "--all", "--json"
        )
        self.assertNotEqual(both.returncode, 0)
        self.assertIn("not both", json.loads(both.stdout)["error"])

        neither = _run(self.repo, "pilot", "strikes", "clear", "--json")
        self.assertNotEqual(neither.returncode, 0)
        self.assertIn("Missing spec id", json.loads(neither.stdout)["error"])
        self.assertEqual(self._read_ledger(), {"fn-1-alpha": ENTRY_A})

    def test_clear_below_threshold_still_clears(self) -> None:
        self._write_ledger({"fn-2-beta": ENTRY_B})  # count == 1
        res = _run(self.repo, "pilot", "strikes", "clear", "fn-2-beta")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self._read_ledger(), {})

    # --- atomicity ------------------------------------------------------

    def test_clear_write_is_atomic_no_partial_file_on_failure(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A, "fn-2-beta": ENTRY_B})
        before = self.ledger.read_text(encoding="utf-8")
        prev_cwd = Path.cwd()
        os.chdir(self.repo)
        try:
            args = flowctl.argparse.Namespace(
                spec_id="fn-1-alpha", all=False, json=True
            )
            with mock.patch.object(
                flowctl.os, "replace", side_effect=OSError("boom")
            ):
                with self.assertRaises(OSError):
                    flowctl.cmd_pilot_strikes_clear(args)
        finally:
            os.chdir(prev_cwd)
        # Original content survives byte-for-byte and no temp file is left.
        self.assertEqual(self.ledger.read_text(encoding="utf-8"), before)
        self.assertEqual(sorted(p.name for p in self.ledger.parent.iterdir()),
                         ["pilot-strikes.json"])

    # --- worktrees ------------------------------------------------------

    def test_worktree_resolves_through_to_shared_common_dir(self) -> None:
        self._write_ledger({"fn-1-alpha": ENTRY_A, "fn-2-beta": ENTRY_B})
        wt = self.tmpdir / "wt"
        _git(self.repo, "worktree", "add", "-q", "-b", "side", str(wt))
        self.assertTrue((wt / ".git").is_file())  # a .git FILE, not a dir

        res = _run(wt, "pilot", "strikes", "list", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(sorted(payload["strikes"]), ["fn-1-alpha", "fn-2-beta"])
        self.assertEqual(
            Path(payload["ledger"]).resolve(), self.ledger.resolve()
        )

        # A clear from the worktree edits the SHARED ledger.
        res = _run(wt, "pilot", "strikes", "clear", "fn-1-alpha", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self._read_ledger(), {"fn-2-beta": ENTRY_B})

    # --- non-repo -------------------------------------------------------

    def test_non_repo_context_fails_cleanly(self) -> None:
        outside = self.tmpdir / "outside"
        outside.mkdir()
        env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(self.tmpdir))
        listing = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "pilot", "strikes", "list", "--json"],
            cwd=str(outside), capture_output=True, text=True, env=env,
        )
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertNotIn("Traceback", listing.stderr)
        payload = json.loads(listing.stdout)
        self.assertEqual(payload["strikes"], {})
        self.assertEqual(payload["ledger"], None)
        self.assertIn("not a git repository", payload["note"])

        clearing = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "pilot", "strikes", "clear",
             "fn-1-alpha", "--json"],
            cwd=str(outside), capture_output=True, text=True, env=env,
        )
        self.assertNotEqual(clearing.returncode, 0)
        self.assertNotIn("Traceback", clearing.stderr)
        self.assertIn(
            "Not a git repository", json.loads(clearing.stdout)["error"]
        )


class PilotStrikesReadinessTestCase(unittest.TestCase):
    """R2: clearing a strike never mutates spec readiness."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.repo = self.tmpdir / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _run(self.repo, "init")
        created = _run(
            self.repo, "spec", "create", "--title", "Struck subject", "--json"
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        self.spec_id = json.loads(created.stdout)["id"]
        self.ledger = self.repo / ".git" / "flow-next" / "pilot-strikes.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _ready(self) -> bool:
        res = _run(self.repo, "show", self.spec_id, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)["ready"]

    def _write_ledger(self, data: dict) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_clear_does_not_re_ready_an_unreadied_spec(self) -> None:
        _run(self.repo, "spec", "ready", self.spec_id)
        unready = _run(self.repo, "spec", "unready", self.spec_id)
        self.assertEqual(unready.returncode, 0, unready.stderr)
        self.assertFalse(self._ready())

        self._write_ledger({self.spec_id: ENTRY_A})
        cleared = _run(
            self.repo, "pilot", "strikes", "clear", self.spec_id, "--json"
        )
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertEqual(json.loads(cleared.stdout)["cleared"], [self.spec_id])

        # Strikes are pilot state, not readiness state.
        self.assertFalse(self._ready())

    def test_clear_all_does_not_unready_a_ready_spec(self) -> None:
        ready = _run(self.repo, "spec", "ready", self.spec_id)
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertTrue(self._ready())

        self._write_ledger({self.spec_id: ENTRY_A})
        cleared = _run(self.repo, "pilot", "strikes", "clear", "--all", "--json")
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertTrue(self._ready())

    def test_bare_handle_resolves_to_the_canonical_ledger_key(self) -> None:
        bare = self.spec_id.split("-")[0] + "-" + self.spec_id.split("-")[1]
        self._write_ledger({self.spec_id: ENTRY_A})
        res = _run(self.repo, "pilot", "strikes", "clear", bare, "--json")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(json.loads(res.stdout)["cleared"], [self.spec_id])


if __name__ == "__main__":
    unittest.main()

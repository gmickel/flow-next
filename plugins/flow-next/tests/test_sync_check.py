"""`flowctl sync check` lifecycle-audit tests (fn-57.1, R2 + R7 + R8).

Asserts the read-only audit over `.flow/sync-runs/` receipts:
  * R8 zero-overhead path: bridge inactive → zero output, exit 0, BEFORE any
    id resolution or receipt IO (a garbage id stays silent).
  * MISSING predicate: triggered (`--events`) ∩ perEvent-enabled ∩
    bridge-active ∩ no event-matching receipt with `timestamp >= --since`.
    Linkage is NOT a precondition.
  * Any-status clears (`errored` / `noop` included); `event: null` (pre-flag)
    receipts never clear; `--since` scopes out prior-run receipts.
  * Nested perEvent keys (`work.firstClaim`) route through the dotted config
    path; disabled / unconfigured events are never MISSING.
  * `Z`-suffixed `--since` parses on Python 3.8-3.10 (`_parse_iso_ts`, not
    bare `fromisoformat`); tracker handles (WOR-17) resolve as the spec id.
  * Exit 0 always on evaluated checks (best-effort contract) — MISSING is an
    output line, never a non-zero exit.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_sync_check.py" -v
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

PAST = "2000-01-01T00:00:00Z"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _future_iso(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class SyncCheckTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_module("flowctl_sync_check_under_test", FLOWCTL_PY)
        self._call(func=self.flowctl.cmd_init)
        self.spec_id = self._call(
            func=self.flowctl.cmd_spec_create, title="Check subject", branch=None
        )["id"]

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- helpers -------------------------------------------------------------

    def _call(self, *, func, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _activate(self) -> None:
        self.flowctl.set_config("tracker.type", "linear")

    def _enable_event(self, event: str, verb: str = "reconcile") -> None:
        self.flowctl.set_config(f"tracker.perEvent.{event}", verb)

    def _receipt(
        self, event: Optional[str], status: str = "pushed", spec_id: Optional[str] = None
    ) -> dict:
        return self._call(
            func=self.flowctl.cmd_sync_receipt,
            id=spec_id or self.spec_id,
            status=status,
            tracker_id=None,
            transport=None,
            merges_file=None,
            note=None,
            event=event,
        )

    def _check_json(
        self, events: str, since: str = PAST, spec_id: Optional[str] = None
    ) -> dict:
        return self._call(
            func=self.flowctl.cmd_sync_check,
            id=spec_id or self.spec_id,
            events=events,
            since=since,
        )

    def _check_plain(
        self, events: str, since: str = PAST, spec_id: Optional[str] = None
    ) -> str:
        ns = argparse.Namespace(
            id=spec_id or self.spec_id, events=events, since=since, json=False
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.flowctl.cmd_sync_check(ns)
        return buf.getvalue()

    # --- R8: zero-overhead inactive path -------------------------------------

    def test_inactive_bridge_prints_nothing_plain_and_json(self) -> None:
        # Bridge never configured → silent return, no SystemExit, zero output.
        self.assertEqual(self._check_plain("capture"), "")
        self.assertEqual(self._check_json("capture"), {})

    def test_inactive_gate_precedes_id_resolution(self) -> None:
        # A garbage id would error_exit AFTER the gate — inactive must stay
        # silent, proving the gate runs before any resolution or output.
        self.assertEqual(
            self._check_plain("capture", spec_id="!!not an id!!"), ""
        )

    # --- MISSING predicate ----------------------------------------------------

    def test_missing_when_enabled_and_no_receipt(self) -> None:
        self._activate()
        self._enable_event("capture")
        res = self._check_json("capture")
        self.assertEqual(res["events"], ["capture"])
        self.assertEqual(res["missing"], ["capture"])
        self.assertEqual(res["count"], 1)
        self.assertEqual(self._check_plain("capture"), "MISSING:capture\n")

    def test_any_status_receipt_clears(self) -> None:
        # The check asserts the touchpoint RAN; errored/noop still clear.
        self._activate()
        self._enable_event("capture")
        for status in ("errored", "noop"):
            self._receipt("capture", status=status)
        res = self._check_json("capture")
        self.assertEqual(res["missing"], [])
        self.assertEqual(res["count"], 0)
        self.assertEqual(self._check_plain("capture"), "OK:capture\n")

    def test_null_event_receipt_never_clears(self) -> None:
        # Pre-fn-57 receipts carry event: null — they never satisfy an
        # event-specific check.
        self._activate()
        self._enable_event("capture")
        self._receipt(None)
        self.assertEqual(self._check_json("capture")["missing"], ["capture"])

    def test_since_scopes_out_prior_run_receipts(self) -> None:
        # Receipts accumulate forever; a receipt OLDER than --since must not
        # cause a false pass for the current run.
        self._activate()
        self._enable_event("capture")
        self._receipt("capture")
        res = self._check_json("capture", since=_future_iso())
        self.assertEqual(res["missing"], ["capture"])

    def test_disabled_event_never_missing(self) -> None:
        # Default perEvent.capture is "off": triggered-but-opted-out is OK.
        self._activate()
        res = self._check_json("capture")
        self.assertEqual(res["missing"], [])
        self.assertEqual(self._check_plain("capture"), "OK:capture\n")

    def test_unconfigured_future_event_never_missing(self) -> None:
        # perEvent keys are an open extension point (R7): an unknown key has
        # no enabled leaf, so it cannot be MISSING.
        self._activate()
        self.assertEqual(self._check_json("futureEvent.someKey")["missing"], [])

    def test_receipt_for_other_spec_does_not_clear(self) -> None:
        self._activate()
        self._enable_event("capture")
        other = self._call(
            func=self.flowctl.cmd_spec_create, title="Other spec", branch=None
        )["id"]
        self._receipt("capture", spec_id=other)
        self.assertEqual(self._check_json("capture")["missing"], ["capture"])

    def test_nested_work_keys_and_multi_event_csv(self) -> None:
        # work.* perEvent keys are NESTED in config; the dotted event key must
        # route through `tracker.perEvent.work.firstClaim`. CSV evaluates each
        # passed event independently, preserving input order in output.
        self._activate()
        self._enable_event("work.firstClaim", "status")
        self._enable_event("work.done", "comment")
        self._receipt("work.firstClaim")
        res = self._check_json("work.firstClaim,work.done")
        self.assertEqual(res["events"], ["work.firstClaim", "work.done"])
        self.assertEqual(res["missing"], ["work.done"])
        self.assertEqual(res["count"], 1)
        self.assertEqual(
            self._check_plain("work.firstClaim,work.done"),
            "OK:work.firstClaim\nMISSING:work.done\n",
        )

    # --- exit-code contract ----------------------------------------------------

    def test_missing_does_not_raise(self) -> None:
        # Exit 0 always: MISSING is an output line, never a SystemExit — the
        # in-process call returning (not raising) IS the exit-0 contract.
        self._activate()
        self._enable_event("capture")
        out = self._check_plain("capture")  # would raise on a non-zero path
        self.assertIn("MISSING:capture", out)

    # --- input validation -------------------------------------------------------

    def test_z_suffix_since_parses(self) -> None:
        # Regression: bare `fromisoformat` crashes on `Z` suffixes under
        # Python 3.8-3.10 — `--since` must route through `_parse_iso_ts`.
        self.assertIsNotNone(self.flowctl._parse_iso_ts("2026-06-09T00:00:00Z"))
        self._activate()
        res = self._check_json("capture", since="2026-06-09T00:00:00Z")
        self.assertIn("events", res)  # parsed + evaluated, no error envelope

    def test_invalid_since_errors(self) -> None:
        self._activate()
        with self.assertRaises(SystemExit):
            self._check_json("capture", since="not-a-timestamp")

    def test_empty_events_errors(self) -> None:
        self._activate()
        with self.assertRaises(SystemExit):
            self._check_json(",")

    # --- id grammar (fn-52.10 lesson: cover the FULL command surface) -----------

    def test_tracker_handle_resolves_as_spec_id(self) -> None:
        self._activate()
        self._enable_event("capture")
        canonical = self._call(
            func=self.flowctl.cmd_spec_create,
            title="Fix login",
            branch=None,
            tracker_first=True,
            tracker_identifier="WOR-17",
        )["id"]
        self.assertTrue(canonical.startswith("wor-17"))
        self._receipt("capture", spec_id=canonical)
        # Check via the UPPERCASE bare tracker handle — must resolve to the
        # canonical id and match the receipt written under it.
        res = self._check_json("capture", spec_id="WOR-17")
        self.assertEqual(res["id"], canonical)
        self.assertEqual(res["missing"], [])

    # --- robustness ---------------------------------------------------------------

    def test_malformed_receipt_is_skipped(self) -> None:
        self._activate()
        self._enable_event("capture")
        runs_dir = self.tmpdir / ".flow" / "sync-runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / "sync-garbage.json").write_text("{not json", encoding="utf-8")
        self._receipt("capture")
        res = self._check_json("capture")
        self.assertEqual(res["missing"], [])

    # --- CLI wiring (argparse e2e) --------------------------------------------------

    def test_cli_inactive_exits_zero_silent(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "sync",
                "check",
                self.spec_id,
                "--events",
                "capture",
                "--since",
                PAST,
            ],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_cli_missing_exits_zero_with_line(self) -> None:
        self._activate()
        self._enable_event("capture")
        proc = subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "sync",
                "check",
                self.spec_id,
                "--events",
                "capture",
                "--since",
                PAST,
            ],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("MISSING:capture", proc.stdout)

    def test_cli_receipt_event_round_trip(self) -> None:
        # The spec's smoke pair: receipt --event + check --json (R1 + R2).
        self._activate()
        self._enable_event("capture")
        subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "sync",
                "receipt",
                self.spec_id,
                "--status",
                "noop",
                "--transport",
                "none",
                "--event",
                "capture",
                "--note",
                "smoke",
            ],
            cwd=self.tmpdir,
            check=True,
            capture_output=True,
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "sync",
                "check",
                self.spec_id,
                "--events",
                "capture",
                "--since",
                PAST,
                "--json",
            ],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        res = json.loads(proc.stdout)
        self.assertEqual(res["missing"], [])
        self.assertEqual(res["count"], 0)


class CompletionReviewEventKeyParity(SyncCheckTestCase):
    """fn-90 re-review regression (2.9.1): the completion-review event tag must
    match the TOP-LEVEL `tracker.perEvent.completionReview` leaf. The prose used
    to dispatch/audit `work.completionReview`, which resolves
    `tracker.perEvent.work.completionReview` → None → never enabled → the audit
    could neither clear nor miss the touchpoint (dead retro-fire backstop)."""

    PLUGIN_ROOT = FLOWCTL_PY.parent.parent

    def test_top_level_key_round_trips_the_audit(self) -> None:
        # Enabled + no receipt → MISSING; a completionReview-tagged receipt clears.
        self._activate()
        self._enable_event("completionReview", "comment")
        self.assertEqual(
            self._check_json("completionReview")["missing"], ["completionReview"]
        )
        self._receipt("completionReview", status="updated")
        self.assertEqual(self._check_json("completionReview")["missing"], [])

    def test_work_prefixed_key_never_resolves_a_leaf(self) -> None:
        # The old buggy tag shape: leaf enabled at top level, event audited with
        # the `work.` prefix → resolves no leaf → never enabled → never MISSING
        # even with zero receipts (the silent dead-backstop failure mode).
        self._activate()
        self._enable_event("completionReview", "comment")
        self.assertEqual(self._check_json("work.completionReview")["missing"], [])

    def test_canonical_prose_carries_no_work_prefixed_tag(self) -> None:
        # Prose guard: no canonical skill/doc may reintroduce the mismatched tag
        # (the Codex mirror is regenerated from these, so it is excluded).
        offenders = []
        for root in (self.PLUGIN_ROOT / "skills", self.PLUGIN_ROOT / "docs"):
            for path in root.rglob("*.md"):
                if "codex" in path.parts:
                    continue
                if "work.completionReview" in path.read_text(encoding="utf-8"):
                    offenders.append(str(path))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()

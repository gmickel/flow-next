"""`tracker.perEvent.land.merged` Done-on-merge touchpoint leaf (fn-66, R3/R10).

fn-66 makes `land.merged` the SOLE driver of the terminal `Done` tracker state
and **active-by-default when the bridge is active** (like make-pr's unconditional
PR-link path) — the merge→Done projection rides the bridge-active predicate alone,
NOT this leaf. The config-schema default for the nested `land.merged` leaf stays
`off` (the fn-52.1 accidental-enable invariant: a bare `enabled=true` activates no
lifecycle-event sync), and when set the leaf only tunes the optional verdict
comment — never the (MERGED-gated) status write.

This test proves the leaf round-trips through the **production CLI** — the real
argparse dispatch (`init` → `config set` → `config get`) invoked via a subprocess
against `scripts/flowctl.py`, NOT an in-process import (the dual-copy invariant:
the bundled CLI must run this code). It mirrors `test_qa_tracker_event.py` style.

Asserts:
  1. fresh repo, no `config set` → `tracker.perEvent.land.merged` merges to `"off"`
     (NOT null) via the merge-defaults path;
  2. `set tracker.perEvent.land.merged push` → `get` round-trips to `"push"`;
  3. setting the land.merged leaf does NOT clobber a sibling perEvent leaf
     (`tracker.perEvent.completionReview` stays `"off"`, and the nested
     `tracker.perEvent.work.firstClaim` stays `"off"`);
  4. setting the land.merged leaf does NOT flip the value-checked activation
     predicate (no type / not enabled → bridge stays inactive);
  5. the leaf lives under the SAME nested `perEvent` object as the fn-52/.53/.60
     leaves (`get_default_tracker_config()` shape), defaulting `off`, alongside an
     unchanged `completionReview` default of `off`;
  6. `push` (the land.merged op verb) is a recognised `TRACKER_PER_EVENT_LEAVES`
     verb (no enum change was needed — only the semantics of the leaf changed).

Hermetic: each test runs in its own `tempfile.TemporaryDirectory`, inits a
throwaway `.flow/`, and shells `sys.executable scripts/flowctl.py` (no network, no
LLM). Windows-portable: `pathlib` everywhere, `sys.executable`, no shell string.

Run:
    python3 -m unittest plugins.flow-next.tests.test_land_tracker_event -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    """In-process load — used ONLY to assert the defaults-dict shape (1 test).

    The round-trip tests below go through the subprocess CLI, not this import.
    """
    spec = importlib.util.spec_from_file_location(
        "flowctl_land_tracker_event_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _flowctl(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    """Run the production CLI as a subprocess; parse the `--json` payload."""
    cmd = [sys.executable, str(FLOWCTL_PY), *args, "--json"]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != expect_rc:
        raise AssertionError(
            f"rc={proc.returncode} (expected {expect_rc}): args={args} "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    return json.loads(proc.stdout.decode("utf-8"))


def _init_repo(tmp: Path) -> None:
    subprocess.check_call(
        [sys.executable, str(FLOWCTL_PY), "init", "--json"],
        cwd=str(tmp),
        stdout=subprocess.DEVNULL,
    )


class LandTrackerEventLeafTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _init_repo(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── (1) fresh default merges to "off", NOT null ──────────────────────

    def test_fresh_repo_land_merged_leaf_defaults_off(self) -> None:
        out = _flowctl(
            self.repo, "config", "get", "tracker.perEvent.land.merged"
        )
        self.assertEqual(out["value"], "off")

    # ── (2) set push → get round-trips ───────────────────────────────────

    def test_set_push_round_trips_via_cli(self) -> None:
        set_out = _flowctl(
            self.repo, "config", "set", "tracker.perEvent.land.merged", "push"
        )
        self.assertEqual(set_out["value"], "push")
        get_out = _flowctl(
            self.repo, "config", "get", "tracker.perEvent.land.merged"
        )
        self.assertEqual(get_out["value"], "push")

    # ── (3) setting land.merged does NOT clobber sibling perEvent leaves ──

    def test_set_land_merged_preserves_sibling_perevent_leaves(self) -> None:
        _flowctl(
            self.repo, "config", "set", "tracker.perEvent.land.merged", "push"
        )
        # completionReview default unchanged (the fn-66 re-scope keeps the
        # SCHEMA default `off` — the discovery ceremony seeds `comment`).
        cr = _flowctl(
            self.repo, "config", "get", "tracker.perEvent.completionReview"
        )
        self.assertEqual(cr["value"], "off")
        sibling = _flowctl(
            self.repo, "config", "get", "tracker.perEvent.work.firstClaim"
        )
        self.assertEqual(sibling["value"], "off")
        # And the land.merged leaf itself is intact.
        lm = _flowctl(
            self.repo, "config", "get", "tracker.perEvent.land.merged"
        )
        self.assertEqual(lm["value"], "push")

    # ── (4) setting land.merged does NOT activate the bridge ─────────────

    def test_set_land_merged_does_not_activate_the_bridge(self) -> None:
        _flowctl(
            self.repo, "config", "set", "tracker.perEvent.land.merged", "push"
        )
        active = _flowctl(self.repo, "sync", "active")
        self.assertFalse(active["active"])

    # ── (5) shape assertion — nested perEvent, defaults off ──────────────

    def test_land_merged_leaf_in_default_tracker_config_nested(self) -> None:
        flowctl = _load_flowctl()
        pe = flowctl.get_default_tracker_config()["perEvent"]
        self.assertIn("land", pe)
        self.assertIn("merged", pe["land"])
        self.assertEqual(pe["land"]["merged"], "off")
        # completionReview SCHEMA default stays off (ceremony seeds comment).
        self.assertEqual(pe["completionReview"], "off")
        # Same nested perEvent object as the fn-52 leaves.
        self.assertEqual(pe["work"]["firstClaim"], "off")
        self.assertEqual(pe["makePr"], "off")

    # ── (6) `push` is a recognised perEvent verb ─────────────────────────

    def test_push_is_a_recognised_per_event_verb(self) -> None:
        flowctl = _load_flowctl()
        self.assertIn("push", flowctl.TRACKER_PER_EVENT_LEAVES)
        self.assertIn("off", flowctl.TRACKER_PER_EVENT_LEAVES)


if __name__ == "__main__":
    unittest.main()

"""`tracker.perEvent.qa` opt-in verdict-post leaf (fn-53.4, R9).

`/flow-next:qa` Phase A optionally posts its verdict as a tracker comment,
gated on a NEW additive `perEvent` leaf: `tracker.perEvent.qa`, default
`off`. `comment` is the only verdict-meaningful verb; the leaf is a no-op
until opted in, so every existing repo stays silent.

This test proves the leaf round-trips through the **production CLI** — the
real argparse dispatch (`init` → `config set` → `config get`) invoked via a
subprocess against `scripts/flowctl.py`, NOT an in-process import of the
function under test. That exercises `cmd_config_get` / `cmd_config_set`
end-to-end (the dual-copy invariant: the bundled CLI must run this code).

Asserts:
  1. fresh repo, no `config set` → `tracker.perEvent.qa` merges to `"off"`
     (NOT null) via the merge-defaults path;
  2. `set tracker.perEvent.qa comment` → `get` round-trips to `"comment"`;
  3. setting the qa leaf does NOT clobber a sibling perEvent leaf
     (`tracker.perEvent.work.firstClaim` stays `"off"`);
  4. the leaf lives under the SAME nested `perEvent` object as the fn-52
     leaves (`get_default_tracker_config()` shape), defaulting `off`;
  5. `comment` is a recognised `TRACKER_PER_EVENT_LEAVES` verb (no enum
     change was needed — only the `qa` *key* is new).

Hermetic: each test runs in its own `tempfile.TemporaryDirectory`, inits a
throwaway `.flow/`, and shells `sys.executable scripts/flowctl.py` (no
network, no LLM). Windows-portable: `pathlib` everywhere, `sys.executable`,
no shell string, no hard-coded separators.

Run:
    python3 -m unittest plugins.flow-next.tests.test_qa_tracker_event -v
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
        "flowctl_qa_tracker_event_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _flowctl(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    """Run the production CLI as a subprocess; parse the `--json` payload.

    Faithfully exercises the real argparse → cmd_* dispatch (the production
    path the bundled CLI runs), not an in-process function call.
    """
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


class QaTrackerEventLeafTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _init_repo(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── (1) fresh default merges to "off", NOT null ──────────────────────

    def test_fresh_repo_qa_leaf_defaults_off(self) -> None:
        out = _flowctl(self.repo, "config", "get", "tracker.perEvent.qa")
        self.assertEqual(out["value"], "off")

    # ── (2) set comment → get round-trips ────────────────────────────────

    def test_set_comment_round_trips_via_cli(self) -> None:
        set_out = _flowctl(
            self.repo, "config", "set", "tracker.perEvent.qa", "comment"
        )
        self.assertEqual(set_out["value"], "comment")
        get_out = _flowctl(self.repo, "config", "get", "tracker.perEvent.qa")
        self.assertEqual(get_out["value"], "comment")

    # ── (3) setting qa does NOT clobber a sibling perEvent leaf ──────────

    def test_set_qa_preserves_sibling_perevent_leaf(self) -> None:
        _flowctl(self.repo, "config", "set", "tracker.perEvent.qa", "comment")
        sibling = _flowctl(
            self.repo, "config", "get", "tracker.perEvent.work.firstClaim"
        )
        self.assertEqual(sibling["value"], "off")
        # And the qa leaf itself is intact.
        qa = _flowctl(self.repo, "config", "get", "tracker.perEvent.qa")
        self.assertEqual(qa["value"], "comment")

    def test_set_qa_does_not_activate_the_bridge(self) -> None:
        # Opting a perEvent leaf in must NOT flip the value-checked activation
        # predicate on (no type / not enabled) — the fn-52.1 invariant.
        _flowctl(self.repo, "config", "set", "tracker.perEvent.qa", "comment")
        active = _flowctl(self.repo, "sync", "active")
        self.assertFalse(active["active"])

    # ── (4)+(5) shape + enum assertions (in-process, defaults dict) ──────

    def test_qa_leaf_in_default_tracker_config_nested_perevent(self) -> None:
        flowctl = _load_flowctl()
        pe = flowctl.get_default_tracker_config()["perEvent"]
        self.assertIn("qa", pe)
        self.assertEqual(pe["qa"], "off")
        # Lives under the SAME nested perEvent object as the fn-52 leaves.
        for leaf in ("capture", "interview", "plan", "makePr", "resolvePr",
                     "completionReview"):
            self.assertEqual(pe[leaf], "off")
        self.assertEqual(pe["work"]["firstClaim"], "off")

    def test_comment_is_a_recognised_per_event_verb(self) -> None:
        # No enum change was needed: `comment` was already a valid leaf verb
        # (fn-52); this task adds only the `qa` KEY, defaulting off.
        flowctl = _load_flowctl()
        self.assertIn("comment", flowctl.TRACKER_PER_EVENT_LEAVES)
        self.assertIn("off", flowctl.TRACKER_PER_EVENT_LEAVES)


if __name__ == "__main__":
    unittest.main()

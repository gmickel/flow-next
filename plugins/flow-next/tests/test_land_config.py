"""Unit tests for the /flow-next:land config surface (fn-60.2, R15).

`get_default_config()` carries a top-level `land` block so
`flowctl config get land.*` returns the spec defaults (NOT `null`) on a
fresh repo, WITHOUT any prior `config set`:

  * land.release            → True
  * land.patienceMinutes    → 30
  * land.reviewSignal       → "silence"  (enum: silence | approve | <github-login>)
  * land.automatedReviewers → ""         (csv; empty = `[bot]`-suffix rule only)
  * land.ciFixBudget        → 3

Plus: `config set` round-trips for the string enum and the integer knob
(set_config auto-coerces digits), and the new top-level `land.*` namespace
does not clash with existing blocks. Mirrors test_work_delegate_config.py.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_land_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class LandConfigDefaultsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        flow_dir = self.tmpdir / ".flow"
        flow_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_config_get_cli(self, key: str, *extra: str) -> dict:
        """Invoke cmd_config_get via the argparse namespace; capture JSON stdout."""
        ns = argparse.Namespace(key=key, json=True, raw="--raw" in extra)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_get(ns)
        return json.loads(buf.getvalue())

    def _run_config_set_cli(self, key: str, value: str) -> dict:
        ns = argparse.Namespace(key=key, value=value, json=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_set(ns)
        return json.loads(buf.getvalue())

    # ── Defaults: present in get_default_config() ────────────────────────

    def test_defaults_dict_has_land_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("land", defaults)
        self.assertEqual(
            defaults["land"],
            {
                "release": True,
                "patienceMinutes": 30,
                "reviewSignal": "silence",
                "automatedReviewers": "",
                "ciFixBudget": 3,
            },
        )

    # ── Defaults: surfaced via `config get --json` on a FRESH repo ───────
    # No config.json on disk and no prior `config set` — the merge must
    # return the spec defaults, NOT null.

    def test_fresh_get_release_is_true(self) -> None:
        out = self._run_config_get_cli("land.release")
        self.assertIs(out["value"], True)

    def test_fresh_get_patience_minutes_is_30(self) -> None:
        out = self._run_config_get_cli("land.patienceMinutes")
        self.assertEqual(out["value"], 30)
        self.assertIsInstance(out["value"], int)

    def test_fresh_get_review_signal_is_silence(self) -> None:
        # The spec's quick-command check: `config get land.reviewSignal --json`
        # → "silence" on a fresh repo, not null.
        out = self._run_config_get_cli("land.reviewSignal")
        self.assertEqual(out["value"], "silence")

    def test_fresh_get_automated_reviewers_is_empty_csv(self) -> None:
        # Empty string (csv allowlist), NOT null — empty means the
        # `[bot]`-suffix rule alone identifies automated reviewers.
        out = self._run_config_get_cli("land.automatedReviewers")
        self.assertEqual(out["value"], "")
        self.assertIsNotNone(out["value"])

    def test_fresh_get_ci_fix_budget_is_3(self) -> None:
        out = self._run_config_get_cli("land.ciFixBudget")
        self.assertEqual(out["value"], 3)
        self.assertIsInstance(out["value"], int)

    # ── set round-trips (no new flowctl command needed) ──────────────────
    # set_config already takes arbitrary nested dot-paths; the only change
    # is the defaults block, so `set` + `get` round-trips with no whitelist.

    def test_set_review_signal_approve_round_trips(self) -> None:
        set_out = self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(set_out["value"], "approve")
        get_out = self._run_config_get_cli("land.reviewSignal")
        self.assertEqual(get_out["value"], "approve")

    def test_set_review_signal_named_reviewer_round_trips(self) -> None:
        # The enum's third arm is an arbitrary GitHub login.
        self._run_config_set_cli("land.reviewSignal", "gmickel")
        get_out = self._run_config_get_cli("land.reviewSignal")
        self.assertEqual(get_out["value"], "gmickel")

    def test_set_patience_minutes_coerces_to_int(self) -> None:
        # set_config auto-coerces digit strings.
        self._run_config_set_cli("land.patienceMinutes", "45")
        get_out = self._run_config_get_cli("land.patienceMinutes")
        self.assertEqual(get_out["value"], 45)
        self.assertIsInstance(get_out["value"], int)

    def test_set_release_false_string_coerces_to_bool(self) -> None:
        self._run_config_set_cli("land.release", "false")
        get_out = self._run_config_get_cli("land.release")
        self.assertIs(get_out["value"], False)

    def test_set_one_land_key_keeps_sibling_defaults(self) -> None:
        # Writing one land.* key must not clobber the other seeded defaults
        # (deep_merge keeps the rest of the block).
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )
        self.assertEqual(
            self._run_config_get_cli("land.patienceMinutes")["value"], 30
        )
        self.assertIs(self._run_config_get_cli("land.release")["value"], True)

    # ── Namespace coexistence ─────────────────────────────────────────────

    def test_land_block_does_not_clash_with_existing_blocks(self) -> None:
        defaults = self.flowctl.get_default_config()
        # land.* is its own top-level block, distinct from work.* and
        # tracker.* — no shared keys leak across.
        self.assertIn("land", defaults)
        self.assertIn("work", defaults)
        self.assertNotIn("release", defaults["work"])
        self.assertNotIn("delegate", defaults["land"])

    def test_setting_land_key_does_not_clobber_work_defaults(self) -> None:
        self._run_config_set_cli("land.reviewSignal", "approve")
        self.assertEqual(
            self._run_config_get_cli("work.delegateModel")["value"], "gpt-5.5"
        )


if __name__ == "__main__":
    unittest.main()

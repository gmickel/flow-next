"""Unit tests for the Codex implementation-delegation config foundation
(fn-55.1, R1 + R2).

Covers two surfaces:

1. **Config defaults** — `get_default_config()` now carries a top-level
   `work` block so `flowctl config get work.delegate*` returns the spec
   defaults (NOT `null`) on a fresh repo, WITHOUT any prior `config set`:
     * work.delegate         → False
     * work.delegateModel    → "gpt-5.6-sol"
     * work.delegateEffort   → "medium"  (floor; enum none|low|medium|high|xhigh)
     * work.delegateSandbox  → "yolo"
     * work.delegateConsent  → False
     * work.delegateDecision → "auto"
   Plus: `set work.delegate codex` round-trips, and the new top-level
   `work.*` namespace does NOT clash with the tracker bridge's
   `tracker.perEvent.work.*` lifecycle keys (phases.md:94-101).

2. **Activation resolution precedence** — the documented chain
     arg token (`delegate:codex` / `delegate:local`)
       > flow config `work.delegate`
       > hard default OFF
   The generic fuzzy "use codex" is NOT a delegation trigger (it stays
   mapped to the review backend); only the explicit `delegate:codex` /
   `delegate:local` tokens (and the config) resolve delegation. The
   precedence is exercised here as a pure, deterministic resolver so the
   contract is pinned before fn-55.2 wires it into the skill.
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
from typing import Any, Optional


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_work_delegate_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# Effort enum: none|low|medium|high|xhigh; `medium` is the floor.
EFFORT_ENUM = ("none", "low", "medium", "high", "xhigh")


def resolve_delegation_active(arg_token: Optional[str], config_value: Any) -> bool:
    """Reference resolver for the documented activation chain (fn-55.1, R1).

    Precedence (highest first):
      1. arg token `delegate:codex` (ON) / `delegate:local` (OFF)
      2. flow config `work.delegate` ("codex" → ON; anything else → OFF)
      3. hard default OFF

    The generic fuzzy "use codex" string is intentionally NOT recognised
    here — only the explicit `delegate:codex` / `delegate:local` tokens
    resolve delegation. A bare "use codex" arrives as some other token (or
    None) and falls through to the config / default tier, so it can never
    flip delegation on by itself.
    """
    if arg_token == "delegate:codex":
        return True
    if arg_token == "delegate:local":
        return False
    return config_value == "codex"


class WorkDelegateDefaultsTestCase(unittest.TestCase):
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

    def test_defaults_dict_has_work_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("work", defaults)
        self.assertEqual(
            defaults["work"],
            {
                "delegate": False,
                "delegateModel": "gpt-5.6-sol",
                "delegateEffort": "medium",
                "delegateSandbox": "yolo",
                "delegateConsent": False,
                "delegateDecision": "auto",
            },
        )

    # ── Defaults: surfaced via `config get --json` on a FRESH repo ───────
    # No config.json on disk and no prior `config set` — the merge must
    # return the spec defaults, NOT null.

    def test_fresh_get_delegate_is_false(self) -> None:
        out = self._run_config_get_cli("work.delegate")
        self.assertIs(out["value"], False)

    def test_fresh_get_model_is_gpt56_sol(self) -> None:
        out = self._run_config_get_cli("work.delegateModel")
        self.assertEqual(out["value"], "gpt-5.6-sol")

    def test_fresh_get_effort_is_medium(self) -> None:
        out = self._run_config_get_cli("work.delegateEffort")
        self.assertEqual(out["value"], "medium")
        # `medium` is the floor and a member of the enum.
        self.assertIn(out["value"], EFFORT_ENUM)

    def test_fresh_get_sandbox_is_yolo(self) -> None:
        out = self._run_config_get_cli("work.delegateSandbox")
        self.assertEqual(out["value"], "yolo")

    def test_fresh_get_consent_is_false(self) -> None:
        out = self._run_config_get_cli("work.delegateConsent")
        self.assertIs(out["value"], False)

    def test_fresh_get_decision_is_auto(self) -> None:
        out = self._run_config_get_cli("work.delegateDecision")
        self.assertEqual(out["value"], "auto")

    def test_effort_enum_excludes_minimal(self) -> None:
        # effort enum includes `none` (not `minimal`); see plan research / model docs.
        self.assertIn("none", EFFORT_ENUM)
        self.assertNotIn("minimal", EFFORT_ENUM)
        self.assertEqual(EFFORT_ENUM[0], "none")

    # ── set work.delegate works with no new flowctl command ──────────────
    # `set_config` already takes arbitrary nested dot-paths; the only change
    # is the defaults block, so `set` + `get` round-trips with no whitelist.

    def test_set_delegate_codex_round_trips(self) -> None:
        set_out = self._run_config_set_cli("work.delegate", "codex")
        self.assertEqual(set_out["value"], "codex")
        get_out = self._run_config_get_cli("work.delegate")
        self.assertEqual(get_out["value"], "codex")

    def test_set_delegate_false_string_coerces_to_bool(self) -> None:
        # set_config auto-coerces "true"/"false"/digits.
        self._run_config_set_cli("work.delegate", "false")
        get_out = self._run_config_get_cli("work.delegate")
        self.assertIs(get_out["value"], False)

    # ── Namespace coexistence: top-level work.* vs tracker.perEvent.work.* ─

    def test_setting_work_delegate_does_not_clobber_tracker_work(self) -> None:
        # After setting the new top-level work.delegate key, the unrelated
        # tracker-sync lifecycle key must still resolve to its default.
        self._run_config_set_cli("work.delegate", "codex")
        tracker_out = self._run_config_get_cli(
            "tracker.perEvent.work.firstClaim"
        )
        # Default for every perEvent leaf is "off" (get_default_tracker_config).
        self.assertEqual(tracker_out["value"], "off")
        # And the top-level work.delegate is intact.
        self.assertEqual(
            self._run_config_get_cli("work.delegate")["value"], "codex"
        )

    def test_top_level_work_and_tracker_work_are_distinct_blocks(self) -> None:
        defaults = self.flowctl.get_default_config()
        # Top-level work has delegate*; tracker.perEvent.work has lifecycle
        # hooks (e.g. firstClaim) — different shapes, no overlap.
        self.assertIn("delegate", defaults["work"])
        self.assertNotIn("delegate", defaults["tracker"]["perEvent"]["work"])
        self.assertIn("firstClaim", defaults["tracker"]["perEvent"]["work"])
        self.assertNotIn("firstClaim", defaults["work"])


class DelegationResolutionPrecedenceTestCase(unittest.TestCase):
    """Pin the documented activation chain: arg > config > default off."""

    def test_arg_codex_beats_config_false(self) -> None:
        # arg `delegate:codex` activates even when config is the default off.
        self.assertTrue(resolve_delegation_active("delegate:codex", False))

    def test_arg_local_beats_config_codex(self) -> None:
        # arg `delegate:local` deactivates even when config says codex.
        self.assertFalse(resolve_delegation_active("delegate:local", "codex"))

    def test_absent_arg_falls_to_config_codex(self) -> None:
        self.assertTrue(resolve_delegation_active(None, "codex"))

    def test_absent_arg_falls_to_config_false(self) -> None:
        self.assertFalse(resolve_delegation_active(None, False))

    def test_absent_arg_and_absent_config_defaults_off(self) -> None:
        # No token, no config value → hard default OFF.
        self.assertFalse(resolve_delegation_active(None, None))

    def test_generic_use_codex_is_not_a_delegation_trigger(self) -> None:
        # The fuzzy "use codex" string maps to the REVIEW backend, never to
        # delegation. It is not the `delegate:codex` token, so it does not
        # activate — regardless of how it surfaces (as a bare arg string or
        # absent token), it falls through to config/default.
        self.assertFalse(resolve_delegation_active("use codex", False))
        self.assertFalse(resolve_delegation_active("use codex", None))
        # Even the bare word "codex" as a loose arg is NOT the token.
        self.assertFalse(resolve_delegation_active("codex", False))
        # Only the exact token resolves on.
        self.assertTrue(resolve_delegation_active("delegate:codex", False))

    def test_default_config_value_resolves_off(self) -> None:
        # Wire the resolver to the actual shipped default: a fresh repo's
        # work.delegate is False → delegation OFF when no arg is given.
        flowctl = _load_flowctl()
        default_value = flowctl.get_default_config()["work"]["delegate"]
        self.assertIs(default_value, False)
        self.assertFalse(resolve_delegation_active(None, default_value))


if __name__ == "__main__":
    unittest.main()

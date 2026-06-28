"""Tracker-sync config defaults + activation predicate tests (fn-52.1, R1).

Asserts:
  * `get_default_config()` carries a `tracker` block with the documented
    shape: version + `enabled:false` + `type:null` + `provenance:null` +
    NESTED `perEvent` (so dotted-path get/set works) all defaulting `off` +
    perTracker + staleAfterHours + conflictTiebreak + readyState (fn-58,
    top-level scalar, default null).
  * The dotted-path API resolves a nested perEvent leaf
    (`tracker.perEvent.work.firstClaim`).
  * `deep_merge` preserves unknown keys under `tracker` (forward-compat) and
    falls back to defaults for unset keys.
  * The activation predicate `tracker_sync_active()` is VALUE-CHECKED:
      - absent raw config ⇒ inactive,
      - persisted `type: null` (even with a perEvent set) ⇒ inactive,
      - `type: ""` / unknown ⇒ inactive,
      - `enabled == true` ⇒ active,
      - `type ∈ {linear, github}` ⇒ active.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import importlib.util
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
        "flowctl_tracker_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TrackerConfigTestCase(unittest.TestCase):
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

    def _write_config(self, data: dict) -> None:
        (self.tmpdir / ".flow" / "config.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    # --- Defaults shape -----------------------------------------------------

    def test_default_config_has_tracker_block(self) -> None:
        cfg = self.flowctl.get_default_config()
        self.assertIn("tracker", cfg)
        t = cfg["tracker"]
        self.assertEqual(t["version"], 1)
        self.assertFalse(t["enabled"])
        self.assertIsNone(t["type"])
        self.assertIsNone(t["provenance"])
        self.assertEqual(t["staleAfterHours"], self.flowctl.TRACKER_DEFAULT_STALE_HOURS)
        self.assertEqual(t["conflictTiebreak"], "always-ask")
        # fn-58 (R3/R4): readiness projection knob — a single scalar at the
        # tracker TOP level (NOT under perTracker), default null (= off).
        self.assertIn("readyState", t)
        self.assertIsNone(t["readyState"])
        self.assertNotIn("readyState", t["perTracker"])

    def test_per_event_is_nested_and_defaults_off(self) -> None:
        t = self.flowctl.get_default_config()["tracker"]
        pe = t["perEvent"]
        # work.* is a nested object, NOT a flat literal key.
        self.assertIsInstance(pe["work"], dict)
        self.assertEqual(pe["work"]["firstClaim"], "off")
        self.assertEqual(pe["work"]["done"], "off")
        for leaf in ("capture", "interview", "plan", "makePr", "resolvePr", "completionReview"):
            self.assertEqual(pe[leaf], "off", f"{leaf} should default off")

    def test_dotted_path_resolves_nested_leaf(self) -> None:
        # No on-disk override → merged default resolves the nested leaf.
        self.assertEqual(
            self.flowctl.get_config("tracker.perEvent.work.firstClaim"), "off"
        )
        self.assertEqual(self.flowctl.get_config("tracker.perEvent.capture"), "off")
        # fn-58: a fresh repo reads a clean null for the readiness knob.
        self.assertIsNone(self.flowctl.get_config("tracker.readyState"))

    # --- config set null coercion (PR #170 review) ---------------------------

    def test_config_set_null_clears_ready_state(self) -> None:
        # Opt in: configure a readiness state, then clear it with the
        # documented off value `null`. The CLI delivers argv strings, so
        # set_config must coerce the literal "null" token to JSON null —
        # otherwise the string "null" persists and skill probes
        # (`jq -r '.value // empty'`) see a configured state named "null".
        self.flowctl.set_config("tracker.readyState", "Ready")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk["tracker"]["readyState"], "Ready")
        self.assertEqual(self.flowctl.get_config("tracker.readyState"), "Ready")

        self.flowctl.set_config("tracker.readyState", "null")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertIn("readyState", on_disk["tracker"])
        self.assertIsNone(on_disk["tracker"]["readyState"])  # real JSON null
        # `config get` round-trips to None (merged read path).
        self.assertIsNone(self.flowctl.get_config("tracker.readyState"))

    def test_config_set_null_is_case_insensitive(self) -> None:
        # Same .lower() treatment as the true/false coercion.
        self.flowctl.set_config("tracker.readyState", "NULL")
        on_disk = json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )
        self.assertIsNone(on_disk["tracker"]["readyState"])

    # --- Forward-compat -----------------------------------------------------

    def test_unknown_key_under_tracker_survives_round_trip(self) -> None:
        self._write_config({"tracker": {"myCustomKey": "hello"}})
        # Unknown key preserved (deep_merge keeps it), unset keys fall to default.
        self.assertEqual(self.flowctl.get_config("tracker.myCustomKey"), "hello")
        self.assertFalse(self.flowctl.get_config("tracker.enabled"))
        self.assertEqual(self.flowctl.get_config("tracker.conflictTiebreak"), "always-ask")

    def test_deep_merge_preserves_unknown_keys(self) -> None:
        merged = self.flowctl.deep_merge(
            self.flowctl.get_default_config(), {"tracker": {"futureKnob": 7}}
        )
        self.assertEqual(merged["tracker"]["futureKnob"], 7)
        # Existing defaults untouched.
        self.assertFalse(merged["tracker"]["enabled"])

    # --- Activation predicate (value-checked) -------------------------------

    def test_activation_inactive_when_absent(self) -> None:
        # No config file at all.
        self.assertFalse(self.flowctl.tracker_sync_active())

    def test_activation_inactive_for_persisted_type_null_with_per_event(self) -> None:
        # The critical regression: a default type:null persisted by an
        # unrelated write (plus a perEvent set) must read INACTIVE — NOT
        # dispatched to an adapter.
        self._write_config(
            {"tracker": {"type": None, "perEvent": {"capture": "reconcile"}}}
        )
        self.assertFalse(self.flowctl.tracker_sync_active())

    def test_activation_inactive_for_empty_or_unknown_type(self) -> None:
        self._write_config({"tracker": {"type": ""}})
        self.assertFalse(self.flowctl.tracker_sync_active())
        # `asana` is a genuinely-unsupported tracker type (jira became a real
        # type in fn-70, so it now activates — see test_activation_active_for_known_type).
        self._write_config({"tracker": {"type": "asana"}})
        self.assertFalse(self.flowctl.tracker_sync_active())

    def test_activation_active_when_enabled_true(self) -> None:
        self._write_config({"tracker": {"enabled": True, "type": None}})
        self.assertTrue(self.flowctl.tracker_sync_active())

    def test_activation_active_for_known_type(self) -> None:
        for ttype in ("linear", "github", "gitlab", "jira", "Linear", "GITHUB", "Jira"):
            self._write_config({"tracker": {"enabled": False, "type": ttype}})
            self.assertTrue(
                self.flowctl.tracker_sync_active(), f"type={ttype} should activate"
            )


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the `planSync.gate` config knob (fn-83.1, R6).

`get_default_config()` carries `gate` inside the existing `planSync` block so
`flowctl config get planSync.gate --json` returns the enum string `"on"`
(NOT `null`) on a fresh repo, WITHOUT any prior `config set`:

  * planSync.gate → "on"  (default ON — justified by the fn-83 in-PR
    zero-false-skip proof; "shadow" is the documented cautious path)

This is a STRING-ENUM knob (`off|shadow|on`), NOT a bool — the probe-side
read (`_psp_gate_mode`) is a strict positive match: only the literal "shadow"
/ "on" activate those modes; bool `true`, typos, and null all resolve to
"off" (= always spawn, today's behavior). Mirrors
test_pipeline_qa_config.py (memory docs-activation-command-for-string-enum).

Matrix documented at the defaults block: planSync.enabled=false ⇒ plan-sync
step skipped entirely (gate irrelevant); enabled=true + off ⇒ always spawn,
probe not invoked; shadow ⇒ probe + ledger record + ALWAYS spawn; on ⇒
probe-gated with deterministic ramped audit sampling.
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
        "flowctl_plansync_gate_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class PlanSyncGateConfigTestCase(unittest.TestCase):
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

    def _run_init_cli(self) -> dict:
        ns = argparse.Namespace(json=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_init(ns)
        return json.loads(buf.getvalue())

    def _read_config_file(self) -> dict:
        return json.loads(
            (self.tmpdir / ".flow" / "config.json").read_text(encoding="utf-8")
        )

    # ── Defaults: present in get_default_config() ────────────────────────

    def test_defaults_dict_has_gate_in_plansync_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("planSync", defaults)
        self.assertEqual(
            defaults["planSync"],
            {"enabled": True, "crossSpec": False, "gate": "on"},
        )

    # ── Defaults: surfaced via `config get --json` on a FRESH repo ───────

    def test_fresh_get_gate_is_on_string(self) -> None:
        out = self._run_config_get_cli("planSync.gate")
        self.assertEqual(out["value"], "on")
        # STRING-ENUM, not a bool — the value is the literal "on", never True.
        self.assertNotIsInstance(out["value"], bool)

    # ── set round-trips across the enum ──────────────────────────────────

    def test_set_shadow_round_trips(self) -> None:
        self._run_config_set_cli("planSync.gate", "shadow")
        self.assertEqual(self._run_config_get_cli("planSync.gate")["value"], "shadow")

    def test_set_off_round_trips(self) -> None:
        self._run_config_set_cli("planSync.gate", "off")
        self.assertEqual(self._run_config_get_cli("planSync.gate")["value"], "off")

    def test_set_on_round_trips(self) -> None:
        self._run_config_set_cli("planSync.gate", "off")
        self._run_config_set_cli("planSync.gate", "on")
        self.assertEqual(self._run_config_get_cli("planSync.gate")["value"], "on")

    # ── The strict-positive probe read (_psp_gate_mode) ──────────────────
    # Only the literal enum strings are recognized; bool `true` (config set
    # coerces "true" → True), typos, and null all resolve to "off".

    def test_gate_mode_default_on(self) -> None:
        self.assertEqual(self.flowctl._psp_gate_mode(), "on")

    def test_gate_mode_shadow_recognized(self) -> None:
        self._run_config_set_cli("planSync.gate", "shadow")
        self.assertEqual(self.flowctl._psp_gate_mode(), "shadow")

    def test_gate_mode_off_recognized(self) -> None:
        self._run_config_set_cli("planSync.gate", "off")
        self.assertEqual(self.flowctl._psp_gate_mode(), "off")

    def test_gate_mode_rejects_bool_true(self) -> None:
        # `config set planSync.gate true` coerces to bool True — NOT an
        # activating value for a string-enum knob.
        self._run_config_set_cli("planSync.gate", "true")
        self.assertEqual(self.flowctl._psp_gate_mode(), "off")

    def test_gate_mode_rejects_typo(self) -> None:
        self._run_config_set_cli("planSync.gate", "onn")
        self.assertEqual(self.flowctl._psp_gate_mode(), "off")

    def test_gate_mode_rejects_null(self) -> None:
        self._run_config_set_cli("planSync.gate", "null")
        self.assertEqual(self.flowctl._psp_gate_mode(), "off")

    # ── init materializes the gate (planSync is NOT init-exempt) ─────────

    def test_fresh_init_materializes_gate(self) -> None:
        out = self._run_init_cli()
        self.assertTrue(out["success"])
        self.assertEqual(
            self._read_config_file()["planSync"],
            {"enabled": True, "crossSpec": False, "gate": "on"},
        )

    def test_init_upgrade_adds_gate_preserving_user_values(self) -> None:
        # Pre-fn-83 config.json with a user-tuned planSync block: init's
        # upgrade merge must add the missing `gate` default WITHOUT
        # clobbering the user's existing keys.
        config_path = self.tmpdir / ".flow" / "config.json"
        config_path.write_text(
            json.dumps({"planSync": {"enabled": False, "crossSpec": True}}),
            encoding="utf-8",
        )
        self._run_init_cli()
        upgraded = self._read_config_file()["planSync"]
        self.assertEqual(upgraded["gate"], "on")
        self.assertIs(upgraded["enabled"], False)
        self.assertIs(upgraded["crossSpec"], True)

    def test_user_set_value_survives_init_rerun(self) -> None:
        self._run_init_cli()
        self._run_config_set_cli("planSync.gate", "shadow")
        self._run_init_cli()
        self.assertEqual(self._run_config_get_cli("planSync.gate")["value"], "shadow")

    # ── deep_merge / namespace hygiene ────────────────────────────────────

    def test_unknown_sibling_keys_under_plansync_survive_re_set(self) -> None:
        self._run_config_set_cli("planSync.future", "x")
        self._run_config_set_cli("planSync.gate", "shadow")
        self.assertEqual(self._run_config_get_cli("planSync.future")["value"], "x")
        self.assertEqual(self._run_config_get_cli("planSync.gate")["value"], "shadow")

    def test_setting_gate_does_not_clobber_plansync_siblings(self) -> None:
        self._run_config_set_cli("planSync.gate", "shadow")
        self.assertIs(
            self._run_config_get_cli("planSync.enabled")["value"], True
        )
        self.assertIs(
            self._run_config_get_cli("planSync.crossSpec")["value"], False
        )


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the optional QA pipeline-stage config gate (fn-72.2, R1/R3).

`get_default_config()` carries a top-level `pipeline` block so
`flowctl config get pipeline.qa --json` returns the enum string `"off"`
(NOT `null`) on a fresh repo, WITHOUT any prior `config set`:

  * pipeline.qa → "off"  (opt-in; OFF by default)

This is a STRING-ENUM knob (`off|on`), NOT a bool — the pilot gate read is
the canonical 3-clause guard (`value != "off" && value != "null"`), so the
activating value is the literal `"on"`; bool `true` is NOT recognized
(memory docs-activation-command-for-string-enum). The default `"off"` keeps
pilot's stage set + behavior byte-for-byte unchanged.

Unlike the `artifacts` block, `pipeline` is NOT in
`_INIT_UNMATERIALIZED_BLOCKS`: there is no setup-ceremony
include-only-if-unset question gated on a `--raw` null probe, so it
materializes into config.json on init like the `work.*` / `land.*` blocks.
Mirrors test_artifacts_config.py / test_land_config.py.
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
        "flowctl_pipeline_qa_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class PipelineQaConfigTestCase(unittest.TestCase):
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

    def test_defaults_dict_has_pipeline_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("pipeline", defaults)
        self.assertEqual(defaults["pipeline"], {"qa": "off"})

    # ── Defaults: surfaced via `config get --json` on a FRESH repo ───────
    # No config.json on disk and no prior `config set` — the merge must
    # return the spec default "off" (the enum string), NOT null and NOT a
    # bool (R1/R3: present, the activating value is "on", not bool true).

    def test_fresh_get_qa_is_off_string(self) -> None:
        out = self._run_config_get_cli("pipeline.qa")
        self.assertEqual(out["value"], "off")
        self.assertIsNotNone(out["value"])
        # STRING-ENUM, not a bool — `value` is the literal "off", never False.
        self.assertNotIsInstance(out["value"], bool)

    # ── set round-trips to the activating enum value "on" ────────────────
    # set_config already takes arbitrary nested dot-paths; the only flowctl
    # change is the defaults block, so `set` + `get` round-trips. The gate
    # activates ONLY on the literal "on".

    def test_set_on_round_trips(self) -> None:
        set_out = self._run_config_set_cli("pipeline.qa", "on")
        self.assertEqual(set_out["value"], "on")
        get_out = self._run_config_get_cli("pipeline.qa")
        self.assertEqual(get_out["value"], "on")

    def test_set_off_round_trips(self) -> None:
        self._run_config_set_cli("pipeline.qa", "on")
        self._run_config_set_cli("pipeline.qa", "off")
        get_out = self._run_config_get_cli("pipeline.qa")
        self.assertEqual(get_out["value"], "off")

    # ── The 3-clause pilot gate read (value != "off" && value != "null") ──
    # The activating value is exactly "on"; default "off" reads OFF; a stray
    # bool `true` is NOT the activating value (string-enum, not bool).

    def test_gate_predicate_off_by_default(self) -> None:
        value = self._run_config_get_cli("pipeline.qa")["value"]
        gate_on = value not in ("off", "null", None)
        self.assertFalse(gate_on)

    def test_gate_predicate_on_after_set_on(self) -> None:
        self._run_config_set_cli("pipeline.qa", "on")
        value = self._run_config_get_cli("pipeline.qa")["value"]
        gate_on = value not in ("off", "null", None)
        self.assertTrue(gate_on)

    # ── deep_merge preservation ──────────────────────────────────────────

    def test_unknown_sibling_keys_under_pipeline_survive_re_set(self) -> None:
        # An unknown sibling under `pipeline` (e.g. a future stage gate) must
        # survive a re-set of pipeline.qa — deep_merge preserves unknown keys
        # instead of clobbering the block.
        self._run_config_set_cli("pipeline.lint", "on")
        self._run_config_set_cli("pipeline.qa", "on")
        self.assertEqual(self._run_config_get_cli("pipeline.lint")["value"], "on")
        self.assertEqual(self._run_config_get_cli("pipeline.qa")["value"], "on")

    # ── init materializes the pipeline block (NOT exempt) ────────────────
    # Unlike artifacts, `pipeline` is NOT in _INIT_UNMATERIALIZED_BLOCKS —
    # there is no setup-ceremony `--raw` null probe for it, so init writes it
    # into config.json like work.*/land.*.

    def test_fresh_init_materializes_pipeline_block(self) -> None:
        out = self._run_init_cli()
        self.assertTrue(out["success"])
        self.assertIn("pipeline", self._read_config_file())
        self.assertEqual(self._read_config_file()["pipeline"], {"qa": "off"})

    def test_init_upgrade_adds_pipeline_block(self) -> None:
        # Existing pre-fn-72 config.json: init's upgrade merge adds missing
        # defaults including the pipeline block.
        config_path = self.tmpdir / ".flow" / "config.json"
        config_path.write_text(
            json.dumps({"memory": {"enabled": True}}), encoding="utf-8"
        )
        self._run_init_cli()
        upgraded = self._read_config_file()
        self.assertIn("pipeline", upgraded)
        self.assertEqual(upgraded["pipeline"], {"qa": "off"})

    def test_user_set_value_survives_init_rerun(self) -> None:
        # An explicit `config set pipeline.qa on` is preserved by a later
        # idempotent init.
        self._run_init_cli()
        self._run_config_set_cli("pipeline.qa", "on")
        self._run_init_cli()
        out = self._run_config_get_cli("pipeline.qa")
        self.assertEqual(out["value"], "on")

    # ── Namespace coexistence ─────────────────────────────────────────────

    def test_pipeline_block_does_not_clash_with_existing_blocks(self) -> None:
        defaults = self.flowctl.get_default_config()
        # pipeline.* is its own top-level block, distinct from work.*,
        # land.*, artifacts.*, and memory.* — no shared keys leak across.
        self.assertIn("pipeline", defaults)
        self.assertIn("work", defaults)
        self.assertIn("artifacts", defaults)
        self.assertNotIn("qa", defaults["work"])
        self.assertNotIn("qa", defaults["artifacts"])
        self.assertNotIn("html", defaults["pipeline"])

    def test_setting_pipeline_key_does_not_clobber_other_defaults(self) -> None:
        self._run_config_set_cli("pipeline.qa", "on")
        self.assertEqual(
            self._run_config_get_cli("work.delegateModel")["value"], "gpt-5.6-terra"
        )
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )
        self.assertIs(
            self._run_config_get_cli("artifacts.html.enabled")["value"], False
        )


if __name__ == "__main__":
    unittest.main()

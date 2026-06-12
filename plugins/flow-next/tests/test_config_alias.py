"""Removal regression tests for the `planSync.crossEpic` config alias
(fn-62.6, R14 — 2.0.0).

The alias (`planSync.crossEpic` → `planSync.crossSpec`, introduced fn-46.1,
deprecated 1.1.3+) was removed in 2.0.0 per the documented 1.x deprecation
promise. These tests pin the post-removal behavior:

  * Defaults dict has `crossSpec`, not `crossEpic`.
  * `_CONFIG_KEY_ALIASES` is empty — `planSync.crossEpic` no longer maps to
    anything (the resolution machinery stays for future renames).
  * Reading the canonical `planSync.crossSpec` NEVER falls back to a legacy
    `crossEpic` value left in the raw file — merged reads return the default,
    `--raw` reads return null.
  * `planSync.crossEpic` is now an unknown key: reads/writes pass through
    literally with NO redirect and NO deprecation warning.
  * The generic `_emit_rename_deprecation` machinery (used by the surviving
    CLI-form renames, e.g. `--epic` → `--spec`) keeps its contract: `extra`
    suffix, per-process dedup, `FLOW_NO_DEPRECATION=1` suppression.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_config_alias_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ConfigAliasRemovalTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        flow_dir = self.tmpdir / ".flow"
        flow_dir.mkdir(parents=True, exist_ok=True)
        # Reset per-process dedup so each test starts clean.
        self.flowctl._RENAME_DEPRECATION_EMITTED.clear()
        # Clear FLOW_NO_DEPRECATION just in case the runner exported it.
        self._prev_no_depr = os.environ.pop("FLOW_NO_DEPRECATION", None)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self._prev_no_depr is not None:
            os.environ["FLOW_NO_DEPRECATION"] = self._prev_no_depr

    def _write_config(self, data: dict) -> None:
        config_path = self.tmpdir / ".flow" / "config.json"
        config_path.write_text(json.dumps(data), encoding="utf-8")

    # --- the removal itself ---

    def test_defaults_use_canonical_key_only(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("crossSpec", defaults["planSync"])
        self.assertNotIn("crossEpic", defaults["planSync"])

    def test_alias_map_is_empty(self) -> None:
        self.assertNotIn(
            "planSync.crossEpic",
            self.flowctl._CONFIG_KEY_ALIASES,
            "2.0.0 removed the crossEpic alias — it must never map again.",
        )
        self.assertEqual(
            self.flowctl._CONFIG_KEY_ALIASES,
            {},
            "No active config-key aliases post-2.0.0.",
        )

    def test_canonical_read_ignores_leftover_legacy_key(self) -> None:
        # Only legacy crossEpic in the file: pre-2.0 this fell back; now the
        # canonical read must return the DEFAULT (False), never the legacy
        # value.
        self._write_config({"planSync": {"crossEpic": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossSpec"
        )
        self.assertEqual(eff, "planSync.crossSpec")
        self.assertFalse(
            value, "Leftover crossEpic must be inert — default wins."
        )
        self.assertEqual(dep, "")

    def test_legacy_read_is_plain_unknown_key_no_warn(self) -> None:
        # `get planSync.crossEpic` no longer redirects or warns — it is a
        # literal key lookup like any other unknown key.
        self._write_config({"planSync": {"crossSpec": True}})
        buf = io.StringIO()
        with redirect_stderr(buf):
            eff, value, dep = self.flowctl.resolve_config_key_for_read(
                "planSync.crossEpic"
            )
        self.assertEqual(eff, "planSync.crossEpic")
        self.assertIsNone(value, "No redirect to canonical post-removal.")
        self.assertEqual(dep, "", "No deprecation form post-removal.")
        self.assertEqual(buf.getvalue(), "", "No warning post-removal.")

    def test_legacy_write_is_not_redirected(self) -> None:
        canonical, dep = self.flowctl.resolve_config_key_for_write(
            "planSync.crossEpic"
        )
        self.assertEqual(
            canonical,
            "planSync.crossEpic",
            "Writes no longer redirect legacy → canonical.",
        )
        self.assertEqual(dep, "")

    def test_canonical_read_write_unchanged(self) -> None:
        self._write_config({"planSync": {"crossSpec": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossSpec"
        )
        self.assertEqual(eff, "planSync.crossSpec")
        self.assertTrue(value)
        self.assertEqual(dep, "")
        canonical, dep2 = self.flowctl.resolve_config_key_for_write(
            "planSync.crossSpec"
        )
        self.assertEqual(canonical, "planSync.crossSpec")
        self.assertEqual(dep2, "")

    def test_default_when_neither_key_set(self) -> None:
        self._write_config({"planSync": {"enabled": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossSpec"
        )
        self.assertEqual(eff, "planSync.crossSpec")
        self.assertFalse(value, "Default for crossSpec is False")
        self.assertEqual(dep, "")

    def test_unrelated_key_unchanged(self) -> None:
        eff, _, dep = self.flowctl.resolve_config_key_for_read(
            "memory.enabled"
        )
        self.assertEqual(eff, "memory.enabled")
        self.assertEqual(dep, "")
        canonical, dep2 = self.flowctl.resolve_config_key_for_write(
            "memory.enabled"
        )
        self.assertEqual(canonical, "memory.enabled")
        self.assertEqual(dep2, "")

    # --- generic deprecation machinery (still used by CLI-form renames) ---

    def test_emit_extra_appended(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.flowctl._emit_rename_deprecation(
                "--epic",
                "--spec",
                extra="Removed in a future major.",
            )
        out = buf.getvalue()
        self.assertIn("--epic is deprecated", out)
        self.assertIn("use --spec", out)
        self.assertIn("Suppress with FLOW_NO_DEPRECATION=1", out)
        self.assertIn("Removed in a future major.", out)

    def test_emit_dedup_per_process(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            for _ in range(3):
                self.flowctl._emit_rename_deprecation("--epic", "--spec")
        out = buf.getvalue()
        # Exactly one warning across 3 calls.
        self.assertEqual(out.count("--epic is deprecated"), 1)

    def test_emit_suppressed_by_env(self) -> None:
        os.environ["FLOW_NO_DEPRECATION"] = "1"
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                self.flowctl._emit_rename_deprecation("--epic", "--spec")
            self.assertEqual(buf.getvalue(), "")
        finally:
            os.environ.pop("FLOW_NO_DEPRECATION", None)

    # --- raw-file probe (load-bearing for setup's --raw reads) ---

    def test_raw_file_probe_distinguishes_unset_from_false(self) -> None:
        # crossSpec absent from raw file → sentinel.
        self._write_config({"planSync": {"enabled": True}})
        sentinel = self.flowctl._get_config_from_file("planSync.crossSpec")
        self.assertIs(sentinel, self.flowctl._CONFIG_RAW_SENTINEL)
        # crossSpec set to False in raw file → False, not sentinel.
        self._write_config({"planSync": {"crossSpec": False}})
        value = self.flowctl._get_config_from_file("planSync.crossSpec")
        self.assertIs(value, False)
        # Critical: `get_config` would return False either way due to merge.
        self.assertIs(self.flowctl.get_config("planSync.crossSpec"), False)

    # --- CLI-level `flowctl config get --raw --json` ---
    # Regression coverage for PR #135 cycle 2: without `--raw`, default-false
    # config keys (planSync.crossSpec, scouts.github) cause /flow-next:setup
    # to skip first-run prompts because the merge step returns the default.
    # `--raw` must emit JSON `null` for keys absent from the on-disk file,
    # `false` for explicit-false, and `true` for explicit-true.

    def _run_config_get_cli(self, key: str, *extra: str) -> dict:
        """Invoke cmd_config_get via the argparse namespace and capture JSON stdout."""
        ns = argparse.Namespace(
            key=key,
            json=True,
            raw="--raw" in extra,
        )
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_get(ns)
        return json.loads(buf.getvalue())

    def test_cli_raw_absent_key_returns_null(self) -> None:
        self._write_config({"planSync": {"enabled": True}})
        out = self._run_config_get_cli("planSync.crossSpec", "--raw")
        self.assertIsNone(out["value"])
        self.assertTrue(out.get("raw"))
        self.assertTrue(out.get("success"))

    def test_cli_raw_explicit_false_returns_false(self) -> None:
        self._write_config({"planSync": {"crossSpec": False}})
        out = self._run_config_get_cli("planSync.crossSpec", "--raw")
        self.assertIs(out["value"], False)
        self.assertTrue(out.get("raw"))

    def test_cli_raw_explicit_true_returns_true(self) -> None:
        self._write_config({"scouts": {"github": True}})
        out = self._run_config_get_cli("scouts.github", "--raw")
        self.assertIs(out["value"], True)
        self.assertTrue(out.get("raw"))

    def test_cli_default_merges_unset_to_default_value(self) -> None:
        # Without --raw, an absent default-false key returns its default.
        self._write_config({"planSync": {"enabled": True}})
        out = self._run_config_get_cli("planSync.crossSpec")
        self.assertIs(out["value"], False)
        self.assertNotIn("raw", out)

    def test_cli_raw_canonical_ignores_leftover_legacy(self) -> None:
        # Removal regression: only legacy crossEpic in the file — the raw
        # canonical read must surface null (pre-2.0 it fell back to legacy).
        self._write_config({"planSync": {"crossEpic": True}})
        out = self._run_config_get_cli("planSync.crossSpec", "--raw")
        self.assertIsNone(out["value"])

    def test_cli_raw_neither_canonical_nor_legacy_returns_null(self) -> None:
        self._write_config({"planSync": {"enabled": True}})
        out = self._run_config_get_cli("planSync.crossSpec", "--raw")
        self.assertIsNone(out["value"])

    def test_cli_legacy_get_no_deprecation_on_stderr(self) -> None:
        # End-to-end: `config get planSync.crossEpic --raw` emits nothing on
        # stderr post-removal (pre-2.0 it warned once per process).
        self._write_config({"planSync": {"crossEpic": True}})
        err = io.StringIO()
        with redirect_stderr(err):
            out = self._run_config_get_cli("planSync.crossEpic", "--raw")
        # Literal unknown-key raw read still sees the file value (the key
        # exists on disk) but produces no deprecation and no redirect.
        self.assertIs(out["value"], True)
        self.assertEqual(out["key"], "planSync.crossEpic")
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

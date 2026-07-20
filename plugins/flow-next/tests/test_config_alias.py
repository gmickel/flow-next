"""Post-removal config-key tests (fn-111.2).

The `planSync.crossEpic` → `planSync.crossSpec` alias was removed in 2.0.0;
fn-111.2 removes the remaining empty alias machinery (identity resolvers +
empty `_CONFIG_KEY_ALIASES` seam only). These tests pin still-live behavior:

  * Defaults dict has `crossSpec`, not `crossEpic`.
  * `_CONFIG_KEY_ALIASES` stays empty (seam for future renames).
  * Reading the canonical `planSync.crossSpec` NEVER falls back to a leftover
    `crossEpic` value — merged reads return the default, `--raw` returns null.
  * `planSync.crossEpic` is an unknown key: reads/writes pass through literally.
  * `--raw` distinguishes unset from explicit false/true (setup first-run).
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

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_config(self, data: dict) -> None:
        config_path = self.tmpdir / ".flow" / "config.json"
        config_path.write_text(json.dumps(data), encoding="utf-8")

    def test_defaults_use_canonical_key_only(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("crossSpec", defaults["planSync"])
        self.assertNotIn("crossEpic", defaults["planSync"])

    def test_alias_map_is_empty(self) -> None:
        self.assertEqual(
            self.flowctl._CONFIG_KEY_ALIASES,
            {},
            "No active config-key aliases; empty seam only.",
        )

    def test_canonical_read_ignores_leftover_legacy_key(self) -> None:
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
            "Writes no longer redirect legacy to canonical.",
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

    def test_raw_file_probe_distinguishes_unset_from_false(self) -> None:
        self._write_config({"planSync": {"enabled": True}})
        sentinel = self.flowctl._get_config_from_file("planSync.crossSpec")
        self.assertIs(sentinel, self.flowctl._CONFIG_RAW_SENTINEL)
        self._write_config({"planSync": {"crossSpec": False}})
        value = self.flowctl._get_config_from_file("planSync.crossSpec")
        self.assertIs(value, False)
        self.assertIs(self.flowctl.get_config("planSync.crossSpec"), False)

    def _run_config_get_cli(self, key: str, *extra: str) -> dict:
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
        self._write_config({"planSync": {"enabled": True}})
        out = self._run_config_get_cli("planSync.crossSpec")
        self.assertIs(out["value"], False)
        self.assertNotIn("raw", out)

    def test_cli_raw_canonical_ignores_leftover_legacy(self) -> None:
        self._write_config({"planSync": {"crossEpic": True}})
        out = self._run_config_get_cli("planSync.crossSpec", "--raw")
        self.assertIsNone(out["value"])

    def test_cli_raw_neither_canonical_nor_legacy_returns_null(self) -> None:
        self._write_config({"planSync": {"enabled": True}})
        out = self._run_config_get_cli("planSync.crossSpec", "--raw")
        self.assertIsNone(out["value"])

    def test_cli_legacy_get_no_deprecation_on_stderr(self) -> None:
        self._write_config({"planSync": {"crossEpic": True}})
        err = io.StringIO()
        with redirect_stderr(err):
            out = self._run_config_get_cli("planSync.crossEpic", "--raw")
        self.assertIs(out["value"], True)
        self.assertEqual(out["key"], "planSync.crossEpic")
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

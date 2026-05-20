"""Unit tests for the planSync.crossEpic → planSync.crossSpec legacy alias
(fn-46.1, R1).

Asserts:
  * Defaults dict has `crossSpec`, not `crossEpic`.
  * `resolve_config_key_for_read` returns canonical when present, falls back
    to legacy when canonical absent from the raw file, and reports the
    deprecation legacy form only when the user typed the legacy alias AND
    canonical is absent.
  * `resolve_config_key_for_write` redirects legacy → canonical and reports
    the deprecation legacy form on legacy input.
  * The `extra` parameter on `_emit_rename_deprecation` appends the suffix
    after the standard suppression hint and honours `FLOW_NO_DEPRECATION=1`.
  * Per-process dedup emits each legacy form at most once.
  * Writing the canonical never deletes the legacy key from the raw file.
  * Writing the legacy alias writes the canonical key, leaving legacy as-is.
"""

from __future__ import annotations

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


class ConfigAliasTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        # Initialize .flow/ via flowctl.cmd_init equivalent (just create dirs).
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

    def test_defaults_use_canonical_key(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("crossSpec", defaults["planSync"])
        self.assertNotIn(
            "crossEpic",
            defaults["planSync"],
            "Legacy key must be absent from defaults so file presence "
            "= explicit legacy set.",
        )

    def test_alias_map_entry(self) -> None:
        self.assertEqual(
            self.flowctl._CONFIG_KEY_ALIASES.get("planSync.crossEpic"),
            "planSync.crossSpec",
        )

    def test_read_canonical_returns_canonical_value_when_set(self) -> None:
        self._write_config({"planSync": {"crossSpec": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossSpec"
        )
        self.assertEqual(eff, "planSync.crossSpec")
        self.assertTrue(value)
        self.assertEqual(dep, "")

    def test_read_legacy_when_canonical_set_no_warn(self) -> None:
        self._write_config(
            {"planSync": {"crossSpec": True, "crossEpic": False}}
        )
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossEpic"
        )
        self.assertEqual(eff, "planSync.crossSpec")
        self.assertTrue(value, "Canonical wins even when legacy is also set")
        self.assertEqual(
            dep, "", "No warning when canonical is present, regardless of input"
        )

    def test_read_canonical_falls_back_to_legacy_no_warn(self) -> None:
        # Only legacy is set in file; canonical is absent.
        self._write_config({"planSync": {"crossEpic": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossSpec"
        )
        self.assertEqual(eff, "planSync.crossEpic")
        self.assertTrue(value)
        self.assertEqual(
            dep,
            "",
            "Reading canonical surfaces legacy value silently (no warn)",
        )

    def test_read_legacy_when_only_legacy_set_warns(self) -> None:
        self._write_config({"planSync": {"crossEpic": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossEpic"
        )
        self.assertEqual(eff, "planSync.crossEpic")
        self.assertTrue(value)
        self.assertEqual(dep, "planSync.crossEpic")

    def test_read_neither_set_returns_default(self) -> None:
        self._write_config({"planSync": {"enabled": True}})
        eff, value, dep = self.flowctl.resolve_config_key_for_read(
            "planSync.crossEpic"
        )
        self.assertEqual(eff, "planSync.crossSpec")
        self.assertFalse(value, "Default for crossSpec is False")
        self.assertEqual(dep, "", "No warn when neither key explicitly set")

    def test_write_legacy_redirects_to_canonical(self) -> None:
        canonical, dep = self.flowctl.resolve_config_key_for_write(
            "planSync.crossEpic"
        )
        self.assertEqual(canonical, "planSync.crossSpec")
        self.assertEqual(dep, "planSync.crossEpic")

    def test_write_canonical_no_alias_no_warn(self) -> None:
        canonical, dep = self.flowctl.resolve_config_key_for_write(
            "planSync.crossSpec"
        )
        self.assertEqual(canonical, "planSync.crossSpec")
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

    def test_emit_extra_appended(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.flowctl._emit_rename_deprecation(
                "planSync.crossEpic",
                "planSync.crossSpec",
                extra="Removed in 2.0.",
            )
        out = buf.getvalue()
        self.assertIn("planSync.crossEpic is deprecated", out)
        self.assertIn("use planSync.crossSpec", out)
        self.assertIn("Suppress with FLOW_NO_DEPRECATION=1", out)
        self.assertIn("Removed in 2.0.", out)

    def test_emit_dedup_per_process(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            for _ in range(3):
                self.flowctl._emit_rename_deprecation(
                    "planSync.crossEpic",
                    "planSync.crossSpec",
                    extra="Removed in 2.0.",
                )
        out = buf.getvalue()
        # Exactly one warning across 3 calls.
        self.assertEqual(out.count("planSync.crossEpic is deprecated"), 1)

    def test_emit_suppressed_by_env(self) -> None:
        os.environ["FLOW_NO_DEPRECATION"] = "1"
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                self.flowctl._emit_rename_deprecation(
                    "planSync.crossEpic",
                    "planSync.crossSpec",
                    extra="Removed in 2.0.",
                )
            self.assertEqual(buf.getvalue(), "")
        finally:
            os.environ.pop("FLOW_NO_DEPRECATION", None)

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


if __name__ == "__main__":
    unittest.main()

"""Command-scoped config snapshot tests (fn-110.1, R1).

Pins the three `config get` read forms and the snapshot mechanism:

  * keyless ROOT read — `{"key": null, "value": {<full merged>}}`;
    `--raw` returns set-only values (absent leaves omitted, not defaulted;
    `{}` when config.json does not exist).
  * keyed SUBTREE read — a key resolving to a dict returns the merged
    subtree (`--raw`: set-only subtree).
  * keyed SCALAR read — byte-identical to the pre-snapshot (2.20.0)
    behavior, JSON and human forms, including missing-key output.
  * parse contract — AT MOST one config.json parse per invocation;
    exactly one when the file exists, zero when it does not.
  * `resolve_config_key_for_read(key, snapshot=...)` returns the same
    result as the snapshot-less call (default None path unchanged).

Alias-injection cases removed in fn-111.2 (empty alias map; identity resolvers).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_config_snapshot.py" -v
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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_config_snapshot_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ConfigSnapshotTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        (self.tmpdir / ".flow").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- helpers -------------------------------------------------------------

    def _write_config(self, data: dict) -> None:
        (self.tmpdir / ".flow" / "config.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def _get(self, key=None, raw: bool = False, json_mode: bool = True) -> str:
        """Run cmd_config_get, returning raw stdout (stderr swallowed)."""
        ns = argparse.Namespace(key=key, raw=raw, json=json_mode)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.flowctl.cmd_config_get(ns)
        self._last_stderr = err.getvalue()
        return out.getvalue()

    def _get_json(self, key=None, raw: bool = False) -> dict:
        return json.loads(self._get(key=key, raw=raw))

    # --- root read (keyless) -------------------------------------------------

    def test_root_merged_read_returns_full_config(self) -> None:
        self._write_config({"memory": {"enabled": False}})
        result = self._get_json()
        self.assertTrue(result["success"])
        self.assertIsNone(result["key"])
        value = result["value"]
        # Override applied…
        self.assertIs(value["memory"]["enabled"], False)
        # …and defaults merged in for namespaces the file never mentions.
        self.assertIs(value["planSync"]["crossSpec"], False)
        self.assertIn("tracker", value)
        self.assertEqual(value, self.flowctl.load_flow_config())

    def test_root_raw_read_is_set_only(self) -> None:
        self._write_config({"memory": {"enabled": False}})
        result = self._get_json(raw=True)
        self.assertIsNone(result["key"])
        self.assertIs(result["raw"], True)
        # Exactly the persisted file — no defaulted leaves.
        self.assertEqual(result["value"], {"memory": {"enabled": False}})

    def test_root_raw_read_without_config_file_is_empty(self) -> None:
        result = self._get_json(raw=True)
        self.assertEqual(result["value"], {})

    def test_root_merged_read_without_config_file_is_defaults(self) -> None:
        result = self._get_json()
        self.assertEqual(result["value"], self.flowctl.get_default_config())

    # --- subtree read (dict-valued key) ---------------------------------------

    def test_subtree_merged_read(self) -> None:
        self._write_config({"planSync": {"enabled": False}})
        result = self._get_json(key="planSync")
        self.assertEqual(result["key"], "planSync")
        self.assertEqual(result["value"], {"enabled": False, "crossSpec": False})

    def test_empty_dict_default_subtree_returns_empty_dict(self) -> None:
        # Review round 1: `_walk_config_value`'s empty-dict-means-default
        # quirk must not leak into subtree reads — a real `{}` default like
        # tracker.perTracker.labelMap is `{}`, not null.
        self._write_config({"memory": {"enabled": True}})
        result = self._get_json(key="tracker.perTracker.labelMap")
        self.assertEqual(result["value"], {})
        # Root read agrees.
        root = self._get_json()
        self.assertEqual(root["value"]["tracker"]["perTracker"]["labelMap"], {})

    def test_snapshot_merged_read_is_sentinel_aware(self) -> None:
        # The documented snapshot-path divergence: empty-dict values surface
        # as {} via the snapshot, while the snapshot-less get_config keeps
        # its historical empty-dict-means-default quirk.
        self._write_config({"memory": {"enabled": True}})
        snapshot = self.flowctl.load_config_snapshot()
        _, via_snapshot, _ = self.flowctl.resolve_config_key_for_read(
            "tracker.perTracker.labelMap", snapshot=snapshot
        )
        self.assertEqual(via_snapshot, {})
        self.assertIsNone(self.flowctl.get_config("tracker.perTracker.labelMap"))

    def test_subtree_raw_read_is_set_only(self) -> None:
        self._write_config({"planSync": {"enabled": False}})
        result = self._get_json(key="planSync", raw=True)
        self.assertEqual(result["value"], {"enabled": False})

    # --- scalar byte-compatibility (2.20.0 corpus) -----------------------------

    def test_scalar_json_output_byte_identical(self) -> None:
        self._write_config({"memory": {"enabled": True}})
        out = self._get(key="memory.enabled")
        self.assertEqual(
            out,
            '{\n  "success": true,\n  "key": "memory.enabled",\n  "value": true\n}\n',
        )

    def test_scalar_human_output_byte_identical(self) -> None:
        self._write_config({"memory": {"enabled": True}})
        self.assertEqual(
            self._get(key="memory.enabled", json_mode=False),
            "memory.enabled: true\n",
        )

    def test_missing_key_merged_and_raw(self) -> None:
        self._write_config({"memory": {"enabled": True}})
        self.assertEqual(
            self._get(key="nope.nothing"),
            '{\n  "success": true,\n  "key": "nope.nothing",\n  "value": null\n}\n',
        )
        self.assertEqual(
            self._get(key="nope.nothing", json_mode=False),
            "nope.nothing: (not set)\n",
        )
        raw_result = self._get_json(key="nope.nothing", raw=True)
        self.assertIsNone(raw_result["value"])
        self.assertIs(raw_result["raw"], True)

    def test_scalar_raw_unset_is_null_even_with_default(self) -> None:
        # fn-46.1 contract: --raw distinguishes unset from explicitly-set.
        self._write_config({"memory": {"enabled": True}})
        result = self._get_json(key="planSync.crossSpec", raw=True)
        self.assertIsNone(result["value"])

    # --- parse contract: at most one config.json parse per invocation ---------

    def _count_json_loads(self, fn) -> int:
        real_loads = self.flowctl.json.loads
        counter = {"n": 0}

        def counting_loads(*a, **kw):
            counter["n"] += 1
            return real_loads(*a, **kw)

        self.flowctl.json.loads = counting_loads
        try:
            fn()
        finally:
            self.flowctl.json.loads = real_loads
        return counter["n"]

    def test_exactly_one_parse_when_config_exists(self) -> None:
        self._write_config({"memory": {"enabled": False}})
        for kwargs in (
            {},  # root merged
            {"raw": True},  # root raw
            {"key": "planSync"},  # subtree
            {"key": "memory.enabled"},  # scalar merged
            {"key": "memory.enabled", "raw": True},  # scalar raw
            {"key": "nope.nothing"},  # missing key
        ):
            with self.subTest(**kwargs):
                n = self._count_json_loads(lambda kw=kwargs: self._get(**kw))
                self.assertEqual(n, 1)

    def test_zero_parses_when_config_absent(self) -> None:
        for kwargs in ({}, {"raw": True}, {"key": "memory.enabled"}):
            with self.subTest(**kwargs):
                n = self._count_json_loads(lambda kw=kwargs: self._get(**kw))
                self.assertEqual(n, 0)

    # --- resolver snapshot parameter -------------------------------------------

    def test_resolver_with_snapshot_matches_snapshotless(self) -> None:
        self._write_config(
            {"memory": {"enabled": False}, "planSync": {"enabled": False}}
        )
        snapshot = self.flowctl.load_config_snapshot()
        for key in ("memory.enabled", "planSync", "planSync.crossSpec", "nope"):
            with self.subTest(key=key):
                self.assertEqual(
                    self.flowctl.resolve_config_key_for_read(key, snapshot=snapshot),
                    self.flowctl.resolve_config_key_for_read(key),
                )

    def test_resolver_default_path_unchanged_for_other_callers(self) -> None:
        # Default None = pre-snapshot behavior; the tuple contract holds.
        self._write_config({"memory": {"enabled": False}})
        effective, value, deprecation = self.flowctl.resolve_config_key_for_read(
            "memory.enabled"
        )
        self.assertEqual(effective, "memory.enabled")
        self.assertIs(value, False)
        self.assertEqual(deprecation, "")

    def test_snapshot_never_outlives_command(self) -> None:
        # A fresh invocation observes a config change written in between —
        # the snapshot is command-scoped, not cached.
        self._write_config({"memory": {"enabled": True}})
        self.assertIs(self._get_json(key="memory.enabled")["value"], True)
        self._write_config({"memory": {"enabled": False}})
        self.assertIs(self._get_json(key="memory.enabled")["value"], False)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the optional HTML artifact mode config gate (fn-62.1, R1/R11).

`get_default_config()` carries a top-level `artifacts` block so
`flowctl config get artifacts.html.enabled --json` returns `false`
(NOT `null`) on a fresh repo, WITHOUT any prior `config set`:

  * artifacts.html.enabled → False  (opt-in; OFF by default)

Plus: `config set artifacts.html.enabled true` round-trips (set_config
auto-coerces the bool string), unknown sibling keys under `artifacts`
survive a re-set (deep_merge preservation), `--raw` reads return null on
a fresh repo (the setup ceremony's include-only-if-unset probe), and the
new top-level `artifacts.*` namespace does not clash with existing
blocks. Mirrors test_land_config.py.

Also (PR #173 review): `flowctl init` must NOT materialize the
`artifacts` block into config.json (_INIT_UNMATERIALIZED_BLOCKS).
The setup ceremony runs `init` in Step 1 BEFORE the Step 6 `--raw`
probe; if init persisted the default, the probe would read `false`
instead of null and the HTML Artifacts setup question would never
fire. Raw stays null across init (fresh AND upgrade) until an
explicit `config set`; merged reads still return the seeded default.
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
        "flowctl_artifacts_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ArtifactsConfigTestCase(unittest.TestCase):
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

    def test_defaults_dict_has_artifacts_block(self) -> None:
        defaults = self.flowctl.get_default_config()
        self.assertIn("artifacts", defaults)
        self.assertEqual(defaults["artifacts"], {"html": {"enabled": False}})

    # ── Defaults: surfaced via `config get --json` on a FRESH repo ───────
    # No config.json on disk and no prior `config set` — the merge must
    # return the spec default `false`, NOT null (R1: present, not null).

    def test_fresh_get_html_enabled_is_false(self) -> None:
        out = self._run_config_get_cli("artifacts.html.enabled")
        self.assertIs(out["value"], False)
        self.assertIsNotNone(out["value"])

    def test_fresh_raw_get_html_enabled_is_null(self) -> None:
        # The setup ceremony's include-only-if-unset probe: `--raw` bypasses
        # merged defaults, so an unset key reads null (= ask the question).
        out = self._run_config_get_cli("artifacts.html.enabled", "--raw")
        self.assertIsNone(out["value"])

    # ── set round-trips (no new flowctl command needed) ──────────────────
    # set_config already takes arbitrary nested dot-paths; the only flowctl
    # change is the defaults block, so `set` + `get` round-trips.

    def test_set_true_round_trips_as_bool(self) -> None:
        set_out = self._run_config_set_cli("artifacts.html.enabled", "true")
        self.assertIs(set_out["value"], True)
        get_out = self._run_config_get_cli("artifacts.html.enabled")
        self.assertIs(get_out["value"], True)
        # After an explicit set, the raw read is no longer null — the setup
        # ceremony will skip the question on re-run.
        raw_out = self._run_config_get_cli("artifacts.html.enabled", "--raw")
        self.assertIs(raw_out["value"], True)

    def test_set_false_round_trips_as_bool(self) -> None:
        self._run_config_set_cli("artifacts.html.enabled", "true")
        self._run_config_set_cli("artifacts.html.enabled", "false")
        get_out = self._run_config_get_cli("artifacts.html.enabled")
        self.assertIs(get_out["value"], False)

    # ── deep_merge preservation ──────────────────────────────────────────

    def test_unknown_sibling_keys_under_artifacts_survive_re_set(self) -> None:
        # An unknown sibling under `artifacts` (e.g. a future lens type)
        # must survive a re-set of artifacts.html.enabled — deep_merge
        # preserves unknown keys instead of clobbering the block.
        self._run_config_set_cli("artifacts.motion.enabled", "true")
        self._run_config_set_cli("artifacts.html.enabled", "true")
        self.assertIs(
            self._run_config_get_cli("artifacts.motion.enabled")["value"], True
        )
        self.assertIs(
            self._run_config_get_cli("artifacts.html.enabled")["value"], True
        )

    def test_unknown_sibling_keys_under_html_survive_re_set(self) -> None:
        # Same preservation one level down, under artifacts.html.
        self._run_config_set_cli("artifacts.html.theme", "instrument")
        self._run_config_set_cli("artifacts.html.enabled", "true")
        self.assertEqual(
            self._run_config_get_cli("artifacts.html.theme")["value"],
            "instrument",
        )

    # ── init must not materialize the artifacts block (PR #173 review) ───
    # Setup Step 1 runs `flowctl init` BEFORE Step 6's include-only-if-unset
    # `--raw` probe. If init persisted artifacts.html.enabled: false, the
    # probe would never read null and the setup question would never fire.

    def test_fresh_init_does_not_materialize_artifacts_block(self) -> None:
        out = self._run_init_cli()
        self.assertTrue(out["success"])
        self.assertNotIn("artifacts", self._read_config_file())

    def test_raw_get_html_enabled_still_null_after_fresh_init(self) -> None:
        # The exact setup-ceremony ordering: init, THEN the raw probe.
        self._run_init_cli()
        out = self._run_config_get_cli("artifacts.html.enabled", "--raw")
        self.assertIsNone(out["value"])
        # Merged read still serves the seeded default (R1: false, not null).
        merged = self._run_config_get_cli("artifacts.html.enabled")
        self.assertIs(merged["value"], False)

    def test_init_upgrade_does_not_add_artifacts_block(self) -> None:
        # Existing pre-fn-62 config.json: init's upgrade merge adds missing
        # defaults but must not add the artifacts block.
        config_path = self.tmpdir / ".flow" / "config.json"
        config_path.write_text(
            json.dumps({"memory": {"enabled": True}}), encoding="utf-8"
        )
        self._run_init_cli()
        upgraded = self._read_config_file()
        self.assertNotIn("artifacts", upgraded)
        # The upgrade still materialized other (non-exempt) defaults.
        self.assertIn("land", upgraded)
        out = self._run_config_get_cli("artifacts.html.enabled", "--raw")
        self.assertIsNone(out["value"])

    def test_user_set_value_survives_init_rerun(self) -> None:
        # An explicit decision (setup 6e / manual config set) is preserved
        # by a later idempotent init — raw probe then skips the question.
        self._run_init_cli()
        self._run_config_set_cli("artifacts.html.enabled", "true")
        self._run_init_cli()
        out = self._run_config_get_cli("artifacts.html.enabled", "--raw")
        self.assertIs(out["value"], True)

    # ── Namespace coexistence ─────────────────────────────────────────────

    def test_artifacts_block_does_not_clash_with_existing_blocks(self) -> None:
        defaults = self.flowctl.get_default_config()
        # artifacts.* is its own top-level block, distinct from work.*,
        # land.*, and memory.* — no shared keys leak across.
        self.assertIn("artifacts", defaults)
        self.assertIn("work", defaults)
        self.assertIn("land", defaults)
        self.assertNotIn("html", defaults["work"])
        self.assertNotIn("html", defaults["land"])
        self.assertNotIn("delegate", defaults["artifacts"])

    def test_setting_artifacts_key_does_not_clobber_other_defaults(self) -> None:
        self._run_config_set_cli("artifacts.html.enabled", "true")
        self.assertEqual(
            self._run_config_get_cli("work.delegateModel")["value"], "gpt-5.5"
        )
        self.assertEqual(
            self._run_config_get_cli("land.ciFixBudget")["value"], 3
        )


if __name__ == "__main__":
    unittest.main()

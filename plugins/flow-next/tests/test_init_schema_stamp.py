"""$schema stamping on cmd_init write paths (fn-138.3, R3).

Contract under test:
- fresh init writes `.flow/config.json` with `$schema` as the FIRST key,
  pointing at the ONE flowctl URL constant (FLOW_CONFIG_SCHEMA_URL), and the
  stamped file validates against the committed schema artifact;
- re-init adds a missing `$schema` (refresh path) but preserves an existing
  value (user-pinned URL wins via the deep_merge override side);
- double init is idempotent: no rewrite, no duplicate keys, stable ordering;
- `config set` (raw read-modify-write) never strips the stamp.

Sibling of test_flow_config_schema_drift.py; reuses its stdlib validator.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "schema" / "flow-config.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flowctl  # noqa: E402
from test_flow_config_schema_drift import validate  # noqa: E402


def _run_init(tmp: Path) -> dict:
    ns = mock.Mock()
    ns.json = True
    captured: dict = {}
    with mock.patch.object(
        flowctl, "json_output", side_effect=lambda d: captured.update(d)
    ):
        with mock.patch.object(
            flowctl, "get_flow_dir", return_value=tmp / ".flow"
        ):
            flowctl.cmd_init(ns)
    return captured


def _pairs_no_duplicates(pairs: list) -> dict:
    """object_pairs_hook that fails the test on duplicate JSON keys."""
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise AssertionError(f"duplicate JSON keys: {keys}")
    return dict(pairs)


class TestSchemaUrlConstant(unittest.TestCase):
    def test_constant_matches_artifact_id(self) -> None:
        # Producer (generator's $id) and consumer (init stamp) must agree;
        # flowctl carries the URL in exactly one constant.
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(flowctl.FLOW_CONFIG_SCHEMA_URL, artifact["$id"])


class TestFreshInitStamp(unittest.TestCase):
    def test_fresh_init_stamps_schema_first_key_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = _run_init(tmp)
            self.assertTrue(result.get("success"))
            cfg_path = tmp / ".flow" / "config.json"
            raw = json.loads(
                cfg_path.read_text(encoding="utf-8"),
                object_pairs_hook=_pairs_no_duplicates,
            )
            self.assertEqual(
                list(raw)[0], "$schema", "$schema must be the first key"
            )
            self.assertEqual(raw["$schema"], flowctl.FLOW_CONFIG_SCHEMA_URL)
            schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
            self.assertEqual(validate(raw, schema), [])


class TestReInitPaths(unittest.TestCase):
    def test_double_init_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _run_init(tmp)
            cfg_path = tmp / ".flow" / "config.json"
            before = cfg_path.read_bytes()
            second = _run_init(tmp)
            self.assertNotIn(
                "upgraded config.json (added missing keys)",
                second.get("actions", []),
                "second init must not rewrite an already-stamped config",
            )
            self.assertEqual(cfg_path.read_bytes(), before)
            json.loads(
                cfg_path.read_text(encoding="utf-8"),
                object_pairs_hook=_pairs_no_duplicates,
            )

    def test_reinit_adds_missing_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            flow_dir = tmp / ".flow"
            flow_dir.mkdir(parents=True)
            cfg_path = flow_dir / "config.json"
            cfg_path.write_text(
                json.dumps({"memory": {"enabled": False}}), encoding="utf-8"
            )
            result = _run_init(tmp)
            self.assertIn(
                "upgraded config.json (added missing keys)",
                result.get("actions", []),
            )
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(raw["$schema"], flowctl.FLOW_CONFIG_SCHEMA_URL)
            # Existing explicit settings survive the refresh untouched.
            self.assertIs(raw["memory"]["enabled"], False)

    def test_reinit_preserves_existing_schema_value(self) -> None:
        # A user-pinned (e.g. versioned) URL is on the deep_merge override
        # side, so re-init must never clobber it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _run_init(tmp)
            cfg_path = tmp / ".flow" / "config.json"
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            raw["$schema"] = "https://example.com/pinned.schema.json"
            cfg_path.write_text(json.dumps(raw), encoding="utf-8")
            _run_init(tmp)
            after = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(
                after["$schema"], "https://example.com/pinned.schema.json"
            )


class TestConfigSetPreservesStamp(unittest.TestCase):
    def test_config_set_round_trips_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _run_init(tmp)
            with mock.patch.object(
                flowctl, "get_flow_dir", return_value=tmp / ".flow"
            ):
                flowctl.set_config("memory.enabled", "false")
            raw = json.loads(
                (tmp / ".flow" / "config.json").read_text(encoding="utf-8"),
                object_pairs_hook=_pairs_no_duplicates,
            )
            self.assertEqual(raw["$schema"], flowctl.FLOW_CONFIG_SCHEMA_URL)
            self.assertEqual(
                list(raw)[0], "$schema", "config set must keep key ordering"
            )
            self.assertIs(raw["memory"]["enabled"], False)


if __name__ == "__main__":
    unittest.main()

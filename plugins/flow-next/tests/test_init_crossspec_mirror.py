"""Removal regression tests for `flowctl init`'s legacy
`planSync.crossEpic` → `planSync.crossSpec` mirror (fn-62.6, R14 — 2.0.0).

History: pre-1.1.3 users had `planSync.crossEpic: true` as the only key.
1.1.11 added a pre-merge mirror in `cmd_init` (crossEpic → crossSpec when
canonical absent) so the 1.1.3 canonical-wins read precedence didn't
silently flip upgraders' effective setting. 2.0.0 removed the alias AND
that mirror per the documented 1.x deprecation promise.

Post-removal contract pinned here:
  * `init` never mirrors a leftover `crossEpic` value — the canonical
    `crossSpec` gets the default (`false`) via the standard default-merge.
  * The leftover legacy key is inert but preserved (init never deletes
    user keys; the merge keeps unknown keys).
  * No `crossEpic`-mentioning action message is ever emitted.
"""

import json
import sys
import unittest
from pathlib import Path
import tempfile
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


def _run_init(repo_root: Path):
    """Invoke `flowctl init --json` against ``repo_root``."""
    args = mock.MagicMock()
    args.json = True
    args.path = str(repo_root)
    # cmd_init reads global state; we need to ensure cwd-style resolution
    # finds repo_root. The simplest path is to chdir during the call.
    cwd = Path.cwd()
    captured: dict = {}

    def capture_output(payload):
        captured.update(payload)

    try:
        import os
        os.chdir(repo_root)
        with mock.patch.object(flowctl, "json_output",
                               side_effect=capture_output):
            flowctl.cmd_init(args)
    finally:
        import os
        os.chdir(cwd)
    return captured


def _read_config(repo_root: Path) -> dict:
    return json.loads((repo_root / ".flow" / "config.json").read_text())


def _mirror_actions(result: dict) -> list:
    return [
        a for a in result.get("actions", [])
        if "crossEpic" in a
    ]


class InitDoesNotMirrorLegacyCrossEpic(unittest.TestCase):
    """Legacy crossEpic + no crossSpec → NO mirror; canonical default lands."""

    def test_true_legacy_is_inert(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            # Seed pre-1.1.3 layout: crossEpic explicitly true, no crossSpec.
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {"enabled": True, "crossEpic": True},
                "memory": {"enabled": True},
                "review": {},
            }))
            result = _run_init(repo_root)

            cfg = _read_config(repo_root)
            # 2.0.0: NO mirror — canonical gets the default, not the legacy
            # value (pre-2.0 this would have been mirrored to True).
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            # Leftover legacy key is preserved (init never deletes user
            # keys) but inert — nothing reads it anymore.
            self.assertEqual(cfg["planSync"]["crossEpic"], True)
            self.assertEqual(
                _mirror_actions(result), [],
                "2.0.0 removed the crossEpic mirror — no mirror action",
            )

    def test_false_legacy_is_inert(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {"crossEpic": False},
            }))
            result = _run_init(repo_root)
            cfg = _read_config(repo_root)
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            self.assertEqual(cfg["planSync"]["crossEpic"], False)
            self.assertEqual(_mirror_actions(result), [])


class InitCanonicalUntouchedByLegacy(unittest.TestCase):
    """An explicit canonical crossSpec is never overwritten by a leftover
    legacy value."""

    def test_canonical_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {
                    "crossEpic": True,    # leftover legacy says enable
                    "crossSpec": False,   # canonical says disable
                },
            }))
            result = _run_init(repo_root)
            cfg = _read_config(repo_root)
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            self.assertEqual(cfg["planSync"]["crossEpic"], True)
            self.assertEqual(_mirror_actions(result), [])


class InitFreshDefaults(unittest.TestCase):
    """Fresh-install style configs (neither key set) get default-merge
    behavior with crossSpec: false and no legacy key ever written."""

    def test_neither_set(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "config.json").write_text(json.dumps({
                "memory": {"enabled": True},
            }))
            result = _run_init(repo_root)
            cfg = _read_config(repo_root)
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            self.assertNotIn("crossEpic", cfg["planSync"])
            self.assertEqual(_mirror_actions(result), [])


class InitIdempotent(unittest.TestCase):
    """Re-running init on a config carrying a leftover legacy key must be a
    no-op for the planSync section (beyond the first default-merge)."""

    def test_idempotent_with_leftover_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {"crossEpic": True},
            }))
            _run_init(repo_root)
            cfg_after_first = _read_config(repo_root)
            self.assertEqual(cfg_after_first["planSync"]["crossSpec"], False)
            result = _run_init(repo_root)
            self.assertEqual(_mirror_actions(result), [])
            cfg_after_second = _read_config(repo_root)
            self.assertEqual(
                cfg_after_second["planSync"], cfg_after_first["planSync"],
                "planSync section must be byte-identical across reruns",
            )


if __name__ == "__main__":
    unittest.main()

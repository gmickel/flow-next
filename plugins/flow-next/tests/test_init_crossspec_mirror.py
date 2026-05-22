"""Tests for `flowctl init`'s legacy `planSync.crossEpic` → canonical
`planSync.crossSpec` mirror (1.1.11).

Pre-1.1.3 users had `planSync.crossEpic: true` (the only key) in their
on-disk config. The 1.1.3 default-merge introduced `planSync.crossSpec:
false` as the new canonical default, and the 1.1.3 read precedence is
"canonical wins on presence". Without a mirror, every upgrading user
who'd opted into cross-spec sync lost the setting silently on the next
`flowctl init` (called by `/flow-next:setup` and bundled worker paths).

1.1.11 adds a pre-merge mirror: if `crossEpic` is in the file and
`crossSpec` is absent, copy `crossEpic` → `crossSpec` so the canonical
key reflects the user's intended setting. Legacy key is preserved per
the 1.1.3 deprecation cadence (removed in 2.0).
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


class InitMirrorsLegacyCrossEpic(unittest.TestCase):
    """legacy crossEpic + no crossSpec → mirror to canonical."""

    def test_mirrors_true_legacy(self):
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
            # Mirror happened: crossSpec now reflects user's intended value.
            self.assertEqual(cfg["planSync"]["crossSpec"], True)
            # Legacy key preserved per 1.1.3 deprecation cadence.
            self.assertEqual(cfg["planSync"]["crossEpic"], True)
            # Action log mentions the mirror.
            actions = result.get("actions", [])
            mirror_msgs = [
                a for a in actions
                if "crossEpic" in a and "crossSpec" in a
            ]
            self.assertEqual(len(mirror_msgs), 1,
                             f"expected mirror action; got actions={actions}")

    def test_mirrors_false_legacy(self):
        # If user explicitly turned crossEpic off (rare but valid),
        # mirroring preserves that too.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {"crossEpic": False},
            }))
            _run_init(repo_root)
            cfg = _read_config(repo_root)
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            self.assertEqual(cfg["planSync"]["crossEpic"], False)


class InitDoesNotMirrorWhenCanonicalPresent(unittest.TestCase):
    """If user already set canonical crossSpec, the legacy value is ignored
    (canonical-wins-on-presence semantics)."""

    def test_canonical_wins(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {
                    "crossEpic": True,    # legacy says enable
                    "crossSpec": False,   # canonical says disable
                },
            }))
            result = _run_init(repo_root)
            cfg = _read_config(repo_root)
            # User's explicit canonical setting wins; no mirror runs.
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            self.assertEqual(cfg["planSync"]["crossEpic"], True)
            actions = result.get("actions", [])
            mirror_msgs = [
                a for a in actions
                if "crossEpic" in a and "crossSpec" in a
            ]
            self.assertEqual(mirror_msgs, [],
                             "must not mirror when canonical is present")


class InitDoesNotMirrorWhenNeitherSet(unittest.TestCase):
    """Fresh-install style configs (neither key set) just get default-merge
    behavior with crossSpec: false."""

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
            # Default canonical (false) lands; no legacy key written.
            self.assertEqual(cfg["planSync"]["crossSpec"], False)
            self.assertNotIn("crossEpic", cfg["planSync"])
            actions = result.get("actions", [])
            mirror_msgs = [
                a for a in actions
                if "crossEpic" in a and "crossSpec" in a
            ]
            self.assertEqual(mirror_msgs, [],
                             "must not mirror when legacy is absent")


class InitIdempotent(unittest.TestCase):
    """Re-running init on a config that already has both keys (post-mirror
    state) must be a no-op for the planSync section."""

    def test_idempotent_after_mirror(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            flow_dir = repo_root / ".flow"
            flow_dir.mkdir()
            # First run: legacy → mirror happens.
            (flow_dir / "config.json").write_text(json.dumps({
                "planSync": {"crossEpic": True},
            }))
            _run_init(repo_root)
            cfg_after_first = _read_config(repo_root)
            self.assertEqual(cfg_after_first["planSync"]["crossSpec"], True)
            # Second run: no mirror action expected.
            result = _run_init(repo_root)
            actions = result.get("actions", [])
            mirror_msgs = [
                a for a in actions
                if "crossEpic" in a and "crossSpec" in a
            ]
            self.assertEqual(mirror_msgs, [],
                             "second run must not re-mirror")
            cfg_after_second = _read_config(repo_root)
            self.assertEqual(
                cfg_after_second["planSync"], cfg_after_first["planSync"],
                "planSync section must be byte-identical across reruns",
            )


if __name__ == "__main__":
    unittest.main()

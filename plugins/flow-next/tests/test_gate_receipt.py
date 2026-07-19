"""Hermetic green-receipt and honor-probe tests for `flowctl gate` (fn-102).

Every assertion drives the production CLI via subprocess against a temporary
real git repository. No network, no package installation, no shared state.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


FLOWCTL_PY = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"
COMMAND = "python3 -m unittest discover -s plugins/flow-next/tests -p 'test_gate_*.py' -q"
GATE_ID = "full-gate"


class GateReceiptTestCase(unittest.TestCase):
    """Temporary git repo with helpers that invoke the public CLI wire."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self._git("init", "-q")
        self._git("config", "user.email", "gate@example.com")
        self._git("config", "user.name", "Gate Test")
        self._commit("src/app.py", "print('seed')\n", "seed")

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @staticmethod
    def _pinned_env() -> dict:
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00Z"
        env["GIT_COMMITTER_DATE"] = "2026-01-01T00:00:00Z"
        return env

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            check=True,
            env=self._pinned_env(),
        )
        return result.stdout.strip()

    def _commit(self, rel: str, content: str, message: str) -> str:
        path = self.tmpdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", message)
        return self._git("rev-parse", "HEAD")

    def _flowctl(
        self, *args: str, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "gate"] + list(args),
            cwd=cwd or self.tmpdir,
            capture_output=True,
            text=True,
        )

    def _receipt(self, gate_id: str = GATE_ID, command: str = COMMAND) -> None:
        result = self._flowctl("receipt", "--gate", gate_id, "--command", command)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def _check(self, gate_id: str = GATE_ID, command: str = COMMAND) -> subprocess.CompletedProcess:
        return self._flowctl("check", "--gate", gate_id, "--command", command)

    def _receipt_path(self, gate_id: str = GATE_ID) -> Path:
        return self.tmpdir / ".flow" / "tmp" / "green-receipts" / f"{self._git('rev-parse', 'HEAD')[:8]}-{gate_id}.json"

    def _rewrite_receipt(self, **updates: object) -> None:
        path = self._receipt_path()
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt.update(updates)
        path.write_text(json.dumps(receipt), encoding="utf-8")

    def test_receipt_round_trip_body_and_path(self) -> None:
        self._receipt()
        path = self._receipt_path()
        self.assertTrue(path.is_file())
        receipt = json.loads(path.read_text(encoding="utf-8"))
        head = self._git("rev-parse", "HEAD")
        self.assertEqual(
            set(receipt),
            {"schema", "head_sha", "gate_id", "command_sha256", "timestamp"},
        )
        self.assertEqual(receipt["schema"], 1)
        self.assertEqual(receipt["head_sha"], head)
        self.assertEqual(receipt["gate_id"], GATE_ID)
        self.assertEqual(
            receipt["command_sha256"],
            hashlib.sha256(COMMAND.encode("utf-8")).hexdigest(),
        )

    def test_check_honors_fresh_matching_clean_receipt(self) -> None:
        self._receipt()
        result = self._check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("HONORED:", result.stdout)

    def test_check_rejects_dirty_tracked_code(self) -> None:
        self._receipt()
        (self.tmpdir / "src" / "app.py").write_text("print('dirty')\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_dirty_flow_bin(self) -> None:
        self._receipt()
        path = self.tmpdir / ".flow" / "bin" / "flowctl.py"
        path.parent.mkdir(parents=True)
        path.write_text("dirty\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_dirty_flow_config(self) -> None:
        self._receipt()
        path = self.tmpdir / ".flow" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 1)

    def test_check_ignores_flow_state_outside_bin_and_config(self) -> None:
        self._receipt()
        path = self.tmpdir / ".flow" / "tasks" / "x.md"
        path.parent.mkdir(parents=True)
        path.write_text("state\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 0)

    def test_check_rejects_moved_head(self) -> None:
        self._receipt()
        self._commit("docs/next.md", "next\n", "next")
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_different_command(self) -> None:
        self._receipt()
        self.assertEqual(self._check(command="different command").returncode, 1)

    def test_check_rejects_stale_receipt(self) -> None:
        self._receipt()
        self._rewrite_receipt(
            timestamp=(datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        )
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_future_receipt(self) -> None:
        self._receipt()
        self._rewrite_receipt(
            timestamp=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        )
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_bad_schema(self) -> None:
        self._receipt()
        self._rewrite_receipt(schema=2)
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_malformed_receipt_without_traceback(self) -> None:
        self._receipt()
        self._receipt_path().write_bytes(b"not json")
        result = self._check()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_check_rejects_missing_receipts_directory(self) -> None:
        self._receipt()
        shutil.rmtree(self.tmpdir / ".flow" / "tmp" / "green-receipts")
        self.assertEqual(self._check().returncode, 1)

    def test_non_git_repo_check_is_run_and_receipt_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            non_repo = Path(raw)
            check = self._flowctl("check", "--gate", GATE_ID, "--command", COMMAND, cwd=non_repo)
            receipt = self._flowctl("receipt", "--gate", GATE_ID, "--command", COMMAND, cwd=non_repo)
        self.assertEqual(check.returncode, 1)
        self.assertEqual(receipt.returncode, 2)

    def test_gate_id_validation_at_both_boundaries(self) -> None:
        invalid_ids = ["../x", "a/b", "..\\x", ".", "..", "", "a" * 65, "-x", ".x"]
        for gate_id in invalid_ids:
            for command in ("receipt", "check"):
                with self.subTest(gate_id=gate_id, command=command):
                    result = self._flowctl(
                        command, "--gate", gate_id, "--command", COMMAND
                    )
                    self.assertEqual(result.returncode, 2, result.stderr or result.stdout)

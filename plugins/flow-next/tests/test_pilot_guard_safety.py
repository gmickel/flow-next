"""Exercise pilot dirty-tree admission against disposable Git/Flow fixtures.

The snapshot tests call the deterministic ``pilot_snapshot`` implementation
with only its GitHub PR listing stubbed. Shell tests run the exact documented
guard and use a continuation marker to show whether later dispatch code could
be reached; they do not start a host skill or reviewer. The full driver writes
``.flow/tmp/pilot-snapshot.json`` before this guard. These tests feed the
snapshot directly, so their no-mutation assertion covers the snapshot helper,
guard, project files, and strike ledger rather than that diagnostic artifact.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
PLUGIN = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))

import test_pilot_strikes as pilot_support  # noqa: E402
from flowctl_test_support import FLOWCTL_CMD  # noqa: E402

flowctl = pilot_support.flowctl

AUTO_MD = PLUGIN / "skills" / "flow-next-flow" / "auto.md"
DOCS_DIR = Path("docs/user-work")
DOC_COUNT = 5
DISPATCH_MARKER = "REVIEWER_DISPATCH_MARKER"

_POSIX_BASH = unittest.skipIf(
    os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"),
    "pilot shell guard needs POSIX bash and jq",
)


def _pilot_guard() -> str:
    text = AUTO_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)
    return next(block for block in blocks if "# fence:pilot-guards" in block)


class PilotGuardSafety(unittest.TestCase):
    """A pilot stop preserves user files and does not advance into dispatch."""

    def setUp(self) -> None:
        pilot_support.PilotStrikesTestCase.setUp(self)
        self.docs = self.repo / DOCS_DIR
        self.docs.mkdir(parents=True)
        for index in range(1, DOC_COUNT + 1):
            (self.docs / f"fixture-{index}.md").write_text(
                f"baseline {index}\n", encoding="utf-8"
            )
        pilot_support._git(self.repo, "add", "docs/user-work")
        pilot_support._git(self.repo, "commit", "-qm", "fixture docs baseline")
        initialized = self._run("init", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr or initialized.stdout)
        self._write_ledger({"fn-999-ledger-sentinel": pilot_support.ENTRY_B})

    def tearDown(self) -> None:
        pilot_support.PilotStrikesTestCase.tearDown(self)

    def _write_ledger(self, data: dict) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _create_spec(self, *, ready: bool) -> str:
        initialized = self._run("init", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr or initialized.stdout)
        created = self._run("spec", "create", "--title", "Pilot guard fixture", "--json")
        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        spec_id = json.loads(created.stdout)["id"]
        if ready:
            result = self._run("spec", "ready", spec_id, "--json")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        spec_path = next((self.repo / ".flow").rglob(f"{spec_id}.json"))
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        pilot_support._git(self.repo, "branch", spec["branch_name"])
        return spec_id

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*FLOWCTL_CMD, *args], cwd=self.repo, capture_output=True, text=True, check=False
        )

    def _snapshot(self, spec_id: str | None = None) -> dict:
        real_run = subprocess.run

        def run(command, *args, **kwargs):
            if command and command[0] == "gh":
                return SimpleNamespace(returncode=0, stdout="[]", stderr="")
            return real_run(command, *args, **kwargs)

        with (
            mock.patch.object(flowctl, "get_repo_root", return_value=self.repo),
            mock.patch.object(flowctl, "get_flow_dir", return_value=self.repo / ".flow"),
            mock.patch.object(flowctl.subprocess, "run", side_effect=run),
            mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}),
            mock.patch.object(flowctl, "_pilot_strikes_ledger_path", return_value=self.ledger),
        ):
            return flowctl.pilot_snapshot(spec_id)

    def _project_bytes(self) -> dict[str, bytes]:
        roots = [self.repo / ".flow", self.repo / DOCS_DIR]
        files = []
        for root in roots:
            if root.exists():
                files.extend(path for path in root.rglob("*") if path.is_file())
        return {path.relative_to(self.repo).as_posix(): path.read_bytes() for path in sorted(files)}

    def _change_project_docs(self) -> None:
        for index in range(1, DOC_COUNT + 1):
            (self.docs / f"fixture-{index}.md").write_text(
                f"changed {index}\n", encoding="utf-8"
            )
        (self.docs / "untracked.md").write_text("new fixture\n", encoding="utf-8")

    def _assert_dispatch_guard_stops(self, snapshot: dict) -> None:
        env = {
            **os.environ,
            "PILOT_SNAPSHOT": json.dumps(snapshot, separators=(",", ":")),
            "GOAL_SPEC": "-",
            "GOAL_REASON_PREFIX": "",
        }
        script = f"{_pilot_guard()}\nprintf '%s\\n' {DISPATCH_MARKER}\n"
        result = subprocess.run(
            ["bash", "-c", script], cwd=self.repo, env=env,
            capture_output=True, text=True, check=False,
        )
        expected = (
            'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- '
            'reason="dirty working tree at tick start"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], expected)
        self.assertNotIn(DISPATCH_MARKER, result.stdout)

    def test_clean_ready_spec_is_selectable(self) -> None:
        spec_id = self._create_spec(ready=True)
        before = self._project_bytes()
        ledger_before = self.ledger.read_bytes()

        result = self._snapshot(spec_id)

        self.assertEqual(result["guards"]["dirty"], [])
        self.assertTrue(result["selected"]["eligible"])
        self.assertEqual(result["selected"]["id"], spec_id)
        self.assertEqual(self._project_bytes(), before)
        self.assertEqual(self.ledger.read_bytes(), ledger_before)

    @_POSIX_BASH
    def test_dirty_ready_tree_is_listed_and_stops_before_dispatch(self) -> None:
        spec_id = self._create_spec(ready=True)
        self._change_project_docs()
        before = self._project_bytes()
        ledger_before = self.ledger.read_bytes()

        result = self._snapshot(spec_id)
        dirty = result["guards"]["dirty"]

        self.assertTrue(result["selected"]["eligible"])
        self.assertEqual(len(dirty), DOC_COUNT + 1)
        dirty_paths = {row[3:] for row in dirty}
        self.assertEqual(
            dirty_paths,
            {f"docs/user-work/fixture-{index}.md" for index in range(1, DOC_COUNT + 1)}
            | {"docs/user-work/untracked.md"},
        )
        self._assert_dispatch_guard_stops(result)
        self.assertEqual(self._project_bytes(), before)
        self.assertEqual(self.ledger.read_bytes(), ledger_before)

    def test_clean_unready_spec_is_independently_ineligible(self) -> None:
        spec_id = self._create_spec(ready=False)
        before = self._project_bytes()
        ledger_before = self.ledger.read_bytes()

        scoped = self._snapshot(spec_id)
        unscoped = self._snapshot()

        candidate = scoped["selected"]
        self.assertFalse(candidate["eligible"])
        self.assertFalse(candidate["spec"].get("ready", False))
        self.assertEqual(candidate["route"]["decision"]["rule"], "spec not ready")
        self.assertEqual(scoped["guards"]["dirty"], [])
        self.assertIsNone(unscoped["selected"])
        self.assertEqual(unscoped["candidates"], [])
        self.assertEqual(self._project_bytes(), before)
        self.assertEqual(self.ledger.read_bytes(), ledger_before)

    @_POSIX_BASH
    def test_dirty_unready_spec_stops_for_dirty_tree_before_selection(self) -> None:
        spec_id = self._create_spec(ready=False)
        self._change_project_docs()
        before = self._project_bytes()
        ledger_before = self.ledger.read_bytes()

        result = self._snapshot(spec_id)

        self.assertFalse(result["selected"]["eligible"])
        self.assertEqual(len(result["guards"]["dirty"]), DOC_COUNT + 1)
        self._assert_dispatch_guard_stops(result)
        self.assertEqual(self._project_bytes(), before)
        self.assertEqual(self.ledger.read_bytes(), ledger_before)

    def test_flow_only_changes_do_not_enter_the_dirty_guard(self) -> None:
        spec_id = self._create_spec(ready=True)
        spec_path = next((self.repo / ".flow").rglob(f"{spec_id}.json"))
        relative_spec_path = spec_path.relative_to(self.repo).as_posix()
        pilot_support._git(self.repo, "add", "-f", ".flow")
        pilot_support._git(self.repo, "commit", "-qm", "fixture flow state baseline")
        spec_path.write_text(
            spec_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )
        status = pilot_support._git(
            self.repo, "status", "--porcelain", "--untracked-files=all"
        ).stdout.splitlines()
        self.assertIn(f" M {relative_spec_path}", status)

        result = self._snapshot(spec_id)

        self.assertEqual(result["guards"]["dirty"], [])
        self.assertTrue(result["selected"]["eligible"])


if __name__ == "__main__":
    unittest.main()

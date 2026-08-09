"""fn-181.3 (R3/R4/R5): behind-upstream staleness advisory on ready/anchor.

Behavioral, production-wire-form tests against a REAL git repo with a real
upstream (a local bare remote — never the network, never a fetch):

  * R3 — `ready`, `ready --all`, and `anchor` emit ONE advisory line (plain)
    and a `stale_vs_upstream` count (JSON) when HEAD is behind its upstream.
  * R3 — not behind / no upstream / detached HEAD / not a git repo: the
    advisory is silently absent, `stale_vs_upstream` is omitted, and the
    rest of the output is byte-identical to the same command run in a repo
    that is up to date.
  * R4 — `list`, `status`, and `next` perform NO upstream check. Asserted by
    spawn counting through a `git` shim on PATH, not by inspection.
  * R5 — at most ONE upstream spawn per invocation regardless of how many
    specs/tasks the command walks.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_upstream_advisory -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

SPEC_ID = "fn-1-sample-spec"
TASK_ID = "fn-1-sample-spec.1"

# The upstream probe's wire form. Spawn counting keys off this fragment, so a
# rewrite of the probe command must update it here — deliberately.
UPSTREAM_PROBE = "status --porcelain=v2 --branch"

REAL_GIT = shutil.which("git")


@unittest.skipIf(os.name == "nt", "POSIX git-shim spawn counting")
@unittest.skipIf(REAL_GIT is None, "git not available")
class UpstreamAdvisoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.upstream = self.root / "upstream.git"
        self.repo = self.root / "work"
        self._git_log = self.root / "git-spawns.log"
        self._shim_dir = self.root / "shim"
        self._install_git_shim()

        subprocess.run(
            ["git", "init", "-q", "--bare", str(self.upstream)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "init", "-q", str(self.repo)], check=True, capture_output=True
        )
        for key, value in (("user.email", "t@t"), ("user.name", "t")):
            self._git("config", key, value)

        self._flowctl("init")
        self._flowctl("spec", "create", "--title", "Sample spec", "--json")
        self._flowctl(
            "task", "create", "--spec", SPEC_ID,
            "--title", "T one", "--acceptance", "acc", "--json",
        )
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        self._git("remote", "add", "origin", str(self.upstream))
        self._git("push", "-q", "origin", "HEAD:refs/heads/main")
        self._git("branch", "--set-upstream-to=origin/main", "-q")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    # --- fixture plumbing -------------------------------------------------

    def _install_git_shim(self) -> None:
        """A `git` on PATH that logs its argv, then delegates to the real git.

        Lets the spawn-count assertions (R4/R5) run against the production
        CLI in a subprocess instead of a stubbed in-process module.
        """
        self._shim_dir.mkdir()
        shim = self._shim_dir / "git"
        shim.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$*" >> "$FLOW_TEST_GIT_LOG"\n'
            f'exec {REAL_GIT} "$@"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)

    def _env(self, *, shim: bool = False) -> dict:
        env = dict(os.environ)
        env["FLOW_TEST_GIT_LOG"] = str(self._git_log)
        if shim:
            env["PATH"] = f"{self._shim_dir}{os.pathsep}{env.get('PATH', '')}"
        return env

    def _git(self, *args: str) -> None:
        result = subprocess.run(
            ["git", *args], cwd=str(self.repo), capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def _flowctl(
        self, *args: str, shim: bool = False, cwd: "Path | None" = None
    ) -> "subprocess.CompletedProcess[str]":
        result = subprocess.run(
            [sys.executable, str(FLOWCTL_PY)] + list(args),
            cwd=str(cwd or self.repo),
            capture_output=True,
            text=True,
            env=self._env(shim=shim),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def _json(self, *args: str) -> dict:
        return json.loads(self._flowctl(*args).stdout)

    def _upstream_spawns(self) -> int:
        if not self._git_log.exists():
            return 0
        return sum(
            1 for line in self._git_log.read_text(encoding="utf-8").splitlines()
            if UPSTREAM_PROBE in line
        )

    def _fall_behind(self, commits: int = 1) -> None:
        """Push N commits, then rewind HEAD — behind without a fetch."""
        for i in range(commits):
            self._git("commit", "-q", "--allow-empty", "-m", f"ahead-{i}")
        self._git("push", "-q", "origin", "HEAD:main")
        self._git("reset", "-q", "--hard", f"HEAD~{commits}")

    @staticmethod
    def _notes(text: str) -> list:
        return [
            line for line in text.splitlines()
            if line.startswith("note: checkout is")
        ]

    # --- R3: behind ------------------------------------------------------

    def test_ready_plain_emits_one_note_when_behind(self) -> None:
        self._fall_behind(2)
        notes = self._notes(self._flowctl("ready", "--spec", SPEC_ID).stdout)
        self.assertEqual(
            notes,
            ["note: checkout is 2 commits behind origin/main; "
             "spec-level state may be stale"],
        )

    def test_singular_commit_wording(self) -> None:
        self._fall_behind(1)
        (note,) = self._notes(self._flowctl("ready", "--spec", SPEC_ID).stdout)
        self.assertIn("1 commit behind origin/main", note)

    def test_ready_json_carries_stale_vs_upstream(self) -> None:
        self._fall_behind(3)
        self.assertEqual(
            self._json("ready", "--spec", SPEC_ID, "--json")["stale_vs_upstream"], 3
        )

    def test_ready_all_emits_the_advisory_in_both_forms(self) -> None:
        self._fall_behind(1)
        self.assertEqual(len(self._notes(self._flowctl("ready", "--all").stdout)), 1)
        self.assertEqual(
            self._json("ready", "--all", "--json")["stale_vs_upstream"], 1
        )

    def test_anchor_emits_the_advisory_in_both_forms(self) -> None:
        self._fall_behind(1)
        self.assertEqual(len(self._notes(self._flowctl("anchor", TASK_ID).stdout)), 1)
        self.assertEqual(
            self._json("anchor", TASK_ID, "--json")["stale_vs_upstream"], 1
        )

    def test_blocked_by_specs_branch_still_advises(self) -> None:
        """The early-return branch of `ready` is a call site too."""
        # Fall behind FIRST: `_fall_behind` ends in `reset --hard`, which
        # would discard an edit to the tracked spec sidecar.
        self._fall_behind(1)
        spec_json = self.repo / ".flow" / "specs" / f"{SPEC_ID}.json"
        payload = json.loads(spec_json.read_text(encoding="utf-8"))
        payload["depends_on_epics"] = ["fn-99-missing"]
        spec_json.write_text(json.dumps(payload), encoding="utf-8")
        out = self._flowctl("ready", "--spec", SPEC_ID).stdout
        self.assertEqual(len(self._notes(out)), 1)
        self.assertIn("is blocked by", out)
        self.assertEqual(
            self._json("ready", "--spec", SPEC_ID, "--json")["stale_vs_upstream"], 1
        )

    # --- R3: every non-behind outcome is silent --------------------------

    def _assert_silent(self, *args: str) -> str:
        plain = self._flowctl(*args).stdout
        self.assertEqual(self._notes(plain), [])
        payload = self._json(*args, "--json")
        self.assertNotIn("stale_vs_upstream", payload)
        return plain

    def test_up_to_date_is_silent(self) -> None:
        self._assert_silent("ready", "--spec", SPEC_ID)
        self._assert_silent("ready", "--all")
        self._assert_silent("anchor", TASK_ID)

    def test_no_upstream_is_silent_and_output_identical(self) -> None:
        baseline = self._flowctl("ready", "--spec", SPEC_ID).stdout
        self._git("checkout", "-q", "-b", "no-upstream")
        self.assertEqual(self._assert_silent("ready", "--spec", SPEC_ID), baseline)

    def test_detached_head_is_silent_and_output_identical(self) -> None:
        baseline = self._flowctl("ready", "--spec", SPEC_ID).stdout
        self._fall_behind(1)
        self._git("checkout", "-q", "--detach")
        self.assertEqual(self._assert_silent("ready", "--spec", SPEC_ID), baseline)

    def test_git_failure_degrades_to_no_advisory(self) -> None:
        """No git repo at all: the command still succeeds, silently."""
        loose = self.root / "loose"
        shutil.copytree(self.repo / ".flow", loose / ".flow")
        result = self._flowctl("ready", "--spec", SPEC_ID, cwd=loose)
        self.assertEqual(self._notes(result.stdout), [])
        self.assertNotIn(
            "stale_vs_upstream",
            json.loads(
                self._flowctl(
                    "ready", "--spec", SPEC_ID, "--json", cwd=loose
                ).stdout
            ),
        )

    # --- R4 / R5: spawn counting -----------------------------------------

    def test_hot_path_commands_never_probe_upstream(self) -> None:
        """R4: list / status / next must not pay a git spawn for this."""
        self._fall_behind(1)
        for args in (("list",), ("list", "--json"), ("status",), ("next", "--json")):
            with self.subTest(args=args):
                self._git_log.unlink(missing_ok=True)
                out = self._flowctl(*args, shim=True).stdout
                self.assertEqual(self._upstream_spawns(), 0)
                self.assertEqual(self._notes(out), [])
                self.assertNotIn("stale_vs_upstream", out)

    def test_one_upstream_spawn_per_invocation(self) -> None:
        """R5: one check per invocation, however many items are walked."""
        for suffix in ("2", "3", "4"):
            self._flowctl(
                "task", "create", "--spec", SPEC_ID,
                "--title", f"T {suffix}", "--acceptance", "acc", "--json",
            )
        self._flowctl("spec", "create", "--title", "Second spec", "--json")
        self._fall_behind(1)
        for args in (
            ("ready", "--spec", SPEC_ID),
            ("ready", "--all"),
            ("anchor", TASK_ID),
        ):
            with self.subTest(args=args):
                self._git_log.unlink(missing_ok=True)
                self._flowctl(*args, shim=True)
                self.assertEqual(self._upstream_spawns(), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

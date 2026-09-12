"""Execute the shipping skill fences; host consent itself needs session evidence."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parent.parent


def fence(path: str, marker: str) -> str:
    text = (PLUGIN / "skills" / path).read_text(encoding="utf-8")
    return next(block for block in re.findall(r"```bash\n(.*?)```", text, re.S) if marker in block)


@unittest.skipIf(sys.platform == "win32" or not shutil.which("bash") or not shutil.which("jq"),
                 "skill fences require POSIX bash and jq")
class MergeDestinationTest(unittest.TestCase):
    def run_fence(self, code, *, env=None, before="", after="", cwd=None):
        return subprocess.run(["bash", "-c", before + "\n" + code + "\n" + after],
                              env={**os.environ, **(env or {})}, text=True, capture_output=True, cwd=cwd)

    def test_destination_is_exact_and_invalid_input_never_authorizes(self):
        code = fence("flow-next-flow/SKILL.md", 'FLOW_UNTIL=""')
        for args, expected in (("fn-1", ""), ("--auto fn-1", ""),
                               ("fn-1 --until=merge", "merge"),
                               ("--auto fn-1 --until=merge", "merge"),
                               ("fn-1 --until=merger", None), ("fn-1 --until", None),
                               ("fn-1 --until=", None),
                               ("--until=merge --until=no fn-1", None)):
            with self.subTest(args=args):
                result = self.run_fence(code, env={"ARGUMENTS": args},
                                        after='printf "destination=%s" "$FLOW_UNTIL"')
                if expected is None:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("NEEDS_HUMAN", result.stdout)
                    self.assertNotIn("destination=", result.stdout)
                else:
                    self.assertEqual((result.returncode, result.stdout), (0, f"destination={expected}"))
        stale = self.run_fence(code, env={"ARGUMENTS": "--auto fn-1", "LAND_AUTHORIZED": "1",
            "LAND_SCOPE_SPEC": "fn-1", "LAND_SCOPE_PR": "https://x/1"},
            after='printf "%s|%s|%s" "$LAND_AUTHORIZED" "$LAND_SCOPE_SPEC" "$LAND_SCOPE_PR"')
        self.assertEqual(stale.stdout, "0||")

    def test_scoped_discovery_ignores_other_specs_and_recovers_closed_spec(self):
        code = fence("flow-next-land/workflow.md", "CANDIDATE_SPECS=")
        specs = {"specs": [{"id": name, "status": status, "tasks": 1, "done": done}
                            for name, status, done in (("fn-1", "open", 1), ("fn-2", "open", 1),
                                                       ("fn-3", "done", 1), ("fn-4", "open", 0))]}
        for scope, expected in (("", "fn-1\nfn-2"), ("fn-1", "fn-1"),
                                ("fn-3", "fn-3"), ("fn-4", ""), ("missing", "")):
            with self.subTest(scope=scope):
                result = self.run_fence(code, env={"SPECS_FIXTURE": json.dumps(specs),
                                                  "LAND_SCOPE_SPEC": scope, "FLOWCTL": "flowctl"},
                                        before='flowctl() { printf "%s" "$SPECS_FIXTURE"; }',
                                        after='printf "%s" "$CANDIDATE_SPECS"')
                self.assertEqual((result.returncode, result.stdout), (0, expected))

    def test_backlog_land_dispatch_requires_current_scoped_authority(self):
        code = fence("flow-next-flow/auto.md", "assert_allowed_dispatch()")
        for authorized, spec, pr, allowed in (("0", "fn-1", "https://x/1", False),
                                             ("1", "", "https://x/1", False),
                                             ("1", "fn-1", "", False),
                                             ("1", "fn-1", "https://x/1", True)):
            with self.subTest(authorized=authorized, spec=spec, pr=pr):
                result = self.run_fence(code, env={"PILOT_AUTONOMY": "backlog",
                    "LAND_AUTHORIZED": authorized, "LAND_SCOPE_SPEC": spec, "LAND_SCOPE_PR": pr},
                    after='assert_allowed_dispatch /flow-next:land\nprintf dispatched')
                self.assertEqual(result.returncode == 0, allowed, result.stdout)
                self.assertEqual("dispatched" in result.stdout, allowed)

    def test_tail_refuses_failed_checkout_or_pull_even_with_visible_merge(self):
        code = fence("flow-next-land/workflow.md", "TAIL_BASE_OID=")
        for failure in ("checkout", "pull"):
            with self.subTest(failure=failure):
                result = self.run_fence(code, env={"FAIL_GIT": failure, "BASE_REF": "main"},
                    before='''git() {
                      [ "$1" = "$FAIL_GIT" ] && return 1
                      [ "$1" = rev-parse ] && printf base
                      return 0
                    }
                    gh() { printf merge; }''', after='printf "tail=%s" "$TAIL_OK"')
                self.assertIn("tail=0", result.stdout)

    def test_already_closed_spec_does_not_commit_again(self):
        code = fence("flow-next-land/workflow.md", 'chore(flow): close ${spec}')
        result = self.run_fence(code, before='''git() {
          [ "$1" = commit ] && printf unexpected-commit
          return 0
        }''')
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_landing_outcomes_preserve_waits_blockers_and_incomplete_tail(self):
        code = fence("flow-next-flow/references/tail.md", "PILOT_LAND_VERDICT=")
        cases = (("AWAITING_REVIEW", "0", "0", "0", "DEFERRED_TO_LAND", "1"),
                 ("AWAITING_REVIEW", "0", "0", "1", "DEFERRED_TO_LAND", "0"),
                 ("RESOLVING", "1", "0", "0", "ADVANCED", "1"),
                 ("FIXING_CI", "0", "0", "0", "DEFERRED_TO_LAND", "1"),
                 ("MERGED", "0", "1", "0", "ADVANCED", "0"),
                 ("MERGED", "0", "0", "0", "NEEDS_HUMAN", "0"),
                 ("RELEASED", "0", "0", "0", "NEEDS_HUMAN", "0"),
                 ("BLOCKED", "1", "1", "0", "BLOCKED", "0"),
                 ("NEEDS_HUMAN", "1", "1", "0", "NEEDS_HUMAN", "0"),
                 ("NO_WORK", "0", "0", "0", "NEEDS_HUMAN", "0"))
        for verdict, progress, complete, tick, expected, again in cases:
            with self.subTest(verdict=verdict, complete=complete, tick=tick):
                result = self.run_fence(code, env={"LAND_RESULT": verdict, "LAND_PROGRESS": progress,
                    "LAND_COMPLETE": complete, "AUTO_TICK": tick, "LAND_OBSERVED": "1", "LAND_AUTHORIZED": "1"},
                    after='printf "%s|%s" "$PILOT_LAND_VERDICT" "$LAND_CONTINUE"')
                self.assertEqual((result.returncode, result.stdout), (0, f"{expected}|{again}"))
        for missing in ("LAND_OBSERVED", "LAND_AUTHORIZED"):
            result = self.run_fence(code, env={"LAND_RESULT": "MERGED", "LAND_COMPLETE": "1",
                "LAND_OBSERVED": "1", "LAND_AUTHORIZED": "1", missing: "0"},
                after='printf "%s|%s" "$PILOT_LAND_VERDICT" "$LAND_CONTINUE"')
            self.assertEqual(result.stdout, "NEEDS_HUMAN|0")

    def test_pinned_pr_probe_never_falls_back_to_unrelated_pr(self):
        code = fence("flow-next-land/workflow.md", "OPEN_PRS=")
        for state, url, head, failed in (("OPEN", "https://x/1", "feature", "0"),
                                          ("MERGED", "https://x/1", "feature", "0"),
                                          ("CLOSED", "https://x/1", "feature", "0"),
                                          ("OPEN", "https://x/2", "feature", "1"),
                                          ("OPEN", "https://x/1", "other", "1")):
            with self.subTest(state=state, url=url, head=head):
                result = self.run_fence(code, env={"LAND_SCOPE_PR": "https://x/1", "SCOPE_BASE": "main",
                    "FLOWCTL": "flowctl", "PR_FIXTURE": json.dumps({"state": state, "url": url,
                      "headRefName": head, "baseRefName": "main", "number": 1})},
                    before='''flowctl() { printf '{"branch_name":"feature"}'; }
                    gh() { [ "$1 $2" = "pr view" ] || { echo forbidden-list >&2; return 1; }; printf "%s" "$PR_FIXTURE"; }
                    for spec in fn-1; do''',
                    after='done\nprintf "%s|%s|%s" "$PR_PROBE_FAILED" "$OPEN_COUNT" "$MERGED_PR_NUM"')
                self.assertEqual(result.stdout, f"{failed}|{'1' if state == 'OPEN' and failed == '0' else '0'}|{'1' if state == 'MERGED' else ''}")
                self.assertNotIn("forbidden-list", result.stderr)

    def test_merge_observation_checks_exact_target_after_command_failure(self):
        code = fence("flow-next-land/workflow.md", "MERGE_CONFIRMED=0")
        for state, url, oid, confirmed in (("MERGED", "https://x/1", "abc", "1"),
                                           ("OPEN", "https://x/1", "abc", "0"),
                                           ("MERGED", "https://x/2", "abc", "0"),
                                           ("MERGED", "https://x/1", "", "0")):
            with self.subTest(state=state, url=url, oid=oid):
                result = self.run_fence(code, env={"LAND_SCOPE_SPEC": "fn-1", "LAND_SCOPE_PR": "https://x/1",
                    "MERGE_RC": "1", "MV_STALE_BASE": "0", "PR_FIXTURE": json.dumps({"url": url,
                      "state": state, "mergeCommit": {"oid": oid}})},
                    before='gh() { printf "%s" "$PR_FIXTURE"; }',
                    after='printf "%s" "$MERGE_CONFIRMED"')
                self.assertEqual(result.stdout, confirmed)

    def test_source_only_flow_evidence_and_trusted_base_gate(self):
        flowctl = str(PLUGIN / "scripts" / "flowctl")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            base = Path(temp) / "base"
            root.mkdir()
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

            def run(*args, cwd=root):
                return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout.strip()

            run("git", "init", "-b", "main")
            run("git", "config", "user.email", "test@example.invalid")
            run("git", "config", "user.name", "Test")
            run(flowctl, "init", "--json")
            run(flowctl, "config", "set", "land.mergeVerdictCommand", 'test "$(git branch --show-current)" = main')
            run("git", "add", "-A")
            run("git", "commit", "-m", "base config")
            base_sha = run("git", "rev-parse", "HEAD")
            run("git", "checkout", "-b", "feature")
            spec = json.loads(run(flowctl, "spec", "create", "--title", "Scoped landing", "--branch", "feature", "--json"))["id"]
            task = json.loads(run(flowctl, "task", "create", "--spec", spec, "--title", "Build", "--json"))["id"]
            run(flowctl, "start", task, "--json")
            run(flowctl, "done", task, "--summary", "Built", "--evidence", '{"commits":[],"tests":[],"prs":[]}', "--json")
            run(flowctl, "config", "set", "land.mergeVerdictCommand", "exit 77")
            run("git", "add", "-A")
            run("git", "commit", "-m", "PR-only Flow artifacts")
            head = run("git", "rev-parse", "HEAD")
            run("git", "worktree", "add", str(base), "main")
            self.assertFalse((base / ".flow" / "specs" / f"{spec}.json").exists())
            fixture = {"url": "https://github.com/test/repo/pull/1", "number": 1, "state": "OPEN",
                       "headRefName": "feature", "headRefOid": head, "baseRefName": "main", "isCrossRepository": False}
            common = {"FLOWCTL": flowctl, "REPO_ROOT": str(root), "LAND_BASE_ROOT": str(base),
                      "LAND_SCOPE_SPEC": spec, "LAND_SCOPE_PR": fixture["url"], "LAND_AUTHORIZED": "1",
                      "LAND_DRY_RUN": "0", "PR_FIXTURE": json.dumps(fixture), "BASE_SHA": base_sha,
                      "HEAD_OID": head, "BASE_REF": "main", "PR_NUMBER": "1", "spec": spec,
                      "PLANNED_ACTION": "merge", "TICK_LOCK": str(Path(temp) / "claim")}
            before = '''gh() {
              if [ "$1 $2" = "repo view" ]; then printf https://github.com/test/repo;
              else printf "%s" "$PR_FIXTURE"; fi
            }
            git() { if [ "$1" = ls-remote ]; then printf '%s\\trefs/heads/main\\n' "$BASE_SHA";
                    else command git "$@"; fi; }
            '''
            code = "\n".join((fence("flow-next-land/references/flow-handoff.md", "LAND_SCOPE_FAILED="),
                              fence("flow-next-land/workflow.md", "if ! LAND_CFG="),
                              fence("flow-next-land/workflow.md", "CANDIDATE_SPECS="),
                              fence("flow-next-land/workflow.md", "MERGE_VERDICT=skipped")))
            result = self.run_fence(code, env=common, before=before,
                                    after='printf "%s|%s|%s" "$CANDIDATE_SPECS" "$MERGE_VERDICT" "$(pwd -P)"', cwd=root)
            self.assertEqual((result.returncode, result.stdout), (0, f"{spec}|green|{root.resolve()}"), result.stderr)
            self.assertEqual(run("git", "branch", "--show-current"), "feature")
            self.assertEqual(run("git", "branch", "--show-current", cwd=base), "main")
            scope_code = fence("flow-next-land/references/flow-handoff.md", "LAND_SCOPE_FAILED=")
            for override in ({"LAND_AUTHORIZED": "0"}, {"LAND_SCOPE_SPEC": "missing"},
                             {"LAND_SCOPE_PR": "https://github.com/test/repo/pull/2"},
                             {"LAND_BASE_ROOT": str(root)}, {"LAND_BASE_ROOT": str(Path(temp) / "absent")}):
                with self.subTest(scope_error=override):
                    rejected = self.run_fence(scope_code, env={**common, **override}, before=before,
                                              after='printf unexpected-continuation', cwd=root)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn("NEEDS_HUMAN", rejected.stdout)
                    self.assertNotIn("unexpected-continuation", rejected.stdout)
            broken_status = before + '''
            git() { if [ "$1" = -C ] && [ "$3" = status ]; then return 128;
                    else command git "$@"; fi; }
            '''
            rejected = self.run_fence(scope_code, env=common, before=broken_status,
                                      after='printf unexpected-continuation', cwd=root)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertNotIn("unexpected-continuation", rejected.stdout)
            (base / "user-work.txt").write_text("preserve me")
            rejected = self.run_fence(scope_code, env=common, before=before,
                                      after='printf unexpected-continuation', cwd=root)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual((base / "user-work.txt").read_text(), "preserve me")

    def test_handoff_updates_only_the_verified_source_branch(self):
        code = fence("flow-next-land/references/flow-handoff.md", "LAND_SCOPE_FAILED=")
        cases = (("main", "behind", "OPEN", "0", False),
                 ("other", "current", "OPEN", "0", False),
                 ("detached", "current", "OPEN", "0", False),
                 ("feature", "behind", "OPEN", "0", True),
                 ("feature", "current", "OPEN", "0", True),
                 ("feature", "diverged", "OPEN", "0", False),
                 ("feature", "behind", "OPEN", "1", False),
                 ("feature", "current", "OPEN", "1", True),
                 ("main", "behind", "MERGED", "0", True))
        for branch, position, state, dry_run, allowed in cases:
            with self.subTest(branch=branch, position=position, state=state, dry_run=dry_run), \
                    tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "source"
                origin = Path(temp) / "origin.git"
                base = Path(temp) / "base"
                claim = Path(temp) / "claim"
                root.mkdir()
                claim.mkdir()
                (claim / "pid").write_text("fixture")
                env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

                def git(*args, cwd=root, git_env=env):
                    return subprocess.run(["git", *args], cwd=cwd, env=git_env,
                                          capture_output=True, text=True, check=True).stdout.strip()

                git("init", "-b", "main")
                git("config", "user.email", "test@example.invalid")
                git("config", "user.name", "Test")
                git("commit", "--allow-empty", "-m", "base")
                base_sha = git("rev-parse", "HEAD")
                git("checkout", "-b", "pr-tip")
                git("commit", "--allow-empty", "-m", "PR head")
                head = git("rev-parse", "HEAD")
                git("init", "--bare", str(origin))
                git("remote", "add", "origin", str(origin))
                git("push", "origin", "HEAD:refs/heads/feature")
                git("branch", "feature", base_sha if position != "current" else head)
                if branch == "detached":
                    git("checkout", "--detach", head)
                elif branch == "other":
                    git("checkout", "-b", "other", head)
                else:
                    git("checkout", branch)
                if position == "diverged":
                    git("commit", "--allow-empty", "-m", "local work")
                if branch == "main":
                    base = root
                else:
                    git("worktree", "add", str(base), "main")
                # Rejecting a foreign source must preserve its local work as well as refs.
                if branch in ("other", "detached"):
                    (root / "user-work.txt").write_text("preserve me")
                refs_before = git("show-ref", "--heads")
                head_before = git("rev-parse", "HEAD")
                branch_before = git("symbolic-ref", "-q", "HEAD") if branch != "detached" else ""
                fixture = {"url": "https://github.com/test/repo/pull/1", "number": 1, "state": state,
                           "headRefName": "feature", "headRefOid": head, "baseRefName": "main",
                           "isCrossRepository": False}
                result = self.run_fence(code, env={**env, "FLOWCTL": "flowctl", "REPO_ROOT": str(root),
                    "LAND_BASE_ROOT": str(base), "LAND_SCOPE_SPEC": "fn-1", "LAND_SCOPE_PR": fixture["url"],
                    "LAND_AUTHORIZED": "1", "LAND_DRY_RUN": dry_run, "PR_FIXTURE": json.dumps(fixture),
                    "TICK_LOCK": str(claim)}, before='''
                    flowctl() { printf '{"branch_name":"feature"}'; }
                    gh() {
                      if [ "$1 $2" = "repo view" ]; then printf https://github.com/test/repo;
                      else printf "%s" "$PR_FIXTURE"; fi
                    }''', after='printf continued', cwd=root)
                self.assertEqual(git("rev-parse", "refs/heads/main"), base_sha, result.stdout + result.stderr)
                self.assertEqual(git("branch", "--show-current"), "" if branch == "detached" else branch)
                self.assertEqual(result.returncode == 0, allowed, result.stdout + result.stderr)
                self.assertEqual("continued" in result.stdout, allowed)
                if allowed and state == "OPEN":
                    self.assertEqual(git("rev-parse", "refs/heads/feature"), head)
                else:
                    self.assertEqual(git("show-ref", "--heads"), refs_before)
                    self.assertEqual(git("rev-parse", "HEAD"), head_before)
                    if branch_before:
                        self.assertEqual(git("symbolic-ref", "HEAD"), branch_before)
                if not allowed:
                    self.assertIn("NEEDS_HUMAN", result.stdout)
                    self.assertEqual(claim.exists(), dry_run == "1")
                if branch in ("other", "detached"):
                    self.assertEqual((root / "user-work.txt").read_text(), "preserve me")


if __name__ == "__main__":
    unittest.main()

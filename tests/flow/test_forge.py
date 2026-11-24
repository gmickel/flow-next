"""Forge rule, adapter registry, and GitLab merge-request reads.

glab answers replay the live recordings in fixtures/gitlab/ (argv, environment,
exit code, raw stdout and stderr from a self-managed GitLab test project).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parents[1] / "plugins" / "flow" / "skills" / "flow" / "scripts"
sys.path.insert(0, str(TESTS.parents[1] / "plugins" / "flow" / "skills" / "flow" / "scripts"))
spec = importlib.util.spec_from_file_location("flowctl_forge_test", SCRIPTS / "forge.py")
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)

FIXTURES = TESTS / "fixtures" / "gitlab"
GITLAB_ORIGIN = "http://localhost:8929/flownext/flownext.git"  # the recorded project
REAL_RUN = subprocess.run


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class FakeCli:
    """subprocess.run stand-in: recorded glab, scripted origin / ssh / gh login, real git otherwise."""

    def __init__(self, origin=None, glab=(), gh_hosts=(), glab_hosts=("localhost:8929",),
                 ssh=None, glab_auth=None, gh=None):
        self.origin, self.gh_hosts, self.glab_hosts = origin, set(gh_hosts), set(glab_hosts)
        self.recorded: dict[tuple, list[dict]] = {}
        for fx in glab:
            self.recorded.setdefault(tuple(fx["argv"]), []).append(fx)
        self.ssh, self.glab_auth, self.gh, self.calls = ssh or {}, glab_auth, gh, []

    def __call__(self, argv, *args, **kwargs):
        argv = list(argv)
        self.calls.append(argv)

        def done(rc, out="", err=""):
            if not kwargs.get("text"):
                out, err = out.encode(), err.encode()
            return subprocess.CompletedProcess(argv, rc, out, err)

        if argv[:4] == ["git", "remote", "get-url", "origin"]:
            return done(0, self.origin + "\n") if self.origin else done(2, err="error: No such remote 'origin'\n")
        if argv[:2] == ["ssh", "-G"]:
            return done(0, f"user git\nhostname {self.ssh.get(argv[2], argv[2])}\nport 22\n")
        if argv[:3] == ["gh", "auth", "token"]:
            return done(0 if argv[4] in self.gh_hosts else 1)
        if argv[0] == "gh" and self.gh is not None:
            ans = self.gh(argv) if callable(self.gh) else self.gh.pop(0)
            return done(*ans)
        if argv[:3] == ["glab", "auth", "status"]:
            if self.glab_auth == "timeout":
                raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))
            fx = fixture(self.glab_auth or ("auth-status-logged-in" if argv[4] in self.glab_hosts
                                            else "auth-status-unknown-host"))
            return done(fx["returncode"], fx["stdout"], fx["stderr"])
        if argv[0] == "glab":
            queue = self.recorded.get(tuple(argv))
            fx = (queue.pop(0) if len(queue) > 1 else queue[0]) if queue else None
            if fx is None:
                raise AssertionError(f"no recorded glab answer for {argv}")
            for key, value in fx["env"].items():
                assert kwargs["env"][key] == value, (key, kwargs.get("env"))
            return done(fx["returncode"], fx["stdout"], fx["stderr"])
        return REAL_RUN(argv, *args, **kwargs)

    def glab_api_calls(self):
        return [argv[2] for argv in self.calls if argv[:2] == ["glab", "api"]]


class ForgeTestCase(unittest.TestCase):
    def setUp(self):
        f.repo_forge.cache_clear()
        self.addCleanup(f.repo_forge.cache_clear)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)

    def run_with(self, fake, fn, env=None):
        clean = {key: "" for key in ("CI_SERVER_HOST", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")}
        with patch.object(f.subprocess, "run", side_effect=fake), patch.dict(os.environ, {**clean, **(env or {})}):
            return fn()


class ForgeRuleTests(ForgeTestCase):
    def test_origin_classification(self):
        cases = [
            ("github https", "https://github.com/o/r.git", {}, (), {}, "github", "github.com"),
            ("github scp", "git@github.com:o/r.git", {}, (), {}, "github", "github.com"),
            ("ssh alias", "git@gh-work:o/r.git", {}, (), {"gh-work": "ssh.github.com"}, "github", "ssh.github.com"),
            ("underscore alias", "git@gh_work:o/r.git", {}, (), {"gh_work": "github.com"}, "github", "github.com"),
            ("ssh url alias", "ssh://git@gl_work/g/p.git", {}, (), {"gl_work": "gitlab.com"}, "gitlab", "gitlab.com"),
            ("gitlab.com", "https://gitlab.com/g/sub/p.git", {}, (), {}, "gitlab", "gitlab.com"),
            ("CI_SERVER_HOST", "https://git.corp.test/g/p.git", {"CI_SERVER_HOST": "git.corp.test"}, (), {}, "gitlab", "git.corp.test"),
            ("self-managed with port", GITLAB_ORIGIN, {}, (), {}, "gitlab", "localhost:8929"),
            ("gh-known host", "https://ghe.corp.test/o/r.git", {}, ("ghe.corp.test",), {}, "github", "ghe.corp.test"),
            ("logged-out host", "https://gitlab.unknown.example/g/p.git", {}, (), {}, None, "gitlab.unknown.example"),
            # gh with an enterprise token claims every host, so glab answers first.
            ("enterprise token", GITLAB_ORIGIN, {"GH_ENTERPRISE_TOKEN": "x"}, ("localhost:8929",), {}, "gitlab", "localhost:8929"),
            ("no origin", None, {}, (), {}, None, None),
            # An SSH origin names no web port: unknown, unless GITLAB_HOST names the same host's port.
            ("ssh origin, web port elsewhere", "ssh://git@localhost:2224/flownext/flownext.git", {"GITLAB_HOST": ""}, (), {}, None, "localhost"),
            ("ssh origin, GITLAB_HOST port", "ssh://git@localhost:2224/flownext/flownext.git", {"GITLAB_HOST": "localhost:8929"}, (), {}, "gitlab", "localhost:8929"),
            ("scp origin, GITLAB_HOST url", "git@localhost:flownext/flownext.git", {"GITLAB_HOST": "http://localhost:8929/"}, (), {}, "gitlab", "localhost:8929"),
        ]
        for name, origin, env, gh_hosts, ssh, forge, host in cases:
            with self.subTest(name):
                f.repo_forge.cache_clear()
                fake = FakeCli(origin, gh_hosts=gh_hosts, ssh=ssh)
                result = self.run_with(fake, lambda: f.repo_forge(str(self.repo)), env)
                self.assertEqual((result.forge, result.host), (forge, host))
                if forge and origin and "localhost" not in origin and "corp" not in origin:
                    # A recognisable host costs no login probe.
                    self.assertFalse([c for c in fake.calls if c[0] in {"gh", "glab"}])

    def test_origin_port(self):
        # A default port is no port; glab keys a login made without the web port by the bare hostname.
        cases = [
            ("gitlab.com:443", "https://gitlab.com:443/g/p.git", (), "gitlab", "gitlab.com"),
            ("github.com:443", "https://github.com:443/o/r.git", (), "github", "github.com"),
            ("glab login by hostname", "https://gitlab.example.com:8443/g/p.git", ("gitlab.example.com",),
             "gitlab", "gitlab.example.com"),
            ("glab login by host:port", "https://gitlab.example.com:8443/g/p.git", ("gitlab.example.com:8443",),
             "gitlab", "gitlab.example.com:8443"),
            ("logged out", "https://gitlab.example.com:8443/g/p.git", (), None, "gitlab.example.com:8443"),
        ]
        for name, origin, glab_hosts, forge, host in cases:
            with self.subTest(name):
                f.repo_forge.cache_clear()
                fake = FakeCli(origin, glab_hosts=glab_hosts)
                result = self.run_with(fake, lambda: f.repo_forge(str(self.repo)))
                self.assertEqual((result.forge, result.host), (forge, host))
                if "example" not in origin:
                    self.assertFalse([c for c in fake.calls if c[0] in {"gh", "glab"}])

    def test_slow_or_offline_glab_reads_unknown_never_github(self):
        for answer in ("timeout", "auth-status-offline"):
            with self.subTest(answer):
                f.repo_forge.cache_clear()
                fake = FakeCli(GITLAB_ORIGIN, gh_hosts=("localhost:8929",), glab_auth=answer)
                result = self.run_with(fake, lambda: f.repo_forge(str(self.repo)), {"GH_ENTERPRISE_TOKEN": "x"})
                self.assertIsNone(result.forge)
                self.assertFalse([c for c in fake.calls if c[0] == "gh"])


class GitLabAdapterTests(ForgeTestCase):
    MRS = "projects/flownext%2Fflownext/merge_requests?"

    def listing(self, head=None, *, state="all", limit=100, glab=(), origin=GITLAB_ORIGIN):
        fake = FakeCli(origin, glab=glab)
        rows = self.run_with(fake, lambda: f.forge_list_prs(self.repo, head, state=state, limit=limit))
        return rows, fake

    def test_rows_map_from_recorded_listings(self):
        rows, _ = self.listing("fn73-fx-reused", glab=[fixture("mr-branch-all")])
        # The fork's MR !7 shares the branch name and is not the origin project's.
        self.assertEqual([(r["number"], r["state"]) for r in rows], [(2, "OPEN"), (1, "CLOSED")])
        self.assertEqual(rows[0], {
            "number": 2, "url": "http://localhost:8929/flownext/flownext/-/merge_requests/2",
            "state": "OPEN", "headRefName": "fn73-fx-reused",
            "headRefOid": "567560351a74b8fc2bb56832769eb26eb081259c", "mergedAt": None, "isDraft": True})
        merged, _ = self.listing("fn73-fx-merged", glab=[fixture("mr-branch-merged")])
        self.assertEqual([(r["state"], r["mergedAt"], r["headRefOid"]) for r in merged],
                         [("MERGED", "2026-11-04T10:24:33.246Z", "070c9c88e67e17a840b6080790b35f375e8335e5")])
        none, _ = self.listing("fn73-fx-absent", glab=[fixture("mr-branch-none")])
        self.assertEqual(none, [])

    def test_locked_is_open(self):
        # A locked MR is mid-merge and could not be produced on the test project; its row
        # differs from a recorded one only in state.
        recorded = json.loads(fixture("mr-branch-merged")["stdout"])[0]
        self.assertEqual(f._gitlab_mr_row({**recorded, "state": "locked"})["state"], "OPEN")

    def test_open_listing_paginates_opened_and_locked(self):
        pages = [fixture(n) for n in ("mr-open-page-1", "mr-open-page-2", "mr-open-page-3", "mr-locked-page-1")]
        with patch.object(f, "_GITLAB_PER_PAGE", 2):
            rows, fake = self.listing(state="open", limit=1000, glab=pages)
        self.assertEqual([r["number"] for r in rows], [6, 5, 4, 2])
        self.assertEqual(fake.glab_api_calls(), [fx["argv"][2] for fx in pages])

    def test_failed_reads_are_probe_failures(self):
        def malformed(change):
            fx = fixture("mr-branch-all")
            listed = json.loads(fx["stdout"])
            change(listed[1])
            fx["stdout"] = json.dumps(listed)
            return fx
        cut = fixture("mr-missing-project")  # a recorded glab failure, answering page 2
        cut["argv"] = ["glab", "api", self.MRS + "state=opened&per_page=2&page=2"]
        cases = [
            ("glab fails", dict(head="fn73-fx-reused", origin="http://localhost:8929/flownext/missing.git",
                                glab=[fixture("mr-missing-project")])),
            *((f"malformed row: {name}", dict(head="fn73-fx-reused", glab=[malformed(change)])) for name, change in (
                ("no iid", lambda mr: mr.pop("iid")), ("no sha", lambda mr: mr.pop("sha")),
                ("no merged_at", lambda mr: mr.pop("merged_at")), ("list state", lambda mr: mr.update(state=["opened"])),
                ("empty source_branch", lambda mr: mr.update(source_branch="")), ("empty web_url", lambda mr: mr.update(web_url="")))),
            ("incomplete pagination", dict(state="open", limit=1000, glab=[fixture("mr-open-page-1"), cut])),
        ]
        for name, kwargs in cases:
            with self.subTest(name), patch.object(f, "_GITLAB_PER_PAGE", 2 if name == "incomplete pagination" else 100):
                f.repo_forge.cache_clear()
                self.assertIsNone(self.listing(**kwargs)[0])

    def test_missing_glab_is_a_probe_failure(self):
        fake = FakeCli(GITLAB_ORIGIN)
        def run(argv, *args, **kwargs):
            if argv[:2] == ["glab", "api"]:
                raise FileNotFoundError("glab")
            return fake(argv, *args, **kwargs)
        self.assertIsNone(self.run_with(run, lambda: f.forge_list_prs(self.repo, "b", state="all", limit=100)))


def as_read(name: str, argv_tail: str, change=None) -> dict:
    """A recorded answer under the adapter's argv; `change` edits its parsed body, for
    shapes the live project cannot produce on demand."""
    fx = fixture(name)
    fx["argv"] = ["glab", "api", f"projects/flownext%2Fflownext{argv_tail}"]
    fx["env"] = {"GITLAB_HOST": "localhost:8929"}
    if change:
        body = json.loads(fx["stdout"])
        change(body)
        fx["stdout"] = json.dumps(body)
    return fx


class GitLabReadinessTests(ForgeTestCase):
    def readiness(self, mr, project="project-squash-default", number=14):
        fake = FakeCli(GITLAB_ORIGIN, glab=[mr, fixture(project)] if isinstance(project, str) else [mr, project])
        return self.run_with(fake, lambda: f.forge_readiness(self.repo, number))

    def test_recorded_states(self):
        cases = [
            # (recording, pipeline, merge_status, approval, ready)
            ("mr-readiness-green", "success", "mergeable", "approved", True),
            ("mr-readiness-not-approved", "success", "not_approved", "required", False),
            ("mr-readiness-approved", "success", "mergeable", "approved", True),
            ("mr-readiness-failed", "failed", "mergeable", "approved", False),
            ("mr-readiness-manual", "manual", "mergeable", "approved", False),
            ("mr-readiness-running", "running", "mergeable", "approved", False),
            ("mr-readiness-skipped", "skipped", "mergeable", "approved", False),
        ]
        for name, pipeline, status, approval, ready in cases:
            with self.subTest(name):
                fx = fixture(name)
                number = json.loads(fx["stdout"])["iid"]
                got = self.readiness(fx, number=number)
                self.assertEqual((got["pipeline"], got["merge_status"], got["approval"], got["ready"]),
                                 (pipeline, status, approval, ready))
                self.assertEqual(got["green"], pipeline == "success")
                self.assertEqual(got["head_sha"], json.loads(fx["stdout"])["sha"])

    def test_free_tier_merge_request(self):
        """Recorded before the Ultimate trial: GitLab's merge check works on every tier."""
        got = self.readiness(as_read("mr-review-read", "/merge_requests/13"), number=13)
        self.assertEqual((got["pipeline"], got["approval"], got["ready"]), ("success", "approved", True))

    def test_squash_forbidden_is_never_ready(self):
        got = self.readiness(fixture("mr-readiness-green"), "project-squash-never")
        self.assertEqual((got["squash_allowed"], got["green"], got["ready"]), (False, True, False))

    def test_a_pipeline_for_another_head_or_none_is_not_green(self):
        for name, change in (
            ("earlier head", lambda mr: mr["head_pipeline"].update(sha="0" * 40)),
            ("no pipeline", lambda mr: mr.update(head_pipeline=None)),
            ("pipelines hidden from the caller", lambda mr: mr.pop("head_pipeline")),
        ):
            with self.subTest(name):
                got = self.readiness(as_read("mr-readiness-green", "/merge_requests/14", change))
                self.assertEqual((got["pipeline"], got["green"], got["ready"]), (None, False, False))

    def merged_result(self, commit):
        fake = FakeCli(GITLAB_ORIGIN, glab=[fixture("mr-readiness-merged-result"), commit,
                                            fixture("project-squash-default")])
        return self.run_with(fake, lambda: f.forge_readiness(self.repo, 21))

    def test_a_merged_results_pipeline_counts_for_its_head(self):
        got = self.merged_result(fixture("commit-merged-result"))
        self.assertEqual((got["pipeline"], got["green"], got["ready"]), ("success", True, True))

    def test_a_merged_results_pipeline_of_another_head_or_unread_is_not_green(self):
        argv_tail = "/repository/commits/200b0dee9c049b7f82f7795a8e9c370c35e17079"
        for name, commit in (
            ("another head", as_read("commit-merged-result", argv_tail,
                                     lambda c: c.update(parent_ids=[c["parent_ids"][0], "0" * 40]))),
            ("commit unreadable", {**fixture("commit-merged-result"), "returncode": 1, "stdout": ""}),
        ):
            with self.subTest(name):
                got = self.merged_result(commit)
                self.assertEqual((got["pipeline"], got["green"], got["ready"]), (None, False, False))

    def test_unreadable_is_not_green_not_approved(self):
        unread = {"head_sha": None, "pipeline": None, "merge_status": None, "approval": "unknown",
                  "squash_allowed": None, "green": False, "ready": False}
        missing = fixture("mr-missing-read")  # a recorded 404, under the adapter's argv
        missing.update(argv=["glab", "api", "projects/flownext%2Fflownext/merge_requests/14"],
                       env={"GITLAB_HOST": "localhost:8929"})
        cases = [
            ("merge request missing", missing, "project-squash-default"),
            ("not JSON", {**as_read("mr-readiness-green", "/merge_requests/14"), "stdout": "<html>"}, "project-squash-default"),
            ("no merge status", as_read("mr-readiness-green", "/merge_requests/14",
                                        lambda mr: mr.pop("detailed_merge_status")), "project-squash-default"),
            ("project unreadable", fixture("mr-readiness-green"),
             {**fixture("project-squash-default"), "returncode": 1, "stdout": ""}),
        ]
        for name, mr, project in cases:
            with self.subTest(name):
                self.assertEqual(self.readiness(mr, project), unread)

    def test_github_has_no_readiness_read(self):
        fake = FakeCli("https://github.com/o/r.git")
        self.assertIsNone(self.run_with(fake, lambda: f.forge_readiness(self.repo, 1)))


class GitLabMergeEvidenceTests(ForgeTestCase):
    def merge_read(self, *glab, origin=GITLAB_ORIGIN, branch="fn317-ready"):
        fake = FakeCli(origin, glab=glab)
        with patch.object(f, "get_repo_root", return_value=self.repo):
            return self.run_with(fake, lambda: f._forge_merge_read(branch))

    def test_merged_rows_carry_their_changed_files(self):
        rows, files = self.merge_read(fixture("mr-evidence-merged"), fixture("mr-evidence-merged-diffs"))
        self.assertEqual([(r["number"], r["state"], r["isDraft"]) for r in rows], [(14, "MERGED", False)])
        self.assertEqual(files, {14: ["fn317/ready.txt"]})
        rows, files = self.merge_read(fixture("mr-evidence-spec-only"), fixture("mr-evidence-spec-only-diffs"),
                                      branch="fn317-spec-only")
        self.assertEqual(files, {19: [".flow/specs/fn-317-fixture.md"]})

    def test_a_failed_file_read_fails_the_whole_read(self):
        missing = fixture("mr-evidence-missing-diffs")
        missing["argv"] = fixture("mr-evidence-merged-diffs")["argv"]
        self.assertIsNone(self.merge_read(fixture("mr-evidence-merged"), missing))

    def test_github_reads_through_the_tracker_own_gh_probe(self):
        self.assertIs(self.merge_read(origin="https://github.com/o/r.git"), NotImplemented)

    def test_tracker_classifies_the_forge_read(self):
        from flowctl_tracker.status import policy
        self.addCleanup(setattr, policy, "forge_merge_read", policy.forge_merge_read)
        policy.forge_merge_read = f._forge_merge_read
        cases = [
            ("merged", "fn317-ready", ("mr-evidence-merged", "mr-evidence-merged-diffs")),
            ("none", "fn317-spec-only", ("mr-evidence-spec-only", "mr-evidence-spec-only-diffs")),
            ("probe-error", "fn317-ready", ("mr-evidence-merged", "mr-evidence-missing-diffs")),
        ]
        for want, branch, names in cases:
            with self.subTest(want):
                f.repo_forge.cache_clear()
                answers = [fixture(n) for n in names]
                if want == "probe-error":   # the recorded 404, answering MR !14's file read
                    answers[1]["argv"] = fixture("mr-evidence-merged-diffs")["argv"]
                fake = FakeCli(GITLAB_ORIGIN, glab=answers)
                with patch.object(f, "get_repo_root", return_value=self.repo):
                    got = self.run_with(fake, lambda b=branch: policy.merge_evidence({}, {"branch_name": b}, None))
                self.assertEqual(got, want)


class _FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class GitHubWaitAndMergeTests(ForgeTestCase):
    ORIGIN = "https://github.com/o/r.git"
    HEAD = "a" * 40
    MERGE_SHA = "b" * 40

    @classmethod
    def _view(cls, **overrides) -> str:
        base = {
            "state": "OPEN", "headRefOid": cls.HEAD, "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN", "reviewDecision": "APPROVED", "isDraft": False,
            "statusCheckRollup": [{"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            "mergeCommit": None,
        }
        base.update(overrides)
        return json.dumps(base)

    def test_wait_ready_and_terminal_states(self):
        cases = [
            ("ready", {}, "ready"),
            ("changes requested", {"reviewDecision": "CHANGES_REQUESTED"}, "changes_requested"),
            ("review required", {"reviewDecision": "REVIEW_REQUIRED"}, "review_required"),
            ("conflict", {"mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}, "blocked"),
            ("draft", {"isDraft": True}, "blocked"),
            ("merged", {"state": "MERGED", "mergeCommit": {"oid": self.MERGE_SHA}}, "merged"),
            ("closed", {"state": "CLOSED"}, "closed"),
        ]
        for name, overrides, want in cases:
            with self.subTest(name):
                clock = _FakeClock()
                fake = FakeCli(self.ORIGIN, gh=[(0, self._view(**overrides), "")])
                got = self.run_with(fake, lambda c=clock: f.forge_wait(
                    self.repo, 42, timeout_s=60, interval_s=10,
                    monotonic=c.monotonic, sleep=c.sleep))
                self.assertEqual(got["state"], want)
                self.assertEqual(got["head_sha"], self.HEAD)
                self.assertEqual(clock.sleeps, [])

    def test_wait_failed_check_returns_at_once(self):
        clock = _FakeClock()
        rollup = [
            {"name": "lint", "status": "COMPLETED", "conclusion": "FAILURE"},
            {"name": "e2e", "status": "IN_PROGRESS", "conclusion": ""},
        ]
        fake = FakeCli(self.ORIGIN, gh=[(0, self._view(statusCheckRollup=rollup), "")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 42, timeout_s=120, interval_s=15,
            monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got["state"], "failing")
        self.assertEqual(got["failing_checks"], ["lint"])
        self.assertEqual(got["running_checks"], ["e2e"])
        self.assertEqual(clock.sleeps, [])

    def test_wait_polls_and_honours_deadline_without_sleeping(self):
        running = self._view(statusCheckRollup=[{"name": "ci", "status": "IN_PROGRESS", "conclusion": ""}])
        clock = _FakeClock()
        fake = FakeCli(self.ORIGIN, gh=[(0, running, ""), (0, self._view(), "")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 42, timeout_s=60, interval_s=15,
            monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got["state"], "ready")
        self.assertEqual(clock.sleeps, [15.0])

        clock2 = _FakeClock()
        fake2 = FakeCli(self.ORIGIN, gh=lambda argv: (0, running, ""))
        got2 = self.run_with(fake2, lambda: f.forge_wait(
            self.repo, 42, timeout_s=25, interval_s=10,
            monotonic=clock2.monotonic, sleep=clock2.sleep))
        self.assertEqual(got2["state"], "pending")
        self.assertEqual(got2["running_checks"], ["ci"])
        self.assertIn("deadline reached", got2["reason"])
        self.assertEqual(clock2.sleeps, [10.0, 10.0, 5.0])

    def test_merge_succeeds_and_confirms_commit(self):
        after = json.dumps({"state": "MERGED", "headRefOid": self.HEAD,
                            "mergeCommit": {"oid": self.MERGE_SHA}})
        fake = FakeCli(self.ORIGIN, gh=[(0, "", ""), (0, after, "")])
        got = self.run_with(fake, lambda: f.forge_merge(self.repo, 42, self.HEAD))
        self.assertEqual(got, {"merged": True, "merge_commit": self.MERGE_SHA,
                               "reason": "merged", "message": "squash merged"})
        self.assertIn(["gh", "pr", "merge", "42", "--repo", "o/r", "--squash",
                       "--match-head-commit", self.HEAD], fake.calls)
        view_calls = [c for c in fake.calls if c[:3] == ["gh", "pr", "view"]]
        self.assertEqual(len(view_calls), 1)
        fields = view_calls[0][view_calls[0].index("--json") + 1]
        self.assertNotIn("mergeQueueEntry", fields)
        self.assertEqual(fields, "state,headRefOid,mergeCommit")

    def test_merge_refuses_moved_head_short_sha_and_reports_queued(self):
        short = f.forge_merge(self.repo, 42, self.HEAD[:12])
        self.assertEqual((short["merged"], short["reason"]), (False, "invalid_head"))

        moved_view = json.dumps({"state": "OPEN", "headRefOid": "c" * 40, "mergeCommit": None})
        fake = FakeCli(self.ORIGIN, gh=[(1, "", "Head branch was modified"), (0, moved_view, "")])
        got = self.run_with(fake, lambda: f.forge_merge(self.repo, 42, self.HEAD))
        self.assertEqual((got["merged"], got["reason"]), (False, "head_moved"))

        open_view = json.dumps({"state": "OPEN", "headRefOid": self.HEAD, "mergeCommit": None})
        for label, stderr in (
            ("will be added", "✓ Pull request o/r#42 will be added to the merge queue for main when ready\n"),
            ("strategy set by queue", "! The merge strategy for main is set by the merge queue\n"),
            ("already queued", "! Pull request o/r#42 is already queued to merge\n"),
        ):
            with self.subTest(label):
                clock = _FakeClock()
                fake_q = FakeCli(self.ORIGIN, gh=[(0, "", stderr), (0, open_view, "")])
                got_q = self.run_with(fake_q, lambda c=clock: f.forge_merge(self.repo, 42, self.HEAD, sleep=c.sleep))
                self.assertEqual((got_q["merged"], got_q["reason"]), (False, "queued"))
                self.assertEqual(clock.sleeps, [])

        # Non-zero exit mentioning "merge queue" is refused, never queued.
        fake_err = FakeCli(self.ORIGIN, gh=[
            (1, "", "X Cannot use `-d` or `--delete-branch` when merge queue enabled\n"),
            (0, open_view, ""),
        ])
        got_err = self.run_with(fake_err, lambda: f.forge_merge(self.repo, 42, self.HEAD))
        self.assertEqual((got_err["merged"], got_err["reason"]), (False, "not_mergeable"))

    def test_merge_retries_confirming_read_after_exit_zero(self):
        merged_view = json.dumps({"state": "MERGED", "headRefOid": self.HEAD,
                                  "mergeCommit": {"oid": self.MERGE_SHA}})
        open_view = json.dumps({"state": "OPEN", "headRefOid": self.HEAD, "mergeCommit": None})
        no_commit_view = json.dumps({"state": "MERGED", "headRefOid": self.HEAD, "mergeCommit": None})
        moved_view = json.dumps({"state": "OPEN", "headRefOid": "c" * 40, "mergeCommit": None})

        # Confirming read fails once, then shows merged.
        clock = _FakeClock()
        fake = FakeCli(self.ORIGIN, gh=[(0, "", ""), (1, "", "shim banner\ntransient error"), (0, merged_view, "")])
        got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 42, self.HEAD, sleep=c.sleep))
        self.assertEqual(got, {"merged": True, "merge_commit": self.MERGE_SHA,
                               "reason": "merged", "message": "squash merged"})
        self.assertEqual(len([c for c in fake.calls if c[:3] == ["gh", "pr", "merge"]]), 1)
        self.assertEqual(len([c for c in fake.calls if c[:3] == ["gh", "pr", "view"]]), 2)
        self.assertEqual(clock.sleeps, [f._MERGE_CONFIRM_INTERVAL_S])

        # Confirming read shows OPEN, then MERGED without mergeCommit, then MERGED with mergeCommit.
        clock2 = _FakeClock()
        fake2 = FakeCli(self.ORIGIN, gh=[(0, "", ""), (0, open_view, ""), (0, no_commit_view, ""), (0, merged_view, "")])
        got2 = self.run_with(fake2, lambda: f.forge_merge(self.repo, 42, self.HEAD, sleep=clock2.sleep))
        self.assertEqual((got2["merged"], got2["reason"], got2["merge_commit"]), (True, "merged", self.MERGE_SHA))
        self.assertEqual(len([c for c in fake2.calls if c[:3] == ["gh", "pr", "merge"]]), 1)
        self.assertEqual(clock2.sleeps, [f._MERGE_CONFIRM_INTERVAL_S, f._MERGE_CONFIRM_INTERVAL_S])

        # Stops repeating as soon as head_moved appears.
        c_early = _FakeClock()
        fake_early = FakeCli(self.ORIGIN, gh=[(0, "", ""), (1, "", "transient"), (0, moved_view, "")])
        got_early = self.run_with(fake_early, lambda: f.forge_merge(
            self.repo, 42, self.HEAD, sleep=c_early.sleep))
        self.assertEqual((got_early["merged"], got_early["reason"]), (False, "head_moved"))
        self.assertEqual(len([c for c in fake_early.calls if c[:3] == ["gh", "pr", "merge"]]), 1)
        self.assertEqual(len([c for c in fake_early.calls if c[:3] == ["gh", "pr", "view"]]), 2)
        self.assertEqual(c_early.sleeps, [f._MERGE_CONFIRM_INTERVAL_S])

    def test_merge_returns_unconfirmed_when_confirming_reads_never_succeed(self):
        open_view = json.dumps({"state": "OPEN", "headRefOid": self.HEAD, "mergeCommit": None})
        expected_reads = 1 + f._MERGE_CONFIRM_RETRIES
        expected_sleeps = [f._MERGE_CONFIRM_INTERVAL_S] * f._MERGE_CONFIRM_RETRIES

        for label, read_reply in (("read errors", (1, "", "shim banner")), ("still open", (0, open_view, ""))):
            with self.subTest(label):
                clock = _FakeClock()
                fake = FakeCli(self.ORIGIN, gh=[(0, "", ""), *([read_reply] * expected_reads)])
                got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 42, self.HEAD, sleep=c.sleep))
                self.assertEqual((got["merged"], got["reason"], got["merge_commit"]), (False, "unconfirmed", None))
                self.assertIn("merge command succeeded", got["message"])
                self.assertIn("could not be confirmed", got["message"])
                self.assertEqual(len([c for c in fake.calls if c[:3] == ["gh", "pr", "merge"]]), 1)
                self.assertEqual(len([c for c in fake.calls if c[:3] == ["gh", "pr", "view"]]), expected_reads)
                self.assertEqual(clock.sleeps, expected_sleeps)

    def test_merge_nonzero_exit_does_not_repeat_confirming_reads(self):
        open_view = json.dumps({"state": "OPEN", "headRefOid": self.HEAD, "mergeCommit": None})
        for label, read_reply in (("read error", (1, "", "view failed")), ("still open", (0, open_view, ""))):
            with self.subTest(label):
                clock = _FakeClock()
                fake = FakeCli(self.ORIGIN, gh=[(1, "", "Pull request is not mergeable"), read_reply])
                got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 42, self.HEAD, sleep=c.sleep))
                self.assertEqual((got["merged"], got["reason"]), (False, "not_mergeable"))
                self.assertEqual(len([c for c in fake.calls if c[:3] == ["gh", "pr", "merge"]]), 1)
                self.assertEqual(len([c for c in fake.calls if c[:3] == ["gh", "pr", "view"]]), 1)
                self.assertEqual(clock.sleeps, [])


class GitLabWaitAndMergeTests(ForgeTestCase):
    HEAD = "d8b76161301680f873478db85eff419251735916"
    MERGE_SHA = "79b0bb356d6d477669ca7ec5466368cf0b588663"

    def test_wait_ready_review_required_and_merged(self):
        clock = _FakeClock()
        fake = FakeCli(GITLAB_ORIGIN, glab=[fixture("mr-readiness-green"), fixture("project-squash-default")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 14, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual((got["state"], got["head_sha"], clock.sleeps), ("ready", self.HEAD, []))

        fake_rev = FakeCli(GITLAB_ORIGIN, glab=[fixture("mr-readiness-not-approved"), fixture("project-squash-default")])
        got_rev = self.run_with(fake_rev, lambda: f.forge_wait(
            self.repo, 14, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got_rev["state"], "review_required")

        fake_m = FakeCli(GITLAB_ORIGIN, glab=[as_read("land-mr-merged", "/merge_requests/14")])
        got_m = self.run_with(fake_m, lambda: f.forge_wait(
            self.repo, 14, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got_m["state"], "merged")
        self.assertIn(self.MERGE_SHA, got_m["reason"])

    def test_wait_failed_pipeline_returns_at_once_with_failed_jobs(self):
        clock = _FakeClock()
        fake = FakeCli(GITLAB_ORIGIN, glab=[
            fixture("mr-readiness-failed"), fixture("project-squash-default"),
            as_read("land-failed-jobs", "/pipelines/16/jobs?scope=failed"),
        ])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 15, timeout_s=120, interval_s=15, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got["state"], "failing")
        self.assertEqual(got["failing_checks"], ["fail"])
        self.assertEqual(clock.sleeps, [])

    def test_wait_running_pipeline_honours_deadline(self):
        clock = _FakeClock()
        fake = FakeCli(GITLAB_ORIGIN, glab=[fixture("mr-readiness-running"), fixture("project-squash-default")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 17, timeout_s=20, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got["state"], "pending")
        self.assertEqual(got["running_checks"], ["pipeline (running)"])
        self.assertIn("deadline reached", got["reason"])
        self.assertEqual(clock.sleeps, [10.0, 10.0])

    def test_merge_succeeds_and_refuses_moved_head_409(self):
        merge_ok = {**fixture("land-merge"), "env": {"GITLAB_HOST": "localhost:8929"}}
        merge_ok["argv"] = [
            "glab", "api", "-X", "PUT", "projects/flownext%2Fflownext/merge_requests/14/merge",
            "-F", "squash=true", "-F", "should_remove_source_branch=true", "-f", f"sha={self.HEAD}",
        ]
        fake = FakeCli(GITLAB_ORIGIN, glab=[merge_ok, as_read("land-mr-merged", "/merge_requests/14")])
        got = self.run_with(fake, lambda: f.forge_merge(self.repo, 14, self.HEAD))
        self.assertEqual(got, {"merged": True, "merge_commit": self.MERGE_SHA,
                               "reason": "merged", "message": "squash merged"})

        stale = "fb633aff58843b154b078ff30eb6cc6df040deeb"
        moved = {**fixture("land-merge-moved-head"), "env": {"GITLAB_HOST": "localhost:8929"}}
        moved["argv"] = [
            "glab", "api", "-X", "PUT", "projects/flownext%2Fflownext/merge_requests/14/merge",
            "-F", "squash=true", "-F", "should_remove_source_branch=true", "-f", f"sha={stale}",
        ]
        fake_moved = FakeCli(GITLAB_ORIGIN, glab=[moved])
        got_moved = self.run_with(fake_moved, lambda: f.forge_merge(self.repo, 14, stale))
        self.assertEqual((got_moved["merged"], got_moved["reason"]), (False, "head_moved"))

    def _merge_put_14(self, head=None, **overrides):
        fx = {**fixture("land-merge"), "env": {"GITLAB_HOST": "localhost:8929"}}
        fx["argv"] = [
            "glab", "api", "-X", "PUT", "projects/flownext%2Fflownext/merge_requests/14/merge",
            "-F", "squash=true", "-F", "should_remove_source_branch=true", "-f", f"sha={head or self.HEAD}",
        ]
        fx.update(overrides)
        return fx

    def test_merge_retries_confirming_read_after_exit_zero(self):
        put = self._merge_put_14()
        read_argv = ["glab", "api", "projects/flownext%2Fflownext/merge_requests/14"]
        read_fail = {**fixture("mr-missing-read"), "argv": read_argv, "env": {"GITLAB_HOST": "localhost:8929"}}
        locked = as_read("land-mr-merged", "/merge_requests/14",
                         lambda mr: mr.update(state="locked", merge_commit_sha=None, squash_commit_sha=None))
        merged = as_read("land-mr-merged", "/merge_requests/14")

        for label, first_after in (("read error", read_fail), ("still locked", locked)):
            with self.subTest(label):
                clock = _FakeClock()
                fake = FakeCli(GITLAB_ORIGIN, glab=[put, first_after, merged])
                got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 14, self.HEAD, sleep=c.sleep))
                self.assertEqual(got, {"merged": True, "merge_commit": self.MERGE_SHA,
                                       "reason": "merged", "message": "squash merged"})
                self.assertEqual(len([c for c in fake.calls if c == put["argv"]]), 1)
                self.assertEqual(len([c for c in fake.calls if c == read_argv]), 2)
                self.assertEqual(clock.sleeps, [f._MERGE_CONFIRM_INTERVAL_S])

    def test_merge_returns_unconfirmed_when_confirming_reads_never_succeed(self):
        put = self._merge_put_14()
        read_argv = ["glab", "api", "projects/flownext%2Fflownext/merge_requests/14"]
        read_fail = {**fixture("mr-missing-read"), "argv": read_argv, "env": {"GITLAB_HOST": "localhost:8929"}}
        locked = as_read("land-mr-merged", "/merge_requests/14",
                         lambda mr: mr.update(state="locked", merge_commit_sha=None, squash_commit_sha=None))
        expected_reads = 1 + f._MERGE_CONFIRM_RETRIES
        expected_sleeps = [f._MERGE_CONFIRM_INTERVAL_S] * f._MERGE_CONFIRM_RETRIES

        for label, bad_after in (("read errors", read_fail), ("still locked", locked)):
            with self.subTest(label):
                clock = _FakeClock()
                fake = FakeCli(GITLAB_ORIGIN, glab=[put, *([bad_after] * expected_reads)])
                got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 14, self.HEAD, sleep=c.sleep))
                self.assertEqual((got["merged"], got["reason"], got["merge_commit"]), (False, "unconfirmed", None))
                self.assertIn("merge command succeeded", got["message"])
                self.assertIn("could not be confirmed", got["message"])
                self.assertEqual(len([c for c in fake.calls if c == put["argv"]]), 1)
                self.assertEqual(len([c for c in fake.calls if c == read_argv]), expected_reads)
                self.assertEqual(clock.sleeps, expected_sleeps)

    def test_merge_refused_behaves_as_before(self):
        put = self._merge_put_14(returncode=1, stdout="", stderr="405 Method Not Allowed")
        read_argv = ["glab", "api", "projects/flownext%2Fflownext/merge_requests/14"]
        clock = _FakeClock()
        fake = FakeCli(GITLAB_ORIGIN, glab=[put])
        got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 14, self.HEAD, sleep=c.sleep))
        self.assertEqual((got["merged"], got["reason"]), (False, "not_mergeable"))
        self.assertEqual(len([c for c in fake.calls if c == put["argv"]]), 1)
        self.assertEqual(len([c for c in fake.calls if c == read_argv]), 0)
        self.assertEqual(clock.sleeps, [])


if __name__ == "__main__":
    unittest.main()

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
from types import SimpleNamespace
from unittest.mock import patch

from flowctl_test_support import FLOWCTL_CMD

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("flowctl_forge_test", SCRIPTS / "flowctl.py")
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
                 ssh=None, glab_timeout=False):
        self.origin, self.gh_hosts, self.glab_hosts = origin, set(gh_hosts), set(glab_hosts)
        self.recorded = {tuple(fx["argv"]): fx for fx in glab}
        self.ssh, self.glab_timeout, self.calls = ssh or {}, glab_timeout, []

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
        if argv[:3] == ["glab", "auth", "status"]:
            if self.glab_timeout:
                raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))
            fx = fixture("auth-status-logged-in" if argv[4] in self.glab_hosts else "auth-status-unknown-host")
            return done(fx["returncode"], fx["stdout"], fx["stderr"])
        if argv[0] == "glab":
            fx = self.recorded.get(tuple(argv))
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
            ("gitlab.com", "https://gitlab.com/g/sub/p.git", {}, (), {}, "gitlab", "gitlab.com"),
            ("CI_SERVER_HOST", "https://git.corp.test/g/p.git", {"CI_SERVER_HOST": "git.corp.test"}, (), {}, "gitlab", "git.corp.test"),
            ("self-managed with port", GITLAB_ORIGIN, {}, (), {}, "gitlab", "localhost:8929"),
            ("gh-known host", "https://ghe.corp.test/o/r.git", {}, ("ghe.corp.test",), {}, "github", "ghe.corp.test"),
            ("logged-out host", "https://gitlab.unknown.example/g/p.git", {}, (), {}, None, "gitlab.unknown.example"),
            # gh with an enterprise token claims every host, so glab answers first.
            ("enterprise token", GITLAB_ORIGIN, {"GH_ENTERPRISE_TOKEN": "x"}, ("localhost:8929",), {}, "gitlab", "localhost:8929"),
            ("no origin", None, {}, (), {}, None, None),
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

    def test_slow_glab_reads_unknown_never_github(self):
        fake = FakeCli(GITLAB_ORIGIN, gh_hosts=("localhost:8929",), glab_timeout=True)
        result = self.run_with(fake, lambda: f.repo_forge(str(self.repo)), {"GH_ENTERPRISE_TOKEN": "x"})
        self.assertIsNone(result.forge)
        self.assertFalse([c for c in fake.calls if c[0] == "gh"])

    def test_registered_fake_forge_answers_the_shared_lookup(self):
        row = {"number": 9, "url": "https://forge.fake.test/o/r/pulls/9", "state": "OPEN",
               "headRefName": "fn-1-feature", "headRefOid": "abc", "mergedAt": None}
        fake_forge = {"owns_host": lambda host: host == "forge.fake.test",
                      "list_prs": lambda repo, origin, head, *, state, limit: [row] if head == "fn-1-feature" else []}
        body = self.repo / "spec.md"
        body.write_text("Implement feature", encoding="utf-8")
        spec_data = {"title": "Feature", "status": "open", "branch_name": "fn-1-feature"}
        fake = FakeCli("https://forge.fake.test/o/r.git", glab_hosts=())
        with patch.dict(f.FORGE_ADAPTERS, {"fake": fake_forge}), patch.object(f, "get_config", return_value=True), patch.object(f, "get_repo_root", return_value=self.repo), patch.object(f, "get_flow_dir", return_value=self.repo), patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), patch.object(f, "load_json_or_exit", return_value=spec_data), patch.object(f, "normalize_epic", side_effect=lambda x: x), patch.object(f, "find_spec_md_path", return_value=body), patch.object(f.TaskInventory, "load", return_value=SimpleNamespace(by_spec={})):
            state = self.run_with(fake, lambda: f.judge_route_state({}, "fn-1-feature"))
            self.assertEqual(f.repo_forge(str(self.repo)).forge, "fake")
            approval = f.forge_approval_rows("fn-1-feature", self.repo)
        self.assertEqual(state["pr_ref"], row)
        self.assertEqual(f.judge_route_lifecycle(state)["value"], "existing_pr_tail")
        self.assertEqual(approval, (None, "spec approval is unsupported on this forge (fake)"))


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
            "headRefOid": "567560351a74b8fc2bb56832769eb26eb081259c", "mergedAt": None})
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
        malformed = fixture("mr-branch-all")
        listed = json.loads(malformed["stdout"])
        del listed[1]["iid"]
        malformed["stdout"] = json.dumps(listed)
        cut = fixture("mr-missing-project")  # a recorded glab failure, answering page 2
        cut["argv"] = ["glab", "api", self.MRS + "state=opened&per_page=2&page=2"]
        cases = [
            ("glab fails", dict(head="fn73-fx-reused", origin="http://localhost:8929/flownext/missing.git",
                                glab=[fixture("mr-missing-project")])),
            ("malformed row", dict(head="fn73-fx-reused", glab=[malformed])),
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

    def test_spec_approval_is_unsupported(self):
        fake = FakeCli(GITLAB_ORIGIN)
        with patch.object(f, "get_repo_root", return_value=self.repo):
            status = self.run_with(fake, lambda: f.spec_approval_status(self.repo, {"id": "fn-1-x"}))
        self.assertEqual(status, {"approved": False, "reason": "spec approval is unsupported on this forge (gitlab)"})


class PilotSnapshotForgeTests(ForgeTestCase):
    def test_snapshot_reads_merge_requests_and_names_the_forge(self):
        def flow(*args):
            proc = REAL_RUN([*FLOWCTL_CMD, *args], cwd=self.repo, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            return proc.stdout
        REAL_RUN(["git", "init", "-q"], cwd=self.repo, check=True)
        flow("init", "--json")
        sid = json.loads(flow("spec", "create", "--title", "MR fixture", "--json"))["id"]
        flow("spec", "set-branch", sid, "--branch", "fn73-fx-reused", "--json")
        flow("spec", "ready", sid)
        fake = FakeCli(GITLAB_ORIGIN, glab=[fixture(n) for n in ("mr-open", "mr-locked", "mr-branch-all")])
        with patch.object(f, "get_repo_root", return_value=self.repo), patch.object(f, "get_flow_dir", return_value=self.repo / ".flow"), patch.object(f, "_pilot_strikes_ledger_path", return_value=None):
            result = self.run_with(fake, lambda: f.pilot_snapshot(sid))
        self.assertEqual(result["forge"], "gitlab")
        self.assertFalse(result["pr_listing_failed"])
        pr = result["selected"]["pr"]
        self.assertEqual((pr["open"]["number"], [r["number"] for r in pr["closed"]]), (2, [1]))
        self.assertEqual(result["route"]["decision"]["value"], "existing_pr_tail")


if __name__ == "__main__":
    unittest.main()

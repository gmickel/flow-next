"""Bitbucket Cloud forge rule and pull request reads.

bkt answers replay the live recordings in fixtures/bitbucket/ (argv, exit code, raw
stdout and stderr from the flownextnew/flownext Bitbucket Cloud test repository).
"""
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flowctl_test_support import FLOWCTL_CMD
from test_forge import REAL_RUN, FakeCli, ForgeTestCase, f

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bitbucket"
ORIGIN = "git@ssh.bitbucket.org:flownextnew/flownext.git"   # the clone link Bitbucket gives the test repository
PULLS = "/repositories/flownextnew/flownext/pullrequests"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def derived(name: str, change, argv=None) -> dict:
    """A recorded answer with its body changed, for shapes the test repository cannot produce."""
    fx = fixture(name)
    body = json.loads(fx["stdout"])
    fx["stdout"] = json.dumps(change(body) or body)
    if argv:
        fx["argv"] = argv
    return fx


def under(name: str, argv: list) -> dict:
    """A recorded answer (a failure, mostly) replayed for another call."""
    return {**fixture(name), "argv": argv}


def branch_argv(branch: str) -> list:
    return ["bkt", "--context", "flownextnew", "api",
            f"{PULLS}?state=OPEN&state=MERGED&state=DECLINED&state=SUPERSEDED"
            f"&q=source.branch.name%3D%22{branch}%22&pagelen=50&page=1"]


class BktCli(FakeCli):
    """FakeCli plus recorded bkt: `bkt context list` answers `contexts`, every other call its argv's recording."""

    def __init__(self, origin=ORIGIN, bkt=(), contexts="context-list", **kwargs):
        super().__init__(origin, **kwargs)
        self.bkt = {tuple(fx["argv"]): fx for fx in bkt}
        self.contexts = contexts

    def __call__(self, argv, *args, **kwargs):
        argv = list(argv)
        if argv[0] != "bkt":
            return super().__call__(argv, *args, **kwargs)
        self.calls.append(argv)
        if self.contexts == "missing":
            raise FileNotFoundError("bkt")
        fx = fixture(self.contexts) if argv[1:] == ["context", "list", "--json"] else self.bkt.get(tuple(argv))
        if fx is None:
            raise AssertionError(f"no recorded bkt answer for {argv}")
        return subprocess.CompletedProcess(argv, fx["returncode"], fx["stdout"], fx["stderr"])

    def api_calls(self):
        return [argv[4] for argv in self.calls if argv[:2] == ["bkt", "--context"]]


class BitbucketForgeRuleTests(ForgeTestCase):
    def test_bitbucket_cloud_hosts_name_the_forge_without_a_login_probe(self):
        cases = [
            ("https", "https://bitbucket.org/flownextnew/flownext.git", {}, "bitbucket.org"),
            ("https with user", "https://flownextnew-admin@bitbucket.org/flownextnew/flownext.git", {}, "bitbucket.org"),
            ("scp, Bitbucket's clone link", ORIGIN, {}, "ssh.bitbucket.org"),
            ("scp on bitbucket.org", "git@bitbucket.org:flownextnew/flownext.git", {}, "bitbucket.org"),
            ("ssh over 443", "ssh://git@altssh.bitbucket.org:443/flownextnew/flownext.git", {}, "altssh.bitbucket.org"),
            ("ssh alias", "git@bb-work:flownextnew/flownext.git", {"bb-work": "ssh.bitbucket.org"}, "ssh.bitbucket.org"),
        ]
        for name, origin, ssh, host in cases:
            with self.subTest(name):
                f.repo_forge.cache_clear()
                fake = BktCli(origin, ssh=ssh)
                got = self.run_with(fake, lambda: f.repo_forge(str(self.repo)))
                self.assertEqual(got, f.ForgeOrigin("bitbucket", host, "flownextnew/flownext"))
                self.assertFalse([c for c in fake.calls if c[0] in {"gh", "glab", "bkt"}])

    def test_self_hosted_bitbucket_stays_unknown(self):
        # Data Center is not recognised: today's unknown-host behaviour, never a Bitbucket read.
        fake = BktCli("https://bitbucket.corp.test/scm/proj/repo.git", glab_hosts=())
        got = self.run_with(fake, lambda: f.repo_forge(str(self.repo)))
        self.assertIsNone(got.forge)
        self.assertFalse([c for c in fake.calls if c[0] == "bkt"])

    def test_github_and_gitlab_reads_never_run_bkt(self):
        for origin, recorded in (("https://github.com/o/r.git", ()), ("https://gitlab.com/g/p.git", ())):
            with self.subTest(origin):
                f.repo_forge.cache_clear()
                fake = BktCli(origin, glab=recorded)
                with patch.object(f, "_glab_get", return_value=[]):
                    self.run_with(fake, lambda: f.forge_list_prs(self.repo, "b", state="all", limit=100))
                self.assertFalse([c for c in fake.calls if c[0] == "bkt"])


class BitbucketAdapterTests(ForgeTestCase):
    def listing(self, head=None, *, state="all", limit=100, **cli):
        fake = BktCli(**cli)
        return self.run_with(fake, lambda: f.forge_list_prs(self.repo, head, state=state, limit=limit)), fake

    def test_rows_map_from_recorded_listings(self):
        rows, fake = self.listing("fx-reused", bkt=[fixture("pr-branch-reused"), fixture("commit-reused")])
        self.assertEqual(rows, [
            {"number": 4, "url": "https://bitbucket.org/flownextnew/flownext/pull-requests/4", "state": "OPEN",
             "headRefName": "fx-reused", "headRefOid": "ef14a8697d98cb0eb95e9e706fa763f10977b16a",
             "mergedAt": None, "isDraft": False},
            {"number": 3, "url": "https://bitbucket.org/flownextnew/flownext/pull-requests/3", "state": "CLOSED",
             "headRefName": "fx-reused", "headRefOid": "ef14a8697d98cb0eb95e9e706fa763f10977b16a",
             "mergedAt": None, "isDraft": False}])
        # A context named on every call, never the active one by default.
        self.assertTrue(all(c[1:3] == ["--context", "flownextnew"] for c in fake.calls
                            if c[0] == "bkt" and c[1] != "context"))
        none, _ = self.listing("fx-nothing", bkt=[fixture("pr-branch-none")])
        self.assertEqual(none, [])

    def test_a_merged_pull_request_carries_its_merge_time_from_activity(self):
        # Bitbucket's own read of the merged PR #5 carries no closed_on.
        self.assertIsNone(json.loads(fixture("pr-view-merged")["stdout"]).get("closed_on"))
        rows, _ = self.listing("fx-merged", bkt=[fixture("pr-branch-merged"), fixture("commit-short"),
                                                fixture("pr-activity-merged")])
        self.assertEqual([(r["number"], r["state"], r["headRefOid"], r["mergedAt"]) for r in rows],
                         [(5, "MERGED", "8def284c7febe434b850a83894afa949f58c3390", "2026-11-13T10:37:52.938378+00:00")])

    def test_a_fork_pull_request_sharing_the_branch_name_is_not_the_origin_repositorys(self):
        rows, _ = self.listing("fx-open", bkt=[fixture("pr-branch-fork"), fixture("commit-open")])
        self.assertEqual([r["number"] for r in rows], [1])   # PR #7 comes from flownextnew/flownext-fork

    def test_open_listing_follows_next_and_carries_short_heads(self):
        pages = [fixture(f"pr-open-page-{n}") for n in (1, 2, 3)]
        with patch.object(f, "_BITBUCKET_PAGELEN", 2):
            rows, fake = self.listing(state="open", limit=1000, bkt=pages)
        self.assertEqual([(r["number"], r["isDraft"]) for r in rows], [(1, False), (6, False), (4, False), (2, True)])
        self.assertEqual(rows[0]["headRefOid"], "ef0162f11cc9")
        self.assertEqual(fake.api_calls(), [fx["argv"][4] for fx in pages])

    def test_the_local_clone_resolves_a_short_hash_without_a_commit_read(self):
        REAL_RUN(["git", "init", "-q"], cwd=self.repo, check=True)
        REAL_RUN(["git", "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "x"],
                 cwd=self.repo, check=True)
        sha = REAL_RUN(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout.strip()
        def local_head(page):
            for pr in page["values"]:
                pr["source"]["commit"]["hash"] = sha[:12]
        local = derived("pr-branch-reused", local_head)
        rows, fake = self.listing("fx-reused", bkt=[local])
        self.assertEqual({r["headRefOid"] for r in rows}, {sha})
        self.assertEqual(len(fake.api_calls()), 1)   # the listing only

    def test_failed_reads_are_probe_failures(self):
        def row(change):
            return derived("pr-branch-reused", lambda page: change(page["values"][1]))
        reused = branch_argv("fx-reused")
        page_two = ["bkt", "--context", "flownextnew", "api", f"{PULLS}?state=OPEN&pagelen=2&page=2"]
        cases = [
            ("bkt fails", dict(head="fx-reused", bkt=[under("pr-branch-missing-repo", reused)])),
            ("no credentials", dict(head="fx-reused", bkt=[under("api-no-credentials", reused)])),
            ("token refused", dict(head="fx-reused", bkt=[under("api-logged-out", reused)])),
            ("no Cloud context", dict(head="fx-reused", contexts="context-list-none")),
            ("bkt missing", dict(head="fx-reused", contexts="missing")),
            *((f"malformed row: {name}", dict(head="fx-reused", bkt=[row(change), fixture("commit-reused")])) for name, change in (
                ("no id", lambda pr: pr.pop("id")), ("unknown state", lambda pr: pr.update(state="WITHDRAWN")),
                ("empty link", lambda pr: pr["links"]["html"].update(href="")), ("no hash", lambda pr: pr["source"]["commit"].pop("hash")),
                ("empty branch", lambda pr: pr["source"]["branch"].update(name="")), ("list draft", lambda pr: pr.update(draft=[True])))),
            ("not a listing", dict(head="fx-reused", bkt=[derived("pr-branch-reused", lambda page: page["values"])])),
            ("empty output", dict(head="fx-reused", bkt=[{**fixture("pr-branch-reused"), "stdout": ""}])),
            ("size disagrees", dict(head="fx-reused", bkt=[derived("pr-branch-reused", lambda page: page.update(size=3)),
                                                           fixture("commit-reused")])),
            ("next page elsewhere", dict(head="fx-reused", bkt=[derived("pr-branch-reused", lambda page: page.update(next="https://example.test/2"))])),
            ("next page fails", dict(state="open", limit=1000, bkt=[fixture("pr-open-page-1"), under("pr-branch-missing-repo", page_two)])),
            ("unresolvable short hash", dict(head="fx-reused", bkt=[
                fixture("pr-branch-reused"), under("commit-unknown", ["bkt", "--context", "flownextnew", "api",
                                                                      "/repositories/flownextnew/flownext/commit/ef14a8697d98"])])),
            ("merged without a merge in its activity", dict(head="fx-merged", bkt=[
                fixture("pr-branch-merged"), fixture("commit-short"),
                derived("pr-activity-merged", lambda page: page.update(values=[v for v in page["values"] if "update" not in v]))])),
        ]
        for name, kwargs in cases:
            with self.subTest(name), patch.object(f, "_BITBUCKET_PAGELEN", 2 if "next page fails" in name else 50):
                f.repo_forge.cache_clear()
                self.assertIsNone(self.listing(**kwargs)[0])

    def test_other_reads_are_unsupported_here(self):
        fake = BktCli()
        with patch.object(f, "get_repo_root", return_value=self.repo):
            self.assertIsNone(self.run_with(fake, lambda: f.forge_readiness(self.repo, 1)))
            self.assertIsNone(self.run_with(fake, lambda: f._forge_merge_read("fx-merged")))
            self.assertEqual(self.run_with(fake, lambda: f.forge_approval_rows("fx-merged", self.repo)),
                             (None, "spec approval is unsupported on this forge (bitbucket)"))
        self.assertFalse([c for c in fake.calls if c[0] == "bkt"])


class BitbucketRouteTests(ForgeTestCase):
    def flow(self, *args):
        proc = REAL_RUN([*FLOWCTL_CMD, *args], cwd=self.repo,
                        capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def spec_on(self, branch):
        REAL_RUN(["git", "init", "-q"], cwd=self.repo, check=True)
        self.flow("init", "--json")
        sid = json.loads(self.flow("spec", "create", "--title", "PR fixture", "--json"))["id"]
        self.flow("spec", "set-branch", sid, "--branch", branch, "--json")
        self.flow("spec", "ready", sid)
        return sid

    def test_snapshot_reads_pull_requests_and_names_the_forge(self):
        sid = self.spec_on("fx-reused")
        fake = BktCli(bkt=[fixture("pr-open"), fixture("pr-branch-reused"), fixture("commit-reused")])
        with patch.object(f, "get_repo_root", return_value=self.repo), patch.object(f, "get_flow_dir", return_value=self.repo / ".flow"), patch.object(f, "_pilot_strikes_ledger_path", return_value=None):
            result = self.run_with(fake, lambda: f.pilot_snapshot(sid))
        self.assertEqual(result["forge"], "bitbucket")
        self.assertFalse(result["pr_listing_failed"])
        pr = result["selected"]["pr"]
        self.assertEqual((pr["open"]["number"], [r["number"] for r in pr["closed"]], pr["probe_failed"]), (4, [3], False))
        self.assertNotIn("readiness", pr["open"])   # no readiness read on Bitbucket yet
        self.assertEqual(result["route"]["decision"]["value"], "existing_pr_tail")

    def test_route_judge_reads_the_branch_pull_requests(self):
        body = self.repo / "spec.md"
        body.write_text("Implement feature", encoding="utf-8")
        spec_data = {"title": "Feature", "status": "open", "branch_name": "fx-merged"}
        fake = BktCli(bkt=[fixture("pr-branch-merged"), fixture("commit-short"), fixture("pr-activity-merged")])
        with patch.object(f, "get_config", return_value=True), patch.object(f, "get_repo_root", return_value=self.repo), patch.object(f, "get_flow_dir", return_value=self.repo), patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), patch.object(f, "load_json_or_exit", return_value=spec_data), patch.object(f, "normalize_epic", side_effect=lambda x: x), patch.object(f, "find_spec_md_path", return_value=body), patch.object(f.TaskInventory, "load", return_value=SimpleNamespace(by_spec={})):
            state = self.run_with(fake, lambda: f.judge_route_state({}, "fn-1-feature"))
            failed = BktCli(bkt=[under("pr-branch-missing-repo", branch_argv("fx-merged"))])
            f.repo_forge.cache_clear()
            unread = self.run_with(failed, lambda: f.judge_route_state({}, "fn-1-feature"))
        self.assertEqual((state["pr_exists"], state["pr_ref"]["number"], state["pr_ref"]["state"]), (True, 5, "MERGED"))
        self.assertIsNone(unread["pr_exists"])   # a failed read is never "no PR"


if __name__ == "__main__":
    unittest.main()

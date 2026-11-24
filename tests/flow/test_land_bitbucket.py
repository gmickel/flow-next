"""land on a Bitbucket Cloud origin: the readiness and merge-evidence reads, and the bkt
commands land's forge reference gives the agent.

bkt answers replay the live recordings in fixtures/bitbucket/ (flownextnew/flownext: pull
request 10 with a green build, approved by a second workspace user; 11 with a failed lint
check and changes requested by that user; 13 in conflict with main; 14 stacked on 10's branch;
12 squash-merged after its branch moved past the head that was read).
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from test_forge_bitbucket import BktCli, ForgeTestCase, derived, f, fixture, under

SKILLS = Path(__file__).resolve().parents[2] / "plugins" / "flow" / "skills"
REPO = "/repositories/flownextnew/flownext"
READY = "588b25c02a5b1146783bae0b703caeba417af6a4"     # pull request 10's head
CHANGES = "32568a47f92cfe6173017b8a11628b2e3c3791b6"   # pull request 11's head
JUDGED, MERGED_HEAD = "dd1a7864bc42", "25d4026aa8e65b009864e9c75a6b54629613445f"   # pull request 12


def api(path):
    return ["bkt", "--context", "flownextnew", "api", path]


def statuses_of(name, head):
    return {**fixture(name), "argv": api(f"{REPO}/commit/{head}/statuses?pagelen=100")}


class BitbucketReadinessTests(ForgeTestCase):
    def readiness(self, pr, commit, statuses, checks, number):
        fake = BktCli(bkt=[pr, commit, statuses, checks])
        return self.run_with(fake, lambda: f.forge_readiness(self.repo, number))

    def ready_pr(self, pr="land-pr-approved-fields", statuses="land-statuses-successful", checks="land-checks-clean"):
        return self.readiness(pr if isinstance(pr, dict) else fixture(pr), fixture("land-commit-ready"),
                              statuses if isinstance(statuses, dict) else statuses_of(statuses, READY),
                              checks if isinstance(checks, dict) else fixture(checks), 10)

    def test_recorded_states(self):
        got = self.ready_pr()
        self.assertEqual(got, {"head_sha": READY, "build": "SUCCESSFUL", "merge_status": "clean", "approval": "approved",
                               "squash_allowed": True, "green": True, "ready": True})
        # Before the second user approved, no review is not a blocker, as on GitHub.
        self.assertEqual(self.ready_pr("land-pr-ready-fields")["approval"], "none")
        self.assertTrue(self.ready_pr("land-pr-ready-fields")["ready"])
        changes = self.readiness(fixture("land-pr-changes-requested-fields"), fixture("land-commit-changes"),
                                 statuses_of("land-statuses-failed", CHANGES), fixture("land-checks-changes"), 11)
        self.assertEqual((changes["build"], changes["approval"], changes["green"], changes["ready"]),
                         ("FAILED", "changes_requested", False, False))

    def test_a_build_that_is_not_successful_is_not_green(self):
        for name, state in (("land-statuses-inprogress", "INPROGRESS"), ("land-statuses-none", None)):
            with self.subTest(name):
                got = self.ready_pr(statuses=name)
                self.assertEqual((got["build"], got["green"], got["ready"]), (state, False, False))
        stopped = statuses_of("land-statuses-stopped", READY)
        stopped["stdout"] = stopped["stdout"].replace("dd1a7864bc42b0a2be253a461e3067cf58e848a5", READY)
        self.assertEqual((self.ready_pr(statuses=stopped)["build"], self.ready_pr(statuses=stopped)["ready"]), ("STOPPED", False))

    def test_a_conflict_or_a_failing_merge_check_is_never_ready(self):
        conflict = {**fixture("land-checks-conflict"), "argv": fixture("land-checks-clean")["argv"]}
        got = self.ready_pr(checks=conflict)
        self.assertEqual((got["merge_status"], got["green"], got["ready"]), ("conflicts", True, False))

    def test_requested_changes_a_draft_or_no_squash_is_never_ready(self):
        cases = {
            "draft": lambda pr: pr.update(draft=True),
            "no squash": lambda pr: pr["destination"]["branch"].update(merge_strategies=["merge_commit", "fast_forward"]),
            "changes requested": lambda pr: pr["participants"][0].update(state="changes_requested", approved=False),
        }
        for name, change in cases.items():
            with self.subTest(name):
                got = self.ready_pr(derived("land-pr-approved-fields", change))
                self.assertFalse(got["ready"])
        self.assertFalse(self.ready_pr(derived("land-pr-approved-fields", cases["no squash"]))["squash_allowed"])

    def test_unreadable_is_not_green_not_approved(self):
        unread = {"head_sha": None, "build": None, "merge_status": None, "approval": "unknown",
                  "squash_allowed": None, "green": False, "ready": False}
        pr_argv = fixture("land-pr-approved-fields")["argv"]
        self.assertEqual(self.ready_pr(under("pr-branch-missing-repo", pr_argv)), unread)
        self.assertEqual(self.ready_pr(derived("land-pr-approved-fields", lambda pr: pr["destination"]["branch"].pop("merge_strategies"))), unread)
        for name, statuses, checks in (
            ("statuses fail", under("pr-branch-missing-repo", statuses_of("land-statuses-successful", READY)["argv"]), "land-checks-clean"),
            ("checks fail", "land-statuses-successful", under("pr-branch-missing-repo", fixture("land-checks-clean")["argv"])),
            ("a status for another head", {**statuses_of("land-statuses-successful", READY),
                                           "stdout": fixture("land-statuses-failed")["stdout"]}, "land-checks-clean"),
        ):
            with self.subTest(name):
                self.assertEqual(self.ready_pr(statuses=statuses, checks=checks), {**unread, "head_sha": READY})
        odd = self.ready_pr(derived("land-pr-approved-fields", lambda pr: pr["participants"][0].update(state="reviewing")))
        self.assertEqual((odd["approval"], odd["ready"]), ("unknown", False))
        no_state = self.ready_pr(derived("land-pr-approved-fields", lambda pr: [pr["participants"][0].pop("state"), None][1]))
        self.assertEqual((no_state["approval"], no_state["ready"]), ("unknown", False))
        self.assertEqual(self.ready_pr(derived("land-pr-approved-fields", lambda pr: pr.update(source="fx-ready"))), unread)

    def test_an_incomplete_merge_check_answer_is_unread(self):
        unread = {"head_sha": READY, "build": None, "merge_status": None, "approval": "unknown",
                  "squash_allowed": None, "green": False, "ready": False}
        for name, change in (
            ("truncated", lambda page: page.update(values=page["values"][:2])),
            ("empty", lambda page: page.update(values=[])),
            ("no git mergeability answer", lambda page: page.update(values=page["values"][:2], size=2)),
        ):
            with self.subTest(name):
                self.assertEqual(self.ready_pr(checks=derived("land-checks-clean", change)), unread)


class BitbucketMergeEvidenceTests(ForgeTestCase):
    def merge_read(self, *bkt):
        fake = BktCli(bkt=bkt)
        with patch.object(f, "get_repo_root", return_value=self.repo):
            return self.run_with(fake, lambda: f._forge_merge_read("fx-race"))

    EVIDENCE = ("land-branch-race", "land-commit-race", "land-activity-race", "land-diffstat-race")

    def test_a_merged_pull_request_carries_its_changed_files(self):
        rows, files = self.merge_read(*map(fixture, self.EVIDENCE))
        self.assertEqual([(r["number"], r["state"], r["headRefOid"], r["mergedAt"]) for r in rows],
                         [(12, "MERGED", MERGED_HEAD, "2026-11-13T13:30:27.276444+00:00")])
        self.assertEqual(files, {12: ["fx-race.txt"]})
        moved = derived("land-diffstat-race", lambda page: page["values"][0].update(
            status="renamed", old={"path": "docs/a.md"}, new={"path": "src/a.md"}))
        self.assertEqual(self.merge_read(*map(fixture, self.EVIDENCE[:3]), moved)[1], {12: ["docs/a.md", "src/a.md"]})

    def test_a_failed_or_malformed_file_read_fails_the_whole_read(self):
        argv = fixture("land-diffstat-race")["argv"]
        for name, diffstat in (("fails", under("pr-branch-missing-repo", argv)),
                               ("no paths", derived("land-diffstat-race", lambda page: page["values"][0].update(old=None, new=None))),
                               ("a side that is not an object", derived("land-diffstat-race", lambda page: page["values"][0].update(new="fx-race.txt"))),
                               ("an empty path", derived("land-diffstat-race", lambda page: page["values"][0].update(new={"path": ""}))),
                               ("an entry that is not an object", derived("land-diffstat-race", lambda page: page.update(values=["fx-race.txt"])))):
            with self.subTest(name):
                self.assertIsNone(self.merge_read(*map(fixture, self.EVIDENCE[:3]), diffstat))

    def test_tracker_classifies_the_forge_read(self):
        from flowctl_tracker.status import policy
        self.addCleanup(setattr, policy, "forge_merge_read", policy.forge_merge_read)
        policy.forge_merge_read = f._forge_merge_read
        spec_only = derived("land-diffstat-race", lambda page: page["values"][0].update(new={"path": ".flow/specs/fn-1.md"}))
        for want, diffstat in (("merged", fixture("land-diffstat-race")), ("none", spec_only),
                               ("probe-error", under("pr-branch-missing-repo", fixture("land-diffstat-race")["argv"]))):
            with self.subTest(want):
                f.repo_forge.cache_clear()
                fake = BktCli(bkt=[*map(fixture, self.EVIDENCE[:3]), diffstat])
                with patch.object(f, "get_repo_root", return_value=self.repo):
                    got = self.run_with(fake, lambda: policy.merge_evidence({}, {"branch_name": "fx-race"}, None))
                self.assertEqual(got, want)


class BitbucketWaitAndMergeTests(ForgeTestCase):
    def _clock(self):
        from test_forge import _FakeClock
        return _FakeClock()

    def test_wait_ready_changes_requested_conflict_and_merged(self):
        clock = self._clock()
        fake = BktCli(bkt=[fixture("land-pr-approved-fields"), fixture("land-commit-ready"),
                           statuses_of("land-statuses-successful", READY), fixture("land-checks-clean")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 10, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual((got["state"], got["head_sha"], clock.sleeps), ("ready", READY, []))

        s_ok = {**statuses_of("land-statuses-successful", CHANGES),
                "stdout": fixture("land-statuses-successful")["stdout"].replace(READY, CHANGES)}
        fake_cr = BktCli(bkt=[fixture("land-pr-changes-requested-fields"), fixture("land-commit-changes"),
                              s_ok, fixture("land-checks-changes")])
        got_cr = self.run_with(fake_cr, lambda: f.forge_wait(
            self.repo, 11, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got_cr["state"], "changes_requested")

        conflict = {**fixture("land-checks-conflict"), "argv": fixture("land-checks-clean")["argv"]}
        fake_cf = BktCli(bkt=[fixture("land-pr-approved-fields"), fixture("land-commit-ready"),
                              statuses_of("land-statuses-successful", READY), conflict])
        self.assertEqual(self.run_with(fake_cf, lambda: f.forge_wait(
            self.repo, 10, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))["state"], "blocked")

        merged_pr = {**fixture("land-pr-race-merged"),
                     "argv": api(f"{REPO}/pullrequests/12?fields=%2Bdestination.branch.merge_strategies")}
        fake_m = BktCli(bkt=[merged_pr])
        got_m = self.run_with(fake_m, lambda: f.forge_wait(
            self.repo, 12, timeout_s=60, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got_m["state"], "merged")

    def test_wait_failed_check_returns_at_once(self):
        clock = self._clock()
        fake = BktCli(bkt=[fixture("land-pr-changes-requested-fields"), fixture("land-commit-changes"),
                           statuses_of("land-statuses-failed", CHANGES), fixture("land-checks-changes")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 11, timeout_s=120, interval_s=15, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got["state"], "failing")
        self.assertEqual(got["failing_checks"], ["fixture lint"])
        self.assertEqual(clock.sleeps, [])

    def test_wait_running_build_honours_deadline(self):
        clock = self._clock()
        fake = BktCli(bkt=[fixture("land-pr-approved-fields"), fixture("land-commit-ready"),
                           statuses_of("land-statuses-inprogress", READY), fixture("land-checks-clean")])
        got = self.run_with(fake, lambda: f.forge_wait(
            self.repo, 10, timeout_s=20, interval_s=10, monotonic=clock.monotonic, sleep=clock.sleep))
        self.assertEqual(got["state"], "pending")
        self.assertEqual(got["running_checks"], ["fixture CI"])
        self.assertIn("deadline reached", got["reason"])
        self.assertEqual(clock.sleeps, [10.0, 10.0])

    def test_merge_succeeds_and_detects_race_window(self):
        merge_post_10 = {
            **fixture("land-merge-race"),
            "argv": ["bkt", "--context", "flownextnew", "api", f"{REPO}/pullrequests/10/merge",
                     "-X", "POST", "-d", '{"merge_strategy":"squash","close_source_branch":true}'],
        }
        def _merged_10(pr):
            pr["source"]["commit"]["hash"] = READY[:12]
            pr["merge_commit"]["hash"] = "999999999999"

        after_10 = derived("land-pr-race-merged", _merged_10, argv=api(f"{REPO}/pullrequests/10"))
        fake = BktCli(bkt=[fixture("land-pr-ready"), fixture("land-commit-ready"), merge_post_10, after_10])
        got = self.run_with(fake, lambda: f.forge_merge(self.repo, 10, READY))
        self.assertEqual(got, {"merged": True, "merge_commit": "999999999999",
                               "reason": "merged", "message": "squash merged"})

        # Race during POST: pre-check saw JUDGED head, post-merge read reveals Bitbucket merged MERGED_HEAD.
        judged_full = "dd1a7864bc42b0a2be253a461e3067cf58e848a5"

        def _before_12(pr):
            pr["id"] = 12
            pr["source"]["commit"]["hash"] = JUDGED

        before_12 = derived("land-pr-ready", _before_12, argv=api(f"{REPO}/pullrequests/12"))
        commit_judged = derived("land-commit-ready", lambda c: c.update(hash=judged_full),
                                argv=api(f"{REPO}/commit/{JUDGED}"))
        merge_post_12 = {
            **fixture("land-merge-race"),
            "argv": ["bkt", "--context", "flownextnew", "api", f"{REPO}/pullrequests/12/merge",
                     "-X", "POST", "-d", '{"merge_strategy":"squash","close_source_branch":true}'],
        }
        fake_race = BktCli(bkt=[before_12, commit_judged, merge_post_12, fixture("land-pr-race-merged")])
        got_race = self.run_with(fake_race, lambda: f.forge_merge(self.repo, 12, judged_full))
        self.assertEqual((got_race["merged"], got_race["reason"], got_race["merge_commit"]),
                         (True, "merged_head_moved", "46b4f5f81b9b"))
        self.assertIn(JUDGED, got_race["message"])
        self.assertIn(MERGED_HEAD[:12], got_race["message"])

    def test_merge_refuses_moved_head_before_post(self):
        fake = BktCli(bkt=[fixture("land-pr-ready"), fixture("land-commit-ready")])
        got = self.run_with(fake, lambda: f.forge_merge(self.repo, 10, "e" * 40))
        self.assertEqual((got["merged"], got["reason"]), (False, "head_moved"))
        self.assertFalse(any("merge" in " ".join(c) for c in fake.calls))

    def _merge_post_10(self, **overrides):
        return {
            **fixture("land-merge-race"),
            "argv": ["bkt", "--context", "flownextnew", "api", f"{REPO}/pullrequests/10/merge",
                     "-X", "POST", "-d", '{"merge_strategy":"squash","close_source_branch":true}'],
            **overrides,
        }

    def _merged_10(self):
        def _edit(pr):
            pr["source"]["commit"]["hash"] = READY[:12]
            pr["merge_commit"]["hash"] = "999999999999"
        return derived("land-pr-race-merged", _edit, argv=api(f"{REPO}/pullrequests/10"))

    def test_merge_retries_confirming_read_after_exit_zero(self):
        pr_argv = api(f"{REPO}/pullrequests/10")
        post = self._merge_post_10()
        merged = self._merged_10()
        read_fail = under("pr-branch-missing-repo", pr_argv)
        still_open = fixture("land-pr-ready")

        for label, first_after in (("read error", read_fail), ("still open", still_open)):
            with self.subTest(label):
                clock = self._clock()
                fake = BktCli(bkt=[fixture("land-pr-ready"), fixture("land-commit-ready"),
                                   post, first_after, merged])
                got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 10, READY, sleep=c.sleep))
                self.assertEqual(got, {"merged": True, "merge_commit": "999999999999",
                                       "reason": "merged", "message": "squash merged"})
                self.assertEqual(len([c for c in fake.calls if c == post["argv"]]), 1)
                self.assertEqual(len([c for c in fake.calls if c == pr_argv]), 3)  # 1 pre-check + 2 confirming reads
                self.assertEqual(clock.sleeps, [f._MERGE_CONFIRM_INTERVAL_S])

    def test_merge_returns_unconfirmed_when_confirming_reads_never_succeed(self):
        pr_argv = api(f"{REPO}/pullrequests/10")
        post = self._merge_post_10()
        read_fail = under("pr-branch-missing-repo", pr_argv)
        still_open = fixture("land-pr-ready")
        expected_reads = 1 + f._MERGE_CONFIRM_RETRIES
        expected_sleeps = [f._MERGE_CONFIRM_INTERVAL_S] * f._MERGE_CONFIRM_RETRIES

        for label, bad_after in (("read errors", read_fail), ("still open", still_open)):
            with self.subTest(label):
                clock = self._clock()
                fake = BktCli(bkt=[fixture("land-pr-ready"), fixture("land-commit-ready"),
                                   post, *([bad_after] * expected_reads)])
                got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 10, READY, sleep=c.sleep))
                self.assertEqual((got["merged"], got["reason"], got["merge_commit"]), (False, "unconfirmed", None))
                self.assertIn("merge command succeeded", got["message"])
                self.assertIn("could not be confirmed", got["message"])
                self.assertEqual(len([c for c in fake.calls if c == post["argv"]]), 1)
                self.assertEqual(len([c for c in fake.calls if c == pr_argv]), 1 + expected_reads)
                self.assertEqual(clock.sleeps, expected_sleeps)

    def test_merge_refused_behaves_as_before(self):
        pr_argv = api(f"{REPO}/pullrequests/10")
        refused = self._merge_post_10(returncode=1, stdout="", stderr="merge refused by branch restriction")
        clock = self._clock()
        fake = BktCli(bkt=[fixture("land-pr-ready"), fixture("land-commit-ready"), refused])
        got = self.run_with(fake, lambda c=clock: f.forge_merge(self.repo, 10, READY, sleep=c.sleep))
        self.assertEqual((got["merged"], got["reason"]), (False, "not_mergeable"))
        self.assertEqual(len([c for c in fake.calls if c == refused["argv"]]), 1)
        self.assertEqual(len([c for c in fake.calls if c == pr_argv]), 1)  # pre-check only
        self.assertEqual(clock.sleeps, [])


if __name__ == "__main__":
    unittest.main()

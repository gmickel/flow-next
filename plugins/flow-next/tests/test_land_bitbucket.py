"""land on a Bitbucket Cloud origin: the readiness and merge-evidence reads, and the bkt
commands land's forge reference gives the agent.

bkt answers replay the live recordings in fixtures/bitbucket/ (flownextnew/flownext: pull
request 10 with a green build, approved by a second workspace user; 11 with a failed lint
check and changes requested by that user; 13 in conflict with main; 14 stacked on 10's branch;
12 squash-merged after its branch moved past the head that was read).
"""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from test_forge_bitbucket import BktCli, ForgeTestCase, derived, f, fixture, under
from test_make_pr_bitbucket import BitbucketShellCase, answers, recorded

SKILLS = Path(__file__).resolve().parent.parent / "skills"
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
                               ("no paths", derived("land-diffstat-race", lambda page: page["values"][0].update(old=None, new=None)))):
            with self.subTest(name):
                self.assertIsNone(self.merge_read(*map(fixture, self.EVIDENCE[:3]), diffstat))

    def test_tracker_classifies_the_forge_read(self):
        from flowctl_tracker.status import policy
        self.addCleanup(setattr, policy, "forge_merge_read", policy.forge_merge_read)
        self.assertIs(f._import_tracker_status().policy.forge_merge_read, f._forge_merge_read)
        spec_only = derived("land-diffstat-race", lambda page: page["values"][0].update(new={"path": ".flow/specs/fn-1.md"}))
        for want, diffstat in (("merged", fixture("land-diffstat-race")), ("none", spec_only),
                               ("probe-error", under("pr-branch-missing-repo", fixture("land-diffstat-race")["argv"]))):
            with self.subTest(want):
                f.repo_forge.cache_clear()
                fake = BktCli(bkt=[*map(fixture, self.EVIDENCE[:3]), diffstat])
                with patch.object(f, "get_repo_root", return_value=self.repo):
                    got = self.run_with(fake, lambda: policy.merge_evidence({}, {"branch_name": "fx-race"}, None))
                self.assertEqual(got, want)


REFERENCE = re.sub(r"\s*\n\s*", " ", (SKILLS / "flow-next-land" / "forge-bitbucket.md").read_text(encoding="utf-8"))
COMMANDS = re.findall(r"`(bkt --context \"\$BKT_CONTEXT\" api [^`]+)`", REFERENCE)


class LandReferenceTests(BitbucketShellCase):
    RECORDINGS = ("land-pr-ready", "land-commit-ready-full", "land-children", "land-merge-race", "land-pr-race-merged")

    def run_command(self, command, pr="10", head=READY, branch="fx-ready", **env):
        repo = self.repo_on("main", "git@ssh.bitbucket.org:flownextnew/flownext.git")
        setup = re.search(r"```bash\n(.*?)```", (SKILLS / "flow-next-land" / "forge-bitbucket.md").read_text(encoding="utf-8"), re.S).group(1)
        statuses = recorded("land-statuses-successful")
        return self.run_sh(["bash", "-c", f"set -o pipefail; {setup}\n{command}"], cwd=repo, PR=pr, HEAD_SHA=head, BRANCH=branch,
                           BKT_ANSWERS=answers(*map(recorded, self.RECORDINGS), statuses), **env)

    def command(self, needle):
        found = [c for c in COMMANDS if needle in c]
        self.assertEqual(len(found), 1, (needle, COMMANDS))
        return found[0]

    def test_every_bkt_command_is_recorded(self):
        self.assertEqual(len(COMMANDS), 5, COMMANDS)
        for command in COMMANDS:
            with self.subTest(command):
                pr = "12" if "/merge" in command else "10"
                result = self.run_command(command, pr=pr)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.strip())

    def test_the_answers_land_reads(self):
        pr = json.loads(self.run_command(self.command('pullrequests/$PR"')).stdout)
        self.assertEqual((pr["state"], pr["source"]["branch"]["name"], pr["source"]["repository"]["full_name"]),
                         ("OPEN", "fx-ready", "flownextnew/flownext"))
        children = json.loads(self.run_command(self.command("destination.branch.name")).stdout)
        self.assertEqual([(c["id"], c["state"], c["destination"]["branch"]["name"]) for c in children["values"]], [(15, "OPEN", "fx-ready")])
        self.assertTrue(json.loads(self.run_command(self.command("/commit/$HEAD_SHA\"")).stdout)["date"])
        statuses = json.loads(self.run_command(self.command("/statuses")).stdout)
        self.assertEqual([s["state"] for s in statuses["values"]], ["SUCCESSFUL"])

    def test_the_merge_squashes_and_the_read_after_it_shows_the_head_it_took(self):
        merge = self.command("/merge")
        self.assertIn('"merge_strategy":"squash"', merge)
        self.assertNotIn("sha", merge)
        merged = json.loads(self.run_command(merge, pr="12").stdout)
        self.assertEqual(merged["state"], "MERGED")
        # Bitbucket ignored the expected head it was sent and merged the branch's moved head (recorded).
        sent = json.loads(json.loads(recorded("land-merge-race").read_text(encoding="utf-8"))["argv"][-1])
        self.assertEqual(sent["sha"], JUDGED)
        after = json.loads(self.run_command(self.command('pullrequests/$PR"'), pr="12").stdout)
        self.assertEqual((after["state"], after["source"]["commit"]["hash"]), ("MERGED", MERGED_HEAD[:12]))
        self.assertFalse(MERGED_HEAD.startswith(JUDGED), "the merged head is not the one that was read")
        self.assertTrue(after["merge_commit"]["hash"])

    def test_no_cloud_context_leaves_the_context_empty(self):
        setup = re.search(r"```bash\n(.*?)```", (SKILLS / "flow-next-land" / "forge-bitbucket.md").read_text(encoding="utf-8"), re.S).group(1)
        repo = self.repo_on("main", "https://bitbucket.org/flownextnew/flownext.git")
        result = self.run_sh(["bash", "-c", f'{setup}\nprintf "%s|%s" "$BKT_CONTEXT" "$REPO"'], cwd=repo, BKT_CONTEXTS="context-list-none")
        self.assertEqual(result.stdout, "|flownextnew/flownext")


if __name__ == "__main__":
    unittest.main()

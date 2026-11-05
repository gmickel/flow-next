"""land on a GitLab origin: the glab commands its forge reference gives the agent.

glab answers replay the live recordings in fixtures/gitlab/ (merge request !14 of the
self-managed test project on the Ultimate trial: approved by a second user, then merged
with squash; !15's failed pipeline for the job reads).
"""
import json
import re
import unittest
from pathlib import Path

from test_make_pr_gitlab import GitLabShellCase, answers, recorded

TESTS = Path(__file__).resolve().parent
SKILLS = TESTS.parent / "skills"
REFERENCE = re.sub(r"\s*\n\s*", " ", (SKILLS / "flow-next-land" / "forge-gitlab.md").read_text(encoding="utf-8"))
COMMANDS = re.findall(r"`(glab api [^`]+)`", REFERENCE)   # land runs only glab api
HEAD = "d8b76161301680f873478db85eff419251735916"   # !14's head when it merged
MOVED = "fb633aff58843b154b078ff30eb6cc6df040deeb"  # a head the branch no longer has


class LandReferenceTests(GitLabShellCase):
    RECORDINGS = ("land-mr-open", "land-mr-merged", "land-mr-children", "land-mr-children-stacked",
                  "land-failed-jobs", "land-job-trace", "land-merge-moved-head", "land-merge")

    def run_command(self, command, head=HEAD, branch="fn317-fail"):
        return self.run_sh(["bash", "-c", f"set -o pipefail; {command}"], MR="14", HEAD_SHA=head,
                           BRANCH=branch, PIPELINE_ID="16", JOB_ID="17",
                           GLAB_ANSWERS=answers(*map(recorded, self.RECORDINGS)))

    def command(self, prefix):
        found = [c for c in COMMANDS if c.startswith(prefix)]
        self.assertEqual(len(found), 1, (prefix, COMMANDS))
        return found[0]

    def test_every_glab_command_is_recorded(self):
        self.assertEqual(len(COMMANDS), 5, COMMANDS)
        for command in COMMANDS:
            with self.subTest(command):
                result = self.run_command(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.strip())

    def test_the_answers_land_reads(self):
        read = self.command('glab api "projects/:id/merge_requests/$MR"')
        opened = json.loads(self.run_command(read).stdout)
        self.assertEqual((opened["state"], opened["sha"], opened["source_branch"]), ("opened", HEAD, "fn317-ready"))
        children = self.command('glab api -X GET "projects/:id/merge_requests"')
        self.assertEqual(json.loads(self.run_command(children).stdout), [], "no stacked child")
        # The branch goes as a field, so glab encodes it: `+` in the URL would read as a space
        # and miss the child (measured: 0 rows from the URL form, !20 from the field).
        stacked = json.loads(self.run_command(children, branch="fn317-stack+a").stdout)
        self.assertEqual([(mr["iid"], mr["target_branch"]) for mr in stacked], [(20, "fn317-stack+a")])
        jobs = json.loads(self.run_command(self.command('glab api "projects/:id/pipelines/')).stdout)
        self.assertEqual([(j["id"], j["status"]) for j in jobs], [(17, "failed")])
        self.assertIn("exit 1", self.run_command(self.command('glab api "projects/:id/jobs/')).stdout)

    def test_merge_pins_the_head_and_squashes(self):
        merge = self.command("glab api -X PUT")
        self.assertIn("squash=true", merge)
        moved = self.run_command(merge, head=MOVED)
        self.assertEqual(moved.returncode, 1)
        self.assertIn("SHA does not match HEAD of source branch", moved.stderr)
        self.assertIn("HTTP 409", moved.stderr)
        merged = self.run_command(merge)
        self.assertEqual(merged.returncode, 0, merged.stderr)
        self.assertEqual(json.loads(merged.stdout)["state"], "merged")
        # The read after the merge confirms it and names the merge commit.
        read = self.command('glab api "projects/:id/merge_requests/$MR"')
        result = self.run_sh(["bash", "-c", f"{read} >/dev/null; {read} | jq -r '.state, (.merge_commit_sha // .squash_commit_sha)'"],
                             MR="14", GLAB_ANSWERS=answers(recorded("land-mr-open"), recorded("land-mr-merged")))
        self.assertEqual(result.stdout.split(), ["merged", "79b0bb356d6d477669ca7ec5466368cf0b588663"])


class LandForgePickTests(unittest.TestCase):
    def test_land_picks_the_forge_with_resolve_pr_tested_lines(self):
        """resolve-pr's ForgePickTests run these lines; land must not drift from them."""
        def lines(skill):
            text = (SKILLS / skill / "workflow.md").read_text(encoding="utf-8")
            return [line for line in text.splitlines() if line.startswith("FORGE=")]
        self.assertEqual(len(lines("flow-next-land")), 2)
        self.assertEqual(lines("flow-next-land"), lines("flow-next-resolve-pr"))


if __name__ == "__main__":
    unittest.main()

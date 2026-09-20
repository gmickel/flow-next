"""R4-R9 land contracts: distinctive headings, reason tokens and API fields.

The host executes prose; these tests do not simulate an agent or reimplement
merge decisions. Removed shell-fence fixtures tested machinery retired by R9.
"""
from pathlib import Path
import unittest

LAND = Path(__file__).resolve().parents[1] / "skills" / "flow-next-land"


class NamedPullRequestContractTest(unittest.TestCase):
    def section(self, heading):
        text = (LAND / "workflow.md").read_text()
        marker = "## " + heading
        self.assertIn(marker, text)
        return text.split(marker, 1)[1].split("\n## ", 1)[0]

    def read_contract(self):
        return self.section("Read the named pull request")

    def test_r4_head_identity(self):
        text = self.read_contract()
        for token in ("headRefOid", "headRefName", "branch_name", "closed"):
            self.assertIn(token, text)

    def test_r4_no_pull_request(self):
        self.assertIn("no pull request", self.read_contract())

    def test_r4_closed_unmerged(self):
        self.assertIn("closed unmerged", self.read_contract())

    def test_r4_already_merged(self):
        self.assertIn("already merged", self.read_contract())

    def test_r4_no_matching_spec(self):
        self.assertIn("no matching spec", self.read_contract())

    def test_r4_open_spec(self):
        self.assertIn("work not finished", self.read_contract())

    def test_r4_multiple_specs(self):
        text = self.read_contract()
        for token in ("branch_name", "headRefName", "status: done", "work not finished"):
            self.assertIn(token, text)

    def test_r5_repair_contract(self):
        text = self.section("Resolve conflicts, threads, then CI")
        for token in ("mode:autonomous", "update-branch", "--failed"):
            self.assertIn(token, text)

    def test_r5_refused_catch_up(self):
        self.assertIn("refused", self.section("Resolve conflicts, threads, then CI"))

    def test_r5_failed_ci_fix(self):
        self.assertIn("failing check", self.section("Resolve conflicts, threads, then CI"))

    def test_r5_identical_second_failure(self):
        self.assertIn("identical", self.section("Resolve conflicts, threads, then CI"))

    def test_r6_merge_gates(self):
        text = self.section("Authorize and gate the merge")
        for token in ("reviewDecision", "mergeVerdictCommand", "patienceMinutes", "merge-ready"):
            self.assertIn(token, text)

    def test_r6_head_moved(self):
        text = self.section("Merge one layer")
        for token in ("--match-head-commit", "sha=<full-head-sha>", "re-read", "RESOLVING"):
            self.assertIn(token, text)

    def test_r6_shortened_head_rejected(self):
        text = self.section("Merge one layer")
        for token in ("shortened", "invalid", "<full-head-sha>"):
            self.assertIn(token, text)

    def test_r6_missing_verdict_command(self):
        self.assertIn("missing", self.section("Authorize and gate the merge"))

    def test_r6_unexecutable_verdict_command(self):
        self.assertIn("unexecutable", self.section("Authorize and gate the merge"))

    def test_r6_timed_out_verdict_command(self):
        self.assertIn("timed-out", self.section("Authorize and gate the merge"))

    def test_r7_native_stack(self):
        text = self.section("Merge one layer")
        for token in ("merge-async", "--match-head-commit", "--squash"):
            self.assertIn(token, text)

    def test_r7_unavailable_stacks(self):
        text = self.section("Merge one layer")
        for token in ("unavailable", "child", "rebase"):
            self.assertIn(token, text)

    def test_r7_nonlowest_layer(self):
        self.assertIn("lowest", self.section("Merge one layer"))

    def test_r8_postmerge(self):
        self.assertIn("LAND_VERDICT", self.section("After confirmed merge"))

    def test_r8_touchpoint_failure(self):
        text = self.section("After confirmed merge")
        for token in ("failure", "MERGED", "merge-commit-sha"):
            self.assertIn(token, text)

    def test_r8_merged_rerun(self):
        self.assertIn("touchpoint", self.read_contract())

    def test_r9_removed_references(self):
        self.assertFalse(list((LAND / "references").glob("*.md")))

    def test_r9_ignored_key_notice(self):
        text = self.read_contract()
        self.assertIn("ignored", text)
        self.assertIn("notice", text)


if __name__ == "__main__":
    unittest.main()

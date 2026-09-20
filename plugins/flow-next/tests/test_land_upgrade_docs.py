"""R11 migration discoverability and retired-key inventory, not prose pins."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "plugins/flow-next/docs"
# Unit 3 removed these schema/default leaves. Merge identity used an environment variable.
RETIRED = {
    "release", "reviewSignal", "automatedReviewers", "reviewTrigger",
    "cleanReviewCommentPattern", "ciFixBudget", "requestReviewers",
    "patienceMinutesAfterReview",
}


class LandUpgradeDocsTest(unittest.TestCase):
    def test_r11_upgrade_contract(self):
        reference = (DOCS / "flowctl.md").read_text(encoding="utf-8")
        upgrade = reference.split("## Landing upgrade", 1)[1].split("\n## ", 1)[0]
        for heading in ("### Repository-wide recipe", "### Review gate",
                        "### Retired keys", "### Retired behaviors"):
            self.assertIn(heading, upgrade)
        rows = [line for line in upgrade.splitlines() if line.startswith("| `land.")]
        documented = set()
        for row in rows:
            documented.update(re.findall(r"`land\.([A-Za-z]+)`", row))
            self.assertRegex(row, r"#\d+")
        self.assertEqual(documented, RETIRED)
        for token in ("headRefOid", "headRefName", "branch_name", "status", "done",
                      "AGENTS.md", "branch protection", "land.mergeVerdictCommand"):
            self.assertIn(token, upgrade)
        recovery = (DOCS / "troubleshooting.md").read_text(encoding="utf-8")
        for token in ("rebase --onto", "--force-with-lease", "gh pr edit"):
            self.assertIn(token, recovery)
        unreleased = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").split("## Unreleased", 1)[1].split("\n## ", 1)[0]
        self.assertIn("major", unreleased)
        self.assertIn("#landing-upgrade", unreleased)
        for key in RETIRED:
            self.assertIn("land." + key, unreleased)


if __name__ == "__main__":
    unittest.main()

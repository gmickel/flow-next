"""`flowctl features status` - the feature map's seed/maintain facts (fn-262).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_features_status -q

Covers spec fn-262 R1 (last-proven line: proven / never proven / malformed
read as absent) and R5 (due when an open drift note exists or a feature's
last proof is at least `features.staleAfterCommits` surface-touching commits
old; memory disabled leaves the age condition alone).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD, MemoryRepoTemplate


def _flowctl(cwd: Path, *args: str) -> dict[str, Any]:
    proc = subprocess.run(
        [*FLOWCTL_CMD, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != 0:
        raise AssertionError(f"rc={proc.returncode}: {proc.stdout} {proc.stderr}")
    return json.loads(proc.stdout) if "--json" in args else {"_stdout": proc.stdout}


def _feature(surface_block: str) -> str:
    return (
        "# Checkout\n\nA user pays for the cart.\n\n"
        f"{surface_block}\n\n## Sub-features\n\n- `checkout.pay` - pay\n"
    )


class FeaturesStatus(MemoryRepoTemplate, unittest.TestCase):
    TEMPLATE_GIT = True

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.init_repo(self.repo)
        self.commit("app/main.py", "print(1)\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *argv: str) -> str:
        return subprocess.run(
            ["git", *argv], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit(self, rel: str, body: str) -> str:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"touch {rel}")
        return self.git("rev-parse", "--short", "HEAD")

    def write_feature(self, name: str, surface_block: str) -> None:
        features = self.repo / ".flow" / "features"
        features.mkdir(parents=True, exist_ok=True)
        (features / "README.md").write_text("# Feature map\n", encoding="utf-8")
        (features / name).write_text(_feature(surface_block), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        return _flowctl(self.repo, "features", "status", "--json")

    def rows(self) -> dict[str, dict[str, Any]]:
        return {row["file"]: row for row in self.status()["features"]}

    def test_no_map_recommends_seed(self) -> None:
        result = self.status()
        self.assertFalse(result["map_exists"])
        self.assertEqual(result["recommendation"], "seed")
        self.assertFalse(result["due"])

    def test_last_proven_line_states(self) -> None:
        head = self.git("rev-parse", "--short", "HEAD")
        cases = {
            "proven.md": ("**Surface:** web\n**Last proven:** 2026-09-01 at " + head, "proven"),
            "blank-between.md": (
                "**Surface:** web\n\n**Last proven:** 2026-09-01 at " + head, "proven"),
            "absent.md": ("**Surface:** web", "never-proven"),
            "bad-date.md": ("**Surface:** web\n**Last proven:** 2026-13-01 at " + head, "malformed"),
            "bad-commit.md": ("**Surface:** web\n**Last proven:** 2026-09-01 at HEAD", "malformed"),
            "trailing.md": (
                "**Surface:** web\n**Last proven:** 2026-09-01 at " + head + " by qa", "malformed"),
            "not-under-surface.md": (
                "**Surface:** web\nSome text.\n**Last proven:** 2026-09-01 at " + head, "malformed"),
            "twice.md": (
                "**Surface:** web\n**Last proven:** 2026-09-01 at " + head
                + "\n**Last proven:** 2026-09-02 at " + head, "malformed"),
        }
        for name, (block, _state) in cases.items():
            self.write_feature(name, block)
        rows = self.rows()
        for name, (_block, state) in cases.items():
            with self.subTest(name):
                self.assertEqual(rows[name]["state"], state)
                # Never proven and malformed both read as absent: stale.
                self.assertEqual(rows[name]["stale"], state != "proven")
        result = self.status()
        self.assertEqual(result["recommendation"], "maintain")
        self.assertTrue(any("malformed" in r and "bad-date.md" in r for r in result["reasons"]))

    def test_age_counts_only_surface_touching_commits(self) -> None:
        _flowctl(self.repo, "config", "set", "features.staleAfterCommits", "2", "--json")
        proven_at = self.git("rev-parse", "--short", "HEAD")
        self.write_feature("checkout.md", "**Surface:** web\n**Last proven:** 2026-09-01 at " + proven_at)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "map")
        self.commit("docs/guide.md", "docs only\n")
        self.commit("app/main.py", "print(2)\n")
        row = self.rows()["checkout.md"]
        self.assertEqual((row["measured_from"], row["commits_since"], row["stale"]), ("commit", 1, False))
        self.assertEqual(self.status()["recommendation"], "none")
        self.commit("app/main.py", "print(3)\n")
        row = self.rows()["checkout.md"]
        self.assertEqual((row["commits_since"], row["stale"]), (2, True))
        self.assertEqual(self.status()["recommendation"], "maintain")

    def test_unreachable_commit_measures_from_date(self) -> None:
        self.write_feature("checkout.md", "**Surface:** web\n**Last proven:** 2000-01-01 at deadbee")
        row = self.rows()["checkout.md"]
        self.assertEqual(row["measured_from"], "date")
        self.assertGreaterEqual(row["commits_since"], 1)

    def test_open_drift_note_makes_map_due_and_stale_note_does_not(self) -> None:
        head = self.git("rev-parse", "--short", "HEAD")
        self.write_feature("checkout.md", "**Surface:** web\n**Last proven:** 2026-09-01 at " + head)
        body = self.repo / "drift.md"
        body.write_text("Expected: Settings\nObserved: Preferences\n", encoding="utf-8")
        added = _flowctl(
            self.repo, "memory", "upsert", "--track", "knowledge", "--category", "workflow",
            "--title", "drift: web/checkout checkout.pay", "--tags", "feature-map-drift",
            "--body-file", str(body), "--json",
        )
        result = self.status()
        self.assertEqual([d["title"] for d in result["open_drift"]], ["drift: web/checkout checkout.pay"])
        self.assertEqual(result["recommendation"], "maintain")
        _flowctl(self.repo, "memory", "mark-stale", added["entry_id"], "--reason", "re-proven", "--json")
        result = self.status()
        self.assertEqual(result["open_drift"], [])
        self.assertEqual(result["recommendation"], "none")

    def test_memory_disabled_leaves_age_condition_alone(self) -> None:
        _flowctl(self.repo, "config", "set", "memory.enabled", "false", "--json")
        self.write_feature("checkout.md", "**Surface:** web")
        result = self.status()
        self.assertIsNone(result["open_drift"])
        self.assertEqual(result["recommendation"], "maintain")
        self.assertEqual(result["reasons"], ["checkout.md: never proven"])


if __name__ == "__main__":
    unittest.main()

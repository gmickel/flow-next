import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "optimization/reached-path/run_claude_fleet_smoke.py"
ORACLES = ROOT / "optimization/reached-path/claude_fleet_oracles.py"
SPEC = importlib.util.spec_from_file_location("fn130_claude_fleet", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ClaudeFleetSmokeHarnessTests(unittest.TestCase):
    @staticmethod
    def harness_source():
        return SCRIPT.read_text() + ORACLES.read_text()

    def test_case_roster_covers_every_optimized_user_workflow(self):
        self.assertEqual(
            MODULE.CASES,
            (
                "setup",
                "tracker-sync",
                "prime",
                "plan",
                "plan-review",
                "work",
                "strategy",
                "make-pr",
                "pilot",
            ),
        )

    def test_scrub_removes_repo_plugin_home_and_tmp_paths(self):
        repo = Path("/tmp/fleet/repo")
        plugin = Path("/tmp/fleet/plugin")
        raw = f"{repo} {plugin} {Path.home()} {MODULE.tempfile.gettempdir()}"
        scrubbed = MODULE.scrub(raw, repo=repo, plugin=plugin)
        self.assertNotIn(str(repo), scrubbed)
        self.assertNotIn(str(plugin), scrubbed)
        self.assertNotIn(str(Path.home()), scrubbed)
        self.assertIn("<fixture-repo>", scrubbed)
        self.assertIn("<plugin-root>", scrubbed)

    def test_emitted_contract_requires_real_skill_and_nonzero_usage(self):
        source = self.harness_source()
        self.assertIn('f"flow-next:flow-next-{case}"', source)
        self.assertIn('f"flow-next:{case}"', source)
        for required in (
            '"skill_invoked"',
            '"nonzero_usage"',
            '"single_inline_flow_plugin"',
            '"flow_reads_from_expected_root"',
            '"claude_exit_zero"',
        ):
            self.assertIn(required, source)
        self.assertIn('"assistant_text"', source)
        self.assertIn('"version drift"', source)

    def test_external_writes_are_guarded(self):
        source = self.harness_source()
        self.assertIn("--dry-run --base main --no-mermaid", source)
        self.assertIn('"no_live_pr_create"', source)
        self.assertIn("strict_empty_mcp", source)
        self.assertIn("no_tracker_receipt_write", source)
        self.assertIn('"configuration_reached"', source)
        self.assertIn('if case == "plan-review":', source)
        self.assertIn("instead of ~/Desktop", source)
        self.assertIn("do not open a GUI application", source)

    def test_b1_is_materialized_from_immutable_commit(self):
        self.assertEqual(MODULE.B1, "8ed71a73ccc593a8a018dcdb805a86f396dcf76f")
        self.assertIn('"git", "archive"', SCRIPT.read_text())

    def test_partial_failures_are_retained(self):
        source = SCRIPT.read_text()
        self.assertIn('"harness_completed": False', source)
        self.assertIn("except Exception as exc:", source)

    def test_partial_reruns_merge_without_hiding_baseline_misses(self):
        source = SCRIPT.read_text()
        self.assertIn("--merge-existing", source)
        self.assertIn("replaced_ids", source)
        self.assertIn('"promotion_pass"', source)
        self.assertIn(
            '"all candidate workflows pass; B1 misses remain visible"', source
        )


if __name__ == "__main__":
    unittest.main()

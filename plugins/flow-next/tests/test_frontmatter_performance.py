"""Shared-envelope and cached optional-YAML contract tests."""

import builtins
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


class TestFrontmatterEnvelope(unittest.TestCase):
    def test_absent_incomplete_and_complete_are_distinct(self) -> None:
        absent = flowctl._frontmatter_envelope("# body\n")
        self.assertEqual((absent.present, absent.complete, absent.body), (False, False, "# body\n"))
        incomplete = flowctl._frontmatter_envelope("---\nname: x\n")
        self.assertEqual((incomplete.present, incomplete.complete), (True, False))
        self.assertEqual(incomplete.body, "---\nname: x\n")
        complete = flowctl._frontmatter_envelope("---\nname: x\n---\nbody\n")
        self.assertTrue(complete.complete)
        self.assertEqual(complete.frontmatter, "\nname: x\n")
        self.assertEqual(complete.body, "\nbody\n")

    def test_optional_yaml_selection_is_cached_once(self) -> None:
        previous = flowctl._YAML_PARSER
        flowctl._YAML_PARSER = flowctl._YAML_PARSER_UNSET
        real_import = builtins.__import__
        yaml_imports = []

        def counting_import(name, *args, **kwargs):
            if name == "yaml":
                yaml_imports.append(name)
            return real_import(name, *args, **kwargs)

        try:
            with mock.patch("builtins.__import__", side_effect=counting_import):
                first = flowctl._optional_yaml_parser()
                self.assertIs(flowctl._optional_yaml_parser(), first)
                self.assertIs(flowctl._optional_yaml_parser(), first)
        finally:
            flowctl._YAML_PARSER = previous
        self.assertEqual(len(yaml_imports), 1)

    def test_pure_stdlib_schema_sentinels_and_coercion_stay_distinct(self) -> None:
        previous = flowctl._YAML_PARSER
        flowctl._YAML_PARSER = None
        try:
            self.assertEqual(flowctl._parse_memory_frontmatter_text("body\n"), {})
            self.assertEqual(
                flowctl._parse_memory_frontmatter_text("---\nbroken\n---\nbody\n"),
                {},
            )
            self.assertIsNone(flowctl._prospect_parse_frontmatter("body\n"))
            self.assertIsNone(
                flowctl._prospect_parse_frontmatter("---\nbroken\n---\nbody\n")
            )
            self.assertEqual(flowctl._prospect_parse_frontmatter("---\n---\n"), {})
            prospect = flowctl._prospect_parse_frontmatter(
                "---\nfloor_violation: true\ngeneration_under_volume: false\n---\n"
            )
            self.assertIs(prospect["floor_violation"], True)
            self.assertIs(prospect["generation_under_volume"], False)
            strategy = flowctl.parse_strategy_file(
                "---\nname: incomplete\n## Target problem\nStill parsed\n"
            )
            self.assertIsNone(strategy["name"])
            self.assertEqual(strategy["target_problem"], "Still parsed")
        finally:
            flowctl._YAML_PARSER = previous


if __name__ == "__main__":
    unittest.main()

"""Post-refactor production-surface and live workflow command contracts."""

from __future__ import annotations

import argparse
import ast
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"
FLOWCTL_PY = PLUGIN / "scripts" / "flowctl.py"
SCRIPTS_DIR = FLOWCTL_PY.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


REMOVED_NAMES = {
    "PurePosixPath",
    "TRACKER_TIEBREAKS",
    "STRATEGY_FRONTMATTER_FIELDS",
    "_STRATEGY_ISO_DATE_RE",
    "_memory_yaml_available",
    "render_strategy_file",
    "require_keys",
    "save_task_definition",
    "validate_strategy_frontmatter",
}

PLAN_INVOCATION_MANIFEST = (
    ("review-backend",),
    ("init",),
    ("config", "get"),
    ("cat",),
    ("show",),
    ("specs",),
    ("spec", "ready"),
    ("strategy", "status"),
    ("strategy", "read"),
    ("spec", "set-plan"),
    ("task", "set-spec"),
    ("spec", "create"),
    ("spec", "add-dep"),
    ("task", "create"),
    ("dep", "add"),
    ("validate",),
    ("sync", "active"),
)


class _ParserCaptured(Exception):
    pass


def _built_parser() -> argparse.ArgumentParser:
    captured: dict[str, argparse.ArgumentParser] = {}

    def capture(parser, *_args, **_kwargs):
        captured["parser"] = parser
        raise _ParserCaptured

    with mock.patch.object(argparse.ArgumentParser, "parse_args", capture):
        with unittest.TestCase().assertRaises(_ParserCaptured):
            flowctl.main()
    return captured["parser"]


def _leaf_parsers(parser: argparse.ArgumentParser, prefix=()):
    subparser_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    if not subparser_actions:
        yield prefix, parser
        return
    for action in subparser_actions:
        seen: set[int] = set()
        for name, child in action.choices.items():
            if id(child) in seen:
                continue
            seen.add(id(child))
            yield from _leaf_parsers(child, prefix + (name,))


class DeadSurfaceContractTest(unittest.TestCase):
    def test_removed_symbols_are_absent_from_production_ast(self) -> None:
        tree = ast.parse(FLOWCTL_PY.read_text(encoding="utf-8"))
        defined = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        }
        assigned = {
            target.id
            for node in tree.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Name)
        }
        imports = {
            alias.asname or alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(REMOVED_NAMES & (defined | assigned | imports))

    def test_non_obvious_compatibility_and_workflow_imports_remain_live(self) -> None:
        for name in (
            "STRATEGY_WALK_MAX_DEPTH",
            "_prospect_slug",
            "_prospect_next_id",
            "render_prospect_body",
            "write_prospect_artifact",
        ):
            self.assertTrue(hasattr(flowctl, name), name)
        prospect_workflow = (
            PLUGIN / "skills" / "flow-next-prospect" / "workflow.md"
        ).read_text(encoding="utf-8")
        for name in (
            "_prospect_slug",
            "_prospect_next_id",
            "render_prospect_body",
            "write_prospect_artifact",
        ):
            self.assertIn(name, prospect_workflow)
        self.assertIn("load_all_runtime(", FLOWCTL_PY.read_text(encoding="utf-8"))


class CliSurfaceContractTest(unittest.TestCase):
    def test_every_registered_leaf_has_a_callable_handler(self) -> None:
        leaves = list(_leaf_parsers(_built_parser()))
        self.assertGreaterEqual(len(leaves), 115)
        missing = [
            " ".join(path)
            for path, parser in leaves
            if not callable(parser.get_default("func"))
        ]
        self.assertEqual(missing, [])

    def test_live_plan_invocation_manifest_exists_and_parses(self) -> None:
        plan_text = "\n".join(
            (
                PLUGIN / "skills" / "flow-next-plan" / name
            ).read_text(encoding="utf-8")
            for name in ("SKILL.md", "steps.md")
        )
        for path in PLAN_INVOCATION_MANIFEST:
            phrase = " ".join(path)
            self.assertIn(phrase, plan_text, phrase)
            result = subprocess.run(
                [sys.executable, str(FLOWCTL_PY), *path, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, (path, result.stderr))


class RepoPromptCapabilityProbeTest(unittest.TestCase):
    PROBE_PATHS = (
        "skills/flow-next-plan/SKILL.md",
        "skills/flow-next-plan-review/SKILL.md",
        "skills/flow-next-impl-review/workflow-common.md",
        "skills/flow-next-spec-completion-review/workflow-common.md",
        "skills/flow-next-setup/workflow.md",
        "skills/flow-next-ralph-init/SKILL.md",
        "codex/skills/flow-next-plan/SKILL.md",
        "codex/skills/flow-next-plan-review/SKILL.md",
        "codex/skills/flow-next-impl-review/workflow-common.md",
        "codex/skills/flow-next-spec-completion-review/workflow-common.md",
        "codex/skills/flow-next-setup/workflow.md",
        "codex/skills/flow-next-ralph-init/SKILL.md",
        "scripts/ralph_smoke_rp.sh",
        "scripts/ralph_e2e_rp_test.sh",
        "scripts/ralph_e2e_short_rp_test.sh",
        "scripts/plan_review_prompt_smoke.sh",
    )

    def test_all_active_probes_use_the_ce_first_ladder(self) -> None:
        needles = (
            "rpce-cli",
            "$HOME/RepoPrompt/repoprompt_ce_cli",
            "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli",
            "rp-cli",
        )
        for relative in self.PROBE_PATHS:
            text = (PLUGIN / relative).read_text(encoding="utf-8")
            probe_start = text.index("command -v rpce-cli")
            probe = text[probe_start : probe_start + 600]
            offsets = [probe.index(needle) for needle in needles]
            self.assertEqual(offsets, sorted(offsets), relative)


class CompletionReviewStateTest(unittest.TestCase):
    def test_completion_review_status_persists_all_authoritative_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            specs = flow_dir / "specs"
            specs.mkdir(parents=True)
            path = specs / "fn-1.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "fn-1",
                        "title": "One",
                        "status": "open",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(id="fn-1", status="ship", json=True)
            output = io.StringIO()
            timestamps = iter(
                ["2026-07-21T23:00:00Z", "2026-07-21T23:00:01Z"]
            )
            with mock.patch.object(flowctl, "ensure_flow_exists", return_value=True):
                with mock.patch.object(flowctl, "get_flow_dir", return_value=flow_dir):
                    with mock.patch.object(flowctl, "now_iso", side_effect=timestamps):
                        with redirect_stdout(output):
                            flowctl.cmd_spec_set_completion_review_status(args)

            stored = json.loads(path.read_text(encoding="utf-8"))
            payload = json.loads(output.getvalue())
            self.assertEqual(stored["completion_review_status"], "ship")
            self.assertEqual(
                stored["completion_reviewed_at"], "2026-07-21T23:00:00Z"
            )
            self.assertEqual(stored["updated_at"], "2026-07-21T23:00:01Z")
            self.assertEqual(stored["created_at"], "2026-01-01T00:00:00Z")
            self.assertEqual(payload["completion_review_status"], "ship")
            self.assertEqual(
                payload["completion_reviewed_at"], stored["completion_reviewed_at"]
            )


if __name__ == "__main__":
    unittest.main()

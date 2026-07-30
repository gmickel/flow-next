"""Format-only prompt tightening and no-new-LLM guards for fn-136.4.

The subprocess inventory is deliberately grep-shaped: it counts literal
invocation spellings in ``flowctl.py``. Any new subprocess site, or any new
Codex/Copilot/Cursor execution bridge, must update this explicit inventory and
therefore cannot ride along unnoticed with deterministic review plumbing.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
FLOWCTL_PATH = REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
SPEC = importlib.util.spec_from_file_location("flowctl_prompt_constraints", FLOWCTL_PATH)
assert SPEC and SPEC.loader
FLOWCTL: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOWCTL)

SPEC_BODY = "SPEC_BODY_LINE1\nSPEC_BODY_LINE2"
HINTS = "hint-a\nhint-b"
DIFF_SUMMARY = " 3 files changed, 10 insertions(+), 2 deletions(-)"
DIFF_CONTENT = "diff --git a/x.py b/x.py\n+print(1)\n"
TASKS = "TASK1\nTASK2"


def _output_format(text: str) -> str:
    start = text.index("## Output Format\n")
    offset = start + len("## Output Format\n")
    in_fence = False
    end = -1
    for line in text[offset:].splitlines(keepends=True):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            end = offset
            break
        offset += len(line)
    if end == -1:
        raise AssertionError("Output Format has no following section boundary")
    return text[start:end]


class ReviewPromptConstraintTest(unittest.TestCase):
    def rendered_prompts(self) -> dict[str, str]:
        return {
            "impl": FLOWCTL.build_review_prompt(
                "impl",
                SPEC_BODY,
                HINTS,
                diff_summary=DIFF_SUMMARY,
                diff_content=DIFF_CONTENT,
            ),
            "impl_empty_optional": FLOWCTL.build_review_prompt(
                "impl", SPEC_BODY, "", diff_summary="", diff_content=""
            ),
            "plan": FLOWCTL.build_review_prompt(
                "plan", SPEC_BODY, HINTS, task_specs=TASKS
            ),
            "plan_no_tasks": FLOWCTL.build_review_prompt("plan", SPEC_BODY, HINTS),
            "standalone": FLOWCTL.build_standalone_review_prompt(
                "main", "auth and sessions", DIFF_SUMMARY
            ),
            "standalone_no_focus": FLOWCTL.build_standalone_review_prompt(
                "main", None, DIFF_SUMMARY
            ),
            "completion": FLOWCTL.build_completion_review_prompt(
                SPEC_BODY, TASKS, DIFF_SUMMARY, DIFF_CONTENT
            ),
            "completion_no_tasks": FLOWCTL.build_completion_review_prompt(
                SPEC_BODY, "", DIFF_SUMMARY, DIFF_CONTENT
            ),
        }

    def test_every_assembled_prompt_uses_unambiguous_finding_fields(self) -> None:
        for name, prompt in self.rendered_prompts().items():
            with self.subTest(prompt=name):
                output = _output_format(prompt)
                for marker in (
                    "Severity",
                    "Confidence",
                    "Classification",
                    "File:Line",
                    "R-IDs",
                    "Problem",
                    "Suggestion",
                ):
                    self.assertIn(marker, output)
                self.assertRegex(output, r"File:Line[^\n]*path:line[^\n]*`-`")
                self.assertRegex(output, r"R-IDs[^\n]*\[R1, R2\][^\n]*\[\]")
                self.assertRegex(
                    output,
                    r"Classification[^\n]*introduced[^\n]*pre_existing",
                )

    def test_flowctl_process_and_llm_invocation_inventory_is_frozen(self) -> None:
        tree = ast.parse(FLOWCTL_PATH.read_text(encoding="utf-8"))
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent

        def enclosing_function(node: ast.AST) -> str:
            parent = parents.get(node)
            while parent and not isinstance(
                parent, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                parent = parents.get(parent)
            return parent.name if parent else "<module>"

        process_methods = {
            "run",
            "Popen",
            "call",
            "check_call",
            "check_output",
        }
        backend_bridges = {
            "run_codex_exec",
            "run_copilot_exec",
            "run_cursor_exec",
        }
        observed: Counter[tuple[str, str]] = Counter()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "subprocess"
                and func.attr in process_methods
            ):
                observed[(f"subprocess.{func.attr}", enclosing_function(node))] += 1
            elif isinstance(func, ast.Name) and func.id in backend_bridges:
                observed[(func.id, enclosing_function(node))] += 1

        expected = Counter(
            {
                ("run_codex_exec", "_codex_run_exec"): 1,
                ("run_copilot_exec", "_copilot_run_exec"): 1,
                ("run_cursor_exec", "_cursor_run_exec"): 1,
                ("subprocess.run", "get_repo_root"): 1,
                ("subprocess.run", "find_strategy_file"): 1,
                ("subprocess.run", "get_state_dir"): 1,
                ("subprocess.run", "run_rp_cli"): 1,
                ("subprocess.run", "run_rp_cli_unchecked"): 1,
                ("subprocess.run", "try_run_rp_cli"): 1,
                ("subprocess.run", "get_changed_files"): 1,
                ("subprocess.run", "find_references"): 1,
                ("subprocess.run", "get_codex_version"): 1,
                ("subprocess.run", "_cursor_list_models"): 1,
                ("subprocess.run", "get_copilot_version"): 1,
                ("subprocess.run", "get_cursor_version"): 1,
                ("subprocess.run", "get_actor"): 2,
                ("subprocess.run", "_spec_alloc_git"): 1,
                ("subprocess.run", "_export_run_git"): 1,
                ("subprocess.run", "_export_read_base_blobs"): 1,
                ("subprocess.run", "_psp_run_git"): 1,
                ("subprocess.run", "_gather_review_diff"): 1,
                ("subprocess.Popen", "_gather_review_diff"): 1,
                ("subprocess.run", "_resolve_review_sha"): 1,
                ("subprocess.run", "_capture_review_snapshot"): 1,
                ("subprocess.run", "_triage_chore_is_version_only"): 1,
                ("subprocess.run", "_triage_run_codex_judge"): 1,
                ("subprocess.run", "_triage_run_copilot_judge"): 1,
                ("subprocess.run", "cmd_triage_skip"): 4,
                ("subprocess.run", "_gate_repo_and_head"): 2,
                ("subprocess.run", "_gate_status_paths"): 1,
                ("subprocess.run", "_gate_walk_candidate_ok"): 3,
                ("subprocess.run", "cmd_gate_classify"): 1,
                ("subprocess.run", "_prime_git"): 1,
                ("subprocess.Popen", "_prime_parse_ls_files_staged"): 1,
                ("subprocess.run", "_prime_git_free_tool"): 1,
                ("subprocess.run", "run_codex_exec"): 1,
                ("subprocess.run", "_dispatch"): 3,
                ("subprocess.run", "_branch_slug"): 1,
            }
        )
        self.assertEqual(observed, expected)

    def test_no_direct_llm_sdk_imports(self) -> None:
        tree = ast.parse(FLOWCTL_PATH.read_text(encoding="utf-8"))
        forbidden = {"anthropic", "google.generativeai", "openai"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertTrue(forbidden.isdisjoint(imported), imported & forbidden)

    def test_prompt_templates_match_generated_codex_mirrors(self) -> None:
        pairs = (
            "skills/flow-next-impl-review/references/impl-review-prompt.md",
            "skills/flow-next-impl-review/references/standalone-review-prompt.md",
            "skills/flow-next-plan-review/references/plan-review-prompt.md",
            "skills/flow-next-spec-completion-review/references/completion-review-prompt.md",
        )
        plugin = REPO / "plugins" / "flow-next"
        for rel in pairs:
            with self.subTest(path=rel):
                self.assertEqual(
                    (plugin / rel).read_bytes(),
                    (plugin / "codex" / rel).read_bytes(),
                    f"stale Codex mirror for {rel}; run scripts/sync-codex.sh",
                )


if __name__ == "__main__":
    unittest.main()

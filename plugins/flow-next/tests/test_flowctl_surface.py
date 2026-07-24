"""Post-refactor production-surface and live workflow command contracts."""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
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

EXPECTED_LEAF_PATHS = frozenset(
    """anchor
block
cat
checkpoint restore
checkpoint save
codex classify-result
codex completion-review
codex deep-pass
codex impl-review
codex plan-review
codex rollback-plan
codex validate
config get
config set
copilot completion-review
copilot deep-pass
copilot impl-review
copilot plan-review
copilot validate
cursor completion-review
cursor deep-pass
cursor impl-review
cursor plan-review
cursor validate
dep add
detect
done
gate check
gate classify
gate receipt
glossary add
glossary list
glossary read
glossary remove
init
list
memory add
memory init
memory list
memory list-legacy
memory mark-fresh
memory mark-stale
memory migrate
memory read
memory search
models resolve
next
pilot-log append
prime classify
prospect archive
prospect promote
ready
repo-map list
review-backend
review-deep-auto
review-rounds attempts
review-rounds increment
review-rounds record
review-rounds reset
review-walkthrough-defer
review-walkthrough-record
rp chat-send
rp prompt-export
rp prompt-get
rp prompt-set
rp select-add
rp select-get
rp setup-review
scope bank
scope resolve
scope write-policy
setup-block apply
setup-block resolve
setup-mode set
show
spec add-dep
spec close
spec create
spec export-cognitive-aid
spec ready
spec reset-review-rounds
spec rm-dep
spec set-backend
spec set-branch
spec set-completion-review-status
spec set-plan
spec set-plan-review-status
spec set-title
spec skeleton
spec unready
specs
start
status
strategy read
strategy status
sync active
sync check
sync check-collisions
sync clear
sync defer
sync get-state
sync list-dep-relations
sync list-stale
sync list-unsynced
sync receipt
sync set-dep-relation
sync set-last-synced
sync set-merge-base
sync set-tracker-id
task create
task reset
task set-acceptance
task set-backend
task set-description
task set-spec
tasks
triage-skip
usage
validate""".splitlines()
)

GROUPED_COMMANDS = {
    path.split(" ", 1)[0] for path in EXPECTED_LEAF_PATHS if " " in path
}
FLOWCTL_INVOCATION = re.compile(
    r'(?<![A-Za-z0-9_])"?\$FLOWCTL"?\s+'
    r"([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?"
)

ACTIVE_REFERENCE_ROOTS = (
    REPO_ROOT / "README.md",
    PLUGIN / "docs",
    PLUGIN / "skills",
    PLUGIN / "agents",
    PLUGIN / "codex" / "skills",
    PLUGIN / "codex" / "agents",
    REPO_ROOT / "agent_docs",
)
ACTIVE_REFERENCE_EXCLUDES = (
    "agent_docs/guidance-eval/",
    "agent_docs/optimization-log.md",
)
SHELL_FENCE_LANGUAGES = {"", "bash", "sh", "shell", "zsh", "powershell"}
EXECUTABLE_FLOWCTL_INVOCATION = re.compile(
    r'(?m)^\s*(?:"?\$FLOWCTL"?|(?:\.flow/bin/|scripts/)?flowctl)'
    r'(?![.A-Za-z0-9_-])\s+'
    r"([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?"
)


def _active_reference_files() -> list[Path]:
    paths: list[Path] = []
    for root in ACTIVE_REFERENCE_ROOTS:
        candidates = (
            [root]
            if root.is_file()
            else (
                path
                for path in root.rglob("*")
                if path.suffix in {".md", ".toml"}
            )
        )
        for path in candidates:
            relative = path.relative_to(REPO_ROOT).as_posix()
            if any(relative.startswith(prefix) for prefix in ACTIVE_REFERENCE_EXCLUDES):
                continue
            paths.append(path)
    return sorted(set(paths))


def _shell_fence_bodies(text: str) -> list[tuple[str, bool]]:
    bodies: list[tuple[str, bool]] = []
    open_language: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if open_language is None:
            match = re.match(r"^\s*```([^\s`]*)\s*$", line)
            if match and match.group(1).lower() in SHELL_FENCE_LANGUAGES:
                open_language = match.group(1).lower()
                body = []
            continue
        if re.match(r"^\s*```\s*$", line):
            bodies.append(("\n".join(body), bool(open_language)))
            open_language = None
            body = []
            continue
        body.append(line)
    return bodies


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
        discovered = {" ".join(path) for path, _parser in leaves}
        self.assertEqual(discovered, EXPECTED_LEAF_PATHS)
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
        invocations = set()
        for match in FLOWCTL_INVOCATION.finditer(plan_text):
            top, child = match.groups()
            invocations.add(
                (top, child) if top in GROUPED_COMMANDS and child else (top,)
            )
        for path in PLAN_INVOCATION_MANIFEST:
            self.assertIn(path, invocations, " ".join(path))
            result = subprocess.run(
                [sys.executable, str(FLOWCTL_PY), *path, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, (path, result.stderr))


class ActiveReferenceContractTest(unittest.TestCase):
    def test_active_shell_snippets_only_invoke_registered_commands(self) -> None:
        failures: list[str] = []
        for path in _active_reference_files():
            text = path.read_text(encoding="utf-8")
            for body, strict in _shell_fence_bodies(text):
                for match in EXECUTABLE_FLOWCTL_INVOCATION.finditer(body):
                    top, child = match.groups()
                    if top not in {path.split(" ", 1)[0] for path in EXPECTED_LEAF_PATHS}:
                        if strict:
                            failures.append(
                                f"{path.relative_to(REPO_ROOT)}: {top}"
                            )
                        # Unlabelled fences also carry prose and diagrams. The
                        # removed-surface test below guards historical command
                        # names even there; language-tagged shell fences are
                        # strict and reject every unknown top-level command.
                        continue
                    if top in GROUPED_COMMANDS and child:
                        command = f"{top} {child}"
                        if command not in EXPECTED_LEAF_PATHS:
                            failures.append(
                                f"{path.relative_to(REPO_ROOT)}: {command}"
                            )
        self.assertEqual(failures, [])

    def test_known_removed_surfaces_are_not_runnable_in_active_snippets(self) -> None:
        removed = re.compile(
            r'(?:flowctl|"?\$FLOWCTL"?|\.flow/bin/flowctl|scripts/flowctl)\s+'
            r"(?:epics?(?:\s|$)|migrate-(?:rename|rollback|state)\b|"
            r"config\s+toggle\b|unblock\b|update\s+[^\n]+--status\b|"
            r"--version\b|setup(?:\s|$)|rp\s+(?:pick-window|builder)\b|"
            r"(?:impl|plan|completion)-review\b|"
            r"spec\s+export-cognitive-aid[^\n]*--section\b)"
        )
        failures: list[str] = []
        for path in _active_reference_files():
            text = path.read_text(encoding="utf-8")
            for body, _strict in _shell_fence_bodies(text):
                if removed.search(body):
                    failures.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(failures, [])

    def test_strategy_commands_use_the_resolved_flowctl_path(self) -> None:
        strategy = PLUGIN / "skills" / "flow-next-strategy"
        for path in strategy.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(
                text,
                r'(?<!\$)(?<!["/])\bflowctl\s+(?:strategy|specs)\b',
                path.relative_to(REPO_ROOT).as_posix(),
            )

    def test_active_payload_contract_omits_removed_export_fields(self) -> None:
        paths = (
            PLUGIN / "skills" / "flow-next-make-pr" / "workflow.md",
            PLUGIN / "skills" / "flow-next-make-pr" / "create-and-finalize.md",
            PLUGIN / "skills" / "flow-next-qa" / "workflow.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("review_receipts", combined)
        self.assertNotRegex(combined, r"export-cognitive-aid[^\n]*--section")
        self.assertIn("deferred_findings", combined)

    def test_smoke_labels_name_the_canonical_operation(self) -> None:
        smoke = (PLUGIN / "scripts" / "smoke_test.sh").read_text(encoding="utf-8")
        for stale_label in (
            "config toggle",
            "planSync config toggle",
            "--- epic set-title ---",
            "epic close",
            "stdin epic set-plan",
            "set-title updates epic JSON",
            "epic set-backend",
        ):
            self.assertNotIn(stale_label, smoke)
        for canonical_label in (
            "config set false/get",
            "--- spec set-title ---",
            "spec close",
            "stdin spec set-plan",
            "spec set-backend",
        ):
            self.assertIn(canonical_label, smoke)

    def test_direct_rp_exploration_targets_community_edition(self) -> None:
        paths = (
            PLUGIN / "skills" / "flow-next-rp-explorer" / "SKILL.md",
            PLUGIN / "skills" / "flow-next-rp-explorer" / "cli-reference.md",
            PLUGIN / "agents" / "context-scout.md",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertIn("rpce-cli", text)
            self.assertNotRegex(text, r"(?m)^\s*rp-cli\s")


class RepoPromptCapabilityProbeTest(unittest.TestCase):
    PROBE_PATHS = (
        "skills/flow-next-plan/SKILL.md",
        "skills/flow-next-plan-review/workflow.md",
        "skills/flow-next-impl-review/workflow-common.md",
        "skills/flow-next-spec-completion-review/workflow-common.md",
        "skills/flow-next-setup/workflow.md",
        "skills/flow-next-ralph-init/SKILL.md",
        "codex/skills/flow-next-plan/SKILL.md",
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
        paths = list(self.PROBE_PATHS)
        mirror_plan_review = PLUGIN / "codex/skills/flow-next-plan-review"
        # Parallel workers defer the combined mirror regeneration. Before
        # sync, the B1 mirror keeps the probe in SKILL.md; after sync, the
        # split mirror keeps it in workflow.md.
        mirror_probe = (
            "codex/skills/flow-next-plan-review/workflow.md"
            if (mirror_plan_review / "workflow-codex.md").exists()
            else "codex/skills/flow-next-plan-review/SKILL.md"
        )
        paths.append(mirror_probe)
        for relative in paths:
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

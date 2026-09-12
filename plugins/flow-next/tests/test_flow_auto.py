"""`flow --auto` retires the pilot skill - behaviour and contract pins (R13).

The unattended driver lives in `skills/flow-next-flow/auto.md`, read only when
flow's mode detection parsed the exact `--auto` token; `--tick` runs one hop.
`/flow-next:pilot` stays one release as a redirect shim onto
`flow --auto --tick`. Everything here is a contract token or a real code path
(G2): the verdict grammar for both shapes, the shim's argument mapping, the
classification pointers resolving to routing files that exist, the tick-only
chain gate, the QA `auto` read, the zero-task route recording, the refusal
inversion, and executable runs of the argument-parse fence and the hard-guard
fence. No sentence pins, no size or hash baselines.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_flow_auto -q
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent

FLOW_DIR = PLUGIN / "skills" / "flow-next-flow"
FLOW_SKILL = FLOW_DIR / "SKILL.md"
AUTO_MD = FLOW_DIR / "auto.md"
FLOW_REFERENCES = FLOW_DIR / "references"
PILOT_SHIM = PLUGIN / "commands" / "pilot.md"
PILOT_STUB = PLUGIN / "skills" / "flow-next-pilot" / "SKILL.md"

VERDICT_GRAMMAR_LINE = (
    "PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> "
    'spec=<id> stage=<stage> reason="<one line>"'
)
JOINED_STAGE_EXAMPLE = "stage=work+qa+make-pr"
CHAINED_TICK_TOKEN = "qa+make-pr"
DEPRECATION_LINE = (
    "pilot is now flow --auto --tick; this alias is removed in the next release"
)
PILOT_ARGUMENTS = ("--spec", "--backlog", "--dry-run", "--review", "--research", "--depth")
CLASSIFY_POINTERS = ("route-matrix.md", "plan-vs-no-plan.md", "gate-selection.md")
PILOT_STAGE_TABLE_HEADER = "| Condition | Stage |"
ATTENDED_REFUSAL_LINE = (
    "NEEDS_HUMAN: /flow-next:flow is attended - run /flow-next:flow --auto for unattended runs"
)
RALPH_REFUSAL_VERDICT = (
    'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="nested under Ralph harness '
    '(FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
)
QA_AUTO_SKIP_TOKEN = "skipped(config: pipeline.qa=auto:"

LOCAL_REF_MENTION_RE = re.compile(r"references/([A-Za-z0-9_.-]+\.md)")
PARSED_VARS = (
    "PILOT_SPEC",
    "AUTO_TICK",
    "PILOT_BACKLOG_OVERRIDE",
    "PILOT_DRY_RUN",
    "PILOT_REVIEW",
    "PILOT_RESEARCH",
    "PILOT_DEPTH",
)

_POSIX_BASH = unittest.skipIf(
    sys.platform == "win32" or shutil.which("bash") is None,
    "executable fence tests need a POSIX bash",
)
_GIT = unittest.skipIf(shutil.which("git") is None, "hard-guard fence needs git")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


def _section(text: str, start: str, end: str) -> str:
    """Slice from the `start` heading up to the `end` heading."""
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def _fence_from(text: str, first_line: str) -> str:
    """The bash fence body starting at `first_line` up to its closing ```."""
    start = text.index(first_line)
    end = text.index("```", start)
    return text[start:end]


class VerdictGrammar(unittest.TestCase):
    """(1) One terminal line, grammar unchanged from pilot, in both shapes."""

    def test_grammar_line_and_joined_stage_example(self) -> None:
        text = _read(AUTO_MD)
        self.assertIn(VERDICT_GRAMMAR_LINE, text)
        self.assertIn(JOINED_STAGE_EXAMPLE, text, "long-horizon runs join dispatched stages with +")
        self.assertIn(f"stage={CHAINED_TICK_TOKEN}", text, "the chained tick keeps its stage token")
        self.assertIn("--tick", text)
        # TRIAGED stays explain-only: never in the live grammar line.
        self.assertNotIn("PILOT_VERDICT=<ADVANCED|TRIAGED", text)
        self.assertIn("PILOT_VERDICT=TRIAGED", text)

    def test_tick_shape_is_one_hop_then_stop(self) -> None:
        text = _read(AUTO_MD)
        self.assertIn("AUTO_TICK=1", text)
        self.assertIn("AUTO_TICK=0", text)


class ShimArgumentMapping(unittest.TestCase):
    """(2) `/flow-next:pilot` is a redirect onto `flow --auto --tick`."""

    def test_both_shim_surfaces_name_the_target_and_deprecation_line(self) -> None:
        for path in (PILOT_SHIM, PILOT_STUB):
            with self.subTest(surface=path.relative_to(PLUGIN).as_posix()):
                text = _read(path)
                self.assertIn("--auto --tick", text)
                self.assertIn(DEPRECATION_LINE, text)
                self.assertIn("flow-next-flow", text)

    def test_every_pilot_argument_has_a_place(self) -> None:
        for path in (PILOT_SHIM, PILOT_STUB):
            text = _read(path)
            for arg in PILOT_ARGUMENTS:
                with self.subTest(surface=path.name, argument=arg):
                    self.assertIn(arg, text)

    def test_stub_frontmatter_is_a_deprecation_alias(self) -> None:
        fm = _frontmatter(_read(PILOT_STUB))
        self.assertRegex(fm, r"(?m)^name:\s*flow-next-pilot\s*$")
        self.assertRegex(fm, r"(?m)^disable-model-invocation:\s*true\s*$")
        self.assertRegex(fm, r"(?m)^user-invocable:\s*false\s*$")

    def test_command_shim_frontmatter_keeps_the_pilot_name(self) -> None:
        fm = _frontmatter(_read(PILOT_SHIM))
        self.assertRegex(fm, r"(?m)^name:\s*pilot\s*$")
        self.assertIn("--spec", fm, "argument-hint keeps pilot's spelling for one release")


class ClassificationPointers(unittest.TestCase):
    """(3) Classification reads the routing reference; the stage table is gone."""

    def test_every_reference_mention_resolves(self) -> None:
        for name in sorted(set(LOCAL_REF_MENTION_RE.findall(_read(AUTO_MD)))):
            with self.subTest(reference=name):
                self.assertTrue((FLOW_REFERENCES / name).is_file(), f"auto.md names references/{name}, missing")

    def test_classify_section_names_the_three_routing_files(self) -> None:
        classify = _section(_read(AUTO_MD), "## Phase 2 - CLASSIFY", "## Phase 3")
        for name in CLASSIFY_POINTERS:
            with self.subTest(reference=name):
                self.assertIn(f"references/{name}", classify)

    def test_pilot_stage_table_is_gone(self) -> None:
        self.assertNotIn(PILOT_STAGE_TABLE_HEADER, _read(AUTO_MD))


class ChainStagesTickOnly(unittest.TestCase):
    """(4) `pipeline.chainStages` is honoured under `--tick` only.

    The executable run of the gate fence (off/on, AUTO_TICK 1/0, stderr
    notice) lives in test_pilot_chain_stages; this pins the gate tokens.
    """

    def test_chain_gate_requires_auto_tick(self) -> None:
        fence = _fence_from(_read(AUTO_MD), "CHAIN_ENABLED=0\n")
        self.assertIn('if [ "${AUTO_TICK:-0}" = "1" ]; then', fence)
        self.assertIn("CHAIN_ENABLED=1", fence)
        self.assertIn(">&2", fence, "long-horizon mode prints the deprecation notice to stderr")

    def test_chained_stage_section_is_tick_only(self) -> None:
        self.assertIn("### Chained stage (`pipeline.chainStages`, `--tick` only)", _read(AUTO_MD))


class QaAutoUnderAuto(unittest.TestCase):
    """(5) `pipeline.qa=auto` takes effect under `--auto`."""

    def test_auto_flag_and_skip_line_token(self) -> None:
        text = _read(AUTO_MD)
        self.assertIn("QA_STAGE_AUTO", text)
        self.assertIn('[ "${QA_GATE:-}" = "auto" ] && QA_STAGE_AUTO=1', text)
        self.assertIn(QA_AUTO_SKIP_TOKEN, text)
        self.assertIn("qa_gate=<off|on|auto>", text)


class ZeroTaskRouteRecording(unittest.TestCase):
    """(6) A zero-task ready spec gets its route recorded and echoed."""

    def test_route_recording_verbs_and_echo(self) -> None:
        classify = _section(_read(AUTO_MD), "## Phase 2 - CLASSIFY", "## Phase 3")
        for token in (
            "spec set-no-plan",
            "spec clear-no-plan",
            "route: direct -",
            "route: plan -",
            "references/plan-vs-no-plan.md",
        ):
            with self.subTest(token=token):
                self.assertIn(token, classify)


class RefusalInversion(unittest.TestCase):
    """(7) Attended flow refuses under every autonomy marker; `--auto` refuses
    under Ralph only, because it sets FLOW_AUTONOMOUS for the stages it
    dispatches."""

    def test_attended_skill_pins_the_line_and_the_marker_family(self) -> None:
        text = _read(FLOW_SKILL)
        self.assertIn(ATTENDED_REFUSAL_LINE, text)
        for marker in ("FLOW_RALPH", "FLOW_AUTONOMOUS", "REVIEW_RECEIPT_PATH", "mode:autonomous"):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def _hard_guard_fence(self) -> str:
        guards = _section(_read(AUTO_MD), "## Hard guards", "## Arguments")
        return _fence_from(guards, 'if [[ -n "${FLOW_RALPH:-}"')

    def test_auto_hard_guard_is_ralph_only(self) -> None:
        fence = self._hard_guard_fence()
        self.assertIn("FLOW_RALPH", fence)
        self.assertIn("REVIEW_RECEIPT_PATH", fence)
        self.assertIn(RALPH_REFUSAL_VERDICT, fence, "pilot's exact Ralph terminal line survives")
        self.assertNotIn("FLOW_AUTONOMOUS", fence)
        self.assertNotIn("mode:autonomous", fence)

    @_POSIX_BASH
    @_GIT
    def test_hard_guard_fence_refuses_ralph_and_admits_autonomous(self) -> None:
        # Executable: the two guards run against a clean throwaway repo.
        # Ralph markers -> exit 1 with the verdict as the last stdout line;
        # FLOW_AUTONOMOUS alone -> nothing printed, exit 0.
        fence = self._hard_guard_fence()
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True, capture_output=True)
            base = {k: v for k, v in os.environ.items()
                    if k not in ("FLOW_RALPH", "REVIEW_RECEIPT_PATH", "FLOW_AUTONOMOUS")}
            script = f'REPO_ROOT="{td}"\n{fence}\nprintf "PASSED"'
            cases = (
                ({"FLOW_RALPH": "1"}, 1, RALPH_REFUSAL_VERDICT),
                ({"REVIEW_RECEIPT_PATH": "/tmp/x.json"}, 1, RALPH_REFUSAL_VERDICT),
                ({"FLOW_AUTONOMOUS": "1"}, 0, "PASSED"),
                ({}, 0, "PASSED"),
            )
            for extra, rc, last_line in cases:
                with self.subTest(env=extra):
                    res = subprocess.run(
                        ["bash", "-c", script], capture_output=True, text=True, env={**base, **extra}
                    )
                    self.assertEqual(res.returncode, rc, res.stderr)
                    self.assertEqual(res.stdout.rstrip("\n").splitlines()[-1], last_line)


class ArgumentParseFence(unittest.TestCase):
    """(8) The argument-parse fence, run for real."""

    def _fence(self) -> str:
        return _fence_from(_read(AUTO_MD), 'RAW_ARGS="$ARGUMENTS"')

    def _parse(self, arguments: str) -> tuple[dict[str, str], str]:
        script = self._fence() + "\n" + "\n".join(f'printf "%s=%s\\n" {v} "${v}"' for v in PARSED_VARS)
        res = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            env={**os.environ, "ARGUMENTS": arguments},
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        parsed = dict(line.split("=", 1) for line in res.stdout.splitlines() if "=" in line)
        return parsed, res.stderr

    DEFAULTS = {
        "PILOT_SPEC": "",
        "AUTO_TICK": "0",
        "PILOT_BACKLOG_OVERRIDE": "",
        "PILOT_DRY_RUN": "0",
        "PILOT_REVIEW": "",
        "PILOT_RESEARCH": "grep",
        "PILOT_DEPTH": "short",
    }

    @_POSIX_BASH
    def test_fence_exports_every_parsed_variable(self) -> None:
        fence = self._fence()
        for var in PARSED_VARS:
            with self.subTest(var=var):
                self.assertRegex(fence, rf"(?m)^export .*\b{var}\b")

    @_POSIX_BASH
    def test_argument_shapes(self) -> None:
        # arguments -> the values that differ from DEFAULTS
        cases = (
            (
                "fn-12 --tick --backlog --explain --review=codex --research rp --depth=long",
                {
                    "PILOT_SPEC": "fn-12",
                    "AUTO_TICK": "1",
                    "PILOT_BACKLOG_OVERRIDE": "1",
                    "PILOT_DRY_RUN": "1",
                    "PILOT_REVIEW": "codex",
                    "PILOT_RESEARCH": "rp",
                    "PILOT_DEPTH": "long",
                },
            ),
            ("--spec fn-9 --dry-run", {"PILOT_SPEC": "fn-9", "PILOT_DRY_RUN": "1"}),
            ("--spec=fn-3", {"PILOT_SPEC": "fn-3"}),
            ("--auto fn-4 --tick", {"PILOT_SPEC": "fn-4", "AUTO_TICK": "1"}),
            ("--review codex --depth long --research=rp", {"PILOT_REVIEW": "codex", "PILOT_DEPTH": "long", "PILOT_RESEARCH": "rp"}),
            ("", {}),
        )
        for arguments, overrides in cases:
            with self.subTest(arguments=arguments):
                parsed, _ = self._parse(arguments)
                self.assertEqual(parsed, {**self.DEFAULTS, **overrides})

    @_POSIX_BASH
    def test_lookalike_flags_do_not_set_the_flags(self) -> None:
        # Exact tokens only: a prefix or suffix lookalike is an unknown flag,
        # warned to stderr and ignored.
        for arguments in ("--ticket", "--auto-x", "--explainer", "--backlogs", "--spec-x"):
            with self.subTest(arguments=arguments):
                parsed, stderr = self._parse(arguments)
                self.assertEqual(parsed, self.DEFAULTS)
                self.assertIn(arguments, stderr)

    @_POSIX_BASH
    def test_positional_id_and_spec_flag_do_not_double_assign(self) -> None:
        parsed, stderr = self._parse("--spec fn-9 fn-10")
        self.assertEqual(parsed["PILOT_SPEC"], "fn-9")
        self.assertIn("fn-10", stderr)

    @_POSIX_BASH
    def test_dangling_value_flag_warns(self) -> None:
        parsed, stderr = self._parse("fn-2 --review")
        self.assertEqual(parsed["PILOT_REVIEW"], "")
        self.assertIn("--review", stderr)


if __name__ == "__main__":
    unittest.main()

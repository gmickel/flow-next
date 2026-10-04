"""`flow --auto` behaviour and contract checks (R13).

The unattended driver lives in `skills/flow-next-flow/auto.md`, read only when
flow's mode detection parsed the exact `--auto` token; `--tick` runs one hop.
Covered here: the verdict grammar line, reference mentions that
resolve, and executable runs of the argument-parse, hard-guard, snapshot and
make-pr verify fences. No sentence pins, no size or hash baselines.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_flow_auto -q
"""

from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent

FLOW_DIR = PLUGIN / "skills" / "flow-next-flow"
AUTO_MD = FLOW_DIR / "auto.md"
FLOW_REFERENCES = FLOW_DIR / "references"

VERDICT_GRAMMAR_LINE = (
    "PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> "
    'spec=<id> stage=<stage> reason="<one line>"'
)

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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fence_from(text: str, first_line: str) -> str:
    """The bash fence body starting at `first_line` up to its closing ```."""
    start = text.index(first_line)
    end = text.index("```", start)
    return text[start:end]


class VerdictGrammar(unittest.TestCase):
    """(1) One terminal line, grammar unchanged from pilot, in both shapes."""

    def test_grammar_line(self) -> None:
        text = _read(AUTO_MD)
        self.assertIn(VERDICT_GRAMMAR_LINE, text)

    def test_already_merged_closed_spec_names_no_work(self) -> None:
        # A driver keyed on NO_WORK must stop on an already-merged scoped spec.
        self.assertIn("PILOT_VERDICT=NO_WORK", _read(AUTO_MD))


class ReferenceMentions(unittest.TestCase):

    def test_every_reference_mention_resolves(self) -> None:
        for name in sorted(set(LOCAL_REF_MENTION_RE.findall(_read(AUTO_MD)))):
            with self.subTest(reference=name):
                self.assertTrue((FLOW_REFERENCES / name).is_file(), f"auto.md names references/{name}, missing")

class HardGuardFence(unittest.TestCase):
    """The hard-guard and snapshot fences, run for real."""

    def _hard_guard_fence(self) -> str:
        return _fence_from(_read(AUTO_MD), '# fence:pilot-guards')

    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_snapshot_guard_consumer_stops_before_dispatch(self) -> None:
        for dirty, rc, expected in (
            ([' M code.py'], 0, 'dirty working tree at tick start'),
            ([], 0, 'PASSED'),
        ):
            result = subprocess.run(['bash', '-c', self._hard_guard_fence() + '\nprintf PASSED'],
                                    env={**os.environ, 'PILOT_SNAPSHOT': json.dumps({'guards': {'dirty': dirty}})},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, rc)
            self.assertIn(expected, result.stdout)
            if dirty:
                self.assertNotIn('PASSED', result.stdout)


    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_snapshot_fences_fail_closed_in_a_fresh_shell(self) -> None:
        # Shell variables do not survive between tool calls: a fence run in a
        # fresh shell reads the snapshot file and stops when it is absent.
        env = {k: v for k, v in os.environ.items() if k != "PILOT_SNAPSHOT"}
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            script = self._hard_guard_fence() + "\nprintf PASSED"
            missing = subprocess.run(["bash", "-c", script], cwd=tmp, env=env,
                                     capture_output=True, text=True)
            self.assertEqual(missing.returncode, 1)
            self.assertIn("pilot snapshot missing or unreadable", missing.stdout)
            self.assertNotIn("PASSED", missing.stdout)
            snap = Path(tmp) / ".flow" / "tmp" / "pilot-snapshot.json"
            snap.parent.mkdir(parents=True)
            snap.write_text(json.dumps({"guards": {"dirty": []}}))
            present = subprocess.run(["bash", "-c", script], cwd=tmp, env=env,
                                     capture_output=True, text=True)
            self.assertEqual(present.returncode, 0, present.stderr)
            self.assertIn("PASSED", present.stdout)


    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_snapshot_write_failure_stops(self) -> None:
        fence = _fence_from(_read(AUTO_MD), "SNAPSHOT_ARGS=()")
        env = {k: v for k, v in os.environ.items() if k != "PILOT_SNAPSHOT"}
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            (Path(tmp) / ".flow").mkdir()
            (Path(tmp) / ".flow" / "tmp").write_text("not a directory")
            stub = Path(tmp) / "flowctl-stub"
            stub.write_text('#!/usr/bin/env bash\nprintf \'{"guards":{}}\'\n')
            stub.chmod(0o755)
            result = subprocess.run(["bash", "-c", fence + "\nprintf PASSED"], cwd=tmp,
                                    env={**env, "FLOWCTL": str(stub), "PILOT_SPEC": ""},
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("NEEDS_HUMAN", result.stdout)
        self.assertNotIn("PASSED", result.stdout)


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
        # Dispatched stages read these from the environment: run the fence and
        # check a child process sees every parsed variable.
        res = subprocess.run(
            ["bash", "-c", self._fence() + "\nenv"],
            capture_output=True,
            text=True,
            env={**os.environ, "ARGUMENTS": "fn-1 --tick"},
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        exported = {line.split("=", 1)[0] for line in res.stdout.splitlines() if "=" in line}
        for var in PARSED_VARS:
            with self.subTest(var=var):
                self.assertIn(var, exported)

    @_POSIX_BASH
    def test_argument_shapes(self) -> None:
        # arguments -> the values that differ from DEFAULTS
        cases = (
            (
                "fn-12 --tick --backlog --explain --review=codex --research custom --depth=long",
                {
                    "PILOT_SPEC": "fn-12",
                    "AUTO_TICK": "1",
                    "PILOT_BACKLOG_OVERRIDE": "1",
                    "PILOT_DRY_RUN": "1",
                    "PILOT_REVIEW": "codex",
                    "PILOT_RESEARCH": "custom",
                    "PILOT_DEPTH": "long",
                },
            ),
            ("wor-17-x", {"PILOT_SPEC": "wor-17-x"}),
            ("fn-9 --dry-run", {"PILOT_SPEC": "fn-9", "PILOT_DRY_RUN": "1"}),
            ("--auto fn-4 --tick", {"PILOT_SPEC": "fn-4", "AUTO_TICK": "1"}),
            ("--review codex --depth long --research=custom", {"PILOT_REVIEW": "codex", "PILOT_DEPTH": "long", "PILOT_RESEARCH": "custom"}),
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
        for arguments in ("--ticket", "--auto-x", "--explainer", "--backlogs", "--spec"):
            with self.subTest(arguments=arguments):
                parsed, stderr = self._parse(arguments)
                self.assertEqual(parsed, self.DEFAULTS)
                self.assertIn(arguments, stderr)

    @_POSIX_BASH
    def test_second_positional_id_does_not_double_assign(self) -> None:
        parsed, stderr = self._parse("fn-9 fn-10")
        self.assertEqual(parsed["PILOT_SPEC"], "fn-9")
        self.assertIn("fn-10", stderr)

    @_POSIX_BASH
    def test_dangling_value_flag_warns(self) -> None:
        parsed, stderr = self._parse("fn-2 --review")
        self.assertEqual(parsed["PILOT_REVIEW"], "")
        self.assertIn("--review", stderr)


class MakePrVerifyProbe(unittest.TestCase):
    @unittest.skipIf(shutil.which("jq") is None, "verify fence needs jq")
    @_POSIX_BASH
    def test_make_pr_verify_probe_parse_failure_is_flagged(self) -> None:
        # A malformed body must set PR_VERIFY_FAILED=1 (jq is the
        # status-bearing command); a valid body yields the first OPEN url; no
        # OPEN row yields "" with the flag still 0.
        cases = {
            '[{"state":"CLOSED","url":"c"},{"state":"OPEN","url":"https://x/1"}]': ("https://x/1", "0"),
            '[{"state":"CLOSED","url":"c"}]': ("", "0"),
            '{not json': ("", "1"),
        }
        line = next(l for l in _read(AUTO_MD).splitlines() if l.startswith("OPEN_PR_URL=$(printf"))
        for body, (url, failed) in cases.items():
            with self.subTest(body=body):
                script = f"PR_VERIFY_FAILED=0\nPR_VERIFY_JSON={body!r}\n{line}\nprintf '%s|%s' \"$OPEN_PR_URL\" \"$PR_VERIFY_FAILED\""
                out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
                self.assertEqual(out, f"{url}|{failed}")

    @_POSIX_BASH
    def test_make_pr_verify_probe_flags_a_gh_failure(self) -> None:
        # A failing gh must set PR_VERIFY_FAILED=1 rather than yield an empty
        # URL that reads as a healthy no-advance strike.
        text = _read(AUTO_MD)
        fence = _fence_from(text, "PR_VERIFY_FAILED=0\n")
        with tempfile.TemporaryDirectory() as tmp:
            gh = Path(tmp) / "gh"
            gh.write_text("#!/bin/sh\nexit 1\n")
            gh.chmod(0o755)
            env = {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ['PATH']}", "BRANCH_NAME": "b"}
            out = subprocess.run(["bash", "-c", fence + 'printf "%s" "$PR_VERIFY_FAILED"'],
                                 capture_output=True, text=True, env=env, check=True).stdout
        self.assertEqual(out, "1")


if __name__ == "__main__":
    unittest.main()

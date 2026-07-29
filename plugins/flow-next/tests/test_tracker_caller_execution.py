"""Execute every tracker lifecycle caller gate against an instrumented flowctl."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_COMMIT = "410756ef8f27d14c3cfbcbffe66356c67fd255ad"
ORACLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "tracker_callers"
    / f"oracle-{SOURCE_COMMIT}.json"
)
VALUES = ("off", "pull", "push", "reconcile", "comment")
WORK_EVENTS = {"work.firstClaim", "work.done", "completionReview"}
DIRECT_EVENTS = {"capture", "interview", "plan"}
COMMENT_EVENTS = {"resolvePr", "qa"}
BODY_FILE_EVENTS = COMMENT_EVENTS | {"work.done", "completionReview"}
UNCONDITIONAL_EVENTS = {"makePr", "land.merged"}


def _bash_fences(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)\n```", text, flags=re.DOTALL)


def _single_fence(path: Path, *needles: str) -> str:
    matches = [
        fence
        for fence in _bash_fences(path.read_text(encoding="utf-8"))
        if all(needle in fence for needle in needles)
    ]
    if len(matches) != 1:
        raise AssertionError(f"{path}: expected one fence for {needles}, got {len(matches)}")
    return matches[0]


def _inject_before_last_fi(source: str, body: str) -> str:
    position = source.rfind("\nfi")
    if position < 0:
        raise AssertionError("caller fence has no terminal fi")
    return source[:position] + "\n" + textwrap.indent(body, "  ") + source[position:]


def _indented_shell_block(path: Path, start: str) -> str:
    """Extract one indented bash statement through its first matching outer `fi`."""
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"(?ms)^   {re.escape(start)}.*?^   fi[ \t]*$",
        text,
    )
    if match is None:
        raise AssertionError(f"{path}: missing shell block starting {start!r}")
    return textwrap.dedent(match.group(0))


def _shell_if_block_around(path: Path, sentinel: str) -> str:
    """Slice a nested Markdown shell block without crossing its indented fence."""
    lines = path.read_text(encoding="utf-8").splitlines()
    sentinel_index = next(
        index for index, line in enumerate(lines) if sentinel in line
    )
    start = sentinel_index
    while start >= 0 and lines[start].strip() != "ACTIVE=0":
        start -= 1
    if start < 0:
        raise AssertionError(f"{path}: no ACTIVE=0 before {sentinel!r}")
    end = sentinel_index
    while end < len(lines) and not lines[end].strip().startswith("fi"):
        end += 1
    if end == len(lines):
        raise AssertionError(f"{path}: no fi after {sentinel!r}")
    return textwrap.dedent("\n".join(lines[start : end + 1]))


class TrackerCallerExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        cls.callers = {row["id"]: row for row in oracle["callers"]}
        cls.values = tuple(oracle["per_event_enum"])
        cls.sources = {
            caller_id: REPO_ROOT / row["file"]
            for caller_id, row in cls.callers.items()
        }

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.call_log = self.root / "calls.jsonl"
        self.import_log = self.root / "imports.txt"
        self.fake_flowctl = self.root / "flowctl"
        self.fake_gh = self.root / "gh"
        self.fake_flowctl.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys

                argv = sys.argv[1:]
                with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(argv, separators=(",", ":")) + "\\n")
                if argv[:2] == ["config", "get"]:
                    leaf = os.environ["TRACKER_LEAF"]
                    if argv == ["config", "get", "--json"]:
                        print(json.dumps({"value": {"tracker": {"perEvent": {"plan": leaf}}}}))
                    else:
                        print(json.dumps({"value": leaf}))
                elif argv[:2] == ["sync", "active"]:
                    print(json.dumps({"active": os.environ["BRIDGE_ACTIVE"] == "true"}))
                elif argv[:2] == ["tracker", "sync"]:
                    pass
                else:
                    raise SystemExit("unexpected fake flowctl argv: " + repr(argv))
                """
            ),
            encoding="utf-8",
        )
        self.fake_flowctl.chmod(0o755)
        self.fake_gh.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                if [ "$MERGED_STATE" = "true" ]; then
                  printf '%s\\n' '[{"state":"MERGED"}]'
                else
                  printf '%s\\n' '[]'
                fi
                """
            ),
            encoding="utf-8",
        )
        self.fake_gh.chmod(0o755)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _environment(self, value: str, active: bool, merged: bool = True) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "FLOWCTL": str(self.fake_flowctl),
                "CALL_LOG": str(self.call_log),
                "IMPORT_LOG": str(self.import_log),
                "TRACKER_LEAF": value,
                "BRIDGE_ACTIVE": str(active).lower(),
                "MERGED_STATE": str(merged).lower(),
                "SPEC_ID": "fn-141-harness",
                "PR_URL": "https://example.test/pull/141",
                "BRANCH_NAME": "fn-141-harness",
                "BODY_FILE": str(self.root / "comment.md"),
                "TMPDIR": str(self.root),
                "PATH": f"{self.root}:{env['PATH']}",
            }
        )
        (self.root / "comment.md").write_text("caller-owned comment\n", encoding="utf-8")
        return env

    def _run_shell(
        self,
        source: str,
        *,
        value: str,
        active: bool,
        merged: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        forbidden = re.search(
            r"(?m)^\s*(?:git|curl|glab|rm|mv)\s|gh\s+pr\s+merge",
            source,
        )
        if forbidden is not None:
            raise AssertionError(
                f"caller harness refused side-effecting command: {forbidden.group(0)!r}"
            )
        return subprocess.run(
            ["/bin/bash", "-c", source],
            cwd=REPO_ROOT,
            env=self._environment(value, active, merged),
            capture_output=True,
            text=True,
            check=False,
        )

    def _calls(self) -> list[list[str]]:
        if not self.call_log.exists():
            return []
        return [
            json.loads(line)
            for line in self.call_log.read_text(encoding="utf-8").splitlines()
        ]

    def _imports(self) -> list[str]:
        if not self.import_log.exists():
            return []
        return self.import_log.read_text(encoding="utf-8").splitlines()

    def _reset_observations(self) -> None:
        self.call_log.unlink(missing_ok=True)
        self.import_log.unlink(missing_ok=True)

    def _expected_op(self, caller_id: str, value: str, merged: bool) -> str | None:
        if caller_id in UNCONDITIONAL_EVENTS:
            if caller_id == "makePr":
                return "reconcile"
            return "push" if merged else "comment"
        if value == "off":
            return None
        if caller_id in DIRECT_EVENTS:
            return value
        if caller_id == "work.firstClaim":
            return "push"
        return "comment"

    def _facade_argv(self, caller_id: str, op: str) -> list[str]:
        row = self.callers[caller_id]
        argv = [
            "tracker",
            "sync",
            "fn-141-harness",
            "--op",
            op,
            "--event",
            row["event"],
        ]
        if op == "comment" and caller_id not in {"capture", "interview", "plan"}:
            argv.extend(["--body-file", str(self.root / "comment.md")])
        return argv

    def _instrumented_fence(self, caller_id: str, op_expression: str) -> str:
        row = self.callers[caller_id]
        fence = _single_fence(
            self.sources[caller_id],
            row["config_key"],
            "tracker sync",
        )
        imports = []
        if caller_id == "plan":
            imports.append("references/tracker-projection.md")
        imports.append("skill:flow-next-tracker-sync")
        body = "\n".join(
            [
                *[
                    f"printf '%s\\n' '{item}' >> \"$IMPORT_LOG\""
                    for item in imports
                ],
                f'"$FLOWCTL" tracker sync "$SPEC_ID" --op {op_expression} '
                f'--event {row["event"]}'
                + (
                    ' --body-file "$BODY_FILE"'
                    if caller_id in BODY_FILE_EVENTS
                    else ""
                ),
            ]
        )
        return _inject_before_last_fi(fence, body)

    def _run_standard(
        self,
        caller_id: str,
        *,
        value: str,
        active: bool,
    ) -> subprocess.CompletedProcess[str]:
        op_expression = '"$OP"'
        if caller_id == "qa":
            op_expression = '"$QA_OP"'
        source = self._instrumented_fence(caller_id, op_expression)
        if caller_id == "plan":
            snapshot = subprocess.run(
                [str(self.fake_flowctl), "config", "get", "--json"],
                env=self._environment(value, active),
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            (self.root / "flow-plan-config-<suffix>.json").write_text(
                snapshot,
                encoding="utf-8",
            )
        return self._run_shell(source, value=value, active=active)

    def _work_outer_fence(self, caller_id: str) -> str:
        phases = REPO_ROOT / "plugins/flow-next/skills/flow-next-work/phases.md"
        heading = {
            "work.firstClaim": "read and execute references/tracker-touchpoints.md#first-claim",
            "work.done": "read and execute references/tracker-touchpoints.md#task-done",
            "completionReview": "read and execute references/tracker-touchpoints.md#completion-review",
        }[caller_id]
        return _shell_if_block_around(phases, heading)

    def _run_work(
        self,
        caller_id: str,
        *,
        value: str,
        active: bool,
    ) -> subprocess.CompletedProcess[str]:
        outer = self._run_shell(self._work_outer_fence(caller_id), value=value, active=active)
        self.assertEqual(outer.returncode, 0, outer.stderr)
        if "GATE ACTIVE" not in outer.stdout:
            return subprocess.CompletedProcess(outer.args, 0, "", "")

        with self.import_log.open("a", encoding="utf-8") as handle:
            handle.write("references/tracker-touchpoints.md\n")
        inner = self._instrumented_fence(caller_id, '"$OP"')
        return self._run_shell(inner, value=value, active=active)

    def _run_make_pr(
        self,
        *,
        value: str,
        active: bool,
    ) -> subprocess.CompletedProcess[str]:
        fence = _single_fence(
            self.sources["makePr"],
            "PR_URL",
            "sync active --json",
            "tracker sync",
        )
        body = "\n".join(
            [
                "printf '%s\\n' 'skill:flow-next-tracker-sync' >> \"$IMPORT_LOG\"",
                '"$FLOWCTL" tracker sync "$SPEC_ID" --op reconcile --event makePr',
            ]
        )
        return self._run_shell(
            _inject_before_last_fi(fence, body),
            value=value,
            active=active,
        )

    def _run_land(
        self,
        *,
        value: str,
        active: bool,
        merged: bool,
    ) -> subprocess.CompletedProcess[str]:
        path = self.sources["land.merged"]
        active_fence = _indented_shell_block(path, "TRACKER_FIRE=0")
        merge_fence = _indented_shell_block(path, 'MERGED_CONFIRMED="$(gh pr list')
        dispatch = textwrap.dedent(
            """\
            if [ "$TRACKER_FIRE" = "1" ]; then
              printf '%s\\n' 'skill:flow-next-tracker-sync' >> "$IMPORT_LOG"
              if [ "$TRACKER_TERMINAL_OK" = "1" ]; then
                "$FLOWCTL" tracker sync "$SPEC_ID" --op push --event land.merged
              else
                "$FLOWCTL" tracker sync "$SPEC_ID" --op comment --event land.merged --body-file "$BODY_FILE"
              fi
            fi
            """
        )
        return self._run_shell(
            "\n".join((active_fence, merge_fence, dispatch)),
            value=value,
            active=active,
            merged=merged,
        )

    def _run_caller(
        self,
        caller_id: str,
        *,
        value: str,
        active: bool,
        merged: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if caller_id in WORK_EVENTS:
            return self._run_work(caller_id, value=value, active=active)
        if caller_id == "makePr":
            return self._run_make_pr(value=value, active=active)
        if caller_id == "land.merged":
            return self._run_land(value=value, active=active, merged=merged)
        return self._run_standard(caller_id, value=value, active=active)

    def _config_calls(self) -> list[list[str]]:
        return [
            argv
            for argv in self._calls()
            if argv[:2] in (["config", "get"], ["sync", "active"])
        ]

    def _facade_calls(self) -> list[list[str]]:
        return [argv for argv in self._calls() if argv[:2] == ["tracker", "sync"]]

    def test_inactive_routes_are_byte_exact_against_pre_teardown_oracle(self) -> None:
        for caller_id, row in self.callers.items():
            with self.subTest(caller=caller_id):
                self._reset_observations()
                result = self._run_caller(caller_id, value="push", active=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self._config_calls(), row["config_reads"]["inactive"])
                self.assertEqual(self._facade_calls(), row["argv"]["inactive"])
                self.assertEqual(self._imports(), row["imports"]["inactive"])
                self.assertEqual(result.stdout, row["stdout"]["inactive"])
                self.assertEqual(result.stderr, row["stderr"]["inactive"])

    def test_every_per_event_value_executes_the_real_caller_gate(self) -> None:
        self.assertEqual(self.values, VALUES)
        for caller_id, row in self.callers.items():
            for value in self.values:
                with self.subTest(caller=caller_id, value=value):
                    self._reset_observations()
                    result = self._run_caller(caller_id, value=value, active=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(self._config_calls(), row["config_reads"]["active"])
                    expected_op = self._expected_op(caller_id, value, merged=True)
                    expected_facades = (
                        [] if expected_op is None else [self._facade_argv(caller_id, expected_op)]
                    )
                    self.assertEqual(self._facade_calls(), expected_facades)
                    expected_imports = []
                    if caller_id in WORK_EVENTS:
                        expected_imports.append("references/tracker-touchpoints.md")
                    if expected_op is not None:
                        if caller_id == "plan":
                            expected_imports.append("references/tracker-projection.md")
                        expected_imports.append("skill:flow-next-tracker-sync")
                    self.assertEqual(self._imports(), expected_imports)
                    self.assertEqual(result.stdout, row["stdout"]["active_success"])
                    self.assertEqual(result.stderr, row["stderr"]["active_success"])

    def test_qa_coerces_every_non_off_value_to_comment(self) -> None:
        for value in VALUES[1:]:
            with self.subTest(value=value):
                self._reset_observations()
                result = self._run_caller("qa", value=value, active=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    self._facade_calls(),
                    [self._facade_argv("qa", "comment")],
                )

    def test_land_status_is_unconditional_and_merge_evidence_selects_operation(self) -> None:
        for value in VALUES:
            for merged, op in ((True, "push"), (False, "comment")):
                with self.subTest(value=value, merged=merged):
                    self._reset_observations()
                    result = self._run_caller(
                        "land.merged",
                        value=value,
                        active=True,
                        merged=merged,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        self._facade_calls(),
                        [self._facade_argv("land.merged", op)],
                    )

    def test_current_active_argv_is_a_declared_delta_from_the_oracle(self) -> None:
        for caller_id, row in self.callers.items():
            with self.subTest(caller=caller_id):
                expected_op = self._expected_op(caller_id, "push", merged=True)
                self.assertIsNotNone(expected_op)
                old_argv = row["argv"]["active"]
                self.assertIn("flow-next-tracker-sync", old_argv)
                self.assertIn("<spec-id>", old_argv)
                if row["resolved_facade_op"] == "configured_value":
                    oracle_operation = "operation:<configured-value>"
                elif caller_id == "land.merged":
                    oracle_operation = "operation:<push-if-merged-else-comment>"
                else:
                    oracle_operation = f"operation:{expected_op}"
                self.assertIn(oracle_operation, old_argv)
                current = self._facade_argv(caller_id, expected_op or "")
                self.assertEqual(current[:3], ["tracker", "sync", "fn-141-harness"])
                self.assertEqual(current[3:5], ["--op", expected_op])
                self.assertEqual(current[5:7], ["--event", row["event"]])


if __name__ == "__main__":
    unittest.main()

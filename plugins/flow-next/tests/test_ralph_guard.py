"""fn-114.3 - Ralph guard defect fixes (structured done-signal, dual-platform,
gated debug, file-tool receipt gate).

Pins the section-C guard fixes without touching the fn-55 canonical-delegation
assertions in test_ralph_guard_codex_delegation.py.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from typing import Optional
from unittest import mock

from pathlib import Path

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = pathlib.Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
GUARD_PY = PLUGIN_DIR / "scripts" / "hooks" / "ralph-guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("ralph_guard_fn114", GUARD_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _drive_hook(
    payload: dict,
    env_extra: Optional[dict] = None,
    *,
    flow_ralph: str = "1",
) -> subprocess.CompletedProcess:
    env = {**os.environ, "FLOW_RALPH": flow_ralph}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(GUARD_PY)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


class DoneDetectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = _load_guard()

    def test_json_status_done_accepted(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --summary-file s.md --evidence-json e.json --json",
            {"stdout": json.dumps({"success": True, "id": "fn-1.2", "status": "done"}), "exit_code": 0},
            json.dumps({"success": True, "id": "fn-1.2", "status": "done"}),
        )
        self.assertTrue(ok)

    def test_word_sniff_rejected(self) -> None:
        # The old sniff matched any response containing "done"/"updated"/"completed".
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --summary-file s.md --evidence-json e.json",
            {"stdout": "something was updated and completed, status ok"},
            "something was updated and completed, status ok",
        )
        self.assertFalse(ok)

    def test_nonzero_exit_rejected(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --json",
            {"stdout": json.dumps({"id": "fn-1.2", "status": "done"}), "exit_code": 1},
            json.dumps({"id": "fn-1.2", "status": "done"}),
        )
        self.assertFalse(ok)

    def test_exact_plain_text_contract(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --summary-file s.md --evidence-json e.json",
            {"stdout": "Task fn-1.2 completed\n"},
            "Task fn-1.2 completed\n",
        )
        self.assertTrue(ok)

    def test_json_flag_without_status_rejected(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --json",
            {"stdout": "Task fn-1.2 completed", "exit_code": 0},
            "Task fn-1.2 completed",
        )
        self.assertFalse(ok)


class DualPlatformMatchersTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = _load_guard()

    def test_shell_and_file_tool_sets(self) -> None:
        self.assertEqual(self.guard.SHELL_TOOLS, frozenset({"Bash", "Execute"}))
        self.assertEqual(
            self.guard.FILE_TOOLS,
            frozenset({"Edit", "Write", "Create", "ApplyPatch"}),
        )

    def test_execute_pretool_runs_command_checks(self) -> None:
        # Execute (Droid shell) must reach the same codex block path as Bash.
        proc = _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Execute",
                "session_id": "dual-shell",
                "tool_input": {"command": "codex exec --output-schema x.json"},
            }
        )
        self.assertEqual(proc.returncode, 2)

    def test_create_file_tool_protected_path(self) -> None:
        proc = _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Create",
                "session_id": "dual-file",
                "tool_input": {"file_path": "/repo/scripts/hooks/ralph-guard.py", "content": "x"},
            }
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("protected file", proc.stderr)


class FileToolReceiptGateTestCase(unittest.TestCase):
    def test_write_receipt_blocked_pre_review(self) -> None:
        receipt = "/tmp/flow-next-test-receipts/impl-fn-1.2.json"
        proc = _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "session_id": "receipt-pre",
                "tool_input": {
                    "file_path": receipt,
                    "content": '{"type":"impl_review","id":"fn-1.2","verdict":"SHIP"}',
                },
            },
            env_extra={"REVIEW_RECEIPT_PATH": receipt},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("before review completes", proc.stderr)


class NeedsHumanReceiptVerdictTestCase(unittest.TestCase):
    def test_needs_human_is_accepted_by_receipt_enum_and_all_verdict_regexes(self) -> None:
        guard = _load_guard()
        self.assertIn("NEEDS_HUMAN", guard.VALID_RECEIPT_VERDICTS)
        source = GUARD_PY.read_text(encoding="utf-8")
        self.assertEqual(source.count("MAJOR_RETHINK|NEEDS_HUMAN"), 3)


class ReviewCounterRecoveryGuardTestCase(unittest.TestCase):
    """fn-159.5: real PreToolUse hook blocks human-only review escapes."""

    def _hook(self, command: str) -> subprocess.CompletedProcess:
        return _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "session_id": "review-counter-recovery",
                "tool_input": {"command": command},
            }
        )

    def test_blocks_spec_reset_review_rounds(self) -> None:
        proc = self._hook("flowctl spec reset-review-rounds fn-159")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_review_rounds_reset(self) -> None:
        proc = self._hook(".flow/bin/flowctl review-rounds reset fn-159 --kind plan")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_force_on_review_dispatch(self) -> None:
        proc = self._hook("$FLOWCTL codex impl-review fn-159.5 --base main --force")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_force_on_review_rounds_increment(self) -> None:
        proc = self._hook(
            "$FLOWCTL review-rounds increment fn-159 --kind plan --force"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_quoted_and_spaced_reset_bypass(self) -> None:
        proc = self._hook('FLOWCTL=.flow/bin/flowctl "$FLOWCTL" spec "reset-review-rounds" fn-159')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_spaced_force_bypass(self) -> None:
        proc = self._hook("flowctl review-rounds increment fn-159 --kind plan \"--force\"")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_python_launcher_reset_bypass(self) -> None:
        proc = self._hook("python3 .flow/bin/flowctl.py spec reset-review-rounds fn-159")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_sh_dash_c_wrapper_bypass(self) -> None:
        proc = self._hook('sh -c "flowctl spec reset-review-rounds fn-159"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_bash_dash_c_wrapper_bypass(self) -> None:
        proc = self._hook("bash -c 'flowctl review-rounds reset fn-159 --kind plan'")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_eval_wrapper_bypass(self) -> None:
        proc = self._hook('eval "flowctl spec reset-review-rounds fn"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_timeout_wrapper_bypass(self) -> None:
        proc = self._hook("timeout 60 flowctl spec reset-review-rounds fn-159")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_env_wrapper_bypass(self) -> None:
        proc = self._hook("env FOO=1 flowctl spec reset-review-rounds fn-159")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_xargs_wrapper_bypass(self) -> None:
        proc = self._hook("xargs -I{} flowctl spec reset-review-rounds {} </tmp/ids")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_wrapper_option_value_bypass(self) -> None:
        # PR #290 bot r8: the stripper dropped a wrapper OPTION but left its
        # separate VALUE token, which then looked like the executable — so no
        # flowctl argv was found and the composed verb was never screened.
        for command in (
            'sub=re; sub+=set; env -u X "$FLOWCTL" review-rounds "$sub" fn-1 --kind plan',
            'sub=re; sub+=set; env --unset=X "$FLOWCTL" review-rounds "$sub" fn-1 --kind plan',
            'env -u X "$FLOWCTL" review-rounds reset fn-1 --kind plan',
            "env -u PATH -C /tmp flowctl spec reset-review-rounds fn-1",
            "timeout -s KILL 60 flowctl spec reset-review-rounds fn-1",
            'timeout -k 5s -s TERM 60 $FLOWCTL review-rounds reset fn-1 --kind plan',
            "xargs -I{} -a /f flowctl spec reset-review-rounds {}",
            "xargs -I {} -a /f flowctl review-rounds reset {} --kind plan",
            "nice -n 5 flowctl spec reset-review-rounds fn-1",
            "stdbuf -o L flowctl review-rounds reset fn-1 --kind plan",
            "sudo -u root $FLOWCTL review-rounds reset fn-1 --kind plan",
            'env -u X "$FLOWCTL" review-rounds increment fn-1 --kind plan --force',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_wrapper_option_values_do_not_widen_the_block(self) -> None:
        # The same consumption must not swallow a legitimate launcher: wrapped
        # `record` / read-only verbs stay allowed.
        for command in (
            'env -u X "$FLOWCTL" review-rounds record fn-1 --kind plan '
            "--review-type plan --backend rp --output-file /tmp/r.txt "
            "--reservation-id r1",
            "timeout -s KILL 60 $FLOWCTL review-rounds record fn-1 --kind plan "
            "--review-type plan --backend rp --output-file /tmp/r.txt "
            "--reservation-id r1",
            "xargs -I{} -a /f $FLOWCTL show {}",
            "nice -n 5 flowctl list",
            "stdbuf -oL $FLOWCTL review-rounds attempts fn-1 --kind plan "
            "--review-type plan",
            'env -u X $FLOWCTL show "$TASK_ID"',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_blocks_command_builtin_wrapper_bypass(self) -> None:
        # PR #290 bot r3: `command` ran the launcher transparently, so the argv
        # pass classified the segment as a `command` invocation and the
        # per-token-quoted verbs slipped past the raw-text floor too.
        proc = self._hook(
            'command "$FLOWCTL" "review-rounds" "reset" fn-1 --kind plan'
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_exec_wrapper_bypass(self) -> None:
        proc = self._hook('exec "$FLOWCTL" "review-rounds" "reset" fn-1 --kind plan')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_builtin_and_sudo_wrapper_bypass(self) -> None:
        for command in (
            "builtin command $FLOWCTL review-rounds reset fn-1 --kind plan",
            "sudo $FLOWCTL review-rounds reset fn-1 --kind plan",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("human-only", proc.stderr)

    def test_command_wrapped_record_is_still_allowed(self) -> None:
        proc = self._hook(
            "command $FLOWCTL review-rounds record fn-159 --kind plan "
            "--review-type plan --backend rp --output-file /tmp/review.txt "
            "--reservation-id r1"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_wrapped_ship_flow_record_is_allowed(self) -> None:
        # Wrapper unwrapping must not widen the block: `review-rounds record`
        # is the system-owned SHIP reset and stays allowed under a wrapper.
        proc = self._hook(
            "timeout 60 sh -c \"$FLOWCTL review-rounds record fn-159 --kind plan "
            "--review-type plan --backend rp --output-file /tmp/review.txt "
            '--reservation-id r1"'
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unparseable_prose_heredoc_is_allowed(self) -> None:
        # Odd apostrophe count -> shlex ValueError. Ordinary Ralph prose writes
        # (summaries, receipts) must NOT be blocked wholesale on parse failure.
        proc = self._hook(
            "cat > /tmp/summary.md << 'MD'\nIt doesn't gate merges.\nMD"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unparseable_command_with_reset_marker_blocked(self) -> None:
        # Same parse failure, but the forbidden verb is present -> fail closed.
        proc = self._hook(
            "cat > /tmp/x << 'MD'\nDon't\nMD\nflowctl review-rounds reset fn-159 --kind plan"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_variable_expanded_recovery_verbs(self) -> None:
        # PR #290 bot r4: the verbs live in assignment VALUES and only meet the
        # launcher at expansion time, so no adjacency screen can see them.
        for command in (
            'verb=review-rounds; sub=reset; "$FLOWCTL" "$verb" "$sub" fn-1 --kind plan',
            'verb=review-rounds; sub="reset"; "$FLOWCTL" "$verb" "$sub" fn-1 --kind plan',
            'v=reset-review-rounds; "$FLOWCTL" spec "$v" fn-1',
            "k=increment; $FLOWCTL review-rounds \"$k\" fn-1 --kind plan --force",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_variable_screen_keeps_legit_flows_allowed(self) -> None:
        # The screen needs BOTH a launcher reference and a guarded-verb
        # assignment; ordinary flowctl use and launcher-free prose stay open.
        for command in (
            "$FLOWCTL review-rounds record fn-1 --kind plan --review-type plan "
            "--backend rp --output-file /tmp/review.txt --reservation-id r1",
            ".flow/bin/flowctl review-rounds record fn-1 --kind plan "
            "--backend rp --output-file /tmp/review.txt --reservation-id r1",
            ".flow/bin/flowctl list",
            "FLOWCTL=.flow/bin/flowctl; $FLOWCTL show fn-1",
            "cat > /tmp/notes.md << 'MD'\nmode=reset was the old plan\nMD",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_blocks_composed_variable_subcommand(self) -> None:
        # PR #290 bot r5: value-matching screens lose to composition — the
        # verb never appears as a literal anywhere in the text. The structural
        # rule ends the arms race: a flowctl SUBCOMMAND position holding an
        # unexpanded expansion is blocked on that ground alone.
        for command in (
            'verb=review; verb="${verb}-rounds"; sub=re; sub="${sub}set"; '
            '"$FLOWCTL" "$verb" "$sub" fn-1 --kind plan',
            'a=rev; b=iew-rounds; "$FLOWCTL" "${a}${b}" reset fn-1 --kind plan',
            '"$FLOWCTL" "$(printf %s review-rounds)" reset fn-1 --kind plan',
            '"$FLOWCTL" review-rounds "`printf %s reset`" fn-1 --kind plan',
            'v=spec; .flow/bin/flowctl "$v" reset-review-rounds fn-1',
            'd=impl-review; "$FLOWCTL" codex "$d" fn-1.1 --base main --force',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_blocks_composed_flag_in_argument_position(self) -> None:
        # PR #290 bot r6: the literal-SUBCOMMAND rule stopped at the
        # subcommand slots, so a composed --force still executed. On a guarded
        # dispatch an expansion is now legal only as the id right after the
        # subcommand or as the value of a literal value-taking flag.
        for command in (
            'flag=--for; flag="${flag}ce"; '
            '"$FLOWCTL" codex impl-review fn-1.1 "$flag"',
            'flag=--for; flag+=ce; "$FLOWCTL" review-rounds increment fn-1 '
            '--kind plan "$flag"',
            '"$FLOWCTL" codex impl-review fn-1.1 --json "$flag"',
            '"$FLOWCTL" cursor plan-review fn-1 "$(printf %s -- --force)"',
            '"$FLOWCTL" copilot completion-review fn-1 --receipt /tmp/r.json "$x"',
            '"$FLOWCTL" codex impl-review "$TASK_ID" $EXTRA',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_shipped_dispatch_fence_shapes_stay_allowed(self) -> None:
        # Every guarded-dispatch invocation flow-next actually ships. The rule
        # is fail-closed, so any of these breaking means the rule is wrong.
        for command in (
            'ROUND_JSON="$($FLOWCTL review-rounds increment "${TASK_ID%.*}" '
            '--kind impl --task "$TASK_ID" --review-type impl '
            '--artifact-file "$ARTIFACT_FILE" --json)"',
            'ROUND_JSON="$("$FLOWCTL" review-rounds increment "$SPEC_ID" '
            '--kind plan --review-type completion '
            '--artifact-file "$ARTIFACT_FILE" --json)"',
            '$FLOWCTL codex impl-review "${args[@]}"',
            '$FLOWCTL cursor impl-review "${args[@]}"',
            'FLOW_REVIEW_BACKEND=cursor:gpt-5.5-high $FLOWCTL cursor impl-review '
            '"$TASK_ID" --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"',
            '$FLOWCTL codex impl-review "$TASK_ID" --spec "codex:gpt-5.5:xhigh" '
            '--receipt "$RECEIPT_PATH"',
            '$FLOWCTL copilot plan-review "$SPEC_ID" --files "$CODE_FILES" '
            '--receipt "$RECEIPT_PATH"',
            '$FLOWCTL codex completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"',
            'scripts/flowctl codex impl-review "${EPIC3}.1" --base HEAD~1 '
            '--receipt "$TEST_DIR/impl-receipt.json" --json',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_shipped_fence_shapes_stay_allowed(self) -> None:
        # Variable ARGUMENTS (ids, paths, --reservation-id) are legal; only the
        # two subcommand positions must be literal. These are the real shapes
        # the plan/impl/completion fences and ralph.sh ship.
        for command in (
            '"$FLOWCTL" review-rounds record "$SPEC_ID" --kind plan '
            '--review-type plan --backend rp --output-file "$RESPONSE" '
            '--reservation-id "$RESERVATION_ID" --status-target plan --json',
            '"$FLOWCTL" review-rounds record "$SPEC_ID" --kind plan '
            '--reservation-id "$(jq -r .reservation_id "$TMP/reserve.json")" '
            '--output-file "$TMP/review.md"',
            '"$FLOWCTL" review-artifact hash --spec "$SPEC_ID" '
            '--out "${TMPDIR:-/tmp}/artifact.json"',
            '"$FLOWCTL" review-findings attach --reservation-id "$RID" '
            '--receipt "$RECEIPT_PATH" --json',
            '"$FLOWCTL" codex impl-review "$TASK_ID" --base "$DIFF_BASE" '
            '--receipt "$RECEIPT_PATH"',
            '"$FLOWCTL" triage-skip --json --receipt "$RECEIPT_PATH"',
            '"$FLOWCTL" list',
            '"$FLOWCTL" show "$TASK_ID"',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_force_with_lease_push_is_allowed(self) -> None:
        proc = self._hook("git push --force-with-lease origin fn-159")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_ship_flow_record_is_allowed_with_blocks_active(self) -> None:
        # fn-159.1 moved SHIP's reset into record, so this ordinary SHIP fence
        # must pass while reset/force blocks are active.
        proc = self._hook(
            "$FLOWCTL review-rounds record fn-159 --kind plan --review-type plan "
            "--backend rp --output-file /tmp/review.txt --reservation-id r1"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


class DebugLogGatingTestCase(unittest.TestCase):
    def test_no_debug_log_without_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {
                **os.environ,
                "FLOW_RALPH": "1",
                "TMPDIR": td,
                "TMP": td,
                "TEMP": td,
            }
            env.pop("RALPH_GUARD_DEBUG", None)
            debug_path = pathlib.Path(td) / "ralph-guard-debug.log"
            if debug_path.exists():
                debug_path.unlink()
            proc = subprocess.run(
                [sys.executable, str(GUARD_PY)],
                input=json.dumps(
                    {
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "session_id": "dbg-off",
                        "tool_input": {"command": "echo hi"},
                    }
                ),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertFalse(debug_path.exists())

    def test_debug_log_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {
                **os.environ,
                "FLOW_RALPH": "1",
                "RALPH_GUARD_DEBUG": "1",
                "TMPDIR": td,
                "TMP": td,
                "TEMP": td,
            }
            debug_path = pathlib.Path(td) / "ralph-guard-debug.log"
            proc = subprocess.run(
                [sys.executable, str(GUARD_PY)],
                input=json.dumps(
                    {
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "session_id": "dbg-on",
                        "tool_input": {"command": "echo hi"},
                    }
                ),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(debug_path.is_file())
            self.assertIn("Hook called", debug_path.read_text(encoding="utf-8"))

    def test_state_file_uses_tempdir(self) -> None:
        guard = _load_guard()
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(guard.tempfile, "gettempdir", return_value=td):
                path = guard.get_state_file("sess-x")
            self.assertEqual(path, pathlib.Path(td) / "ralph-guard-sess-x.json")
            self.assertNotEqual(str(path), "/tmp/ralph-guard-sess-x.json")


class DeadWeightTestCase(unittest.TestCase):
    def test_no_ralph_guard_version(self) -> None:
        guard = _load_guard()
        self.assertFalse(hasattr(guard, "RALPH_GUARD_VERSION"))

    def test_local_dev_points_at_e2e(self) -> None:
        local_dev = PLUGIN_DIR.parent.parent / "agent_docs" / "local-dev.md"
        text = local_dev.read_text(encoding="utf-8")
        self.assertIn("ralph_e2e_test.sh", text)


class UnchangedArtifactDriverTerminalTestCase(unittest.TestCase):
    """fn-159.7: autonomous drivers never spin a delivered hash refusal."""

    MARKER = "NOT_RETRYABLE: artifact unchanged since last verdict"

    def test_plan_flow_stops_without_refund_force_reset_or_redispatch(self) -> None:
        text = (PLUGIN_DIR / "skills" / "flow-next-plan-review" / "workflow.md").read_text()
        self.assertIn(self.MARKER, text)
        for phrase in ("Do not refund", "dispatch again", "--force", "reset"):
            self.assertIn(phrase, text)

    def test_impl_flow_stops_without_refund_force_reset_or_redispatch(self) -> None:
        common = (PLUGIN_DIR / "skills" / "flow-next-impl-review" / "workflow-common.md").read_text()
        skill = (PLUGIN_DIR / "skills" / "flow-next-impl-review" / "SKILL.md").read_text()
        self.assertIn(self.MARKER, common)
        self.assertIn(self.MARKER, skill)
        for phrase in ("never\nrefund", "reset", "--force", "redispatch"):
            self.assertIn(phrase, common + skill)

    def test_completion_flow_stops_without_refund_force_reset_or_redispatch(self) -> None:
        common = (PLUGIN_DIR / "skills" / "flow-next-spec-completion-review" / "workflow-common.md").read_text()
        skill = (PLUGIN_DIR / "skills" / "flow-next-spec-completion-review" / "SKILL.md").read_text()
        self.assertIn(self.MARKER, common)
        self.assertIn(self.MARKER, skill)
        for phrase in ("refund", "reset", "--force", "redispatch"):
            self.assertIn(phrase, common + skill)

    def test_pilot_land_and_ralph_driver_map_marker_to_human_terminal(self) -> None:
        pilot = (PLUGIN_DIR / "skills" / "flow-next-pilot" / "workflow.md").read_text()
        land = (PLUGIN_DIR / "skills" / "flow-next-land" / "workflow.md").read_text()
        ralph = (PLUGIN_DIR / "skills" / "flow-next-ralph-init" / "templates" / "ralph.sh").read_text()
        for text in (pilot, land, ralph):
            self.assertIn(self.MARKER, text)
            self.assertIn("NEEDS_HUMAN", text)
        self.assertIn("exit 1", ralph)
        self.assertNotIn("force_retry=1", ralph[ralph.index(self.MARKER):ralph.index(self.MARKER) + 700])

    def test_ralph_terminal_fires_on_marker_content_alone(self) -> None:
        """fn-159.7 review r1: flowctl exits 1 INSIDE a session that itself
        exits 0, so an rc conjunct would never fire on the common case."""
        ralph = (
            PLUGIN_DIR / "skills" / "flow-next-ralph-init" / "templates" / "ralph.sh"
        ).read_text()
        gate_at = ralph.index(self.MARKER)
        line_start = ralph.rindex("\n", 0, gate_at) + 1
        gate_line = ralph[line_start:ralph.index("\n", gate_at)]
        self.assertIn("grep -Fq", gate_line)
        self.assertNotIn("claude_rc", gate_line)
        # Content-matched terminals elsewhere in the template set the pattern.
        self.assertTrue(gate_line.lstrip().startswith("if grep -Fq"), gate_line)


if __name__ == "__main__":
    unittest.main()


class TestProtectedRegistrationFiles(unittest.TestCase):
    """fn-114 review: the guard must block edits to its own hook registration."""

    def _blocks(self, file_path: str) -> bool:
        import io, contextlib
        guard = _load_guard()
        data = {"tool_name": "Edit", "tool_input": {"file_path": file_path}}
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                guard.handle_protected_file_check(data)
            except SystemExit:
                pass
        return "BLOCKED" in (out.getvalue() + err.getvalue())

    def test_blocks_claude_settings(self) -> None:
        self.assertTrue(self._blocks("/repo/.claude/settings.json"))

    def test_blocks_factory_hooks(self) -> None:
        self.assertTrue(self._blocks("/repo/.factory/hooks.json"))

    def test_blocks_project_codex_hooks(self) -> None:
        self.assertTrue(self._blocks("/repo/.codex/hooks.json"))

    def test_allows_ordinary_file(self) -> None:
        self.assertFalse(self._blocks("/repo/src/app.py"))

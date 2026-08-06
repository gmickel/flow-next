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
import re
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

    def test_blocks_cap_raise_via_config_set_leaf_key(self) -> None:
        """fn-168 R7 route 1: extending the gate is the same self-grant as resetting it."""
        proc = self._hook("$FLOWCTL config set review.maxIterations 99")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_cap_raise_via_config_set_parent_key_json(self) -> None:
        """fn-168 R7 route 1b: the parent-key form writes the same value.

        `_set_config_locked` json.loads-coerces a `{`-leading value and its nested
        walk replaces whole subtrees, so `config set review '{"maxIterations":99}'`
        raises the cap without ever naming the leaf key. A leaf-only screen would
        be security theatre.
        """
        proc = self._hook(
            "$FLOWCTL config set review '{\"maxIterations\": 99}'"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_cap_raise_via_encoded_json_key(self) -> None:
        """An escaped member name must not slip past a substring check.

        `config set` json.loads-coerces the value, which resolves `\u006d` — so
        the guard decodes before comparing member names rather than grepping.
        """
        proc = self._hook(
            '$FLOWCTL config set review \'{"\\u006daxIterations": 99}\''
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_cap_raise_via_composed_key_or_value(self) -> None:
        """Composition leaves no token reading `maxIterations`."""
        for command in (
            'k=maxIter; k="${k}ations"; $FLOWCTL config set "review.$k" 99',
            'v=\'{"maxIter\'; $FLOWCTL config set review "${v}ations\": 99}"',
            'PAYLOAD=99; $FLOWCTL config set review.maxIterations "$PAYLOAD"',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("human-only", proc.stderr)

    def test_blocks_expansion_in_a_review_namespace_config_value(self) -> None:
        """Under `review.*` an unexpanded value is unknowable, so it fails closed."""
        proc = self._hook('$FLOWCTL config set review "$PAYLOAD"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_allows_variable_values_outside_the_review_namespace(self) -> None:
        """The literal-only contract is scoped: other namespaces keep expansions."""
        proc = self._hook(
            '$FLOWCTL config set tracker.perTracker.teamId "$TEAM_ID"'
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_blocks_cap_raise_via_composed_config_subcommand(self) -> None:
        """A composed `set` verb must not skip the cap screen entirely.

        `verb=set; $FLOWCTL config "$verb" review '{"max\\u0049terations":99}'`
        leaves no `config set` text for the raw-text floor and no literal `set`
        token for the argv screen, so `config` joins the guarded subcommand groups
        and an expansion in that slot fails closed.
        """
        proc = self._hook(
            'verb=set; $FLOWCTL config "$verb" review '
            '\'{"max\\u0049terations":99}\''
        )
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("human-only", proc.stderr)

    def test_allows_literal_config_read_with_variable_key(self) -> None:
        """Only the SUBCOMMAND slot is literal-only; arguments stay variable."""
        proc = self._hook('$FLOWCTL config get "$SOME_KEY"')
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_blocks_cap_raise_via_env_assignment(self) -> None:
        """fn-168 R7 route 3: the HIGHER-precedence rung, a pre-existing hole."""
        proc = self._hook(
            "MAX_REVIEW_ITERATIONS=99 $FLOWCTL codex impl-review fn-168.5 --base main"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("human-only", proc.stderr)

    def test_blocks_composed_env_var_name_for_the_cap(self) -> None:
        """PR #295 bot r1: the literal name never appears, the override still lands.

        `n=MAX_REVIEW_; n="${n}ITERATIONS"; export "$n=99"` reaches the review
        process as MAX_REVIEW_ITERATIONS=99 while a whole-name regex sees nothing.
        The screen keys on the distinctive prefix, and an export whose NAME is an
        expansion fails closed beside a launcher.
        """
        for command in (
            'name=MAX_REVIEW_; name="${name}ITERATIONS"; export "$name=99"; '
            "$FLOWCTL codex impl-review fn-168.5 --base main",
            'v=99; export "$v"; $FLOWCTL review-rounds increment fn-168 --kind plan',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("human-only", proc.stderr)

    def test_blocks_shell_writes_to_the_protected_config(self) -> None:
        """PR #295 bot r1: PROTECTED_FILE_PATTERNS screens FILE TOOLS only.

        A Bash write to `.flow/config.json` — redirect, mv-into-place, an
        interpreter opening it for writing, or `sed -i` — never reached
        `handle_protected_file_check`, so the durable cap was settable from the
        shell despite the new invariant.
        """
        for command in (
            "jq '.review.maxIterations=99' .flow/config.json > /tmp/c "
            "&& mv /tmp/c .flow/config.json",
            "python3 -c \"import json;d=json.load(open('.flow/config.json'));"
            "d['review']['maxIterations']=99;json.dump(d,open('.flow/config.json','w'))\"",
            "echo '{\"review\":{\"maxIterations\":99}}' > .flow/config.json",
            "sed -i.bak 's/8/99/' .flow/config.json",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("human-only", proc.stderr)

    def test_blocks_every_shell_reference_to_the_protected_config(self) -> None:
        """PR #295 bot r3: enumerate writer APIs and the list always leaks.

        The first version listed mutation tokens; `Path(...).write_bytes(...)`,
        `os.replace('/tmp/c', <path>)` and `... | sponge <path>` all walked
        straight through, and each is enough to install a larger
        `review.maxIterations`. Any such list is a race against the next writer
        API someone thinks of, so the polarity is inverted: a shell command that
        NAMES the protected config is refused outright.

        Reads are refused too, deliberately. Ralph has no need to shell-read the
        file — `flowctl config get <key>` is the sanctioned path and never spells
        it — and "read-only" is not decidable from a command line.
        """
        for command in (
            # writes the old allowlist missed
            "python3 -c \"from pathlib import Path; "
            "Path('.flow/config.json').write_bytes(b'{}')\"",
            "python3 -c \"import os; os.replace('/tmp/c', '.flow/config.json')\"",
            "jq '.review.maxIterations=99' .flow/config.json | sponge .flow/config.json",
            "install -m644 /tmp/c .flow/config.json",
            # writes it did catch, still caught
            "echo '{}' > .flow/config.json",
            "sed -i.bak 's/8/99/' .flow/config.json",
            # reads: refused under the inverted policy
            "cat .flow/config.json",
            "jq -r .review.backend .flow/config.json",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("human-only", proc.stderr)

    def test_allows_the_sanctioned_config_read_path(self) -> None:
        """`flowctl config get` never spells the path, so it stays legal."""
        for command in (
            "$FLOWCTL config get review.maxIterations --json",
            "$FLOWCTL config get tracker.type --json",
            "cat .flow/meta.json",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_allows_unrelated_config_set_writes(self) -> None:
        """The cap block is scoped to the cap, NOT to `config set`.

        Tracker resolve transactions and setup legitimately write config under
        Ralph; a blanket block would break them.
        """
        for command in (
            "$FLOWCTL config set review.backend codex",
            "$FLOWCTL config set tracker.type linear",
            "$FLOWCTL config get review.maxIterations",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

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

    def test_blocks_combined_interpreter_option_bypass(self) -> None:
        # PR #290 bot r9: only the exact token `-c` was recognized, so every
        # combined short-option cluster a shell accepts (`-lc`, `-xc`, `-lec`)
        # carried the same command string straight past the recursion. The
        # payload composes the verb, so the raw-text floor cannot see it.
        composed = 'sub=re; sub+=set; "$FLOWCTL" review-rounds "$sub" fn-1 --kind plan'
        for command in (
            f"bash -lc '{composed}'",
            f"bash -xc '{composed}'",
            f"bash -lec '{composed}'",
            f"sh -lc -- '{composed}'",
            f"zsh -xec '{composed}'",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_interpreter_option_screen_keeps_legit_shells_allowed(self) -> None:
        # A login shell runs no command string, and an ordinary `-c` payload
        # stays allowed.
        for command in (
            "bash -l",
            "bash -c 'flowctl list'",
            "bash -lc '.flow/bin/flowctl show fn-1'",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_blocks_line_continuation_bypass(self) -> None:
        # fn-159 review F2: `shlex` keeps `\<newline>` as a token of its own,
        # so the verb and its subcommand were never adjacent for either screen
        # — while bash removes the continuation and runs the reset.
        for command in (
            ".flow/bin/flowctl review-rounds \\\n reset fn-1 --kind plan",
            "flowctl spec \\\n reset-review-rounds fn-1",
            'sub=re; sub+=set; "$FLOWCTL" review-rounds \\\n "$sub" fn-1',
            ".flow/bin/flowctl review-rounds \\\r\n reset fn-1",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_blocks_intra_word_line_continuation_bypass(self) -> None:
        # fn-159 verification F1: the collapse substituted a SPACE, but bash
        # removes `\<newline>` ENTIRELY. Every INTRA-word continuation
        # therefore re-split into two harmless tokens for both screens while
        # bash ran the joined word — probe-verified exit 0 before this fix.
        for command in (
            ".flow/bin/flowctl review-rounds re\\\nset fn-1 --kind plan",
            "flowctl spec reset-review-\\\nrounds fn-1",
            "$FLOWCTL codex impl-review fn-1 --base main --fo\\\nrce",
            ".flow/bin/flowctl review-rounds re\\\r\nset fn-1",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_line_continuation_keeps_legit_record_allowed(self) -> None:
        proc = self._hook(
            ".flow/bin/flowctl review-rounds record fn-1 \\\n"
            "  --kind plan --verdict SHIP"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_self_defaulting_launcher_is_not_composition(self) -> None:
        # fn-159 review F5: the composition screen read `${FLOWCTL:-…}` as a
        # self-reference and blocked `review-rounds record` — a REQUIRED fence
        # step — in the preamble's own self-defaulting idiom.
        for value in (
            "${FLOWCTL:-.flow/bin/flowctl}",
            "${FLOWCTL-.flow/bin/flowctl}",
            "${FLOWCTL:=.flow/bin/flowctl}",
            "${FLOWCTL=.flow/bin/flowctl}",
        ):
            command = (
                f'FLOWCTL="{value}"; "$FLOWCTL" review-rounds record fn-1 '
                "--kind plan --verdict SHIP"
            )
            with self.subTest(value=value):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_self_defaulting_launcher_is_screened_as_a_launcher(self) -> None:
        # fn-159 verification F2: the F5 exemption left a self-defaulting
        # launcher var neither launcher-recognized NOR composed, so the whole
        # flowctl argv screen was skipped for it — `"$fc" review-rounds "$V"`
        # ran unscreened (differential probe: 2 before F5, 0 after).
        for command in (
            'fc="${fc:-.flow/bin/flowctl}"; "$fc" review-rounds "$V" fn-1',
            'fc="${fc:-.flow/bin/flowctl}"; "$fc" spec reset-review-rounds fn-1',
            # Both vars self-default; only the launcher one is exempt from the
            # composition screen, and the subcommand slot is still an expansion.
            'L="${L:-.flow/bin/flowctl}"; V="${V:-reset}"; '
            '"$L" review-rounds "$V" fn-1',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_self_defaulting_launcher_with_nested_default_allows_record(self) -> None:
        # The preamble's own shape must stay allowed for the REQUIRED fence step.
        proc = self._hook(
            'FLOWCTL="${FLOWCTL:-${CLAUDE_PLUGIN_ROOT}/scripts/flowctl}"; '
            '"$FLOWCTL" review-rounds record fn-1 --kind plan --verdict SHIP'
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_real_composition_still_blocked(self) -> None:
        for command in (
            'p=.flow/bin/flow; p+=ctl; "$p" review-rounds "$v" fn-1',
            'p=.flow/bin/flow; p="${p}ctl"; "$p" review-rounds "$v" fn-1',
            # A self reference nested INSIDE the default is still composition.
            'p=x; p="${p:-$p}ctl"; "$p" review-rounds "$v" fn-1',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
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

    def test_blocks_variable_backed_launcher(self) -> None:
        # PR #290 bot r9 (a): a variable ASSIGNED a launcher path in the same
        # command text executes the launcher just as surely as spelling it out,
        # so the whole flowctl argv screen — including the literal-subcommand
        # rule — applies to `"$fc"`. Before this, none of these were classified
        # as flowctl argvs at all.
        for command in (
            'fc=.flow/bin/flowctl; v=rev; v+=iew-rounds; s=re; s+=set; '
            '"$fc" "$v" "$s" fn-1 --kind plan',
            'FC="scripts/flowctl"; d=impl; d+=-review; '
            '"$FC" codex "$d" fn-1.1 --base main --force',
            'launcher=/repo/.flow/bin/flowctl.py; a=spe; a+=c; '
            'python3 "$launcher" "$a" reset-review-rounds fn-1',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_variable_backed_launcher_keeps_ordinary_use_allowed(self) -> None:
        # Recognizing the variable must not widen the block: literal
        # subcommands through a bound launcher stay legal.
        for command in (
            "fc=.flow/bin/flowctl; $fc list",
            'fc=.flow/bin/flowctl; "$fc" show fn-1',
            'fc=.flow/bin/flowctl; "$fc" review-rounds record fn-1 --kind plan '
            "--review-type plan --backend rp --output-file /tmp/r.txt "
            '--reservation-id "$RID"',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_composition_plus_indirect_execution_fails_closed(self) -> None:
        # PR #290 bot r9 (b): the structural screen. Composition means no verb
        # (and no launcher path) ever appears as a literal, so the guard cannot
        # know what runs — and no fence has this shape. Blocked on structure,
        # regardless of content.
        for command in (
            # Launcher path itself composed: never matches the launcher regex.
            'p=.flow/bin/flow; p+=ctl; v=review-rounds; s=reset; "$p" "$v" "$s" fn-1',
            'p=/repo/.flow/bin/flow; p="${p}ctl"; "$p" spec reset-review-rounds fn-1',
            # Composed executable that expands to something unknowable.
            'x=fl; x+=owctl; y=re; y+=set; $x review-rounds "$y" fn-1 --kind plan',
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("human-only", proc.stderr)

    def test_composition_screen_leaves_argument_arrays_alone(self) -> None:
        # The shipped fences compose ARGUMENT arrays and expand them in
        # argument position, with launcher and subcommands spelled literally.
        # The screen must never fire on that shape.
        for command in (
            'args=(); [ -n "$TASK_ID" ] && args+=("$TASK_ID"); '
            'args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH"); '
            '$FLOWCTL codex impl-review "${args[@]}"',
            'FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"; '
            'args+=(--base main); "$FLOWCTL" cursor impl-review "$TASK_ID" '
            '"${args[@]}"',
            'EXTRA_FIELDS=",\\"a\\":1"; EXTRA_FIELDS+=",\\"b\\":2"; '
            '"$FLOWCTL" review-rounds record fn-1 --kind plan --review-type plan '
            "--backend rp --output-file /tmp/r.txt --reservation-id r1",
        ):
            with self.subTest(command=command):
                proc = self._hook(command)
                self.assertEqual(proc.returncode, 0, proc.stderr)


class CompositionScreenShippedFenceSweepTestCase(unittest.TestCase):
    """The composition screen must never fire on anything flow-next ships.

    Sweeps every flowctl-bearing bash block in the plugin (canonical skills,
    docs, the codex mirror, and the shell scripts) — the screen is fail-closed,
    so a hit here means the rule is wrong, not that the fence is.
    """

    def test_no_shipped_bash_block_trips_the_composition_screen(self) -> None:
        guard = _load_guard()
        hits = []
        probed = 0
        for path in sorted(PLUGIN_DIR.rglob("*")):
            if not path.is_file() or path.suffix not in (".md", ".sh"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            blocks = (
                re.findall(r"```(?:bash|sh)\n(.*?)```", text, re.S)
                if path.suffix == ".md" else [text]
            )
            for block in blocks:
                if "flowctl" not in block and "FLOWCTL" not in block:
                    continue
                probed += 1
                scan = guard._ShellScan(block)
                argvs = guard._flowctl_argvs(block, scan)
                if argvs is None:
                    continue
                if guard._composed_indirect_execution(scan, argvs):
                    hits.append((str(path), block.strip().splitlines()[0][:70]))
        self.assertGreater(probed, 100, "sweep found no fences to probe")
        self.assertEqual(hits, [])


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
        text = (PLUGIN_DIR / "skills" / "flow-next-plan-review" / "workflow.md").read_text(encoding="utf-8")
        self.assertIn(self.MARKER, text)
        for phrase in ("Do not refund", "dispatch again", "--force", "reset"):
            self.assertIn(phrase, text)

    def test_impl_flow_stops_without_refund_force_reset_or_redispatch(self) -> None:
        common = (PLUGIN_DIR / "skills" / "flow-next-impl-review" / "workflow-common.md").read_text(encoding="utf-8")
        skill = (PLUGIN_DIR / "skills" / "flow-next-impl-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(self.MARKER, common)
        self.assertIn(self.MARKER, skill)
        for phrase in ("never\nrefund", "reset", "--force", "redispatch"):
            self.assertIn(phrase, common + skill)

    def test_completion_flow_stops_without_refund_force_reset_or_redispatch(self) -> None:
        common = (PLUGIN_DIR / "skills" / "flow-next-spec-completion-review" / "workflow-common.md").read_text(encoding="utf-8")
        skill = (PLUGIN_DIR / "skills" / "flow-next-spec-completion-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(self.MARKER, common)
        self.assertIn(self.MARKER, skill)
        for phrase in ("refund", "reset", "--force", "redispatch"):
            self.assertIn(phrase, common + skill)

    def test_pilot_land_and_ralph_driver_map_marker_to_human_terminal(self) -> None:
        pilot = (PLUGIN_DIR / "skills" / "flow-next-pilot" / "workflow.md").read_text(encoding="utf-8")
        land = (PLUGIN_DIR / "skills" / "flow-next-land" / "workflow.md").read_text(encoding="utf-8")
        ralph = (PLUGIN_DIR / "skills" / "flow-next-ralph-init" / "templates" / "ralph.sh").read_text(encoding="utf-8")
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
        ).read_text(encoding="utf-8")
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

    def test_blocks_flow_config_json(self) -> None:
        """fn-168 R7 route 2: the cap has a persistent rung in .flow/config.json.

        Without this, an agent could raise `review.maxIterations` with a file tool
        and never go near `flowctl config set`. File tools only — flowctl's own
        writers (`config set`, tracker resolve) do not pass through here.
        """
        self.assertTrue(self._blocks("/repo/.flow/config.json"))

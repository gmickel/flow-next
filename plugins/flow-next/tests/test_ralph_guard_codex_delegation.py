"""Ralph-guard amendment + host circuit-breaker prose contract for Codex
implementation-delegation (fn-55.5, R8 + R9).

Two surfaces:

  * ``ralph-guard.py`` ``is_canonical_codex_delegation`` — the PreToolUse Bash
    allowance. It allows ONLY the FULL canonical delegation shape (inline
    ``FLOW_DELEGATE_CODEX=1`` + ``codex exec`` + ``--ignore-user-config`` +
    ``--output-schema`` + ``-o .flow/tmp/codex-*`` + a sandbox flag, NO
    ``--last``/``resume``/``review``) — NOT merely the sentinel's presence. A
    sentinel-prefixed but otherwise-arbitrary command STILL blocks.
  * The prose contract authored in this task: the
    ``references/codex-delegation.md`` circuit-breaker/Ralph-safe/attribution
    section is FILLED (no stub); ``worker.md`` carries the ``DELEGATION_RESULT=``
    /``DELEGATION_ACTION=`` terminal signal + ``evidence.delegation`` inline +
    the ``AI-Orchestrator``/``AI-Implementer`` trailers + the ``REVIEW_MODE=none``
    verification backstop; ``phases.md`` carries the host-owned counter + the
    bridge (``rollback_and_disable`` → immediate disable; 3 strikes → disable;
    ``commit`` → reset).

The guard helper is PURE (no git, no model), so we both unit-test it in-process
AND drive the FULL hook end-to-end as a subprocess (the production path —
``FLOW_RALPH=1`` + a PreToolUse Bash event), asserting allow == exit 0 and
block == exit 2.

``ralph-guard.py`` is a hook (NOT dogfooded into ``.flow/bin``), so it is
single-copy — no dual-copy invariant to assert here.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
TESTS_DIR = HERE.parent
PLUGIN_DIR = TESTS_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
GUARD_PY = PLUGIN_DIR / "scripts" / "hooks" / "ralph-guard.py"
WORK_SKILL = PLUGIN_DIR / "skills" / "flow-next-work"
REFERENCE_MD = WORK_SKILL / "references" / "codex-delegation.md"
PHASES_MD = WORK_SKILL / "phases.md"
WORKER_MD = PLUGIN_DIR / "agents" / "worker.md"


def _load_guard():
    spec = importlib.util.spec_from_file_location("ralph_guard_under_test", GUARD_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# A fully canonical yolo invocation, lifted from the reference's invocation block.
CANONICAL_YOLO = (
    'FLOW_DELEGATE_CODEX=1 codex exec --ignore-user-config -m "gpt-5.5" '
    "-c 'model_reasoning_effort=\"medium\"' "
    "--dangerously-bypass-approvals-and-sandbox "
    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json "
    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json "
    "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md"
)
# A fully canonical full-auto invocation (-s workspace-write).
CANONICAL_FULLAUTO = (
    'FLOW_DELEGATE_CODEX=1 codex exec --ignore-user-config -m "gpt-5.5" '
    "-c 'model_reasoning_effort=\"high\"' -s workspace-write "
    "--output-schema .flow/tmp/codex-fn-9.1/result-schema.json "
    "-o .flow/tmp/codex-fn-9.1/result-batch-1.json "
    "- < .flow/tmp/codex-fn-9.1/prompt-batch-1.md"
)


def _drive_hook(command: str) -> int:
    """Run ralph-guard.py as the real PreToolUse Bash hook; return its exit code.

    Exit 0 = allowed (passed all checks); exit 2 = blocked (``output_block``).
    This exercises the production path — the same JSON envelope Claude Code feeds
    the hook — not just the helper in isolation.
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "session_id": "test-session",
        "tool_input": {"command": command},
    }
    # Inherit the real env (PATH + SYSTEMROOT on Windows so the python subprocess
    # can start) and just activate the guard. A bare {FLOW_RALPH, Unix PATH} env
    # strips SYSTEMROOT and breaks python on the Windows runner — the guard only
    # parses the command STRING, so the ambient env is harmless.
    proc = subprocess.run(
        [sys.executable, str(GUARD_PY)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "FLOW_RALPH": "1"},
    )
    return proc.returncode


# ── Pure helper (in-process) ──────────────────────────────────────────────────


class CanonicalDelegationHelperTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = _load_guard()

    def ok(self, cmd: str) -> bool:
        return self.guard.is_canonical_codex_delegation(cmd)

    # --- allow: the full canonical shape ---

    def test_canonical_yolo_allowed(self) -> None:
        self.assertTrue(self.ok(CANONICAL_YOLO))

    def test_canonical_fullauto_allowed(self) -> None:
        self.assertTrue(self.ok(CANONICAL_FULLAUTO))

    def test_canonical_with_dot_slash_o_target_allowed(self) -> None:
        # `-o ./.flow/tmp/codex-*` is still under the scratch dir.
        self.assertTrue(
            self.ok(CANONICAL_YOLO.replace("-o .flow/tmp", "-o ./.flow/tmp"))
        )

    # --- block: NOT merely the sentinel's presence ---

    def test_bare_codex_exec_blocked(self) -> None:
        self.assertFalse(self.ok("codex exec --output-schema x.json"))

    def test_sentinel_plus_last_blocked(self) -> None:
        # The headline acceptance case: sentinel-prefixed but --last → still block.
        self.assertFalse(self.ok("FLOW_DELEGATE_CODEX=1 codex exec --last"))

    def test_canonical_with_last_appended_blocked(self) -> None:
        # Even an otherwise-canonical shape with --last is blocked.
        self.assertFalse(self.ok(CANONICAL_YOLO + " --last"))

    def test_last_hidden_as_m_value_blocked(self) -> None:
        # `-m --last` would swallow --last as the model value, slipping past the
        # per-option check. The global token-level `--last` reject + the -m model
        # charset both block it.
        self.assertFalse(self.ok(CANONICAL_YOLO.replace('-m "gpt-5.5"', "-m --last")))

    def test_canonical_missing_model_blocked(self) -> None:
        # `-m` is REQUIRED, not optional: with --ignore-user-config a missing -m
        # falls back to codex's built-in default model (NOT gpt-5.5), violating
        # the "model always passed explicitly from flow config" contract (R6/R9).
        self.assertFalse(self.ok(CANONICAL_YOLO.replace('-m "gpt-5.5" ', "")))

    def test_m_value_starting_with_dash_blocked(self) -> None:
        # A model value that starts with `-` (a parked flag) → block.
        self.assertFalse(self.ok(CANONICAL_YOLO.replace('-m "gpt-5.5"', "-m -evil")))

    def test_last_anywhere_in_tokens_blocked(self) -> None:
        # --last appearing anywhere (even after the prompt) → global reject.
        self.assertFalse(self.ok(CANONICAL_YOLO + " --last extra"))

    def test_missing_ignore_user_config_blocked(self) -> None:
        self.assertFalse(
            self.ok(CANONICAL_YOLO.replace("--ignore-user-config ", ""))
        )

    def test_missing_output_schema_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json ", ""
                )
            )
        )

    def test_missing_sandbox_flag_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "--dangerously-bypass-approvals-and-sandbox ", ""
                )
            )
        )

    def test_o_target_outside_scratch_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json",
                    "-o /tmp/result-batch-1.json",
                )
            )
        )

    def test_codex_resume_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                "FLOW_DELEGATE_CODEX=1 codex resume --ignore-user-config "
                "--output-schema .flow/tmp/codex-a/s.json "
                "-o .flow/tmp/codex-a/r.json "
                "--dangerously-bypass-approvals-and-sandbox"
            )
        )

    def test_codex_review_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                "FLOW_DELEGATE_CODEX=1 codex review --ignore-user-config "
                "--output-schema .flow/tmp/codex-a/s.json "
                "-o .flow/tmp/codex-a/r.json "
                "--dangerously-bypass-approvals-and-sandbox"
            )
        )

    def test_sentinel_buried_in_args_does_not_pass(self) -> None:
        # The sentinel must precede the `codex` token (it is an env prefix). A
        # sentinel that appears AFTER `codex exec` is not an env-prefix → block.
        self.assertFalse(
            self.ok(
                "codex exec FLOW_DELEGATE_CODEX=1 --ignore-user-config "
                "--output-schema .flow/tmp/codex-a/s.json "
                "-o .flow/tmp/codex-a/r.json "
                "--dangerously-bypass-approvals-and-sandbox"
            )
        )

    # --- block: shell-chaining / second-command bypass (RP finding 1) ---

    def test_chained_trailing_command_blocked(self) -> None:
        # A canonical-looking invocation with a trailing `; rm -rf` must NOT
        # inherit the allowance — it is not a single canonical command.
        self.assertFalse(self.ok(CANONICAL_YOLO + " ; rm -rf /"))

    def test_chained_second_codex_exec_blocked(self) -> None:
        # `&& codex exec --last` rides along on the same Bash call — block.
        self.assertFalse(self.ok(CANONICAL_YOLO + " && codex exec --last"))

    def test_piped_command_blocked(self) -> None:
        self.assertFalse(self.ok(CANONICAL_YOLO + " | tee /tmp/x"))

    def test_command_substitution_blocked(self) -> None:
        self.assertFalse(
            self.ok(CANONICAL_YOLO.replace('-m "gpt-5.5"', "-m $(whoami)"))
        )

    def test_extra_output_redirect_blocked(self) -> None:
        self.assertFalse(self.ok(CANONICAL_YOLO + " > /tmp/leak"))

    def test_newline_chained_command_blocked(self) -> None:
        self.assertFalse(self.ok(CANONICAL_YOLO + "\ncodex exec --last"))

    def test_two_codex_tokens_blocked(self) -> None:
        # Two `codex` tokens (no operator, just whitespace-joined) → not one cmd.
        self.assertFalse(self.ok(CANONICAL_YOLO + " codex exec --last"))

    # --- block: schema / prompt not under the SAME scratch dir (RP finding 2) ---

    def test_schema_outside_scratch_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json",
                    "--output-schema /tmp/schema.json",
                )
            )
        )

    def test_schema_in_different_scratch_dir_blocked(self) -> None:
        # Schema under a DIFFERENT codex-* scratch dir than -o → block.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json",
                    "--output-schema .flow/tmp/codex-other/result-schema.json",
                )
            )
        )

    def test_prompt_outside_scratch_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md",
                    "- < /tmp/prompt.md",
                )
            )
        )

    def test_inline_prompt_no_stdin_redirect_blocked(self) -> None:
        # No `- < <scratch>/…` stdin redirect (inline prompt arg) → block.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md",
                    '"inline prompt text"',
                )
            )
        )

    def test_sibling_prefix_scratch_dir_not_confused(self) -> None:
        # `-o` under codex-fn-1.2 but schema under codex-fn-1.2-evil (a string
        # prefix, NOT the same dir) → block. The trailing-slash anchor prevents
        # the prefix collision.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json",
                    "--output-schema .flow/tmp/codex-fn-1.2-evil/result-schema.json",
                )
            )
        )

    # --- block: quoted-token smuggling (RP re-review finding) ---

    def test_flags_smuggled_inside_quoted_prompt_blocked(self) -> None:
        # The required flags live inside ONE quoted positional arg passed to
        # `codex exec` — substring matching would see them, but `codex exec`
        # actually receives an arbitrary prompt and none of the flags. The
        # shlex/argv parse rejects the unexpected positional token.
        self.assertFalse(
            self.ok(
                'FLOW_DELEGATE_CODEX=1 codex exec "do arbitrary work" '
                '"--ignore-user-config '
                "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json "
                "-o .flow/tmp/codex-fn-1.2/result-batch-1.json "
                "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md "
                '--dangerously-bypass-approvals-and-sandbox"'
            )
        )

    def test_extra_positional_prompt_arg_blocked(self) -> None:
        # An otherwise-canonical command with a stray positional prompt arg → the
        # argv walk hits an unexpected token → block. (Canonical basenames here so
        # the ONLY reason to block is the stray positional, not a bad basename.)
        self.assertFalse(
            self.ok(
                "FLOW_DELEGATE_CODEX=1 codex exec --ignore-user-config "
                "-c 'model_reasoning_effort=\"medium\"' "
                "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json "
                "-o .flow/tmp/codex-fn-1.2/result-batch-1.json "
                "--dangerously-bypass-approvals-and-sandbox "
                '"arbitrary prompt" '
                "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md"
            )
        )

    def test_unbalanced_quotes_blocked(self) -> None:
        # A shlex parse error (unbalanced quote) → block, never crash.
        self.assertFalse(
            self.ok('FLOW_DELEGATE_CODEX=1 codex exec --ignore-user-config "unterminated')
        )

    def test_unknown_flag_blocked(self) -> None:
        # An extra unrecognized flag (not in the canonical allowlist) → block.
        self.assertFalse(self.ok(CANONICAL_YOLO + " --some-unknown-flag"))

    def test_bad_full_auto_sandbox_value_blocked(self) -> None:
        # `-s` must be followed by exactly `workspace-write`.
        self.assertFalse(
            self.ok(
                CANONICAL_FULLAUTO.replace("-s workspace-write", "-s danger-full-access")
            )
        )

    # --- block: arbitrary -c config overrides + duplicate singletons (RP finding) ---

    def test_extra_c_mcp_override_blocked(self) -> None:
        # A second `-c mcp_servers.evil.command=...` would re-enable MCP and
        # silently defeat --ignore-user-config. Only the effort pair is allowed,
        # and -c must appear exactly once.
        self.assertFalse(
            self.ok(CANONICAL_YOLO + ' -c mcp_servers.evil.command="python3"')
        )

    def test_c_non_effort_key_blocked(self) -> None:
        # `-c <anything-but-the-effort-pair>` → block.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "-c 'model_reasoning_effort=\"medium\"'",
                    "-c 'sandbox_workspace_write.network_access=true'",
                )
            )
        )

    def test_c_bad_effort_value_blocked(self) -> None:
        # The effort value must be one of the enum (none|low|medium|high|xhigh).
        self.assertFalse(self.ok(CANONICAL_YOLO.replace("medium", "insane")))

    def test_missing_c_blocked(self) -> None:
        # `-c` is mandatory exactly once (the reference always emits it).
        self.assertFalse(
            self.ok(CANONICAL_YOLO.replace("-c 'model_reasoning_effort=\"medium\"' ", ""))
        )

    def test_duplicate_ignore_user_config_blocked(self) -> None:
        self.assertFalse(self.ok(CANONICAL_YOLO + " --ignore-user-config"))

    def test_duplicate_o_blocked(self) -> None:
        # Second -o with a canonical basename → blocks on the duplicate, not a
        # bad basename.
        self.assertFalse(
            self.ok(CANONICAL_YOLO + " -o .flow/tmp/codex-fn-1.2/result-batch-2.json")
        )

    def test_duplicate_output_schema_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO
                + " --output-schema .flow/tmp/codex-fn-1.2/result-schema.json"
            )
        )

    # --- block: path traversal / containment escape (RP finding) ---

    def test_o_path_traversal_blocked(self) -> None:
        # `.flow/tmp/codex-fn-1.2/../../tasks/x.json` prefix-matches the scratch
        # dir but ESCAPES it — must block.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json",
                    "-o .flow/tmp/codex-fn-1.2/../../tasks/result-batch-1.json",
                )
            )
        )

    def test_schema_path_traversal_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json",
                    "--output-schema .flow/tmp/codex-fn-1.2/../../config.json",
                )
            )
        )

    def test_prompt_path_traversal_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md",
                    "- < .flow/tmp/codex-fn-1.2/../../specs/prompt-batch-1.md",
                )
            )
        )

    def test_nested_subdir_in_scratch_blocked(self) -> None:
        # An extra path segment under the scratch dir is non-canonical.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json",
                    "-o .flow/tmp/codex-fn-1.2/sub/result-batch-1.json",
                )
            )
        )

    def test_wrong_basename_in_scratch_blocked(self) -> None:
        # A non-canonical basename under the scratch dir → block.
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json",
                    "-o .flow/tmp/codex-fn-1.2/evil.sh",
                )
            )
        )

    def test_absolute_o_path_blocked(self) -> None:
        self.assertFalse(
            self.ok(
                CANONICAL_YOLO.replace(
                    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json", "-o /etc/passwd"
                )
            )
        )


# ── Full hook end-to-end (subprocess — the production path) ───────────────────


@unittest.skipIf(
    sys.platform == "win32",
    "Drives the shipped ralph-guard hook as a subprocess; the guard writes session "
    "state to a hardcoded POSIX `/tmp/ralph-guard-*.json` path (a pre-existing "
    "guard limitation, not fn-55) which errors on Windows → the hook exits 1. The "
    "canonical-shape LOGIC is covered in-process by CanonicalDelegationHelperTestCase "
    "on every platform; the end-to-end hook path runs on macOS + ubuntu.",
)
class HookEndToEndTestCase(unittest.TestCase):
    """Drive the SHIPPED hook entry point, not just the helper, so the wiring
    (codex section early-pass + the --last / copilot blocks staying intact) is
    verified on the production path."""

    ALLOWED = 0
    BLOCKED = 2

    def test_canonical_yolo_passes_hook(self) -> None:
        self.assertEqual(_drive_hook(CANONICAL_YOLO), self.ALLOWED)

    def test_canonical_fullauto_passes_hook(self) -> None:
        self.assertEqual(_drive_hook(CANONICAL_FULLAUTO), self.ALLOWED)

    def test_bare_codex_exec_blocked_by_hook(self) -> None:
        self.assertEqual(_drive_hook("codex exec --output-schema x.json"), self.BLOCKED)

    def test_sentinel_plus_last_blocked_by_hook(self) -> None:
        self.assertEqual(
            _drive_hook("FLOW_DELEGATE_CODEX=1 codex exec --last"), self.BLOCKED
        )

    def test_sentinel_missing_ignore_user_config_blocked_by_hook(self) -> None:
        self.assertEqual(
            _drive_hook(CANONICAL_YOLO.replace("--ignore-user-config ", "")),
            self.BLOCKED,
        )

    def test_codex_dash_dash_last_blocked_by_hook(self) -> None:
        # A flowctl-codex wrapper carrying --last must still be blocked (the
        # --last guard fires for any non-canonical codex invocation).
        self.assertEqual(
            _drive_hook("flowctl codex impl-review fn-1.2 --last"), self.BLOCKED
        )

    def test_copilot_still_blocked_by_hook(self) -> None:
        # The copilot block must stay intact (we did not touch it).
        self.assertEqual(_drive_hook("copilot --prompt foo"), self.BLOCKED)

    def test_flowctl_codex_wrapper_still_allowed_by_hook(self) -> None:
        self.assertEqual(
            _drive_hook("flowctl codex impl-review fn-1.2"), self.ALLOWED
        )

    def test_non_codex_command_passes_hook(self) -> None:
        self.assertEqual(_drive_hook("echo hello"), self.ALLOWED)

    def test_chained_trailing_command_blocked_by_hook(self) -> None:
        # The headline finding-1 case on the production path: a canonical-looking
        # invocation with a trailing `; codex exec --last` must STILL be blocked.
        self.assertEqual(
            _drive_hook(CANONICAL_YOLO + " ; codex exec --last"), self.BLOCKED
        )

    def test_schema_outside_scratch_blocked_by_hook(self) -> None:
        self.assertEqual(
            _drive_hook(
                CANONICAL_YOLO.replace(
                    "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json",
                    "--output-schema /tmp/schema.json",
                )
            ),
            self.BLOCKED,
        )

    def test_quoted_smuggled_flags_blocked_by_hook(self) -> None:
        # Quoted-token smuggling on the production path: flags inside a quoted
        # positional arg must STILL be blocked by the shipped hook.
        self.assertEqual(
            _drive_hook(
                'FLOW_DELEGATE_CODEX=1 codex exec "do arbitrary work" '
                '"--ignore-user-config '
                "--output-schema .flow/tmp/codex-fn-1.2/result-schema.json "
                "-o .flow/tmp/codex-fn-1.2/result-batch-1.json "
                "- < .flow/tmp/codex-fn-1.2/prompt-batch-1.md "
                '--dangerously-bypass-approvals-and-sandbox"'
            ),
            self.BLOCKED,
        )

    def test_extra_c_mcp_override_blocked_by_hook(self) -> None:
        # The security-critical case on the production path: an extra
        # `-c mcp_servers.…` that would re-enable MCP must be blocked.
        self.assertEqual(
            _drive_hook(
                CANONICAL_YOLO + ' -c mcp_servers.evil.command="python3"'
            ),
            self.BLOCKED,
        )

    def test_o_path_traversal_blocked_by_hook(self) -> None:
        # Path-traversal containment escape on the production path → block.
        self.assertEqual(
            _drive_hook(
                CANONICAL_YOLO.replace(
                    "-o .flow/tmp/codex-fn-1.2/result-batch-1.json",
                    "-o .flow/tmp/codex-fn-1.2/../../tasks/result-batch-1.json",
                )
            ),
            self.BLOCKED,
        )

    def test_last_hidden_as_m_value_blocked_by_hook(self) -> None:
        # `-m --last` on the production path must STILL be blocked.
        self.assertEqual(
            _drive_hook(CANONICAL_YOLO.replace('-m "gpt-5.5"', "-m --last")),
            self.BLOCKED,
        )


# ── Version bump ──────────────────────────────────────────────────────────────


class RalphGuardVersionTestCase(unittest.TestCase):
    def test_version_bumped_past_0_14(self) -> None:
        guard = _load_guard()
        ver = guard.RALPH_GUARD_VERSION
        major, minor, *_ = (int(p) for p in ver.split("."))
        # fn-55.5 bumps the guard; must be strictly newer than the 0.14.0 baseline.
        self.assertGreaterEqual(
            (major, minor), (0, 15), f"RALPH_GUARD_VERSION not bumped: {ver}"
        )


# ── Prose contract (reference + worker.md + phases.md) ────────────────────────


class ProseContractTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference = REFERENCE_MD.read_text(encoding="utf-8")
        cls.worker = WORKER_MD.read_text(encoding="utf-8")
        cls.phases = PHASES_MD.read_text(encoding="utf-8")

    def test_reference_stub_is_filled(self) -> None:
        self.assertNotIn("_(stub — authored by fn-55.5)_", self.reference)

    def test_reference_documents_host_owned_counter_bridge(self) -> None:
        for token in (
            "rollback_and_disable",
            "consecutive_failures",
            "DELEGATION_RESULT",
            "DELEGATION_ACTION",
        ):
            self.assertIn(token, self.reference, f"reference missing {token}")

    def test_reference_documents_ralph_safe_consent_gate(self) -> None:
        self.assertIn("work.delegateConsent", self.reference)
        # Confabulation guard (memory drop-receipt-to-break-codex).
        self.assertIn("REVIEW_RECEIPT_PATH", self.reference)

    def test_worker_emits_terminal_delegation_signal(self) -> None:
        self.assertIn("DELEGATION_RESULT=", self.worker)
        self.assertIn("DELEGATION_ACTION=", self.worker)

    def test_worker_inlines_evidence_delegation(self) -> None:
        # The result is INLINED (no scratch-file pointer that would dangle).
        self.assertIn("evidence.delegation", self.worker)
        self.assertNotIn("result_file", self.worker)

    def test_worker_carries_attribution_trailers(self) -> None:
        self.assertIn("AI-Orchestrator: Claude", self.worker)
        self.assertIn("AI-Implementer: codex", self.worker)

    def test_worker_review_none_verification_backstop(self) -> None:
        # When REVIEW_MODE=none + delegation, the worker runs its own verification
        # and does not trust verification_summary as the sole gate.
        self.assertIn("verification_summary", self.worker)
        self.assertIn("REVIEW_MODE", self.worker)

    def test_phases_host_owned_circuit_breaker(self) -> None:
        self.assertIn("consecutive_failures", self.phases)
        self.assertIn("rollback_and_disable", self.phases)
        self.assertIn("delegation_active = false", self.phases)

    def test_phases_three_strikes_then_reset(self) -> None:
        # 3 strikes disables; success resets to 0.
        self.assertIn("consecutive_failures >= 3", self.phases)
        self.assertIn("consecutive_failures = 0", self.phases)


if __name__ == "__main__":
    unittest.main()

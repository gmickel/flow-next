"""Unit tests for fn-76 strongest-available model resolution.

Covers the optimistic-first happy path (R2), the fallback ladder on the
distinctive model-unavailable signatures only (R3), the per-CLI-version cache
(R4), and floor-rung hygiene / receipt recording (R5). Everything is mocked —
NO live CLI is invoked. The one live capture allowed for this task (the cursor
model-unavailable signature) is pinned verbatim as a fixture below.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from typing import Any, Optional

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location("flowctl_under_test_mr", flowctl_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()
BackendSpec = flowctl.BackendSpec
BACKEND_REGISTRY = flowctl.BACKEND_REGISTRY


# --- Captured signature fixtures (live probes 2026-07-10) ---
#
# codex / copilot: verbatim substrings from the 2026-07-10 live probes (spec
# "Live verification base"). cursor: captured live during THIS task (fn-76.1) by
# dispatching a fake model id — ``cursor-agent -p --output-format json --trust
# --mode ask --model definitely-not-a-model-xyz "OK"`` on 2026-07-10. The
# distinctive substring is ``Cannot use this model:``.
CODEX_UNAVAILABLE_STREAM = (
    '{"type":"error","message":"stream error: unexpected status 400 Bad '
    "Request: {\\\"error\\\":{\\\"message\\\":\\\"The 'gpt-5.6-sol' model "
    'requires a newer version of Codex. Please upgrade.","type":'
    '"invalid_request_error"}}"}'
)
COPILOT_UNAVAILABLE_STREAM = (
    'Model "gpt-5.6-sol" from --model flag is not available. '
    "Run /model to see the available models."
)
# Verbatim tail of the live cursor-agent stderr (2026-07-10 capture, truncated).
CURSOR_UNAVAILABLE_STREAM = (
    "Cannot use this model: definitely-not-a-model-xyz. "
    "Available models: auto, gpt-5.6-sol-high, gpt-5.5-high, gpt-5.4-high, "
    "composer-2.5, claude-opus-4-8-thinking-high"
)

# Ranking handles derived from the registry (the source of truth) so a ranking
# change does not require editing every assertion in this file. The literal ids
# above stay literal: they are captured CLI error text, i.e. fixture data.
CODEX_TOP, CODEX_SECOND, CODEX_THIRD = BACKEND_REGISTRY["codex"]["models"][:3]
COPILOT_TOP, COPILOT_SECOND = BACKEND_REGISTRY["copilot"]["models"][:2]
CURSOR_TOP = BACKEND_REGISTRY["cursor"]["models"][0]

CODEX_OK_STREAM = '{"type":"thread.started","thread_id":"t1"}\n{"type":"agent_message","message":"<verdict>SHIP</verdict>"}'
CURSOR_OK_STREAM = '{"type":"result","is_error":false,"result":"ok","session_id":"s1"}'

# claude (fn-221): probed 2026-09-05 on Claude Code 2.1.260. A bad ``--model``
# EXITS 0; the signature is the JSON payload (``is_error`` + ``api_error_status``
# 404 + the selected-model text) and/or the stderr tag. Exit code is never the
# signal, so every claude fixture below returns rc 0.
CLAUDE_TOP, CLAUDE_SECOND, CLAUDE_THIRD = BACKEND_REGISTRY["claude"]["models"][:3]
CLAUDE_OK_STREAM = (
    '{"type":"result","subtype":"success","is_error":false,'
    '"result":"<verdict>SHIP</verdict>","session_id":"claude-s1"}'
)
CLAUDE_UNAVAILABLE_STDERR = (
    "[claude-code:unrecognized_model] Model not found: definitely-not-a-model"
)
# The fixed read-only argv every claude dispatch carries (fn-221 R2).
CLAUDE_FIXED_ARGV = [
    "-p", "--output-format", "json", "--permission-mode", "dontAsk",
    "--tools", "Read", "Grep", "Glob", "--strict-mcp-config",
]


def _claude_result(
    *, is_error=True, status=404, text="There's an issue with the selected model."
) -> str:
    """Build a claude result payload; ``status=None`` omits api_error_status."""
    payload = {
        "type": "result",
        "subtype": "error" if is_error else "success",
        "is_error": is_error,
        "result": text,
        "session_id": "claude-s1",
    }
    if status is not None:
        payload["api_error_status"] = status
    return json.dumps(payload)


CLAUDE_UNAVAILABLE_JSON = _claude_result()


def _model_of(argv: list) -> Optional[str]:
    """Return the ``--model`` value in an argv, or None (floor omits --model)."""
    if "--model" in argv:
        return argv[argv.index("--model") + 1]
    return None


class _Fake:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@contextmanager
def _scripted(module, *, dispatch_result, version="0.142", list_models=None, calls=None, inputs=None):
    """Stub subprocess.run + shutil.which for the review CLIs.

    ``dispatch_result(model) -> (stdout, stderr, rc)`` decides each dispatch's
    outcome by the ``--model`` value (None = floor). ``--version`` returns
    ``version``; ``--list-models`` returns ``list_models`` (newline-joined).
    Every call's argv is appended to ``calls`` (when given); each dispatch's
    ``input=`` kwarg (stdin delivery, claude) to ``inputs``. ``git`` argv is
    passed through to the real subprocess so fixtures can read a repo.
    """
    real_run = module.subprocess.run
    real_which = module.shutil.which

    def fake_run(cmd, **kwargs):
        argv = list(cmd)
        if argv and argv[0] == "git":
            return real_run(cmd, **kwargs)
        if calls is not None:
            calls.append(argv)
        if inputs is not None and "--version" not in argv:
            inputs.append(kwargs.get("input"))
        if "--version" in argv:
            return _Fake(stdout=version, returncode=0)
        if "--list-models" in argv:
            # REAL cursor-agent format (live-verified 2026-07-10): a header line
            # then one "<id> - <Description>" line per model — the parser must
            # cope with the descriptions, not bare ids (the bug the first cut
            # of _cursor_list_models had).
            lines = ["Available models", ""]
            lines += [f"{m} - Humanized {m.upper()} Description" for m in (list_models or [])]
            return _Fake(stdout="\n".join(lines), returncode=0 if list_models is not None else 1)
        out, err, rc = dispatch_result(_model_of(argv))
        return _Fake(stdout=out, stderr=err, returncode=rc)

    def fake_which(binary):
        if binary in ("codex", "copilot", "cursor-agent", "claude"):
            return f"/fake/bin/{binary}"
        return real_which(binary)

    module.subprocess.run = fake_run
    module.shutil.which = fake_which
    try:
        yield
    finally:
        module.subprocess.run = real_run
        module.shutil.which = real_which


@contextmanager
def _repo():
    with tempfile.TemporaryDirectory(prefix="fn76-cache-") as td:
        root = Path(td)
        (root / ".flow").mkdir()
        yield root


def _cache_models(root: Path) -> dict:
    data = json.loads(
        (root / ".flow" / ".cache" / "model-resolution.json").read_text(
            encoding="utf-8"
        )
    )
    return {key: value["model"] for key, value in data.items()}


def _cache_worker(
    root: Path, operation: str, backend: str, intent: str, model: str = ""
) -> subprocess.CompletedProcess:
    flowctl_path = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"
    call = (
        f"m._model_cache_put(root, {backend!r}, 'v', {intent!r}, {model!r})"
        if operation == "put"
        else f"m._model_cache_invalidate(root, {backend!r}, 'v', {intent!r})"
    )
    script = (
        "import importlib.util, pathlib, sys\n"
        f"p = pathlib.Path({str(flowctl_path)!r})\n"
        "s = importlib.util.spec_from_file_location('cache_worker_flowctl', p)\n"
        "m = importlib.util.module_from_spec(s); sys.modules[s.name] = m\n"
        "s.loader.exec_module(m)\n"
        f"root = pathlib.Path({str(root)!r})\n"
        f"{call}\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )


# --- Signature detectors ---


class TestSignatureDetectors(unittest.TestCase):
    def test_codex_signature_matches(self) -> None:
        self.assertTrue(flowctl._codex_model_unavailable(CODEX_UNAVAILABLE_STREAM, ""))
        self.assertTrue(flowctl._codex_model_unavailable("", "model_not_found"))

    def test_copilot_signature_matches(self) -> None:
        self.assertTrue(
            flowctl._copilot_model_unavailable("", COPILOT_UNAVAILABLE_STREAM)
        )

    def test_cursor_signature_matches(self) -> None:
        self.assertTrue(
            flowctl._cursor_model_unavailable("", CURSOR_UNAVAILABLE_STREAM)
        )

    def test_claude_signature_matches(self) -> None:
        # fn-221 R3: the full JSON signature, or the stderr tag alone.
        self.assertTrue(
            flowctl._claude_model_unavailable(json.loads(CLAUDE_UNAVAILABLE_JSON), "")
        )
        self.assertTrue(
            flowctl._claude_model_unavailable(None, CLAUDE_UNAVAILABLE_STDERR)
        )
        self.assertTrue(
            flowctl._claude_model_unavailable(
                json.loads(_claude_result(status=None)), CLAUDE_UNAVAILABLE_STDERR
            )
        )

    def test_claude_partial_signatures_do_not_match(self) -> None:
        # A 404 without the selected-model text, the text without a 404, a
        # non-error payload, or no payload at all: transport failures, never a
        # ladder step (fn-221 R3 negative fixtures).
        for payload in (
            json.loads(_claude_result(text="Request failed")),
            json.loads(_claude_result(status=None)),
            json.loads(_claude_result(status=500)),
            json.loads(_claude_result(is_error=False)),
            None,
        ):
            with self.subTest(payload=payload):
                self.assertFalse(
                    flowctl._claude_model_unavailable(payload, "connection reset")
                )

    def test_non_signature_failures_do_not_match(self) -> None:
        # Auth / network / sandbox / timeout must never look like model-unavailable.
        for blob in (
            "error: 401 Unauthorized",
            "connection reset by peer",
            "sandbox denied write access",
            "codex exec timed out (600s)",
        ):
            self.assertFalse(flowctl._codex_model_unavailable(blob, ""))
            self.assertFalse(flowctl._copilot_model_unavailable(blob, ""))
            self.assertFalse(flowctl._cursor_model_unavailable(blob, ""))


# --- R2: optimistic-first happy path ---


class TestHappyPath(unittest.TestCase):
    def test_codex_happy_path_dispatches_ranking_top_once_no_probe(self) -> None:
        calls: list = []
        with _scripted(
            flowctl,
            dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0),
            calls=calls,
        ):
            with _repo() as root:
                out, tid, rc, err = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"),
                    repo_root=root,
                )
        self.assertEqual(rc, 0)
        # Exactly ONE subprocess: the dispatch. No --version, no --list-models.
        self.assertEqual(len(calls), 1)
        self.assertNotIn("--version", calls[0])
        self.assertEqual(_model_of(calls[0]), CODEX_TOP)  # ranking top

    def test_codex_happy_argv_byte_identical_to_hardcoded_default(self) -> None:
        # The unconfigured dispatch argv must equal an EXPLICIT ranking-top pin.
        unconf: list = []
        explicit: list = []
        with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), calls=unconf):
            with _repo() as root:
                flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
        with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), calls=explicit):
            with _repo() as root:
                flowctl.run_codex_exec(
                    "p", sandbox="read-only",
                    spec=BackendSpec.parse(f"codex:{CODEX_TOP}:high"), repo_root=root,
                )
        self.assertEqual(unconf[0], explicit[0])

    def test_copilot_happy_path_dispatches_ranking_top_once(self) -> None:
        calls: list = []
        with _scripted(flowctl, dispatch_result=lambda m: ("SHIP", "", 0), calls=calls):
            with _repo() as root:
                out, sid, rc, err = flowctl.run_copilot_exec(
                    "p", "sess", root, spec=BackendSpec("copilot"),
                )
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(_model_of(calls[0]), COPILOT_TOP)  # ranking top

    def test_cursor_happy_path_no_list_call(self) -> None:
        calls: list = []
        with _scripted(flowctl, dispatch_result=lambda m: (CURSOR_OK_STREAM, "", 0), calls=calls):
            with _repo() as root:
                out, sid, rc, err = flowctl.run_cursor_exec(
                    "p", spec=BackendSpec("cursor"), repo_root=root,
                )
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)  # no --list-models on the happy path
        self.assertEqual(_model_of(calls[0]), CURSOR_TOP)


# --- R3: fallback ladder (signature-only) ---


class TestCodexLadder(unittest.TestCase):
    def test_ladder_steps_down_on_signature(self) -> None:
        # the ranking top fails the signature; the next rung succeeds.
        def result(model):
            if model == CODEX_TOP:
                return (CODEX_UNAVAILABLE_STREAM, "", 1)
            return (CODEX_OK_STREAM, "", 0)

        calls: list = []
        err = io.StringIO()
        with _scripted(flowctl, dispatch_result=result, calls=calls):
            with _repo() as root, redirect_stderr(err):
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root,
                )
        self.assertEqual(rc, 0)
        dispatched = [_model_of(c) for c in calls if "exec" in c]
        self.assertEqual(dispatched[:2], [CODEX_TOP, CODEX_SECOND])
        self.assertIn(f"downgraded to '{CODEX_SECOND}'", err.getvalue())

    def test_non_signature_failure_propagates_without_ladder(self) -> None:
        # A generic (non-signature) failure must NOT trigger a step-down.
        calls: list = []
        with _scripted(flowctl, dispatch_result=lambda m: ("", "boom: 500 server error", 1), calls=calls):
            with _repo() as root:
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root,
                )
        self.assertEqual(rc, 1)
        dispatched = [c for c in calls if "exec" in c]
        self.assertEqual(len(dispatched), 1)  # only the top, no ladder

    def test_max_two_steps_then_floor_omits_model_and_effort(self) -> None:
        # top + 2 step-downs all signature-fail → floor omits --model and -c effort.
        calls: list = []
        res = {}

        def result(model):
            return (CODEX_UNAVAILABLE_STREAM, "", 1) if model is not None else (CODEX_OK_STREAM, "", 0)

        with _scripted(flowctl, dispatch_result=result, calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"),
                    repo_root=root, resolution_out=res,
                )
        self.assertEqual(rc, 0)
        dispatched = [_model_of(c) for c in calls if "exec" in c]
        # ranking[0..2] tried, then floor (None = --model omitted).
        self.assertEqual(
            dispatched, [CODEX_TOP, CODEX_SECOND, CODEX_THIRD, None]
        )
        floor_argv = [c for c in calls if "exec" in c][-1]
        self.assertNotIn("--model", floor_argv)
        # R5: the floor omits the model AND the reasoning-effort pin. Asserted on
        # the effort override itself, not on `-c` presence: fn-187 R2 puts an
        # unconditional `-c project_doc_max_bytes=0` on every dispatch (the floor
        # inherits the host project doc too), so bare `-c` is no longer a proxy
        # for "no effort pin".
        joined = " ".join(floor_argv)
        self.assertNotIn("model_reasoning_effort", joined)
        self.assertIn("project_doc_max_bytes=0", floor_argv)
        self.assertTrue(res["floor"])
        self.assertIsNone(res["model"])

    def test_ladder_does_not_touch_review_cap(self) -> None:
        # The cap lives ABOVE the exec wrapper — a ladder retry must never call
        # enforce_and_increment_review_cap.
        original = flowctl.enforce_and_increment_review_cap
        hits = {"n": 0}

        def spy(*a, **k):
            hits["n"] += 1
            return 1

        flowctl.enforce_and_increment_review_cap = spy
        try:
            def result(model):
                return (CODEX_UNAVAILABLE_STREAM, "", 1) if model == CODEX_TOP else (CODEX_OK_STREAM, "", 0)

            with _scripted(flowctl, dispatch_result=result):
                with _repo() as root, redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec(
                        "p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root,
                    )
        finally:
            flowctl.enforce_and_increment_review_cap = original
        self.assertEqual(hits["n"], 0)


class TestCopilotLadder(unittest.TestCase):
    def test_ladder_steps_down_on_signature(self) -> None:
        def result(model):
            if model == COPILOT_TOP:
                return ("", COPILOT_UNAVAILABLE_STREAM, 1)
            return ("SHIP", "", 0)

        calls: list = []
        with _scripted(flowctl, dispatch_result=result, calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, sid, rc, e = flowctl.run_copilot_exec("p", "sess", root, spec=BackendSpec("copilot"))
        self.assertEqual(rc, 0)
        dispatched = [_model_of(c) for c in calls if "-p" in c or "--session-id" in " ".join(c) or "--model" in c]
        self.assertEqual(dispatched[:2], [COPILOT_TOP, COPILOT_SECOND])

    def test_floor_uses_auto_and_omits_effort(self) -> None:
        calls: list = []
        res = {}
        with _scripted(flowctl, dispatch_result=lambda m: ("", COPILOT_UNAVAILABLE_STREAM, 1) if m != "auto" else ("SHIP", "", 0), calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                flowctl.run_copilot_exec("p", "sess", root, spec=BackendSpec("copilot"), resolution_out=res)
        # The lazy --version subprocess may trail the floor dispatch; pick the
        # last actual dispatch (argv carrying --model).
        floor_argv = [c for c in calls if "--model" in c][-1]
        self.assertEqual(_model_of(floor_argv), "auto")
        self.assertNotIn("--effort", floor_argv)
        self.assertEqual(res["model"], "auto")
        self.assertTrue(res["floor"])


class TestCursorLadder(unittest.TestCase):
    def test_consults_list_models_and_picks_best_intersection(self) -> None:
        # top fails; --list-models offers gpt-5.5-high (a lower ranking entry).
        def result(model):
            if model == CURSOR_TOP:
                return (CURSOR_UNAVAILABLE_STREAM, CURSOR_UNAVAILABLE_STREAM, 1)
            return (CURSOR_OK_STREAM, "", 0)

        calls: list = []
        with _scripted(flowctl, dispatch_result=result, list_models=["auto", "gpt-5.5-high", "gpt-5.4-high"], calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, sid, rc, e = flowctl.run_cursor_exec("p", spec=BackendSpec("cursor"), repo_root=root)
        self.assertEqual(rc, 0)
        self.assertTrue(any("--list-models" in c for c in calls))
        dispatched = [_model_of(c) for c in calls if "ask" in c]
        self.assertEqual(dispatched[0], CURSOR_TOP)
        self.assertEqual(dispatched[1], "gpt-5.5-high")  # best list ∩ ranking

    def test_empty_list_falls_to_floor_auto(self) -> None:
        calls: list = []
        res = {}
        with _scripted(flowctl, dispatch_result=lambda m: (CURSOR_UNAVAILABLE_STREAM, CURSOR_UNAVAILABLE_STREAM, 1) if m != "auto" else (CURSOR_OK_STREAM, "", 0), list_models=None, calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                flowctl.run_cursor_exec("p", spec=BackendSpec("cursor"), repo_root=root, resolution_out=res)
        self.assertEqual(res["model"], "auto")
        self.assertTrue(res["floor"])


class TestClaudeLadder(unittest.TestCase):
    """fn-221 R3: the claude ladder keys on the probed signature only."""

    def _run(self, root, result, *, calls=None, inputs=None, version="2.1.260",
             res=None, session_id=None, spec=None):
        with _scripted(flowctl, dispatch_result=result, version=version, calls=calls, inputs=inputs):
            with redirect_stderr(io.StringIO()):
                return flowctl.run_claude_exec(
                    "p", session_id, spec=spec or BackendSpec("claude"),
                    repo_root=root, resolution_out=res,
                )

    def test_steps_down_on_full_json_signature_at_exit_0(self) -> None:
        def result(model):
            if model == CLAUDE_TOP:
                return (CLAUDE_UNAVAILABLE_JSON, "", 0)  # exit 0 on a bad model
            return (CLAUDE_OK_STREAM, "", 0)

        calls: list = []
        inputs: list = []
        with _repo() as root:
            out, sid, rc, err = self._run(root, result, calls=calls, inputs=inputs)
        self.assertEqual(rc, 0)
        self.assertEqual(sid, "claude-s1")
        self.assertEqual(out, "<verdict>SHIP</verdict>")
        self.assertEqual([_model_of(c) for c in calls if "-p" in c], [CLAUDE_TOP, CLAUDE_SECOND])
        self.assertEqual(inputs, ["p", "p"])  # prompt on stdin, every dispatch

    def test_steps_down_on_stderr_tag(self) -> None:
        def result(model):
            if model == CLAUDE_TOP:
                return (_claude_result(status=None), CLAUDE_UNAVAILABLE_STDERR, 0)
            return (CLAUDE_OK_STREAM, "", 0)

        calls: list = []
        with _repo() as root:
            out, sid, rc, err = self._run(root, result, calls=calls)
        self.assertEqual(rc, 0)
        self.assertEqual([_model_of(c) for c in calls if "-p" in c], [CLAUDE_TOP, CLAUDE_SECOND])

    def test_partial_signature_is_transport_failure_no_step_no_cache(self) -> None:
        # fn-221 R3 negative fixtures: exit-0 error payloads WITHOUT the
        # signature propagate as failures - one dispatch, no cache write.
        for stdout in (
            _claude_result(text="Request failed"),  # 404 without the text
            _claude_result(status=None),  # the text without a 404
            "not json at all",  # not the result JSON
        ):
            with self.subTest(stdout=stdout[:40]):
                calls: list = []
                with _repo() as root:
                    out, sid, rc, err = self._run(root, lambda m, _out=stdout: (_out, "", 0), calls=calls)
                    cache_file = root / ".flow" / ".cache" / "model-resolution.json"
                    self.assertFalse(cache_file.exists())
                self.assertEqual(rc, 1)
                self.assertEqual(len([c for c in calls if "-p" in c]), 1)

    def test_non_result_payloads_are_transport_failures(self) -> None:
        # fn-221 R2 (fan-out round 1): the claude parser is STRICT - one JSON
        # object with type "result". A wrong-type object, a type-less object
        # that still carries result + session_id, and a valid result followed
        # by corruption must never become a SHIP; cursor's JSON-lines salvage
        # is not shared.
        ship = '"result":"<verdict>SHIP</verdict>","session_id":"s1"'
        for stdout in (
            '{"type":"assistant",' + ship + "}",
            "{" + ship + "}",
            CLAUDE_OK_STREAM + "\ngarbage that is not json",
            '{"type":"system","subtype":"init"}\n' + CLAUDE_OK_STREAM,
        ):
            with self.subTest(stdout=stdout[:48]):
                calls: list = []
                with _repo() as root:
                    out, sid, rc, err = self._run(root, lambda m, _out=stdout: (_out, "", 0), calls=calls)
                self.assertEqual((out, rc), ("", 1))
                self.assertIsNone(flowctl.parse_codex_verdict(out))
                self.assertEqual(len([c for c in calls if "-p" in c]), 1)

    def test_error_envelope_text_never_reaches_reviewer_output(self) -> None:
        # fn-221 R2 (fan-out round 1): the shared finalizer parses the verdict
        # before the exit code, so an error envelope's text must travel on
        # stderr, never in the output slot - a 500 whose text contains a
        # verdict tag is a transport failure, not a SHIP.
        envelope = _claude_result(status=500, text="Overloaded <verdict>SHIP</verdict>")
        with _repo() as root:
            out, sid, rc, err = self._run(root, lambda m: (envelope, "", 0))
        self.assertEqual((out, rc), ("", 1))
        self.assertIn("Overloaded", err)  # diagnostic preserved on stderr
        self.assertIsNone(flowctl.parse_codex_verdict(out))
        flowctl._wire_backend_review_hooks()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            flowctl._finish_backend_exec(
                backend="claude", reg=BACKEND_REGISTRY["claude"],
                args=argparse.Namespace(json=False), receipt_path=None,
                output=out, stderr=err, exit_code=rc,
            )

    def test_max_two_steps_then_floor_omits_model_and_effort(self) -> None:
        calls: list = []
        res: dict = {}

        def result(model):
            return (CLAUDE_UNAVAILABLE_JSON, "", 0) if model is not None else (CLAUDE_OK_STREAM, "", 0)

        with _repo() as root:
            out, sid, rc, err = self._run(root, result, calls=calls, res=res)
        self.assertEqual(rc, 0)
        dispatched = [c for c in calls if "-p" in c]
        self.assertEqual(
            [_model_of(c) for c in dispatched],
            [CLAUDE_TOP, CLAUDE_SECOND, CLAUDE_THIRD, None],
        )
        # Every non-floor rung carried the resolved effort; the floor neither.
        for argv in dispatched[:3]:
            self.assertIn("--effort", argv)
        floor_argv = dispatched[-1]
        self.assertNotIn("--model", floor_argv)
        self.assertNotIn("--effort", floor_argv)
        self.assertTrue(res["floor"])
        self.assertIsNone(res["model"])
        # The receipt agrees with the argv: no effort at the floor.
        self.assertEqual(
            flowctl._receipt_model_effort(BackendSpec("claude").resolve(), res),
            ("default", None),
        )

    def test_caches_per_cli_version(self) -> None:
        def step_once(model):
            return (CLAUDE_UNAVAILABLE_JSON, "", 0) if model == CLAUDE_TOP else (CLAUDE_OK_STREAM, "", 0)

        with _repo() as root:
            self._run(root, step_once, version="2.1.260")
            cache = _cache_models(root)
            self.assertEqual(list(cache.values()), [CLAUDE_SECOND])
            self.assertTrue(next(iter(cache)).startswith("claude@2.1.260@"))
            # Same version: the cached rung dispatches directly, no top round-trip.
            calls: list = []
            self._run(root, lambda m: (CLAUDE_OK_STREAM, "", 0), calls=calls, version="2.1.260")
            self.assertEqual([_model_of(c) for c in calls if "-p" in c], [CLAUDE_SECOND])
            # A newer CLI: different key, cold, the top is tried again. The
            # in-process --version memo (success-only, per executable path)
            # would otherwise report the old version inside this one test
            # process; a real upgrade is always a new process.
            flowctl._CLI_VERSION_CACHE.clear()
            calls = []
            self._run(root, lambda m: (CLAUDE_OK_STREAM, "", 0), calls=calls, version="2.2.0")
            self.assertEqual([_model_of(c) for c in calls if "-p" in c], [CLAUDE_TOP])

    def test_argv_is_the_fixed_read_only_token_list(self) -> None:
        calls: list = []
        inputs: list = []
        with _repo() as root:
            self._run(root, lambda m: (CLAUDE_OK_STREAM, "", 0), calls=calls, inputs=inputs,
                      session_id="sid-9")
        argv = [c for c in calls if "-p" in c][0]
        self.assertEqual(argv[0], "/fake/bin/claude")
        self.assertEqual(
            argv[1:],
            CLAUDE_FIXED_ARGV + ["--model", CLAUDE_TOP, "--effort", "high", "--resume", "sid-9"],
        )
        tools = argv[argv.index("--tools") + 1: argv.index("--strict-mcp-config")]
        self.assertEqual(tools, ["Read", "Grep", "Glob"])
        self.assertNotIn("--allowedTools", argv)
        for forbidden in ("Bash", "Edit", "Write"):
            self.assertNotIn(forbidden, argv)
        self.assertEqual(inputs, ["p"])  # the prompt is never a positional


@contextmanager
def _git_repo():
    """A real git repo with three commits; yields (root, [sha0, sha1, sha2])."""
    with _repo() as root:
        def git(*a):
            return subprocess.run(["git", *a], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        shas = []
        for i in range(3):
            (root / "f.txt").write_text(f"line {i}\n", encoding="utf-8")
            git("add", "f.txt")
            git("commit", "-q", "-m", f"c{i}")
            shas.append(git("rev-parse", "HEAD"))
        yield root, shas


def _diff_name(receipt_id: str, base: str, head: str) -> str:
    return f"{receipt_id}-{base[:7]}-{head[:7]}.diff"


class TestClaudeAdapterBoundary(unittest.TestCase):
    """fn-221 R2: ``_claude_run_exec`` delivers the diff by path on PRIMARY
    dispatches (``args.claude_range`` set), never on optional passes."""

    def _call(self, root, *, args, session_id=None, calls=None, inputs=None, seen=None):
        scratch = root / ".flow" / "tmp" / "claude-review"

        def result(model):
            if seen is not None:
                seen.append(sorted(p.name for p in scratch.glob("*.diff")) if scratch.exists() else [])
            return (CLAUDE_OK_STREAM, "", 0)

        with _scripted(flowctl, dispatch_result=result, calls=calls, inputs=inputs):
            with redirect_stderr(io.StringIO()):
                return flowctl._claude_run_exec(
                    "p", session_id=session_id, repo_root=root,
                    spec=BackendSpec("claude"), resolution_out={}, args=args,
                )

    def test_primary_rereview_and_changed_base_write_distinct_files(self) -> None:
        with _git_repo() as (root, (c0, c1, c2)):
            scratch = root / ".flow" / "tmp" / "claude-review"
            first = scratch / _diff_name("rcpt", c0, c1)
            calls: list = []
            inputs: list = []
            seen: list = []
            # Primary, no session: the file exists BEFORE the stub runs.
            out, sid, rc, err = self._call(
                root, args=argparse.Namespace(claude_range=(c0, c1, "rcpt")),
                calls=calls, inputs=inputs, seen=seen,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(seen, [[first.name]])
            expected = subprocess.run(
                ["git", "diff", f"{c0}..{c1}"], cwd=root, capture_output=True, text=True, check=True,
            ).stdout
            self.assertEqual(first.read_text(encoding="utf-8"), expected)
            self.assertIn(str(first), inputs[0])
            self.assertIn(f"{c0}..{c1}", inputs[0])
            self.assertNotIn("--resume", calls[-1])
            first_bytes = first.read_bytes()

            # Re-review after a fix: same receipt, a session, a NEW head.
            calls, inputs = [], []
            second = scratch / _diff_name("rcpt", c0, c2)
            self._call(
                root, args=argparse.Namespace(claude_range=(c0, c2, "rcpt")),
                session_id="sid-1", calls=calls, inputs=inputs,
            )
            self.assertEqual(calls[-1][calls[-1].index("--resume") + 1], "sid-1")
            self.assertTrue(second.exists())
            self.assertIn(str(second), inputs[0])
            self.assertIn(f"{c0}..{c2}", inputs[0])
            self.assertEqual(first.read_bytes(), first_bytes)

            # Same head, a different base: a third file, the others untouched.
            second_bytes = second.read_bytes()
            third = scratch / _diff_name("rcpt", c1, c2)
            self._call(
                root, args=argparse.Namespace(claude_range=(c1, c2, "rcpt")),
                session_id="sid-1",
            )
            self.assertEqual(
                sorted(p.name for p in scratch.iterdir()),
                sorted([first.name, second.name, third.name]),
            )
            self.assertEqual(first.read_bytes(), first_bytes)
            self.assertEqual(second.read_bytes(), second_bytes)

    def test_optional_pass_resumes_and_writes_nothing(self) -> None:
        with _git_repo() as (root, (c0, c1, c2)):
            scratch = root / ".flow" / "tmp" / "claude-review"
            self._call(root, args=argparse.Namespace(claude_range=(c0, c1, "rcpt")))
            before = sorted(p.name for p in scratch.iterdir())
            # HEAD moves, then a deep pass / validate (no range field) resumes.
            subprocess.run(["git", "reset", "-q", "--hard", c2], cwd=root, check=True)
            calls: list = []
            inputs: list = []
            out, sid, rc, err = self._call(
                root, args=argparse.Namespace(sandbox="auto", json=False),
                session_id="sid-1", calls=calls, inputs=inputs,
            )
            self.assertEqual(rc, 0)
            self.assertIn("--resume", calls[-1])
            self.assertEqual(inputs, ["p"])  # no transport note appended
            self.assertEqual(sorted(p.name for p in scratch.iterdir()), before)

    def test_two_receipt_ids_write_two_files(self) -> None:
        with _git_repo() as (root, (c0, c1, _c2)):
            scratch = root / ".flow" / "tmp" / "claude-review"
            self._call(root, args=argparse.Namespace(claude_range=(c0, c1, "a")))
            self._call(root, args=argparse.Namespace(claude_range=(c0, c1, "b")))
            self.assertEqual(
                sorted(p.name for p in scratch.iterdir()),
                sorted([_diff_name("a", c0, c1), _diff_name("b", c0, c1)]),
            )
            # Atomic: no temp file is left beside the published diffs.
            self.assertFalse(any(p.suffix == ".tmp" for p in scratch.iterdir()))

    def test_symlinked_scratch_paths_fail_before_spawn(self) -> None:
        with _git_repo() as (root, (c0, c1, _c2)):
            with tempfile.TemporaryDirectory() as elsewhere:
                scratch = root / ".flow" / "tmp" / "claude-review"
                scratch.parent.mkdir(parents=True, exist_ok=True)
                scratch.symlink_to(elsewhere, target_is_directory=True)
                calls: list = []
                out, sid, rc, err = self._call(
                    root, args=argparse.Namespace(claude_range=(c0, c1, "rcpt")),
                    session_id="sid-1", calls=calls,
                )
                self.assertEqual(rc, 2)
                self.assertEqual(sid, "sid-1")
                self.assertIn("symlink", err)
                self.assertEqual([c for c in calls if "-p" in c], [])
                scratch.unlink()
            # A symlinked leaf is refused too.
            scratch.mkdir(parents=True)
            with tempfile.TemporaryDirectory() as elsewhere:
                target = Path(elsewhere) / "victim.diff"
                target.write_text("", encoding="utf-8")
                (scratch / _diff_name("rcpt", c0, c1)).symlink_to(target)
                calls = []
                out, sid, rc, err = self._call(
                    root, args=argparse.Namespace(claude_range=(c0, c1, "rcpt")), calls=calls,
                )
                self.assertEqual(rc, 2)
                self.assertIn("symlink", err)
                self.assertEqual([c for c in calls if "-p" in c], [])
                self.assertEqual(target.read_text(encoding="utf-8"), "")

    def test_dispatch_backend_review_sets_the_range_field(self) -> None:
        # The driver, not the adapter, owns the range: the primary boundary
        # stamps (base, head, receipt-id) on args before run_exec sees them.
        recorded: dict = {}

        def run_exec(prompt, *, session_id, repo_root, spec, resolution_out, args):
            recorded["range"] = args.claude_range
            return "ok", "sid", 0, ""

        args = argparse.Namespace(json=False)
        flowctl._dispatch_backend_review(
            backend="claude", reg={"run_exec": run_exec, "cli_label": "claude"},
            args=args, prompt="p", session_id=None, repo_root=Path("."),
            resolved_spec=BackendSpec("claude"), resolution_out={},
            receipt_path="/x/.flow/review-receipts/fn-9.1-impl.json",
            spec_id="fn-9", review_kind="impl", review_type="impl",
            reviewed_head_sha="b" * 40, reviewed_base_sha="a" * 40,
        )
        self.assertEqual(recorded["range"], ("a" * 40, "b" * 40, "fn-9.1-impl"))


# --- R4: per-CLI-version cache ---


class TestCache(unittest.TestCase):
    def _codex_ladder_run(self, root, calls=None):
        def result(model):
            return (CODEX_UNAVAILABLE_STREAM, "", 1) if model == CODEX_TOP else (CODEX_OK_STREAM, "", 0)
        with _scripted(flowctl, dispatch_result=result, version="0.142", calls=calls):
            with redirect_stderr(io.StringIO()):
                return flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)

    def test_round_trip_second_run_uses_cached_model_directly(self) -> None:
        with _repo() as root:
            # First run: ladder resolves top → second rung, caches it.
            self._codex_ladder_run(root)
            cache = _cache_models(root)
            self.assertEqual(list(cache.values()), [CODEX_SECOND])
            self.assertTrue(next(iter(cache)).startswith("codex@0.142@"))

            # Second run: cache hit → dispatch the cached rung DIRECTLY.
            calls: list = []
            def result(model):
                # If the cache were ignored, the top would be tried and fail.
                return (CODEX_OK_STREAM, "", 0)
            with _scripted(flowctl, dispatch_result=result, version="0.142", calls=calls):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
            dispatched = [_model_of(c) for c in calls if "exec" in c]
            self.assertEqual(dispatched, [CODEX_SECOND])  # cached, no top round-trip

    def test_cache_key_is_per_cli_version(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)  # caches under codex@0.142
            # A NEWER CLI version → different key → cold, dispatches top again.
            calls: list = []
            with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), version="0.144", calls=calls):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
            dispatched = [_model_of(c) for c in calls if "exec" in c]
            self.assertEqual(dispatched, [CODEX_TOP])  # top works on new CLI

    def test_cached_model_signature_failure_invalidates_and_reresolves(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)  # cache: codex@0.142 -> second rung
            # Now the cached rung ALSO fails the signature (org revoked
            # mid-version); the third rung works. The stale entry must be
            # dropped and re-resolved.
            def result(model):
                if model in (CODEX_TOP, CODEX_SECOND):
                    return (CODEX_UNAVAILABLE_STREAM, "", 1)
                return (CODEX_OK_STREAM, "", 0)
            with _scripted(flowctl, dispatch_result=result, version="0.142"):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
            self.assertEqual(list(_cache_models(root).values()), [CODEX_THIRD])

    def test_corrupt_cache_is_cold_start(self) -> None:
        with _repo() as root:
            cache_path = root / ".flow" / ".cache" / "model-resolution.json"
            cache_path.parent.mkdir(parents=True)
            cache_path.write_text("{ this is not json", encoding="utf-8")
            calls: list = []
            with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), calls=calls):
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root,
                )
            self.assertEqual(rc, 0)  # corrupt cache never raises
            self.assertEqual(_model_of([c for c in calls if "exec" in c][0]), CODEX_TOP)

    def test_explicit_model_bypasses_cache_entirely(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)  # writes codex@0.142 -> second rung
            calls: list = []
            # Explicit pin of the ranking top must dispatch it verbatim, ignoring
            # the cached downgrade, and never consult --version.
            with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), calls=calls):
                flowctl.run_codex_exec(
                    "p", sandbox="read-only",
                    spec=BackendSpec.parse(f"codex:{CODEX_TOP}:high"), repo_root=root,
                )
            self.assertNotIn("--version", [tok for c in calls for tok in c])
            self.assertEqual(_model_of([c for c in calls if "exec" in c][0]), CODEX_TOP)

    def test_resolved_intent_same_model_has_distinct_cache_intent(self) -> None:
        with _repo() as root:
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                registry_spec = BackendSpec("codex").resolve()
                self.assertTrue(registry_spec.routing_intent.startswith("registry:"))
                with _scripted(
                    flowctl,
                    dispatch_result=lambda model: (
                        (CODEX_UNAVAILABLE_STREAM, "", 1)
                        if model == CODEX_TOP
                        else (CODEX_OK_STREAM, "", 0)
                    ),
                ):
                    with redirect_stderr(io.StringIO()):
                        flowctl.run_codex_exec(
                            "p", spec=registry_spec, repo_root=root
                        )

                # Same model, different routing intent (a non-explicit spec
                # carried through a re-resolve) — a distinct cache identity.
                carried_spec = BackendSpec(
                    "codex", model=CODEX_TOP, model_explicit=False
                ).resolve()
                self.assertEqual(carried_spec.model, registry_spec.model)
                self.assertNotEqual(
                    carried_spec.routing_intent, registry_spec.routing_intent
                )

                calls: list = []
                with _scripted(
                    flowctl,
                    dispatch_result=lambda model: (CODEX_OK_STREAM, "", 0),
                    calls=calls,
                ):
                    flowctl.run_codex_exec("p", spec=carried_spec, repo_root=root)
                dispatched = [_model_of(c) for c in calls if "exec" in c]
                self.assertEqual(dispatched, [CODEX_TOP])
                self.assertEqual(_cache_models(root), {})

                # The obsolete registry-intent entry was pruned. A subsequent
                # happy path must not pay even a CLI-version subprocess.
                calls = []
                with _scripted(
                    flowctl,
                    dispatch_result=lambda model: (CODEX_OK_STREAM, "", 0),
                    calls=calls,
                ):
                    flowctl.run_codex_exec("p", spec=carried_spec, repo_root=root)
                self.assertNotIn("--version", [token for call in calls for token in call])
            finally:
                os.chdir(previous_cwd)

    def test_malformed_structured_entries_are_cold(self) -> None:
        corruptions = (
            ("empty model", lambda entry: entry.update(model="")),
            ("NaN timestamp", lambda entry: entry.update(cached_at=float("nan"))),
            ("boolean timestamp", lambda entry: entry.update(cached_at=True)),
        )
        for label, corrupt in corruptions:
            with self.subTest(label=label), _repo() as root:
                self._codex_ladder_run(root)
                cache_path = root / ".flow" / ".cache" / "model-resolution.json"
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
                corrupt(next(iter(cache.values())))
                cache_path.write_text(json.dumps(cache), encoding="utf-8")

                calls: list = []
                with _scripted(
                    flowctl,
                    dispatch_result=lambda model: (CODEX_OK_STREAM, "", 0),
                    calls=calls,
                ):
                    flowctl.run_codex_exec(
                        "p", spec=BackendSpec("codex"), repo_root=root
                    )
                self.assertEqual(
                    [_model_of(call) for call in calls if "exec" in call],
                    [CODEX_TOP],
                )

    def test_expired_downgrade_reprobes_stronger_model(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)
            cache_path = root / ".flow" / ".cache" / "model-resolution.json"
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            for entry in cache.values():
                entry["cached_at"] = (
                    flowctl._model_cache_now() - flowctl._MODEL_CACHE_TTL_SECS - 1
                )
            cache_path.write_text(json.dumps(cache), encoding="utf-8")

            calls: list = []
            with _scripted(
                flowctl,
                dispatch_result=lambda model: (CODEX_OK_STREAM, "", 0),
                calls=calls,
            ):
                flowctl.run_codex_exec("p", spec=BackendSpec("codex"), repo_root=root)
            self.assertEqual(
                [_model_of(c) for c in calls if "exec" in c], [CODEX_TOP]
            )

    def test_expired_floor_reprobes_stronger_model(self) -> None:
        with _repo() as root:
            with _scripted(
                flowctl,
                dispatch_result=lambda model: (
                    (CODEX_OK_STREAM, "", 0)
                    if model is None
                    else (CODEX_UNAVAILABLE_STREAM, "", 1)
                ),
            ):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec(
                        "p", spec=BackendSpec("codex"), repo_root=root
                    )
            cache_path = root / ".flow" / ".cache" / "model-resolution.json"
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [entry["model"] for entry in cache.values()],
                [flowctl._MODEL_CACHE_FLOOR],
            )
            for entry in cache.values():
                entry["cached_at"] = (
                    flowctl._model_cache_now() - flowctl._MODEL_CACHE_TTL_SECS - 1
                )
            cache_path.write_text(json.dumps(cache), encoding="utf-8")

            calls: list = []
            with _scripted(
                flowctl,
                dispatch_result=lambda model: (CODEX_OK_STREAM, "", 0),
                calls=calls,
            ):
                flowctl.run_codex_exec("p", spec=BackendSpec("codex"), repo_root=root)
            self.assertEqual(
                [_model_of(c) for c in calls if "exec" in c], [CODEX_TOP]
            )

    def test_concurrent_puts_preserve_every_intent(self) -> None:
        with _repo() as root:
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
                results = list(
                    pool.map(
                        lambda i: _cache_worker(
                            root, "put", f"backend-{i}", f"intent-{i}", f"model-{i}"
                        ),
                        range(20),
                    )
                )
            self.assertTrue(
                all(result.returncode == 0 for result in results),
                [result.stderr for result in results],
            )
            self.assertEqual(
                set(_cache_models(root).values()),
                {f"model-{i}" for i in range(20)},
            )

    def test_concurrent_put_and_invalidate_preserve_unrelated_entries(self) -> None:
        with _repo() as root:
            flowctl._model_cache_put(root, "keep", "v", "keep-intent", "keep-model")
            flowctl._model_cache_put(
                root, "remove", "v", "remove-intent", "remove-model"
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                put = pool.submit(
                    _cache_worker,
                    root,
                    "put",
                    "new",
                    "new-intent",
                    "new-model",
                )
                invalidate = pool.submit(
                    _cache_worker,
                    root,
                    "invalidate",
                    "remove",
                    "remove-intent",
                )
            self.assertEqual(put.result().returncode, 0, put.result().stderr)
            self.assertEqual(
                invalidate.result().returncode, 0, invalidate.result().stderr
            )
            self.assertEqual(
                set(_cache_models(root).values()), {"keep-model", "new-model"}
            )


# --- R5: receipt records the actually-used model ---


class TestResolutionOut(unittest.TestCase):
    def test_records_downgraded_model(self) -> None:
        res = {}
        def result(model):
            return (CODEX_UNAVAILABLE_STREAM, "", 1) if model == CODEX_TOP else (CODEX_OK_STREAM, "", 0)
        with _scripted(flowctl, dispatch_result=result):
            with _repo() as root, redirect_stderr(io.StringIO()):
                flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"),
                    repo_root=root, resolution_out=res,
                )
        self.assertEqual(res["model"], CODEX_SECOND)
        self.assertFalse(res["floor"])

    def test_records_happy_path_model(self) -> None:
        res = {}
        with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0)):
            with _repo() as root:
                flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"),
                    repo_root=root, resolution_out=res,
                )
        self.assertEqual(res["model"], CODEX_TOP)
        self.assertFalse(res["floor"])


class TestHandlerResolvedSpecs(unittest.TestCase):
    """PR #203 round 1 regression (found by BOTH bot reviewers): the review
    handlers pass PRE-RESOLVED specs into ``run_*_exec`` — the registry default
    is already filled in and ``model_explicit`` is False. Inferring explicitness
    from ``spec.model is not None`` misclassified that shape as a pin and
    bypassed the ladder/cache on every real (handler-driven) review; the unit
    tests only exercised BARE specs, which resolve inside the wrapper and dodge
    the bug. These tests pin the handler shape."""

    def test_preresolved_default_still_ladders_codex(self) -> None:
        handler_spec = BackendSpec("codex").resolve()  # what _resolve_codex_review_spec passes
        self.assertFalse(handler_spec.model_explicit)
        self.assertIsNotNone(handler_spec.model)

        def result(model):
            if model == CODEX_TOP:
                return (CODEX_UNAVAILABLE_STREAM, "", 1)
            return (CODEX_OK_STREAM, "", 0)

        calls: list = []
        with _scripted(flowctl, dispatch_result=result, calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=handler_spec, repo_root=root,
                )
        self.assertEqual(rc, 0)
        dispatched = [_model_of(c) for c in calls if "exec" in c]
        self.assertEqual(dispatched[:2], [CODEX_TOP, CODEX_SECOND])

    def test_preresolved_default_still_ladders_cursor(self) -> None:
        handler_spec = BackendSpec("cursor").resolve()
        self.assertFalse(handler_spec.model_explicit)

        def result(model):
            if model == CURSOR_TOP:
                # signature lands on STDERR (live capture 2026-07-10); stdout is
                # not parseable JSON, so _parse_cursor_result blanks it.
                return ("", CURSOR_UNAVAILABLE_STREAM, 1)
            return (CURSOR_OK_STREAM, "", 0)

        calls: list = []
        with _scripted(
            flowctl, dispatch_result=result, calls=calls,
            list_models=["auto", "gpt-5.5-high", "composer-2.5"],
        ):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, sid, rc, e = flowctl.run_cursor_exec(
                    "p", spec=handler_spec, repo_root=root,
                )
        self.assertEqual(rc, 0)
        self.assertTrue(any("--list-models" in c for c in calls))

    def test_parsed_pin_bypasses_ladder_and_propagates_failure(self) -> None:
        pinned = BackendSpec.parse("codex:gpt-5.4")
        self.assertTrue(pinned.model_explicit)
        calls: list = []
        with _scripted(
            flowctl,
            dispatch_result=lambda m: (CODEX_UNAVAILABLE_STREAM, "", 1),
            calls=calls,
        ):
            with _repo() as root:
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=pinned, repo_root=root,
                )
        self.assertEqual(rc, 1)  # explicit pin: failure propagates, no ladder
        self.assertEqual(len([c for c in calls if "exec" in c]), 1)

    def test_env_pin_bypasses_ladder(self) -> None:
        with mock.patch.dict(os.environ, {"FLOW_CODEX_MODEL": "gpt-5.4"}):
            handler_spec = BackendSpec("codex").resolve()
        self.assertTrue(handler_spec.model_explicit)
        calls: list = []
        with _scripted(
            flowctl,
            dispatch_result=lambda m: (CODEX_UNAVAILABLE_STREAM, "", 1),
            calls=calls,
        ):
            with _repo() as root:
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=handler_spec, repo_root=root,
                )
        self.assertEqual(rc, 1)
        self.assertEqual(len([c for c in calls if "exec" in c]), 1)

    def test_double_resolve_keeps_default_unexplicit(self) -> None:
        # resolve() must PROPAGATE the flag, never re-infer it from presence —
        # a re-resolved default-filled spec stays ladder-eligible.
        once = BackendSpec("cursor").resolve()
        twice = once.resolve()
        self.assertFalse(once.model_explicit)
        self.assertFalse(twice.model_explicit)
        # And a parsed pin survives double-resolve as a pin.
        pinned_twice = BackendSpec.parse("cursor:composer-2.5").resolve().resolve()
        self.assertTrue(pinned_twice.model_explicit)

class TestResumePreservesPriorModel(unittest.TestCase):
    """PR #203 round 2 (codex bot): a resumed codex session runs the model the
    ORIGINAL dispatch used — the receipt must preserve the prior receipt's
    (possibly downgraded/floored) model, never re-stamp the ranking top."""

    def test_resume_marks_resolution_and_helper_preserves_prior(self) -> None:
        calls: list = []
        resolution: dict = {}
        with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), calls=calls):
            with _repo() as root:
                out, tid, rc, e = flowctl.run_codex_exec(
                    "p", session_id="thread-1", sandbox="read-only",
                    spec=BackendSpec("codex").resolve(), repo_root=root,
                    resolution_out=resolution,
                )
        self.assertEqual(rc, 0)
        self.assertTrue(resolution.get("resumed"))
        self.assertNotIn("model", resolution)  # resume never saw a model
        # The stamping helper must keep the prior receipt's downgraded model.
        spec = BackendSpec("codex").resolve()  # ranking top
        model, effort = flowctl._receipt_model_effort(
            spec, resolution, prior_model="gpt-5.5", prior_effort="high",
        )
        self.assertEqual((model, effort), ("gpt-5.5", "high"))

    def test_no_resume_no_prior_falls_back_to_spec(self) -> None:
        spec = BackendSpec("codex").resolve()
        model, effort = flowctl._receipt_model_effort(spec, {}, prior_model="gpt-5.5")
        self.assertEqual(model, spec.model)  # no resume marker -> spec values


# --- fn-195: the role map, staleness stamp and `models resolve` are GONE ---


class TestRoleMapRemoved(unittest.TestCase):
    """Routing config is deleted: no models block, no validation, no verb.

    Routing is a preference the user writes in their instruction file. A repo
    whose config still carries the old keys keeps working - flowctl ignores
    them and the removed-key advisory names them once.
    """

    def test_defaults_carry_no_models_block(self) -> None:
        self.assertNotIn("models", flowctl.get_default_config())

    def test_role_map_symbols_are_gone(self) -> None:
        for name in (
            "MODEL_ROLES",
            "MODEL_ROLE_BACKENDS",
            "MODELS_STALE_DAYS",
            "get_role_map_pin",
            "resolve_role_model",
            "resolve_models_role",
            "cmd_models_resolve",
            "models_pin_nudge_message",
            "parse_models_verified_at",
            "_validate_models_config_key",
            "_validate_models_roles_tree",
        ):
            self.assertFalse(hasattr(flowctl, name), name)

    def test_models_keys_are_reported_as_removed(self) -> None:
        for key in ("models.roles", "models.verifiedAt", "models.verifiedWith"):
            self.assertIn(key, flowctl.REMOVED_CONFIG_KEYS)

    def test_stale_models_config_is_ignored_not_rejected(self) -> None:
        # A repo carrying the deleted keys resolves exactly like a fresh one.
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {"review": {"codex": "gpt-5.6-luna"}},
                            "verifiedAt": "2020-01-01",
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec("codex").resolve()
                self.assertEqual(r.model, CODEX_TOP)  # registry default
                self.assertFalse(r.model_explicit)
                m, e, src = flowctl.resolve_fast_judge_model("codex")
                self.assertEqual((m, e, src), ("gpt-5.6-luna", "high", "baseline"))
            finally:
                os.chdir(prev)


class TestReviewResolutionOrder(unittest.TestCase):
    """Review resolution after the role map: explicit > env > registry."""

    def setUp(self) -> None:
        self._env = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_review_baseline_is_registry_default(self) -> None:
        with _repo() as root:
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec("codex").resolve()
                self.assertEqual(r.model, CODEX_TOP)
                self.assertEqual(r.effort, "high")
                self.assertFalse(r.model_explicit)
            finally:
                os.chdir(prev)

    def test_review_env_beats_registry_default(self) -> None:
        with _repo() as root:
            os.environ["FLOW_CODEX_MODEL"] = "gpt-5.5"
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec("codex").resolve()
                self.assertEqual(r.model, "gpt-5.5")
                self.assertTrue(r.model_explicit)
            finally:
                os.chdir(prev)

    def test_review_explicit_spec_beats_env(self) -> None:
        with _repo() as root:
            os.environ["FLOW_CODEX_MODEL"] = "gpt-5.5"
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec.parse("codex:gpt-5.4:xhigh").resolve()
                self.assertEqual(r.model, "gpt-5.4")
                self.assertEqual(r.effort, "xhigh")
                self.assertTrue(r.model_explicit)
            finally:
                os.chdir(prev)

    def test_resolve_review_spec_bare_config_backend(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex"}}), encoding="utf-8"
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                resolved = flowctl.resolve_review_spec("codex", None)
                self.assertEqual(resolved.model, CODEX_TOP)
                self.assertFalse(resolved.model_explicit)
            finally:
                os.chdir(prev)

    # -- fast judge (triage) --

    def test_fast_judge_baseline_codex_and_copilot(self) -> None:
        m, e, src = flowctl.resolve_fast_judge_model("codex")
        self.assertEqual((m, e, src), ("gpt-5.6-luna", "high", "baseline"))
        m, e, src = flowctl.resolve_fast_judge_model("copilot")
        self.assertEqual((m, e, src), ("claude-haiku-4.5", "low", "baseline"))

    def test_fast_judge_explicit_beats_baseline(self) -> None:
        m, e, src = flowctl.resolve_fast_judge_model(
            "codex", explicit_model="gpt-5.5", explicit_effort="low"
        )
        self.assertEqual((m, e, src), ("gpt-5.5", "low", "explicit"))


class TestReviewPinLadderStart(unittest.TestCase):
    """A non-explicit start below the ranking top is the ladder START."""

    def test_ladder_reorders_to_start_at_pin(self) -> None:
        flowctl = _load_flowctl()
        ranking = list(flowctl.BACKEND_REGISTRY["codex"].get("models") or [])
        self.assertGreater(len(ranking), 1)
        pin = ranking[1]
        calls = []

        def dispatch(model, is_floor):
            calls.append(model)
            return ("<verdict>SHIP</verdict>", "sid", 0, "")

        spec = flowctl.BackendSpec("codex", model=pin, model_explicit=False)
        flowctl._dispatch_review_with_fallback(
            backend="codex", spec=spec, explicit_model=False, repo_root=None,
            dispatch=dispatch, is_unavailable=lambda o, e: False,
            floor_model=None, version_fn=lambda: "v",
        )
        self.assertEqual(calls[0], pin, "ladder must start at the pinned model")


if __name__ == "__main__":
    unittest.main()

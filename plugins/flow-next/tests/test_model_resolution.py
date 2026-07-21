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

import importlib.util
import io
import json
import os
import tempfile
import unittest
from unittest import mock
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from typing import Any, Optional


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

CODEX_OK_STREAM = '{"type":"thread.started","thread_id":"t1"}\n{"type":"agent_message","message":"<verdict>SHIP</verdict>"}'
CURSOR_OK_STREAM = '{"type":"result","is_error":false,"result":"ok","session_id":"s1"}'


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
def _scripted(module, *, dispatch_result, version="0.142", list_models=None, calls=None):
    """Stub subprocess.run + shutil.which for the review CLIs.

    ``dispatch_result(model) -> (stdout, stderr, rc)`` decides each dispatch's
    outcome by the ``--model`` value (None = floor). ``--version`` returns
    ``version``; ``--list-models`` returns ``list_models`` (newline-joined).
    Every call's argv is appended to ``calls`` (when given).
    """
    real_run = module.subprocess.run
    real_which = module.shutil.which

    def fake_run(cmd, **kwargs):
        argv = list(cmd)
        if calls is not None:
            calls.append(argv)
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
        if binary in ("codex", "copilot", "cursor-agent"):
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
        self.assertEqual(_model_of(calls[0]), "gpt-5.6-sol")  # ranking top

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
                    spec=BackendSpec.parse("codex:gpt-5.6-sol:high"), repo_root=root,
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
        self.assertEqual(_model_of(calls[0]), "gpt-5.5")  # ranking top

    def test_cursor_happy_path_no_list_call(self) -> None:
        calls: list = []
        with _scripted(flowctl, dispatch_result=lambda m: (CURSOR_OK_STREAM, "", 0), calls=calls):
            with _repo() as root:
                out, sid, rc, err = flowctl.run_cursor_exec(
                    "p", spec=BackendSpec("cursor"), repo_root=root,
                )
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)  # no --list-models on the happy path
        self.assertEqual(_model_of(calls[0]), "gpt-5.6-sol-high")


# --- R3: fallback ladder (signature-only) ---


class TestCodexLadder(unittest.TestCase):
    def test_ladder_steps_down_on_signature(self) -> None:
        # top (gpt-5.6-sol) fails signature; gpt-5.5 succeeds.
        def result(model):
            if model == "gpt-5.6-sol":
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
        self.assertEqual(dispatched[:2], ["gpt-5.6-sol", "gpt-5.5"])
        self.assertIn("downgraded to 'gpt-5.5'", err.getvalue())

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
        self.assertEqual(dispatched, ["gpt-5.6-sol", "gpt-5.5", "gpt-5.4", None])
        floor_argv = [c for c in calls if "exec" in c][-1]
        self.assertNotIn("--model", floor_argv)
        self.assertNotIn("-c", floor_argv)  # R5: floor omits effort
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
                return (CODEX_UNAVAILABLE_STREAM, "", 1) if model == "gpt-5.6-sol" else (CODEX_OK_STREAM, "", 0)

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
            if model == "gpt-5.5":
                return ("", COPILOT_UNAVAILABLE_STREAM, 1)
            return ("SHIP", "", 0)

        calls: list = []
        with _scripted(flowctl, dispatch_result=result, calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, sid, rc, e = flowctl.run_copilot_exec("p", "sess", root, spec=BackendSpec("copilot"))
        self.assertEqual(rc, 0)
        dispatched = [_model_of(c) for c in calls if "-p" in c or "--session-id" in " ".join(c) or "--model" in c]
        self.assertEqual(dispatched[:2], ["gpt-5.5", "gpt-5.4"])

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
            if model == "gpt-5.6-sol-high":
                return (CURSOR_UNAVAILABLE_STREAM, CURSOR_UNAVAILABLE_STREAM, 1)
            return (CURSOR_OK_STREAM, "", 0)

        calls: list = []
        with _scripted(flowctl, dispatch_result=result, list_models=["auto", "gpt-5.5-high", "gpt-5.4-high"], calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                out, sid, rc, e = flowctl.run_cursor_exec("p", spec=BackendSpec("cursor"), repo_root=root)
        self.assertEqual(rc, 0)
        self.assertTrue(any("--list-models" in c for c in calls))
        dispatched = [_model_of(c) for c in calls if "ask" in c]
        self.assertEqual(dispatched[0], "gpt-5.6-sol-high")
        self.assertEqual(dispatched[1], "gpt-5.5-high")  # best list ∩ ranking

    def test_empty_list_falls_to_floor_auto(self) -> None:
        calls: list = []
        res = {}
        with _scripted(flowctl, dispatch_result=lambda m: (CURSOR_UNAVAILABLE_STREAM, CURSOR_UNAVAILABLE_STREAM, 1) if m != "auto" else (CURSOR_OK_STREAM, "", 0), list_models=None, calls=calls):
            with _repo() as root, redirect_stderr(io.StringIO()):
                flowctl.run_cursor_exec("p", spec=BackendSpec("cursor"), repo_root=root, resolution_out=res)
        self.assertEqual(res["model"], "auto")
        self.assertTrue(res["floor"])


# --- R4: per-CLI-version cache ---


class TestCache(unittest.TestCase):
    def _codex_ladder_run(self, root, calls=None):
        def result(model):
            return (CODEX_UNAVAILABLE_STREAM, "", 1) if model == "gpt-5.6-sol" else (CODEX_OK_STREAM, "", 0)
        with _scripted(flowctl, dispatch_result=result, version="0.142", calls=calls):
            with redirect_stderr(io.StringIO()):
                return flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)

    def test_round_trip_second_run_uses_cached_model_directly(self) -> None:
        with _repo() as root:
            # First run: ladder resolves gpt-5.6-sol → gpt-5.5, caches it.
            self._codex_ladder_run(root)
            cache = json.loads((root / ".flow" / ".cache" / "model-resolution.json").read_text())
            self.assertEqual(cache["codex@0.142"], "gpt-5.5")

            # Second run: cache hit → dispatch gpt-5.5 DIRECTLY (no failed top).
            calls: list = []
            def result(model):
                # If the cache were ignored, the top would be tried and fail.
                return (CODEX_OK_STREAM, "", 0)
            with _scripted(flowctl, dispatch_result=result, version="0.142", calls=calls):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
            dispatched = [_model_of(c) for c in calls if "exec" in c]
            self.assertEqual(dispatched, ["gpt-5.5"])  # cached, no top round-trip

    def test_cache_key_is_per_cli_version(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)  # caches under codex@0.142
            # A NEWER CLI version → different key → cold, dispatches top again.
            calls: list = []
            with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), version="0.144", calls=calls):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
            dispatched = [_model_of(c) for c in calls if "exec" in c]
            self.assertEqual(dispatched, ["gpt-5.6-sol"])  # top works on new CLI

    def test_cached_model_signature_failure_invalidates_and_reresolves(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)  # cache: codex@0.142 -> gpt-5.5
            # Now gpt-5.5 ALSO fails the signature (org revoked mid-version);
            # gpt-5.4 works. The stale entry must be dropped and re-resolved.
            def result(model):
                if model in ("gpt-5.6-sol", "gpt-5.5"):
                    return (CODEX_UNAVAILABLE_STREAM, "", 1)
                return (CODEX_OK_STREAM, "", 0)
            with _scripted(flowctl, dispatch_result=result, version="0.142"):
                with redirect_stderr(io.StringIO()):
                    flowctl.run_codex_exec("p", sandbox="read-only", spec=BackendSpec("codex"), repo_root=root)
            cache = json.loads((root / ".flow" / ".cache" / "model-resolution.json").read_text())
            self.assertEqual(cache["codex@0.142"], "gpt-5.4")

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
            self.assertEqual(_model_of([c for c in calls if "exec" in c][0]), "gpt-5.6-sol")

    def test_explicit_model_bypasses_cache_entirely(self) -> None:
        with _repo() as root:
            self._codex_ladder_run(root)  # writes codex@0.142 -> gpt-5.5
            calls: list = []
            # Explicit pin of the ranking top must dispatch it verbatim, ignoring
            # the cached downgrade, and never consult --version.
            with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0), calls=calls):
                flowctl.run_codex_exec(
                    "p", sandbox="read-only",
                    spec=BackendSpec.parse("codex:gpt-5.6-sol:high"), repo_root=root,
                )
            self.assertNotIn("--version", [tok for c in calls for tok in c])
            self.assertEqual(_model_of([c for c in calls if "exec" in c][0]), "gpt-5.6-sol")


# --- R5: receipt records the actually-used model ---


class TestResolutionOut(unittest.TestCase):
    def test_records_downgraded_model(self) -> None:
        res = {}
        def result(model):
            return (CODEX_UNAVAILABLE_STREAM, "", 1) if model == "gpt-5.6-sol" else (CODEX_OK_STREAM, "", 0)
        with _scripted(flowctl, dispatch_result=result):
            with _repo() as root, redirect_stderr(io.StringIO()):
                flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"),
                    repo_root=root, resolution_out=res,
                )
        self.assertEqual(res["model"], "gpt-5.5")
        self.assertFalse(res["floor"])

    def test_records_happy_path_model(self) -> None:
        res = {}
        with _scripted(flowctl, dispatch_result=lambda m: (CODEX_OK_STREAM, "", 0)):
            with _repo() as root:
                flowctl.run_codex_exec(
                    "p", sandbox="read-only", spec=BackendSpec("codex"),
                    repo_root=root, resolution_out=res,
                )
        self.assertEqual(res["model"], "gpt-5.6-sol")
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
            if model == "gpt-5.6-sol":
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
        self.assertEqual(dispatched[:2], ["gpt-5.6-sol", "gpt-5.5"])

    def test_preresolved_default_still_ladders_cursor(self) -> None:
        handler_spec = BackendSpec("cursor").resolve()
        self.assertFalse(handler_spec.model_explicit)

        def result(model):
            if model == "gpt-5.6-sol-high":
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


# --- fn-115.1 role-map config + resolution order + staleness nudge ---


class TestRoleMapConfigSchema(unittest.TestCase):
    """models.roles / verifiedAt validation on config set."""

    def setUp(self) -> None:
        self._env = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_defaults_carry_models_block(self) -> None:
        defaults = flowctl.get_default_config()
        self.assertIn("models", defaults)
        self.assertEqual(defaults["models"]["roles"], {})
        self.assertIsNone(defaults["models"]["verifiedAt"])
        self.assertIsNone(defaults["models"]["verifiedWith"])

    def test_known_roles_and_backends(self) -> None:
        self.assertEqual(
            list(flowctl.MODEL_ROLES),
            [
                "fastJudge",
                "review",
                "delegate",
                "scoutFast",
                "scoutIntelligent",
            ],
        )
        self.assertEqual(
            list(flowctl.MODEL_ROLE_BACKENDS), ["codex", "copilot", "cursor"]
        )

    def test_reject_unknown_role(self) -> None:
        err = flowctl._validate_models_config_key(
            "models.roles.mystery.codex", "gpt-5.6-luna"
        )
        self.assertIsNotNone(err)
        self.assertIn("Unknown model role", err)
        self.assertIn("fastJudge", err)

    def test_reject_unknown_backend(self) -> None:
        err = flowctl._validate_models_config_key(
            "models.roles.review.rp", "anything"
        )
        self.assertIsNotNone(err)
        self.assertIn("Unknown model-role backend", err)
        self.assertIn("codex", err)

    def test_reject_unknown_models_leaf(self) -> None:
        err = flowctl._validate_models_config_key("models.foobar", "x")
        self.assertIsNotNone(err)
        self.assertIn("Unknown models key", err)

    def test_accept_role_pin_and_verified_at(self) -> None:
        self.assertIsNone(
            flowctl._validate_models_config_key(
                "models.roles.fastJudge.codex", "gpt-5.6-luna"
            )
        )
        self.assertIsNone(
            flowctl._validate_models_config_key(
                "models.roles.review.codex", "gpt-5.6-sol:medium"
            )
        )
        self.assertIsNone(
            flowctl._validate_models_config_key("models.verifiedAt", "2026-07-19")
        )
        self.assertIsNone(
            flowctl._validate_models_config_key(
                "models.verifiedWith", {"codex": "0.144"}
            )
        )

    def test_reject_bad_verified_at(self) -> None:
        err = flowctl._validate_models_config_key(
            "models.verifiedAt", "not-a-date"
        )
        self.assertIsNotNone(err)
        self.assertIn("ISO date", err)

    def test_config_set_round_trip_verified_at(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text("{}", encoding="utf-8")
            prev = Path.cwd()
            try:
                os.chdir(root)
                flowctl.set_config("models.verifiedAt", "2026-07-19")
                flowctl.set_config(
                    "models.roles.review.codex", "gpt-5.6-sol:medium"
                )
                self.assertEqual(
                    flowctl.get_config("models.verifiedAt"), "2026-07-19"
                )
                self.assertEqual(
                    flowctl.get_role_map_pin("review", "codex"),
                    "gpt-5.6-sol:medium",
                )
            finally:
                os.chdir(prev)

    def test_config_set_cli_rejects_unknown_role(self) -> None:
        import argparse
        from contextlib import redirect_stdout

        with _repo() as root:
            (root / ".flow" / "config.json").write_text("{}", encoding="utf-8")
            prev = Path.cwd()
            try:
                os.chdir(root)
                ns = argparse.Namespace(
                    key="models.roles.bogus.codex",
                    value="x",
                    json=True,
                )
                buf = io.StringIO()
                with self.assertRaises(SystemExit) as cm:
                    with redirect_stdout(buf):
                        flowctl.cmd_config_set(ns)
                self.assertNotEqual(cm.exception.code, 0)
                payload = json.loads(buf.getvalue())
                self.assertFalse(payload["success"])
                self.assertIn("Unknown model role", payload["error"])
            finally:
                os.chdir(prev)


class TestRoleMapResolutionOrder(unittest.TestCase):
    """Resolution matrix per consumer: explicit/env/role-map/baseline."""

    def setUp(self) -> None:
        self._env = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    # -- review consumer (BackendSpec.resolve / resolve_review_spec) --

    def test_review_baseline_is_registry_default(self) -> None:
        with _repo() as root:
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec("codex").resolve()
                self.assertEqual(r.model, "gpt-5.6-sol")
                self.assertEqual(r.effort, "high")
                self.assertFalse(r.model_explicit)
            finally:
                os.chdir(prev)

    def test_review_role_map_beats_registry_baseline(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {
                                "review": {"codex": "gpt-5.6-sol:medium"}
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec("codex").resolve()
                self.assertEqual(r.model, "gpt-5.6-sol")
                self.assertEqual(r.effort, "medium")
                # Role-map fill stays ladder-eligible (pin-too-new heals).
                self.assertFalse(r.model_explicit)
            finally:
                os.chdir(prev)

    def test_review_env_beats_role_map(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {"review": {"codex": "gpt-5.6-luna"}}
                        }
                    }
                ),
                encoding="utf-8",
            )
            os.environ["FLOW_CODEX_MODEL"] = "gpt-5.5"
            prev = Path.cwd()
            try:
                os.chdir(root)
                r = BackendSpec("codex").resolve()
                self.assertEqual(r.model, "gpt-5.5")
                self.assertTrue(r.model_explicit)
            finally:
                os.chdir(prev)

    def test_review_explicit_spec_beats_env_and_role_map(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {"review": {"codex": "gpt-5.6-luna"}}
                        }
                    }
                ),
                encoding="utf-8",
            )
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

    def test_resolve_review_spec_role_map_via_bare_config_backend(self) -> None:
        # review.backend=codex (no model) + role map pin → role map model.
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "review": {"backend": "codex"},
                        "models": {
                            "roles": {
                                "review": {"codex": "gpt-5.6-terra"}
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                resolved = flowctl.resolve_review_spec("codex", None)
                self.assertEqual(resolved.model, "gpt-5.6-terra")
                self.assertFalse(resolved.model_explicit)
            finally:
                os.chdir(prev)

    # -- fastJudge consumer (triage) --

    def test_fast_judge_baseline_codex_and_copilot(self) -> None:
        m, e, src = flowctl.resolve_fast_judge_model("codex")
        self.assertEqual((m, e, src), ("gpt-5.6-luna", "high", "baseline"))
        m, e, src = flowctl.resolve_fast_judge_model("copilot")
        self.assertEqual((m, e, src), ("claude-haiku-4.5", "low", "baseline"))

    def test_fast_judge_role_map_beats_baseline(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {
                                "fastJudge": {
                                    "codex": "gpt-5.6-terra:medium"
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                m, e, src = flowctl.resolve_fast_judge_model("codex")
                self.assertEqual(m, "gpt-5.6-terra")
                self.assertEqual(e, "medium")
                self.assertEqual(src, "role-map")
            finally:
                os.chdir(prev)

    def test_fast_judge_explicit_beats_role_map(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {
                                "fastJudge": {"codex": "gpt-5.6-terra"}
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                m, e, src = flowctl.resolve_fast_judge_model(
                    "codex",
                    explicit_model="gpt-5.5",
                    explicit_effort="low",
                )
                self.assertEqual(m, "gpt-5.5")
                self.assertEqual(e, "low")
                self.assertEqual(src, "explicit")
            finally:
                os.chdir(prev)

    def test_triage_judge_uses_role_map_default(self) -> None:
        # Wire check: _triage_run_codex_judge argv carries the role-map model
        # when --model is unset (CLI missing → early return after resolve).
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {
                                "fastJudge": {"codex": "gpt-5.6-terra"}
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch.object(flowctl.shutil, "which", return_value=None):
                    v, reason, model_used = flowctl._triage_run_codex_judge(
                        "prompt", None, None
                    )
                # CLI absent: no model_used, but resolve still ran; prove via
                # resolve_fast_judge_model that the wire prefers the role map.
                m, _e, src = flowctl.resolve_fast_judge_model("codex")
                self.assertEqual(m, "gpt-5.6-terra")
                self.assertEqual(src, "role-map")
                self.assertIsNone(v)
                self.assertIsNone(model_used)
                self.assertIn("not available", reason)
            finally:
                os.chdir(prev)

    # -- delegate consumer --

    def test_delegate_baseline(self) -> None:
        with _repo() as root:
            prev = Path.cwd()
            try:
                os.chdir(root)
                model, src = flowctl.resolve_delegate_model()
                self.assertEqual(model, "gpt-5.6-terra")
                self.assertEqual(src, "baseline")
            finally:
                os.chdir(prev)

    def test_delegate_role_map_beats_baseline(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {
                                "delegate": {"codex": "gpt-5.6-sol"}
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                model, src = flowctl.resolve_delegate_model()
                self.assertEqual(model, "gpt-5.6-sol")
                self.assertEqual(src, "role-map")
            finally:
                os.chdir(prev)

    def test_delegate_work_delegate_model_beats_role_map(self) -> None:
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "work": {"delegateModel": "gpt-5.5"},
                        "models": {
                            "roles": {
                                "delegate": {"codex": "gpt-5.6-sol"}
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                model, src = flowctl.resolve_delegate_model()
                self.assertEqual(model, "gpt-5.5")
                self.assertEqual(src, "config")
            finally:
                os.chdir(prev)

    def test_delegate_merged_default_does_not_beat_role_map(self) -> None:
        # work.delegateModel only wins when RAW-set, not via defaults merge.
        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps(
                    {
                        "models": {
                            "roles": {
                                "delegate": {"codex": "gpt-5.6-sol"}
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                # Merged default still surfaces gpt-5.6-terra via config get,
                # but resolve_delegate_model prefers the role map.
                self.assertEqual(
                    flowctl.get_config("work.delegateModel"), "gpt-5.6-terra"
                )
                model, src = flowctl.resolve_delegate_model()
                self.assertEqual(model, "gpt-5.6-sol")
                self.assertEqual(src, "role-map")
            finally:
                os.chdir(prev)


class TestModelsStalenessNudge(unittest.TestCase):
    """Mechanical date check only — never blocks, absent = quiet."""

    def test_absent_verified_at_no_nudge(self) -> None:
        self.assertIsNone(flowctl.models_pin_nudge_message(None))
        self.assertIsNone(flowctl.models_pin_nudge_message(""))

    def test_fresh_pin_no_nudge(self) -> None:
        now = flowctl.datetime(2026, 7, 21, tzinfo=flowctl.timezone.utc)
        self.assertIsNone(
            flowctl.models_pin_nudge_message("2026-07-01", now=now)
        )
        # Age 89 days — still under the 90d threshold.
        self.assertIsNone(
            flowctl.models_pin_nudge_message("2026-04-23", now=now)
        )

    def test_stale_pin_one_line(self) -> None:
        now = flowctl.datetime(2026, 7, 21, tzinfo=flowctl.timezone.utc)
        # Exactly 90 days.
        msg = flowctl.models_pin_nudge_message("2026-04-22", now=now)
        self.assertEqual(
            msg,
            "model pins last verified 2026-04-22; re-run setup to refresh",
        )
        # Older than 90 days.
        msg = flowctl.models_pin_nudge_message("2026-01-01", now=now)
        self.assertIn("2026-01-01", msg)
        self.assertIn("re-run setup to refresh", msg)

    def test_iso_datetime_verified_at(self) -> None:
        now = flowctl.datetime(2026, 7, 21, tzinfo=flowctl.timezone.utc)
        msg = flowctl.models_pin_nudge_message(
            "2026-01-01T12:00:00Z", now=now
        )
        self.assertIsNotNone(msg)
        self.assertIn("2026-01-01", msg)

    def test_status_prints_nudge_when_stale(self) -> None:
        import argparse
        from contextlib import redirect_stdout

        with _repo() as root:
            (root / ".flow" / "config.json").write_text(
                json.dumps({"models": {"verifiedAt": "2025-01-01"}}),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                ns = argparse.Namespace(json=False)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    flowctl.cmd_status(ns)
                out = buf.getvalue()
                self.assertIn("model pins last verified 2025-01-01", out)
                self.assertIn("re-run setup to refresh", out)
            finally:
                os.chdir(prev)

    def test_status_silent_when_verified_at_absent(self) -> None:
        import argparse
        from contextlib import redirect_stdout

        with _repo() as root:
            (root / ".flow" / "config.json").write_text("{}", encoding="utf-8")
            prev = Path.cwd()
            try:
                os.chdir(root)
                ns = argparse.Namespace(json=False)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    flowctl.cmd_status(ns)
                out = buf.getvalue()
                self.assertNotIn("model pins last verified", out)
            finally:
                os.chdir(prev)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for BackendSpec parser + registry (fn-28 task 1).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers every valid form and every invalid-input branch listed in the task
spec. If the grammar/validation/resolution semantics break here, the whole
fn-28 plumbing chain will be wrong downstream.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any


def _load_flowctl() -> Any:
    """Load flowctl.py as a module without running it as a script.

    Resolves relative to this file so the test works from any cwd (same
    approach the smoke test uses).
    """
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location("flowctl_under_test", flowctl_path)
    mod = importlib.util.module_from_spec(spec)
    # Prevent argparse / CLI dispatch at import time — flowctl.py guards main()
    # under ``if __name__ == "__main__"``, so importing is side-effect free.
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()
BackendSpec = flowctl.BackendSpec
BACKEND_REGISTRY = flowctl.BACKEND_REGISTRY


# --- Registry shape ---


class TestRegistryShape(unittest.TestCase):
    """Registry contents are the contract downstream code depends on."""

    def test_exactly_five_backends(self) -> None:
        # cursor added in fn-74 (model-yes / effort-no shape).
        self.assertEqual(
            sorted(BACKEND_REGISTRY.keys()),
            ["codex", "copilot", "cursor", "none", "rp"],
        )

    def test_cursor_effort_is_none(self) -> None:
        # Cursor folds reasoning effort into the model name → no effort axis.
        self.assertIsNone(BACKEND_REGISTRY["cursor"]["efforts"])

    def test_cursor_default_model(self) -> None:
        self.assertEqual(
            BACKEND_REGISTRY["cursor"]["default_model"], "gpt-5.6-sol-high"
        )
        # No default_effort — effort is not a cursor field.
        self.assertNotIn("default_effort", BACKEND_REGISTRY["cursor"])

    def test_cursor_model_catalog(self) -> None:
        # Source of truth: ``cursor-agent --list-models`` (v2026.06). Keep synced
        # — Cursor ships new rows + auto-updates the CLI without changelog.
        # fn-76: ``models`` is an ORDERED quality ranking (strongest first), a
        # list — not a set. ``default_model`` MUST equal ``models[0]``.
        self.assertEqual(
            BACKEND_REGISTRY["cursor"]["models"],
            [
                "gpt-5.6-sol-high",
                "gpt-5.6-sol-xhigh",
                "gpt-5.6-sol-max",
                "gpt-5.6-sol-medium",
                "gpt-5.6-sol-low",
                "gpt-5.6-terra-high",
                "gpt-5.6-luna-high",
                "claude-opus-4-8-thinking-high",
                "claude-opus-4-7-thinking-high",
                "gpt-5.5-high",
                "gpt-5.4-high",
                "gpt-5.3-codex-xhigh",
                "gpt-5.3-codex-high",
                "gpt-5.3-codex",
                "gpt-5.2",
                "composer-2.5",
                "auto",
            ],
        )

    def test_rp_rejects_model_and_effort(self) -> None:
        self.assertIsNone(BACKEND_REGISTRY["rp"]["models"])
        self.assertIsNone(BACKEND_REGISTRY["rp"]["efforts"])

    def test_none_rejects_model_and_effort(self) -> None:
        self.assertIsNone(BACKEND_REGISTRY["none"]["models"])
        self.assertIsNone(BACKEND_REGISTRY["none"]["efforts"])

    def test_codex_effort_set(self) -> None:
        self.assertEqual(
            BACKEND_REGISTRY["codex"]["efforts"],
            {"none", "minimal", "low", "medium", "high", "xhigh"},
        )

    def test_copilot_effort_set(self) -> None:
        # Copilot rejects ``none`` and ``minimal`` (see fn-27 model catalog).
        self.assertEqual(
            BACKEND_REGISTRY["copilot"]["efforts"],
            {"low", "medium", "high", "xhigh"},
        )

    def test_codex_defaults(self) -> None:
        # fn-76: default_model is the ranking top (gpt-5.6-sol). Older codex CLIs
        # (< 0.144) 400 on it; the run_codex_exec ladder downgrades to gpt-5.5.
        self.assertEqual(BACKEND_REGISTRY["codex"]["default_model"], "gpt-5.6-sol")
        self.assertEqual(BACKEND_REGISTRY["codex"]["default_effort"], "high")

    def test_copilot_defaults(self) -> None:
        # Bumped to gpt-5.5/high when the newer OpenAI/Anthropic rows were
        # activated in copilot CLI 1.0.36 (verified live via `copilot -p
        # "/model"`). Stays on `high` effort — `xhigh` spends far more
        # reasoning tokens without matching quality gains on review prompts.
        self.assertEqual(BACKEND_REGISTRY["copilot"]["default_model"], "gpt-5.5")
        self.assertEqual(BACKEND_REGISTRY["copilot"]["default_effort"], "high")

    def test_copilot_model_catalog(self) -> None:
        # Source of truth: `copilot -p "/model"` against CLI 1.0.65. Keep in
        # sync when GitHub activates new rows; older rows stay listed until
        # copilot itself rejects them. fn-76: ORDERED quality ranking (strongest
        # first), a list — ``default_model`` MUST equal ``models[0]``.
        self.assertEqual(
            BACKEND_REGISTRY["copilot"]["models"],
            [
                "gpt-5.5",
                "gpt-5.4",
                "claude-opus-4.7",
                "claude-opus-4.6",
                "claude-opus-4.5",
                "claude-sonnet-4.5",
                "claude-sonnet-4",
                "claude-haiku-4.5",
                "gpt-5.4-mini",
                "gpt-5.3-codex",
                "gpt-5-mini",
                "gpt-4.1",
            ],
        )

    def test_ranking_is_ordered_list_not_set(self) -> None:
        # fn-76: every model-bearing backend's ``models`` is an ordered list
        # (the quality ranking), not a set — order is load-bearing for the
        # fallback ladder.
        for backend in ("codex", "copilot", "cursor"):
            with self.subTest(backend=backend):
                self.assertIsInstance(
                    BACKEND_REGISTRY[backend]["models"], list
                )

    def test_default_model_equals_ranking_top(self) -> None:
        # fn-76 invariant: the optimistic-first default IS the ranking's first
        # entry, so the happy-path dispatch argv is byte-identical to a hardcoded
        # default. If these ever diverge, the happy path stops dispatching the
        # strongest model.
        for backend in ("codex", "copilot", "cursor"):
            with self.subTest(backend=backend):
                reg = BACKEND_REGISTRY[backend]
                self.assertEqual(reg["default_model"], reg["models"][0])


# --- Valid specs ---


class TestParseValid(unittest.TestCase):
    def test_bare_codex(self) -> None:
        s = BackendSpec.parse("codex")
        self.assertEqual(s, BackendSpec("codex", None, None))

    def test_bare_rp(self) -> None:
        s = BackendSpec.parse("rp")
        self.assertEqual(s, BackendSpec("rp", None, None))

    def test_bare_none(self) -> None:
        s = BackendSpec.parse("none")
        self.assertEqual(s, BackendSpec("none", None, None))

    def test_bare_copilot(self) -> None:
        s = BackendSpec.parse("copilot")
        self.assertEqual(s, BackendSpec("copilot", None, None))

    def test_codex_with_model(self) -> None:
        s = BackendSpec.parse("codex:gpt-5.4")
        self.assertEqual(s, BackendSpec("codex", "gpt-5.4", None))

    def test_codex_full(self) -> None:
        s = BackendSpec.parse("codex:gpt-5.4:xhigh")
        self.assertEqual(s, BackendSpec("codex", "gpt-5.4", "xhigh"))

    def test_copilot_full(self) -> None:
        s = BackendSpec.parse("copilot:claude-opus-4.5:xhigh")
        self.assertEqual(s, BackendSpec("copilot", "claude-opus-4.5", "xhigh"))

    def test_copilot_model_only(self) -> None:
        s = BackendSpec.parse("copilot:gpt-5.4")
        self.assertEqual(s, BackendSpec("copilot", "gpt-5.4", None))

    def test_bare_cursor(self) -> None:
        s = BackendSpec.parse("cursor")
        self.assertEqual(s, BackendSpec("cursor", None, None))

    def test_cursor_with_model(self) -> None:
        s = BackendSpec.parse("cursor:gpt-5.5-high")
        self.assertEqual(s, BackendSpec("cursor", "gpt-5.5-high", None))

    def test_cursor_model_with_baked_effort_name(self) -> None:
        # Effort is part of the model string for cursor — this is a model, not
        # a separate effort field.
        s = BackendSpec.parse("cursor:gpt-5.3-codex-xhigh")
        self.assertEqual(s, BackendSpec("cursor", "gpt-5.3-codex-xhigh", None))

    def test_codex_all_efforts(self) -> None:
        for eff in ("none", "minimal", "low", "medium", "high", "xhigh"):
            with self.subTest(effort=eff):
                s = BackendSpec.parse(f"codex:gpt-5.4:{eff}")
                self.assertEqual(s.effort, eff)

    def test_leading_trailing_whitespace_tolerated(self) -> None:
        # Per parser: outer strip + per-part strip — pasting from help text
        # with trailing newlines shouldn't blow up.
        self.assertEqual(
            BackendSpec.parse("  codex:gpt-5.4:xhigh  "),
            BackendSpec("codex", "gpt-5.4", "xhigh"),
        )

    def test_empty_middle_part_is_none(self) -> None:
        # ``codex::high`` means "default model, effort=high". Weird but legal
        # — the parser treats an empty part as unset so the round-trip works.
        s = BackendSpec.parse("codex::high")
        self.assertEqual(s, BackendSpec("codex", None, "high"))


# --- Invalid specs ---


class TestParseInvalid(unittest.TestCase):
    def test_empty_string(self) -> None:
        with self.assertRaisesRegex(ValueError, "Empty backend spec"):
            BackendSpec.parse("")

    def test_whitespace_only(self) -> None:
        with self.assertRaisesRegex(ValueError, "Empty backend spec"):
            BackendSpec.parse("   ")

    def test_none_value(self) -> None:
        # Defensive: ``None`` is not a string but downstream code may pass it.
        with self.assertRaisesRegex(ValueError, "Empty backend spec"):
            BackendSpec.parse(None)  # type: ignore[arg-type]

    def test_unknown_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown backend"):
            BackendSpec.parse("foo")

    def test_unknown_backend_lists_valid_set(self) -> None:
        # Users need a copy-pasteable list — don't regress.
        try:
            BackendSpec.parse("foo")
            self.fail("expected ValueError")
        except ValueError as e:
            msg = str(e)
            for name in ("rp", "codex", "copilot", "none"):
                self.assertIn(name, msg)

    def test_too_many_colons(self) -> None:
        with self.assertRaisesRegex(ValueError, "Too many ':' separators"):
            BackendSpec.parse("codex:gpt-5.4:high:extra")

    def test_way_too_many_colons(self) -> None:
        with self.assertRaisesRegex(ValueError, "Too many ':' separators"):
            BackendSpec.parse("copilot:::::")

    def test_trailing_colon(self) -> None:
        # ``codex:`` — model part is empty string; parser treats as None, so
        # this parses as bare ``codex``. That's the same lenient rule as
        # ``codex::high``. Confirm behavior is stable (not a crash).
        s = BackendSpec.parse("codex:")
        self.assertEqual(s, BackendSpec("codex", None, None))

    def test_unknown_model_codex_warns_and_accepts(self) -> None:
        # fn-76 R1: unknown models are a PREFERENCE miss, not a parse error —
        # warn-and-accept (the CLI is the availability authority). Effort stays
        # strict (covered separately).
        err = io.StringIO()
        with redirect_stderr(err):
            s = BackendSpec.parse("codex:gpt-99")
        self.assertEqual(s, BackendSpec("codex", "gpt-99", None))
        self.assertTrue(s.model_explicit)
        self.assertIn("not in flow-next's codex ranking", err.getvalue())

    def test_unknown_model_copilot_warns_and_accepts(self) -> None:
        # An effort-looking string in the model slot is just an unknown model
        # now — warn-and-accept, no raise.
        err = io.StringIO()
        with redirect_stderr(err):
            s = BackendSpec.parse("copilot:xhigh-is-not-a-model")
        self.assertEqual(s, BackendSpec("copilot", "xhigh-is-not-a-model", None))
        self.assertIn("not in flow-next's copilot ranking", err.getvalue())

    def test_unknown_effort_codex(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown effort for codex"):
            BackendSpec.parse("codex:gpt-5.4:bogus-effort")

    def test_unknown_effort_lists_sorted_valid(self) -> None:
        try:
            BackendSpec.parse("codex:gpt-5.4:bogus")
            self.fail("expected ValueError")
        except ValueError as e:
            self.assertIn("'high'", str(e))
            self.assertIn("'xhigh'", str(e))

    def test_copilot_rejects_codex_only_efforts(self) -> None:
        # ``none`` and ``minimal`` are codex-only; copilot must reject.
        with self.assertRaisesRegex(ValueError, "Unknown effort for copilot"):
            BackendSpec.parse("copilot:gpt-5.4:minimal")
        with self.assertRaisesRegex(ValueError, "Unknown effort for copilot"):
            BackendSpec.parse("copilot:gpt-5.4:none")

    def test_cursor_rejects_effort(self) -> None:
        # Cursor has no effort axis — ``cursor:<model>:<effort>`` must raise.
        with self.assertRaisesRegex(ValueError, "does not accept an effort"):
            BackendSpec.parse("cursor:gpt-5.5-high:high")

    def test_cursor_unknown_model_warns_and_accepts(self) -> None:
        # fn-76 R1: warn-and-accept for cursor too.
        err = io.StringIO()
        with redirect_stderr(err):
            s = BackendSpec.parse("cursor:bogus")
        self.assertEqual(s, BackendSpec("cursor", "bogus", None))
        self.assertIn("not in flow-next's cursor ranking", err.getvalue())

    def test_cursor_rejects_gpt5_high_lookalike_in_effort_slot(self) -> None:
        # A copilot/codex-style ``cursor:gpt-5.2:xhigh`` (effort in slot 3) must
        # fail on the effort axis, not silently parse.
        with self.assertRaisesRegex(ValueError, "does not accept an effort"):
            BackendSpec.parse("cursor:gpt-5.2:xhigh")

    def test_rp_rejects_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not accept a model"):
            BackendSpec.parse("rp:opus")

    def test_rp_rejects_effort(self) -> None:
        # rp has no models either, so model check fires first. Force effort-only
        # with empty model slot.
        with self.assertRaisesRegex(ValueError, "does not accept an effort"):
            BackendSpec.parse("rp::high")

    def test_none_rejects_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not accept a model"):
            BackendSpec.parse("none:gpt-5.4")

    def test_none_rejects_effort(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not accept an effort"):
            BackendSpec.parse("none::high")

    def test_case_sensitive_backend_name(self) -> None:
        # Backend names are lowercase per the registry. Uppercase must fail
        # rather than silently lowercasing — that would hide typos.
        with self.assertRaisesRegex(ValueError, "Unknown backend"):
            BackendSpec.parse("Codex")
        with self.assertRaisesRegex(ValueError, "Unknown backend"):
            BackendSpec.parse("RP")

    def test_case_sensitive_model_warns_and_accepts(self) -> None:
        # fn-76 R1: an uppercase (unknown) model is no longer a hard error — it
        # warns and is accepted verbatim (case-preserving); the CLI rejects it if
        # truly unavailable. Effort case-sensitivity stays strict (below).
        err = io.StringIO()
        with redirect_stderr(err):
            s = BackendSpec.parse("codex:GPT-5.4")
        self.assertEqual(s.model, "GPT-5.4")
        self.assertIn("not in flow-next's codex ranking", err.getvalue())

    def test_case_sensitive_effort(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown effort"):
            BackendSpec.parse("codex:gpt-5.4:HIGH")


# --- resolve() precedence ---


class TestResolve(unittest.TestCase):
    """Per-field env-fill precedence: explicit > env > registry default."""

    def setUp(self) -> None:
        # Snapshot + scrub any FLOW_* env that could bleed between tests.
        self._env_snapshot = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_CODEX_") or key.startswith("FLOW_COPILOT_") \
               or key.startswith("FLOW_CURSOR_") \
               or key.startswith("FLOW_RP_") or key.startswith("FLOW_NONE_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def test_bare_codex_fills_both_defaults(self) -> None:
        r = BackendSpec.parse("codex").resolve()
        # fn-76: codex default is now the ranking top (gpt-5.6-sol).
        self.assertEqual(r, BackendSpec("codex", "gpt-5.6-sol", "high"))
        # Unconfigured → not explicit → ladder-/cache-eligible downstream.
        self.assertFalse(r.model_explicit)

    def test_bare_copilot_fills_both_defaults(self) -> None:
        r = BackendSpec.parse("copilot").resolve()
        self.assertEqual(r, BackendSpec("copilot", "gpt-5.5", "high"))

    def test_bare_cursor_fills_model_effort_stays_none(self) -> None:
        # Model fills from registry default; effort stays None (no effort axis).
        r = BackendSpec.parse("cursor").resolve()
        self.assertEqual(r, BackendSpec("cursor", "gpt-5.6-sol-high", None))

    def test_cursor_env_fills_missing_model(self) -> None:
        os.environ["FLOW_CURSOR_MODEL"] = "composer-2.5"
        r = BackendSpec.parse("cursor").resolve()
        self.assertEqual(r, BackendSpec("cursor", "composer-2.5", None))

    def test_cursor_effort_env_is_ignored(self) -> None:
        # No effort axis — a stray FLOW_CURSOR_EFFORT must never leak in.
        os.environ["FLOW_CURSOR_EFFORT"] = "xhigh"
        r = BackendSpec.parse("cursor:gpt-5.4-high").resolve()
        self.assertEqual(r, BackendSpec("cursor", "gpt-5.4-high", None))

    def test_env_fills_missing_model(self) -> None:
        os.environ["FLOW_CODEX_MODEL"] = "gpt-5.2"
        r = BackendSpec.parse("codex").resolve()
        self.assertEqual(r.model, "gpt-5.2")
        self.assertEqual(r.effort, "high")  # still registry default

    def test_env_fills_missing_effort(self) -> None:
        os.environ["FLOW_CODEX_EFFORT"] = "low"
        r = BackendSpec.parse("codex:gpt-5.2").resolve()
        self.assertEqual(r.model, "gpt-5.2")  # explicit wins
        self.assertEqual(r.effort, "low")  # from env

    def test_explicit_spec_wins_over_env(self) -> None:
        # Critical: env only fills *missing* fields; explicit spec values are
        # never overridden. This is the subtle contract called out in the epic
        # risks section.
        os.environ["FLOW_CODEX_MODEL"] = "gpt-5.2"
        os.environ["FLOW_CODEX_EFFORT"] = "low"
        r = BackendSpec.parse("codex:gpt-5.4:xhigh").resolve()
        self.assertEqual(r, BackendSpec("codex", "gpt-5.4", "xhigh"))

    def test_rp_resolve_returns_no_model_no_effort(self) -> None:
        # rp has no model/effort concept — resolve must not leak env values in.
        os.environ["FLOW_RP_MODEL"] = "bogus"
        os.environ["FLOW_RP_EFFORT"] = "bogus"
        r = BackendSpec.parse("rp").resolve()
        self.assertEqual(r, BackendSpec("rp", None, None))

    def test_none_resolve_returns_no_model_no_effort(self) -> None:
        os.environ["FLOW_NONE_MODEL"] = "bogus"
        r = BackendSpec.parse("none").resolve()
        self.assertEqual(r, BackendSpec("none", None, None))

    def test_copilot_env_override(self) -> None:
        os.environ["FLOW_COPILOT_MODEL"] = "claude-opus-4.5"
        os.environ["FLOW_COPILOT_EFFORT"] = "xhigh"
        r = BackendSpec.parse("copilot").resolve()
        self.assertEqual(r, BackendSpec("copilot", "claude-opus-4.5", "xhigh"))

    def test_resolve_is_idempotent(self) -> None:
        # Calling resolve twice must not change the result — downstream code
        # may resolve defensively.
        once = BackendSpec.parse("codex").resolve()
        twice = once.resolve()
        self.assertEqual(once, twice)


# --- __str__ round-trip ---


class TestStrRoundTrip(unittest.TestCase):
    def test_full_spec_roundtrip(self) -> None:
        self.assertEqual(
            str(BackendSpec("codex", "gpt-5.4", "xhigh")),
            "codex:gpt-5.4:xhigh",
        )

    def test_bare_backend_no_trailing_colons(self) -> None:
        self.assertEqual(str(BackendSpec("codex")), "codex")
        self.assertEqual(str(BackendSpec("rp")), "rp")
        self.assertEqual(str(BackendSpec("none")), "none")

    def test_model_only(self) -> None:
        self.assertEqual(str(BackendSpec("codex", "gpt-5.4")), "codex:gpt-5.4")

    def test_effort_only_keeps_empty_model_slot(self) -> None:
        # Round-trip must preserve the spec: ``codex::high`` means "default
        # model, effort=high". If __str__ dropped the empty slot, re-parsing
        # would see ``codex:high`` → unknown model error.
        s = BackendSpec("codex", None, "high")
        self.assertEqual(str(s), "codex::high")
        self.assertEqual(BackendSpec.parse(str(s)), s)

    def test_parse_str_roundtrip_valid_specs(self) -> None:
        for raw in (
            "codex",
            "rp",
            "none",
            "copilot",
            "codex:gpt-5.4",
            "codex:gpt-5.4:xhigh",
            "copilot:claude-opus-4.5:xhigh",
            "copilot:gpt-5.4:medium",
            "cursor",
            "cursor:gpt-5.5-high",
            "cursor:gpt-5.3-codex-xhigh",
        ):
            with self.subTest(spec=raw):
                self.assertEqual(str(BackendSpec.parse(raw)), raw)


# --- Frozen dataclass guarantees ---


class TestFrozen(unittest.TestCase):
    def test_spec_is_hashable(self) -> None:
        # Frozen dataclasses are hashable — downstream code may stick specs
        # into sets / dict keys.
        s = BackendSpec("codex", "gpt-5.4", "high")
        self.assertEqual(hash(s), hash(BackendSpec("codex", "gpt-5.4", "high")))
        seen = {s, s, BackendSpec("codex")}
        self.assertEqual(len(seen), 2)

    def test_spec_is_immutable(self) -> None:
        s = BackendSpec("codex", "gpt-5.4", "high")
        with self.assertRaises(Exception):  # FrozenInstanceError is a dataclass subclass
            s.model = "gpt-5.2"  # type: ignore[misc]


# --- VALID_BACKENDS constant (fn-28.2) ---


class TestValidBackends(unittest.TestCase):
    """``VALID_BACKENDS`` mirrors registry keys sorted — downstream argparse
    ``choices=`` and any "valid list" UI depends on this shape."""

    def test_exists(self) -> None:
        self.assertTrue(hasattr(flowctl, "VALID_BACKENDS"))

    def test_matches_registry(self) -> None:
        self.assertEqual(
            flowctl.VALID_BACKENDS, sorted(BACKEND_REGISTRY.keys())
        )

    def test_is_sorted(self) -> None:
        self.assertEqual(
            list(flowctl.VALID_BACKENDS), sorted(flowctl.VALID_BACKENDS)
        )


# --- parse_backend_spec_lenient (legacy fallback — fn-28.2) ---


class TestLenientParse(unittest.TestCase):
    """Graceful fallback for stored legacy values. Runtime must never crash on
    old data — warn and degrade to bare backend."""

    def _capture_stderr(self, fn):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result = fn()
        return result, buf.getvalue()

    def test_empty_returns_none_no_warning(self) -> None:
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient("")
        )
        self.assertIsNone(result)
        self.assertEqual(err, "")

    def test_whitespace_returns_none_no_warning(self) -> None:
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient("   ")
        )
        self.assertIsNone(result)
        self.assertEqual(err, "")

    def test_none_returns_none_no_warning(self) -> None:
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient(None)
        )
        self.assertIsNone(result)
        self.assertEqual(err, "")

    def test_valid_spec_roundtrips_no_warning(self) -> None:
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient("codex:gpt-5.4:high")
        )
        self.assertEqual(result, BackendSpec("codex", "gpt-5.4", "high"))
        self.assertEqual(err, "")

    def test_legacy_dash_model_effort_falls_back_to_bare(self) -> None:
        # Hot-path case called out in the task spec: pre-epic users stored
        # ``codex:gpt-5.4-high`` (dash, not colon). Parser rejects as unknown
        # model; lenient must degrade to bare backend + stderr warning.
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient("codex:gpt-5.4-high")
        )
        self.assertEqual(result, BackendSpec("codex", None, None))
        self.assertIn("warning:", err)
        self.assertIn("codex:gpt-5.4-high", err)
        self.assertIn("codex", err)

    def test_legacy_bad_effort_falls_back_to_bare(self) -> None:
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient("codex:gpt-5.4:bogus")
        )
        self.assertEqual(result, BackendSpec("codex", None, None))
        self.assertIn("warning:", err)

    def test_unknown_backend_returns_none(self) -> None:
        # No recognizable backend prefix — caller gets None and stderr note.
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient("bogus-prefix:foo:bar")
        )
        self.assertIsNone(result)
        self.assertIn("No recognizable backend prefix", err)

    def test_warn_false_suppresses_stderr(self) -> None:
        result, err = self._capture_stderr(
            lambda: flowctl.parse_backend_spec_lenient(
                "codex:gpt-5.4-high", warn=False
            )
        )
        self.assertEqual(result, BackendSpec("codex", None, None))
        self.assertEqual(err, "")


# --- Command integration tests (fn-28.2) ---


@contextmanager
def _flow_fixture():
    """Spin up an isolated .flow dir under a temp cwd for command tests.

    Yields the temp path. Restores cwd + clears the module-level cache so each
    fixture test sees a fresh .flow/. Temp dir is cleaned via TemporaryDirectory.
    """
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="flowctl-cmd-test-") as td:
        os.chdir(td)
        try:
            # cmd_init requires git init — not strictly needed for set/show
            # commands but mirrors real usage.
            flow_dir = Path(td) / ".flow"
            flow_dir.mkdir(parents=True, exist_ok=True)
            (flow_dir / "epics").mkdir(exist_ok=True)
            (flow_dir / "tasks").mkdir(exist_ok=True)
            (flow_dir / "config.json").write_text("{}")
            yield Path(td)
        finally:
            os.chdir(old_cwd)


def _write_epic(flow_dir: Path, epic_id: str, **fields: Any) -> None:
    data = {
        "id": epic_id,
        "title": "Test epic",
        "status": "open",
        "branch_name": epic_id,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "next_task": 1,
        "depends_on_epics": [],
        "default_impl": None,
        "default_review": None,
        "default_sync": None,
    }
    data.update(fields)
    (flow_dir / "epics" / f"{epic_id}.json").write_text(json.dumps(data))


def _write_task(flow_dir: Path, task_id: str, epic_id: str, **fields: Any) -> None:
    data = {
        "id": task_id,
        "epic": epic_id,
        "title": "Test task",
        "status": "todo",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "depends_on": [],
        "impl": None,
        "review": None,
        "sync": None,
    }
    data.update(fields)
    (flow_dir / "tasks" / f"{task_id}.json").write_text(json.dumps(data))


def _ns(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


class TestSetBackendValidation(unittest.TestCase):
    """``cmd_epic_set_backend`` / ``cmd_task_set_backend`` must reject bad
    specs before writing to disk."""

    def test_task_set_backend_valid_spec_stored_as_is(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            out = io.StringIO()
            with redirect_stdout(out):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="codex:gpt-5.4:xhigh",
                        sync=None,
                        json=True,
                    )
                )
            raw = json.loads(
                (td / ".flow" / "tasks" / "fn-9-e.1.json").read_text()
            )
            # Store raw string exactly as typed (no normalization).
            self.assertEqual(raw["review"], "codex:gpt-5.4:xhigh")

    def test_task_set_backend_warns_and_accepts_unknown_model(self) -> None:
        # fn-76 R1: an unknown model is a preference miss, not a hard error — it
        # warns and is stored verbatim (the CLI is the availability authority).
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="codex:gpt-99",
                        sync=None,
                        json=True,
                    )
                )
            raw = json.loads(
                (td / ".flow" / "tasks" / "fn-9-e.1.json").read_text()
            )
            self.assertEqual(raw["review"], "codex:gpt-99")
            self.assertIn("not in flow-next's codex ranking", err.getvalue())

    def test_task_set_backend_rejects_rp_with_model(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            out = io.StringIO()
            with self.assertRaises(SystemExit), redirect_stdout(out):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="rp:claude-opus",
                        sync=None,
                        json=True,
                    )
                )
            payload = json.loads(out.getvalue())
            self.assertFalse(payload["success"])
            self.assertIn("does not accept a model", payload["error"])

    def test_task_set_backend_accepts_copilot_xhigh(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            out = io.StringIO()
            with redirect_stdout(out):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="copilot:claude-opus-4.5:xhigh",
                        sync=None,
                        json=True,
                    )
                )
            raw = json.loads(
                (td / ".flow" / "tasks" / "fn-9-e.1.json").read_text()
            )
            self.assertEqual(raw["review"], "copilot:claude-opus-4.5:xhigh")

    def test_task_set_backend_rejects_bad_spec_does_not_touch_disk(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow", "fn-9-e.1", "fn-9-e", review="codex"
            )
            before = (td / ".flow" / "tasks" / "fn-9-e.1.json").read_text()
            # A bad EFFORT still hard-fails (effort axis stays strict, fn-76) —
            # disk must be untouched. (An unknown MODEL now warn-and-accepts, so
            # it is no longer the rejection case.)
            with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="codex:gpt-5.4:bogus-effort",
                        sync=None,
                        json=True,
                    )
                )
            after = (td / ".flow" / "tasks" / "fn-9-e.1.json").read_text()
            self.assertEqual(
                before, after, "disk must be untouched on validation failure"
            )


# --- run_codex_exec / run_copilot_exec honor spec.model + spec.effort (fn-28.3) ---


class _FakeCompleted:
    """Minimal stand-in for subprocess.CompletedProcess.

    Captures the argv the caller would have passed to subprocess.run so tests
    can assert on --model / --effort / -c model_reasoning_effort flags
    without actually invoking codex or copilot.
    """

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@contextmanager
def _stub_subprocess(module, captured: list, *, stdout: str = "", returncode: int = 0):
    """Replace ``subprocess.run`` in the flowctl module with a capturing stub.

    The stub records ``(cmd_argv, kwargs)`` to ``captured`` and returns a
    ``_FakeCompleted`` whose stdout/returncode match the test's intent.
    Any call into ``shutil.which`` is also stubbed to return a sentinel path
    so ``require_codex`` / ``require_copilot`` don't error out on hosts that
    don't have codex/copilot installed.
    """
    import subprocess as _subprocess

    real_run = module.subprocess.run
    real_which = module.shutil.which

    def fake_run(cmd, **kwargs):
        captured.append((list(cmd), kwargs))
        return _FakeCompleted(stdout=stdout, returncode=returncode)

    def fake_which(binary):
        if binary in ("codex", "copilot"):
            return f"/fake/bin/{binary}"
        return real_which(binary)

    module.subprocess.run = fake_run
    module.shutil.which = fake_which
    try:
        yield
    finally:
        module.subprocess.run = real_run
        module.shutil.which = real_which


class TestRunCodexExecHonorsSpec(unittest.TestCase):
    """``run_codex_exec`` must pull model + effort from the passed ``BackendSpec``
    instead of the env-var / hardcoded defaults that lived there pre-fn-28.3."""

    def setUp(self) -> None:
        self._env_snapshot = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def test_spec_model_and_effort_flow_into_argv(self) -> None:
        # BackendSpec("codex", "gpt-5.2", "medium") must produce:
        #   --model gpt-5.2
        #   -c model_reasoning_effort="medium"
        # NOT the old hardcoded --model gpt-5.4 / effort="high".
        captured: list = []
        spec = BackendSpec("codex", "gpt-5.2", "medium")
        with _stub_subprocess(flowctl, captured, stdout='{"type":"thread.started","thread_id":"t1"}'):
            flowctl.run_codex_exec("prompt", sandbox="read-only", spec=spec)
        self.assertEqual(len(captured), 1)
        argv, _kwargs = captured[0]
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.2")
        # -c flag carries the effort in the form model_reasoning_effort="<val>"
        self.assertIn("-c", argv)
        c_val = argv[argv.index("-c") + 1]
        self.assertEqual(c_val, 'model_reasoning_effort="medium"')

    def test_spec_none_falls_back_to_registry_defaults(self) -> None:
        # Defensive path: spec=None must resolve via bare-codex defaults
        # (fn-76: ranking top gpt-5.6-sol / high). This keeps non-review callers
        # safe. repo_root defaults to None → cache/ladder are no-ops, so the
        # happy path dispatches the ranking top directly.
        captured: list = []
        with _stub_subprocess(flowctl, captured, stdout='{"type":"thread.started","thread_id":"t1"}'):
            flowctl.run_codex_exec("prompt", sandbox="read-only", spec=None)
        argv, _ = captured[0]
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.6-sol")
        self.assertEqual(
            argv[argv.index("-c") + 1],
            'model_reasoning_effort="high"',
        )

    def test_partial_spec_gets_resolved(self) -> None:
        # Spec with only backend set — should resolve() upstream. Effort env
        # fills the gap.
        os.environ["FLOW_CODEX_EFFORT"] = "low"
        captured: list = []
        spec = BackendSpec("codex")  # no model, no effort
        with _stub_subprocess(flowctl, captured, stdout='{"type":"thread.started","thread_id":"t1"}'):
            flowctl.run_codex_exec("prompt", sandbox="read-only", spec=spec)
        argv, _ = captured[0]
        # Registry default model (fn-76 ranking top, no env set) + env effort.
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.6-sol")
        self.assertEqual(
            argv[argv.index("-c") + 1],
            'model_reasoning_effort="low"',
        )

    def test_explicit_spec_wins_over_env(self) -> None:
        # Env must NOT override an explicit spec value — that would defeat
        # per-task model pinning.
        os.environ["FLOW_CODEX_MODEL"] = "gpt-5"
        os.environ["FLOW_CODEX_EFFORT"] = "low"
        captured: list = []
        spec = BackendSpec("codex", "gpt-5.2", "xhigh")
        with _stub_subprocess(flowctl, captured, stdout='{"type":"thread.started","thread_id":"t1"}'):
            flowctl.run_codex_exec("prompt", sandbox="read-only", spec=spec)
        argv, _ = captured[0]
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.2")
        self.assertEqual(
            argv[argv.index("-c") + 1],
            'model_reasoning_effort="xhigh"',
        )


class TestRunCopilotExecHonorsSpec(unittest.TestCase):
    """``run_copilot_exec`` must honor the spec. The claude-* effort skip
    is a live fn-27 bug fix and must remain intact."""

    def setUp(self) -> None:
        self._env_snapshot = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)
        self._tmp = tempfile.TemporaryDirectory(prefix="copilot-spec-test-")
        self.repo_root = Path(self._tmp.name)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)
        self._tmp.cleanup()

    def test_spec_model_and_effort_flow_into_argv(self) -> None:
        captured: list = []
        spec = BackendSpec("copilot", "gpt-5.4", "medium")
        with _stub_subprocess(flowctl, captured, stdout="verdict"):
            flowctl.run_copilot_exec(
                "prompt", session_id="s1", repo_root=self.repo_root, spec=spec
            )
        argv, _ = captured[0]
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.4")
        # gpt-5.4 accepts --effort (non-claude model).
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")

    def test_claude_model_skips_effort_flag(self) -> None:
        # THE fn-27 live bug fix: Claude models reject --effort. Must stay.
        captured: list = []
        spec = BackendSpec("copilot", "claude-opus-4.5", "xhigh")
        with _stub_subprocess(flowctl, captured, stdout="verdict"):
            flowctl.run_copilot_exec(
                "prompt", session_id="s1", repo_root=self.repo_root, spec=spec
            )
        argv, _ = captured[0]
        self.assertEqual(argv[argv.index("--model") + 1], "claude-opus-4.5")
        # --effort must NOT appear for claude-* — Copilot CLI rejects it.
        self.assertNotIn("--effort", argv)

    def test_claude_haiku_also_skips_effort(self) -> None:
        # Every claude-* model, not just opus. Use .startswith("claude-").
        captured: list = []
        spec = BackendSpec("copilot", "claude-haiku-4.5", "low")
        with _stub_subprocess(flowctl, captured, stdout="verdict"):
            flowctl.run_copilot_exec(
                "prompt", session_id="s1", repo_root=self.repo_root, spec=spec
            )
        argv, _ = captured[0]
        self.assertEqual(argv[argv.index("--model") + 1], "claude-haiku-4.5")
        self.assertNotIn("--effort", argv)

    def test_gpt_model_keeps_effort(self) -> None:
        # Sanity — non-claude must keep --effort.
        captured: list = []
        spec = BackendSpec("copilot", "gpt-4.1", "high")
        with _stub_subprocess(flowctl, captured, stdout="verdict"):
            flowctl.run_copilot_exec(
                "prompt", session_id="s1", repo_root=self.repo_root, spec=spec
            )
        argv, _ = captured[0]
        self.assertIn("--effort", argv)
        self.assertEqual(argv[argv.index("--effort") + 1], "high")

    def test_explicit_spec_wins_over_env(self) -> None:
        os.environ["FLOW_COPILOT_MODEL"] = "gpt-4.1"
        os.environ["FLOW_COPILOT_EFFORT"] = "low"
        captured: list = []
        spec = BackendSpec("copilot", "gpt-5.4", "xhigh")
        with _stub_subprocess(flowctl, captured, stdout="verdict"):
            flowctl.run_copilot_exec(
                "prompt", session_id="s1", repo_root=self.repo_root, spec=spec
            )
        argv, _ = captured[0]
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.4")
        self.assertEqual(argv[argv.index("--effort") + 1], "xhigh")


# --- resolve_review_spec precedence (fn-28.3) ---


class TestResolveReviewSpec(unittest.TestCase):
    """The resolution helper is the single source of truth for which spec
    flows into a review. Test each precedence rung."""

    def setUp(self) -> None:
        self._env_snapshot = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def test_task_review_spec_wins(self) -> None:
        # Task fn-9-e.1 has review: "codex:gpt-5.2" — resolved spec must
        # carry that model through even when an env model var is set.
        os.environ["FLOW_CODEX_MODEL"] = "gpt-5"  # loses to task spec
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e", default_review="codex:gpt-5.4")
            _write_task(
                td / ".flow", "fn-9-e.1", "fn-9-e", review="codex:gpt-5.2"
            )
            resolved = flowctl.resolve_review_spec("codex", "fn-9-e.1")
            self.assertEqual(resolved.backend, "codex")
            self.assertEqual(resolved.model, "gpt-5.2")

    def test_epic_default_fills_when_task_unset(self) -> None:
        with _flow_fixture() as td:
            _write_epic(
                td / ".flow", "fn-9-e", default_review="codex:gpt-5.2:medium"
            )
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")  # no per-task spec
            resolved = flowctl.resolve_review_spec("codex", "fn-9-e.1")
            self.assertEqual(resolved.model, "gpt-5.2")
            self.assertEqual(resolved.effort, "medium")

    def test_env_review_backend_beats_config(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "codex:gpt-5.2"
        with _flow_fixture() as td:
            # Config says gpt-5 but env wins.
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex:gpt-5"}})
            )
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            resolved = flowctl.resolve_review_spec("codex", "fn-9-e.1")
            self.assertEqual(resolved.model, "gpt-5.2")

    def test_config_backend_when_nothing_else_set(self) -> None:
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "copilot:gpt-5.4"}})
            )
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            resolved = flowctl.resolve_review_spec("codex", "fn-9-e.1")
            # Config spec says copilot — resolved carries that forward. The
            # codex command still executes via codex CLI; model name travels
            # in spec.
            self.assertEqual(resolved.backend, "copilot")
            self.assertEqual(resolved.model, "gpt-5.4")

    def test_return_source_reports_config(self) -> None:
        # PR #184 Finding B: return_source tags where the resolved spec came from.
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex:gpt-5.4"}})
            )
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            spec, source = flowctl.resolve_review_spec(
                "copilot", "fn-9-e.1", return_source=True)
            self.assertEqual(source, "config")
            self.assertEqual(spec.backend, "codex")

    def test_codex_helper_coerces_config_default(self) -> None:
        # Finding B: explicit `flowctl codex` with config default=rp (a modelless
        # non-codex backend) coerces to the codex default — never stamps a
        # foreign/null model on the receipt.
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "rp"}})
            )
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            args = argparse.Namespace(spec=None, json=False)
            out = flowctl._resolve_codex_review_spec(args, "fn-9-e.1")
            self.assertEqual(out.backend, "codex")
            self.assertTrue(out.model)

    def test_codex_helper_coerces_per_task_cross_backend(self) -> None:
        # A stored per-task cross-backend review is COERCED to the codex default —
        # `flowctl codex` ALWAYS runs codex, so a foreign (e.g. cursor-format) model can't
        # be honored; an explicit `--review=codex` wins over the stored spec (PR #184).
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e",
                        review="cursor:gpt-5.5-high")
            args = argparse.Namespace(spec=None, json=False)
            out = flowctl._resolve_codex_review_spec(args, "fn-9-e.1")
            self.assertEqual(out.backend, "codex")
            self.assertTrue(out.model)

    def test_copilot_helper_coerces_per_task_cross_backend(self) -> None:
        # Symmetric to codex: a stored per-task cursor spec is coerced to the copilot default.
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e",
                        review="cursor:gpt-5.5-high")
            args = argparse.Namespace(spec=None, json=False)
            out = flowctl._resolve_copilot_review_spec(args, "fn-9-e.1")
            self.assertEqual(out.backend, "copilot")

    def test_copilot_helper_coerces_config_default(self) -> None:
        # Finding B + A: copilot coerces a non-copilot config default to copilot's
        # gpt-5.5 (not the retired gpt-5.2), so the receipt is accurate.
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "rp"}})
            )
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            args = argparse.Namespace(spec=None, json=False)
            out = flowctl._resolve_copilot_review_spec(args, "fn-9-e.1")
            self.assertEqual(out.backend, "copilot")
            self.assertEqual(out.model, "gpt-5.5")

    def test_backend_hint_fallback_when_nothing_set(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            resolved = flowctl.resolve_review_spec("codex", "fn-9-e.1")
            self.assertEqual(resolved.backend, "codex")
            self.assertEqual(resolved.model, "gpt-5.6-sol")  # fn-76 ranking top
            self.assertEqual(resolved.effort, "high")

    def test_no_task_id_still_resolves(self) -> None:
        # Plan / completion reviews pass task_id=None — must still resolve.
        with _flow_fixture():
            resolved = flowctl.resolve_review_spec("copilot", None)
            self.assertEqual(resolved.backend, "copilot")
            self.assertEqual(resolved.model, "gpt-5.5")  # registry default

    def test_spec_id_resolves_per_spec_default_review_no_task(self) -> None:
        # PR #184 T3: plan/completion reviews pass task_id=None but DO know the
        # spec id. A per-spec ``default_review`` must be discovered directly via
        # ``spec_id`` (no task to follow) and tagged source "epic".
        with _flow_fixture() as td:
            _write_epic(
                td / ".flow", "fn-9-e", default_review="cursor:gpt-5.3-codex"
            )
            spec, source = flowctl.resolve_review_spec(
                "cursor", None, spec_id="fn-9-e", return_source=True
            )
            self.assertEqual(source, "epic")
            self.assertEqual(spec.backend, "cursor")
            self.assertEqual(spec.model, "gpt-5.3-codex")

    def test_cursor_helper_honors_per_spec_default_review(self) -> None:
        # The cursor helper threads spec_id through and HONORS the per-spec
        # ``default_review`` (source "epic" is never coerced), so an epic-scoped
        # plan/completion review runs the configured cursor model.
        with _flow_fixture() as td:
            _write_epic(
                td / ".flow", "fn-9-e", default_review="cursor:gpt-5.3-codex"
            )
            args = argparse.Namespace(spec=None, json=False)
            out = flowctl._resolve_cursor_review_spec(
                args, None, spec_id="fn-9-e"
            )
            self.assertEqual(out.backend, "cursor")
            self.assertEqual(out.model, "gpt-5.3-codex")


# --- Per-task review spec actually runs that model (fn-28.3 integration) ---


class TestPerTaskReviewSpecIntegration(unittest.TestCase):
    """End-to-end-ish: task with ``review: "codex:gpt-5.2"`` + `flowctl codex
    impl-review fn-X` => subprocess argv contains ``--model gpt-5.2`` (not the
    default gpt-5.5). Receipt stamps model+effort+spec from resolved spec."""

    def setUp(self) -> None:
        self._env_snapshot = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def _stub_review_side_effects(self, module):
        """Stub out git/file-system heavy helpers so cmd_codex_impl_review
        can run in-process without an actual git repo or codex binary.

        Returns a context manager. Minimum set needed:
          - get_repo_root → fixture dir
          - get_changed_files → empty list (skip embed logic)
          - gather_context_hints → ""
          - build_review_prompt → returns "fake"
          - parse_codex_verdict → SHIP
        Plus ``subprocess.run`` / ``shutil.which`` from _stub_subprocess for
        the run_codex_exec call.
        """
        @contextmanager
        def _cm(fixture_dir: Path, captured: list):
            saved = {
                "get_repo_root": module.get_repo_root,
                "get_changed_files": module.get_changed_files,
                "gather_context_hints": module.gather_context_hints,
                "build_review_prompt": module.build_review_prompt,
                "parse_codex_verdict": module.parse_codex_verdict,
                "resolve_codex_sandbox": module.resolve_codex_sandbox,
                "is_sandbox_failure": module.is_sandbox_failure,
                "subprocess_Popen": module.subprocess.Popen,
            }

            # Minimal git diff via Popen stub — return empty diff.
            class _FakePopen:
                def __init__(self, *args, **kwargs):
                    self.stdout = io.BytesIO(b"")
                    self.stderr = io.BytesIO(b"")

                def wait(self):
                    return 0

            module.get_repo_root = lambda: fixture_dir
            module.get_changed_files = lambda base: []
            module.gather_context_hints = lambda base: ""
            module.build_review_prompt = lambda *a, **kw: "fake-prompt"
            module.parse_codex_verdict = lambda out: "SHIP"
            module.resolve_codex_sandbox = lambda s: "read-only"
            module.is_sandbox_failure = lambda *a, **kw: False
            module.subprocess.Popen = _FakePopen

            with _stub_subprocess(
                module,
                captured,
                stdout='{"type":"thread.started","thread_id":"t-abc"}\n',
            ):
                try:
                    yield
                finally:
                    for name, fn in saved.items():
                        if name == "subprocess_Popen":
                            module.subprocess.Popen = fn
                        else:
                            setattr(module, name, fn)

        return _cm

    def test_task_with_codex_gpt52_spec_runs_gpt52(self) -> None:
        captured: list = []
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow", "fn-9-e.1", "fn-9-e", review="codex:gpt-5.2"
            )
            # Task spec markdown needs to exist too (cmd reads .md file).
            (td / ".flow" / "tasks" / "fn-9-e.1.md").write_text(
                "# Fake task\n\nTest task spec content."
            )
            receipt_path = td / "receipt.json"
            cm = self._stub_review_side_effects(flowctl)
            with cm(td, captured):
                args = _ns(
                    task="fn-9-e.1",
                    base="main",
                    focus=None,
                    receipt=str(receipt_path),
                    json=True,
                    sandbox="read-only",
                    spec=None,
                )
                try:
                    with redirect_stdout(io.StringIO()):
                        flowctl.cmd_codex_impl_review(args)
                except SystemExit:
                    # json_output calls sys.exit(0) on success — fine.
                    pass
            # Find the codex exec argv (not the git diff Popen calls).
            exec_calls = [
                (argv, kw) for (argv, kw) in captured
                if argv and argv[0].endswith("/codex")
            ]
            self.assertTrue(exec_calls, f"no codex exec calls captured: {captured}")
            argv, _ = exec_calls[-1]
            # Per-task spec `codex:gpt-5.2` (effort unset → registry default "high").
            self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.2")
            self.assertEqual(
                argv[argv.index("-c") + 1],
                'model_reasoning_effort="high"',
            )
            # Receipt carries model + effort + canonical spec string.
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["model"], "gpt-5.2")
            self.assertEqual(receipt["effort"], "high")
            self.assertEqual(receipt["spec"], "codex:gpt-5.2:high")

    def test_spec_cli_flag_overrides_task_spec(self) -> None:
        # Task says codex:gpt-5.2 but --spec on argv says codex:gpt-5:low.
        # --spec must win.
        captured: list = []
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow", "fn-9-e.1", "fn-9-e", review="codex:gpt-5.2"
            )
            (td / ".flow" / "tasks" / "fn-9-e.1.md").write_text("# Fake")
            receipt_path = td / "receipt.json"
            cm = self._stub_review_side_effects(flowctl)
            with cm(td, captured):
                args = _ns(
                    task="fn-9-e.1",
                    base="main",
                    focus=None,
                    receipt=str(receipt_path),
                    json=True,
                    sandbox="read-only",
                    spec="codex:gpt-5:low",
                )
                try:
                    with redirect_stdout(io.StringIO()):
                        flowctl.cmd_codex_impl_review(args)
                except SystemExit:
                    pass
            exec_calls = [
                (argv, kw) for (argv, kw) in captured
                if argv and argv[0].endswith("/codex")
            ]
            argv, _ = exec_calls[-1]
            self.assertEqual(argv[argv.index("--model") + 1], "gpt-5")
            self.assertEqual(
                argv[argv.index("-c") + 1],
                'model_reasoning_effort="low"',
            )
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["model"], "gpt-5")
            self.assertEqual(receipt["effort"], "low")
            self.assertEqual(receipt["spec"], "codex:gpt-5:low")

    def test_invalid_spec_cli_flag_rejected(self) -> None:
        # --spec takes strict parse — bad specs must fail loudly.
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            (td / ".flow" / "tasks" / "fn-9-e.1.md").write_text("# Fake")
            args = _ns(
                task="fn-9-e.1",
                base="main",
                focus=None,
                receipt=None,
                json=True,
                sandbox="read-only",
                # fn-76: an unknown MODEL now warn-and-accepts, so use a bad
                # EFFORT (effort axis stays strict) to exercise strict --spec
                # rejection.
                spec="codex:gpt-5.4:bogus-effort",
            )
            out = io.StringIO()
            with self.assertRaises(SystemExit), redirect_stdout(out):
                flowctl.cmd_codex_impl_review(args)
            payload = json.loads(out.getvalue())
            self.assertFalse(payload["success"])
            self.assertIn("Invalid --spec", payload["error"])
            self.assertIn("Unknown effort for codex", payload["error"])


# --- cmd_review_backend (fn-28.4) ---


class TestReviewBackendCmd(unittest.TestCase):
    """``flowctl review-backend`` accepts spec-form FLOW_REVIEW_BACKEND and
    config.json review.backend. Text mode still prints bare backend for
    back-compat with skill greps; JSON mode returns full resolved spec."""

    def setUp(self) -> None:
        self._env_snapshot = os.environ.copy()
        # Scrub any FLOW_* env so each test starts clean.
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def _run_json(self) -> dict:
        out = io.StringIO()
        with redirect_stdout(out):
            flowctl.cmd_review_backend(_ns(json=True))
        return json.loads(out.getvalue())

    def _run_text(self) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            flowctl.cmd_review_backend(_ns(json=False))
        return out.getvalue().strip()

    # --- env spec form ---

    def test_env_spec_returns_full_resolution(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "codex:gpt-5.2:medium"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "codex")
            self.assertEqual(payload["spec"], "codex:gpt-5.2:medium")
            self.assertEqual(payload["model"], "gpt-5.2")
            self.assertEqual(payload["effort"], "medium")
            self.assertEqual(payload["source"], "env")

    def test_env_spec_text_mode_prints_bare_backend(self) -> None:
        # Back-compat contract: `BACKEND=$(flowctl review-backend)` in skills
        # must still get `codex`, not `codex:gpt-5.4:xhigh`.
        os.environ["FLOW_REVIEW_BACKEND"] = "codex:gpt-5.4:xhigh"
        with _flow_fixture():
            self.assertEqual(self._run_text(), "codex")

    def test_env_copilot_spec_full_form(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "copilot:claude-opus-4.5:xhigh"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "copilot")
            self.assertEqual(payload["spec"], "copilot:claude-opus-4.5:xhigh")
            self.assertEqual(payload["model"], "claude-opus-4.5")
            self.assertEqual(payload["effort"], "xhigh")

    # --- env bare form (back-compat) ---

    def test_env_bare_codex_resolves_defaults(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "codex"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "codex")
            self.assertEqual(payload["spec"], "codex:gpt-5.6-sol:high")
            self.assertEqual(payload["model"], "gpt-5.6-sol")
            self.assertEqual(payload["effort"], "high")
            self.assertEqual(payload["source"], "env")

    def test_env_bare_rp_has_no_model_or_effort(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "rp"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "rp")
            self.assertEqual(payload["spec"], "rp")
            self.assertIsNone(payload["model"])
            self.assertIsNone(payload["effort"])

    def test_env_bare_none_returns_none(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "none"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "none")
            self.assertEqual(payload["source"], "env")

    # --- config.json source ---

    def test_config_spec_form_resolves(self) -> None:
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "copilot:claude-haiku-4.5"}})
            )
            payload = self._run_json()
            self.assertEqual(payload["backend"], "copilot")
            self.assertEqual(payload["spec"], "copilot:claude-haiku-4.5:high")
            self.assertEqual(payload["model"], "claude-haiku-4.5")
            self.assertEqual(payload["source"], "config")

    def test_env_beats_config(self) -> None:
        os.environ["FLOW_REVIEW_BACKEND"] = "codex:gpt-5.2"
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "copilot"}})
            )
            payload = self._run_json()
            self.assertEqual(payload["backend"], "codex")
            self.assertEqual(payload["model"], "gpt-5.2")
            self.assertEqual(payload["source"], "env")

    # --- unset fallback ---

    def test_unset_returns_ask(self) -> None:
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "ASK")
            self.assertEqual(payload["spec"], "ASK")
            self.assertIsNone(payload["model"])
            self.assertIsNone(payload["effort"])
            self.assertEqual(payload["source"], "none")

    def test_unset_text_prints_ask(self) -> None:
        with _flow_fixture():
            self.assertEqual(self._run_text(), "ASK")

    # --- legacy / invalid fallthrough ---

    def test_invalid_spec_falls_back_to_bare_backend(self) -> None:
        # Pre-fn-28 legacy stored value "codex:gpt-5.4-high" (no colon between
        # model+effort). Lenient parse recovers the bare backend rather than
        # silently returning ASK (pre-fn-28.4 behavior).
        os.environ["FLOW_REVIEW_BACKEND"] = "codex:gpt-5.4-high"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "codex")
            # Full spec resolves to registry defaults since model was unparseable
            # (fn-76: legacy dash-composite still degrades to bare; ranking top).
            self.assertEqual(payload["spec"], "codex:gpt-5.6-sol:high")
            self.assertEqual(payload["source"], "env")

    def test_garbage_env_returns_ask(self) -> None:
        # Garbage with no recognizable backend prefix → fall through to ASK.
        os.environ["FLOW_REVIEW_BACKEND"] = "not-a-backend"
        with _flow_fixture():
            payload = self._run_json()
            self.assertEqual(payload["backend"], "ASK")

    # --- spec-form config precedence vs env bare ---

    def test_config_spec_beats_empty_env(self) -> None:
        # Spec-form in config resolves even when env is empty string.
        os.environ["FLOW_REVIEW_BACKEND"] = ""
        with _flow_fixture() as td:
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex:gpt-5.2:low"}})
            )
            payload = self._run_json()
            self.assertEqual(payload["backend"], "codex")
            self.assertEqual(payload["spec"], "codex:gpt-5.2:low")
            self.assertEqual(payload["effort"], "low")
            self.assertEqual(payload["source"], "config")


class TestRalphBareBackendExtraction(unittest.TestCase):
    """Ralph's `${VAR%%:*}` pattern must extract bare backend for both bare
    and spec forms. This is a smoke test against the pattern the Ralph shell
    script uses — not the shell itself, but the equivalent pure-Python form.
    If this pattern is ever changed in ralph.sh, update this test too.
    """

    def test_bare_backend_extraction_python_equivalent(self) -> None:
        # Python equivalent of bash ${VAR%%:*}
        def bare(v: str) -> str:
            return v.split(":", 1)[0]

        self.assertEqual(bare("codex"), "codex")
        self.assertEqual(bare("codex:gpt-5.4:xhigh"), "codex")
        self.assertEqual(bare("copilot:claude-opus-4.5"), "copilot")
        self.assertEqual(bare("rp"), "rp")
        self.assertEqual(bare("none"), "none")
        # Degenerate: trailing colon still parses cleanly.
        self.assertEqual(bare("codex:"), "codex")


class NoEmbedRegression(unittest.TestCase):
    """PR #184 — all review backends (codex/copilot/cursor) read changed files
    from disk; the review prompt NEVER embeds file contents. These guard against
    a silent re-introduction of embedding (which broke cursor's argv limit and
    bloated codex/copilot prompts)."""

    def test_review_prompt_has_no_embedded_files_block(self) -> None:
        prompt = flowctl.build_review_prompt(
            "impl", "SPEC", "HINTS", diff_summary="DSUM", diff_content="DDIFF")
        self.assertNotIn("<embedded_files>", prompt)
        self.assertTrue(
            "read files from" in prompt or "full access" in prompt,
            "review prompt must instruct the reviewer to read files from disk")

    def test_completion_prompt_has_no_embedded_files_block(self) -> None:
        prompt = flowctl.build_completion_review_prompt(
            "EPIC", "TASKS", "DSUM", "DDIFF")
        self.assertNotIn("<embedded_files>", prompt)

    def test_embed_helper_stays_removed(self) -> None:
        # get_embedded_file_contents was removed when backends went agentic;
        # its return is a regression signal.
        self.assertFalse(hasattr(flowctl, "get_embedded_file_contents"))

    def test_builders_reject_embed_kwargs(self) -> None:
        # The dead files_embedded / embedded_files params must not come back.
        for name in ("build_review_prompt", "build_standalone_review_prompt",
                     "build_completion_review_prompt", "build_rereview_preamble"):
            params = inspect.signature(getattr(flowctl, name)).parameters
            self.assertNotIn("files_embedded", params,
                             f"{name} regained files_embedded")
            self.assertNotIn("embedded_files", params,
                             f"{name} regained embedded_files")


class TestReviewBackendTaskAware(unittest.TestCase):
    """PR #184 codex finding — `flowctl review-backend <id>` must let a per-task /
    per-spec `review` override route above env/config, so the review skills pick the
    right backend even when it differs from the project default (else a task set to
    `review: cursor:...` under a codex default would run the wrong CLI)."""

    def _rb(self, review_id):
        out = io.StringIO()
        with redirect_stdout(out):
            flowctl.cmd_review_backend(_ns(id=review_id, json=False))
        return out.getvalue().strip()

    def test_per_spec_override_beats_config(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e", default_review="cursor:gpt-5.3-codex")
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex"}}))
            self.assertEqual(self._rb("fn-9-e"), "cursor")   # per-spec override wins
            self.assertEqual(self._rb(None), "codex")        # no id → config default

    def test_per_task_override_beats_config(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e", default_review="codex")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e", review="cursor:gpt-5.3-codex")
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex"}}))
            self.assertEqual(self._rb("fn-9-e.1"), "cursor")

    def test_no_override_falls_through_to_config(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")  # no default_review
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "copilot"}}))
            self.assertEqual(self._rb("fn-9-e"), "copilot")  # id given, no override → config

    def test_bare_handle_canonicalized_to_slugged_spec(self) -> None:
        # A bare `fn-9` / `fn-9.1` handle must expand to the slugged on-disk id so its
        # stored override applies — else resolve_review_spec's exact-file lookup misses it.
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-cool-slug", default_review="cursor:gpt-5.3-codex")
            (td / ".flow" / "config.json").write_text(
                json.dumps({"review": {"backend": "codex"}}))
            self.assertEqual(self._rb("fn-9"), "cursor")     # bare spec handle canonicalized
            _write_task(td / ".flow", "fn-9-cool-slug.1", "fn-9-cool-slug",
                        review="cursor:gpt-5.3-codex")
            self.assertEqual(self._rb("fn-9.1"), "cursor")   # bare task handle canonicalized


# --- fn-112 review-driver hooks + generic cmd_backend_review ---


class TestBackendReviewDriverHooks(unittest.TestCase):
    """Registry hooks + driver entry points for the impl-review migration."""

    @classmethod
    def setUpClass(cls) -> None:
        flowctl._wire_backend_review_hooks()

    def test_review_backends_expose_required_hooks(self) -> None:
        required = {
            "run_exec",
            "resolve_spec",
            "check_probe",
            "gather_diff",
            "prompt_fit",
            "resume_modes",
            "mint_session_id",
            "include_effort",
            "extract_review",
            "has_sandbox",
        }
        for backend in ("codex", "copilot", "cursor"):
            with self.subTest(backend=backend):
                reg = BACKEND_REGISTRY[backend]
                for key in required:
                    self.assertIn(key, reg, f"{backend} missing hook {key}")
                self.assertTrue(callable(reg["run_exec"]))
                self.assertTrue(callable(reg["resolve_spec"]))
                self.assertTrue(callable(reg["check_probe"]))
                self.assertTrue(callable(reg["gather_diff"]))

    def test_hook_variance_preserved(self) -> None:
        # Genuine differences stay as hooks, not collapsed to one behavior.
        self.assertTrue(BACKEND_REGISTRY["codex"]["has_sandbox"])
        self.assertFalse(BACKEND_REGISTRY["copilot"]["has_sandbox"])
        self.assertFalse(BACKEND_REGISTRY["cursor"]["has_sandbox"])

        self.assertFalse(BACKEND_REGISTRY["codex"]["mint_session_id"])
        self.assertTrue(BACKEND_REGISTRY["copilot"]["mint_session_id"])
        self.assertFalse(BACKEND_REGISTRY["cursor"]["mint_session_id"])

        self.assertTrue(BACKEND_REGISTRY["codex"]["include_effort"])
        self.assertTrue(BACKEND_REGISTRY["copilot"]["include_effort"])
        self.assertFalse(BACKEND_REGISTRY["cursor"]["include_effort"])

        self.assertEqual(BACKEND_REGISTRY["codex"]["prompt_fit"], "none")
        self.assertEqual(BACKEND_REGISTRY["copilot"]["prompt_fit"], "none")
        self.assertEqual(BACKEND_REGISTRY["cursor"]["prompt_fit"], "cursor_argv")

        self.assertEqual(
            BACKEND_REGISTRY["codex"]["resume_modes"], (None, "codex")
        )
        self.assertEqual(BACKEND_REGISTRY["copilot"]["resume_modes"], ("copilot",))
        self.assertEqual(BACKEND_REGISTRY["cursor"]["resume_modes"], ("cursor",))

    def test_impl_wrappers_route_through_driver(self) -> None:
        # Thin wrappers must call cmd_backend_review (not re-implement the body).
        for fn in (
            flowctl.cmd_codex_impl_review,
            flowctl.cmd_copilot_impl_review,
            flowctl.cmd_cursor_impl_review,
        ):
            src = inspect.getsource(fn)
            self.assertIn("cmd_backend_review(", src)
            # Strip docstrings so historical prose mentioning run_*_exec is ignored.
            body = re.sub(r'""".*?"""', "", src, flags=re.S)
            body = re.sub(r"'''.*?'''", "", body, flags=re.S)
            self.assertNotIn("run_codex_exec(", body)
            self.assertNotIn("run_copilot_exec(", body)
            self.assertNotIn("run_cursor_exec(", body)

    def test_cmd_backend_review_exists(self) -> None:
        self.assertTrue(callable(flowctl.cmd_backend_review))
        sig = inspect.signature(flowctl.cmd_backend_review)
        self.assertIn("backend", sig.parameters)
        self.assertIn("kind", sig.parameters)

    def test_plan_completion_wrappers_route_through_driver(self) -> None:
        for fn in (
            flowctl.cmd_codex_plan_review,
            flowctl.cmd_copilot_plan_review,
            flowctl.cmd_cursor_plan_review,
            flowctl.cmd_codex_completion_review,
            flowctl.cmd_copilot_completion_review,
            flowctl.cmd_cursor_completion_review,
        ):
            src = inspect.getsource(fn)
            self.assertIn("cmd_backend_review(", src)
            body = re.sub(r'""".*?"""', "", src, flags=re.S)
            body = re.sub(r"'''.*?'''", "", body, flags=re.S)
            self.assertNotIn("run_codex_exec(", body)
            self.assertNotIn("run_copilot_exec(", body)
            self.assertNotIn("run_cursor_exec(", body)

    def test_stamp_ralph_iteration_helper(self) -> None:
        self.assertTrue(callable(flowctl.stamp_ralph_iteration))
        src = Path(flowctl.__file__).read_text(encoding="utf-8")
        self.assertEqual(src.count("def stamp_ralph_iteration("), 1)
        self.assertEqual(
            len(re.findall(r'os\.environ\.get\("RALPH_ITERATION"\)', src)), 1
        )
        receipt: dict = {}
        old = os.environ.get("RALPH_ITERATION")
        try:
            os.environ["RALPH_ITERATION"] = "7"
            flowctl.stamp_ralph_iteration(receipt)
            self.assertEqual(receipt["iteration"], 7)
            receipt2: dict = {}
            os.environ["RALPH_ITERATION"] = "nope"
            flowctl.stamp_ralph_iteration(receipt2)
            self.assertNotIn("iteration", receipt2)
        finally:
            if old is None:
                os.environ.pop("RALPH_ITERATION", None)
            else:
                os.environ["RALPH_ITERATION"] = old

    def test_plan_completion_pipelines_exist(self) -> None:
        self.assertTrue(callable(flowctl._backend_plan_review))
        self.assertTrue(callable(flowctl._backend_completion_review))
        self.assertTrue(callable(flowctl._self_write_review_status))

    def test_fourth_backend_registry_entry_only(self) -> None:
        """fn-112.4 extensibility proof: a 4th backend is a registry entry.

        Register a hypothetical backend with only BACKEND_REGISTRY hooks
        (mock run_exec) and drive cmd_backend_review through impl kind
        end-to-end. No new cmd_* clone required.
        """
        import subprocess

        backend = "mockreview"
        self.assertNotIn(backend, BACKEND_REGISTRY)

        review_out = (
            "Reviewed.\n\n"
            "```json\n"
            '{"suppressed_count":{"50":1},"classification_counts":'
            '{"introduced":1,"pre_existing":0},"unaddressed":["R1"]}\n'
            "```\n"
            "<verdict>NEEDS_WORK</verdict>\n"
        )
        calls: list[dict] = []

        def _mock_run_exec(
            prompt,
            *,
            session_id=None,
            repo_root,
            spec,
            resolution_out=None,
            args=None,
        ):
            calls.append({"prompt": prompt, "spec": spec, "session_id": session_id})
            if resolution_out is not None:
                resolution_out["model"] = "mock-1"
                resolution_out["effort"] = "high"
            return review_out, "mock-sid-1", 0, ""

        def _mock_resolve(args, task_id, spec_id=None):
            return BackendSpec(
                backend, model="mock-1", effort="high"
            ).resolve()

        entry = {
            "models": ["mock-1"],
            "efforts": {"high"},
            "default_model": "mock-1",
            "default_effort": "high",
            "run_exec": _mock_run_exec,
            "resolve_spec": _mock_resolve,
            "check_probe": lambda: "0.0.1",
            "gather_diff": flowctl._gather_review_diff_capped,
            "resume_modes": ("mockreview",),
            "track_prior_receipt_model": False,
            "require_nonempty_sid": False,
            "mint_session_id": False,
            "has_sandbox": False,
            "include_effort": True,
            "extract_review": lambda output: output,
            "display_name": "MockReview",
            "cli_label": "mockreview",
            "no_verdict_label": "MockReview",
            "prompt_fit": "none",
            "build_impl_prompt": "default",
        }

        prev_cwd = os.getcwd()
        with tempfile.TemporaryDirectory(prefix="fn112-4th-") as td:
            repo = Path(td)
            subprocess.run(
                ["git", "init", "-q"], cwd=repo, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "t@t.t"],
                cwd=repo, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "t"],
                cwd=repo, check=True, capture_output=True,
            )
            (repo / "src").mkdir()
            (repo / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-A"], cwd=repo, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", "base"],
                cwd=repo, check=True, capture_output=True,
            )
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo, check=True, capture_output=True, text=True,
            ).stdout.strip()
            (repo / "src" / "a.py").write_text("x=2\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-A"], cwd=repo, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", "change"],
                cwd=repo, check=True, capture_output=True,
            )

            flow = repo / ".flow"
            (flow / "specs").mkdir(parents=True)
            (flow / "tasks").mkdir(parents=True)
            epic = "fn-112-demo"
            task = f"{epic}.1"
            (flow / "specs" / f"{epic}.md").write_text(
                "# Demo\n\n## Acceptance Criteria\n\n- **R1:** do\n",
                encoding="utf-8",
            )
            (flow / "specs" / f"{epic}.json").write_text(
                json.dumps({"id": epic, "title": "Demo", "status": "in_progress"}),
                encoding="utf-8",
            )
            (flow / "tasks" / f"{task}.md").write_text(
                "---\nsatisfies: [R1]\n---\n\n## Description\n\nDo.\n",
                encoding="utf-8",
            )

            receipt = repo / "receipt.json"
            args = argparse.Namespace(
                task=task,
                base=base,
                focus=None,
                receipt=str(receipt),
                json=False,
                spec=None,
            )

            BACKEND_REGISTRY[backend] = entry
            try:
                os.chdir(repo)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    flowctl.cmd_backend_review(args, backend=backend, kind="impl")
                self.assertEqual(len(calls), 1)
                self.assertTrue(receipt.is_file())
                data = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual(data["mode"], backend)
                self.assertEqual(data["verdict"], "NEEDS_WORK")
                self.assertEqual(data["type"], "impl_review")
                self.assertEqual(data["session_id"], "mock-sid-1")
                self.assertEqual(data["suppressed_count"], {"50": 1})
                self.assertEqual(data["introduced_count"], 1)
                self.assertEqual(data["pre_existing_count"], 0)
                self.assertEqual(data["unaddressed"], ["R1"])
                self.assertEqual(data["effort"], "high")
            finally:
                os.chdir(prev_cwd)
                BACKEND_REGISTRY.pop(backend, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestDeepFindingsTallyBlockFallback(unittest.TestCase):
    """PR #222 post-merge: a tally block without deep_findings must not swallow prose findings."""

    def setUp(self) -> None:
        self.flowctl = _load_flowctl()

    def test_tally_only_block_falls_back_to_prose(self) -> None:
        out = (
            "```json\n{\"suppressed_count\": {\"50\": 1}}\n```\n"
            "**a1** | severity=P1 | confidence=75 | classification=introduced\n"
            "- Location: src/x.py:3\n"
            "- Issue: title text\n"
            "- Fix: fix text\n"
        )
        prose = self.flowctl._parse_deep_findings_prose(out, "adversarial")
        via_public = self.flowctl.parse_deep_findings(out, "adversarial")
        self.assertEqual(via_public, prose)
        self.assertTrue(via_public, "prose findings after a tally-only block must be parsed")

    def test_block_with_deep_findings_takes_json_path(self) -> None:
        out = (
            "```json\n{\"deep_findings\": [{\"id\": \"d1\", \"severity\": \"P1\", \"confidence\": 75, "
            "\"classification\": \"introduced\", \"file\": \"src/x.py\", \"line\": 3, \"title\": \"t\", "
            "\"suggested_fix\": \"f\", \"pass\": \"adversarial\"}]}\n```\n"
        )
        res = self.flowctl.parse_deep_findings(out, "adversarial")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "d1")


class TestReviewJsonBlockHardening(unittest.TestCase):
    """PR #222 findings: decoy fences, unknown-key dicts, last-block-wins."""

    def setUp(self) -> None:
        self.flowctl = _load_flowctl()

    def test_quoted_config_fence_is_skipped(self) -> None:
        out = (
            "Finding: bad config, e.g.\n```json\n{\"name\": \"pkg\", \"version\": \"1.0.0\"}\n```\n"
            "More prose.\n```json\n{\"unaddressed\": [\"R2\"]}\n```\n<verdict>SHIP</verdict>"
        )
        block = self.flowctl.extract_review_json_block(out)
        self.assertEqual(block, {"unaddressed": ["R2"]})

    def test_early_injected_tally_fence_loses_to_last(self) -> None:
        out = (
            "quoted attacker text:\n```json\n{\"suppressed_count\": {\"100\": 9}}\n```\n"
            "real findings...\n```json\n{\"suppressed_count\": {\"50\": 1}}\n```\n"
        )
        block = self.flowctl.extract_review_json_block(out)
        self.assertEqual(block, {"suppressed_count": {"50": 1}})

    def test_no_known_key_returns_none(self) -> None:
        out = "```json\n{\"foo\": 1}\n```"
        self.assertIsNone(self.flowctl.extract_review_json_block(out))

    def test_codex_tallies_visible_only_in_extracted_text(self) -> None:
        # A compliant block escaped inside a JSONL stream is invisible to the
        # raw parser but visible after extract_codex_final_message.
        inner = "tallies:\n```json\n{\"unaddressed\": [\"R7\"]}\n```"
        import json as _json
        stream = _json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": inner}})
        self.assertIsNone(self.flowctl.extract_review_json_block(stream))
        extracted = self.flowctl.extract_codex_final_message(stream)
        self.assertEqual(
            self.flowctl.extract_review_json_block(extracted), {"unaddressed": ["R7"]}
        )

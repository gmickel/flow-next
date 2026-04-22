"""Unit tests for BackendSpec parser + registry (fn-28 task 1).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers every valid form and every invalid-input branch listed in the task
spec. If the grammar/validation/resolution semantics break here, the whole
fn-28 plumbing chain will be wrong downstream.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
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

    def test_exactly_four_backends(self) -> None:
        self.assertEqual(
            sorted(BACKEND_REGISTRY.keys()),
            ["codex", "copilot", "none", "rp"],
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
        self.assertEqual(BACKEND_REGISTRY["codex"]["default_model"], "gpt-5.4")
        self.assertEqual(BACKEND_REGISTRY["codex"]["default_effort"], "high")

    def test_copilot_defaults(self) -> None:
        # Matches fn-27 runtime default (commit f519faa).
        self.assertEqual(BACKEND_REGISTRY["copilot"]["default_model"], "gpt-5.2")
        self.assertEqual(BACKEND_REGISTRY["copilot"]["default_effort"], "high")

    def test_copilot_model_catalog(self) -> None:
        # Verified list from fn-27 §Model Catalog (copilot --help + live probe).
        self.assertEqual(
            BACKEND_REGISTRY["copilot"]["models"],
            {
                "claude-sonnet-4.5",
                "claude-haiku-4.5",
                "claude-opus-4.5",
                "claude-sonnet-4",
                "gpt-5.2",
                "gpt-5.2-codex",
                "gpt-5-mini",
                "gpt-4.1",
            },
        )


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
        s = BackendSpec.parse("copilot:gpt-5.2")
        self.assertEqual(s, BackendSpec("copilot", "gpt-5.2", None))

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

    def test_unknown_model_codex(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown model for codex"):
            BackendSpec.parse("codex:gpt-99")

    def test_unknown_model_lists_sorted_valid(self) -> None:
        try:
            BackendSpec.parse("codex:gpt-99")
            self.fail("expected ValueError")
        except ValueError as e:
            msg = str(e)
            # Spec says: sorted valid-list in message.
            self.assertIn("'gpt-5-codex'", msg)
            self.assertIn("'gpt-5.4'", msg)

    def test_unknown_model_copilot(self) -> None:
        # Effort-looking string in model slot must fail cleanly.
        with self.assertRaisesRegex(ValueError, "Unknown model for copilot"):
            BackendSpec.parse("copilot:xhigh-is-not-a-model")

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
            BackendSpec.parse("copilot:gpt-5.2:minimal")
        with self.assertRaisesRegex(ValueError, "Unknown effort for copilot"):
            BackendSpec.parse("copilot:gpt-5.2:none")

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

    def test_case_sensitive_model(self) -> None:
        # Registry models are lowercase; uppercase must fail.
        with self.assertRaisesRegex(ValueError, "Unknown model"):
            BackendSpec.parse("codex:GPT-5.4")

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
               or key.startswith("FLOW_RP_") or key.startswith("FLOW_NONE_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def test_bare_codex_fills_both_defaults(self) -> None:
        r = BackendSpec.parse("codex").resolve()
        self.assertEqual(r, BackendSpec("codex", "gpt-5.4", "high"))

    def test_bare_copilot_fills_both_defaults(self) -> None:
        r = BackendSpec.parse("copilot").resolve()
        self.assertEqual(r, BackendSpec("copilot", "gpt-5.2", "high"))

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
            "copilot:gpt-5.2:medium",
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


if __name__ == "__main__":
    unittest.main(verbosity=2)

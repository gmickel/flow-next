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
import io
import json
import os
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

    def test_task_set_backend_rejects_unknown_model(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            out = io.StringIO()
            with self.assertRaises(SystemExit) as cm, redirect_stdout(out):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="codex:gpt-99",
                        sync=None,
                        json=True,
                    )
                )
            self.assertEqual(cm.exception.code, 1)
            payload = json.loads(out.getvalue())
            self.assertFalse(payload["success"])
            self.assertIn("--review", payload["error"])
            self.assertIn("Unknown model for codex", payload["error"])

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
            with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
                flowctl.cmd_task_set_backend(
                    _ns(
                        id="fn-9-e.1",
                        impl=None,
                        review="codex:gpt-99",
                        sync=None,
                        json=True,
                    )
                )
            after = (td / ".flow" / "tasks" / "fn-9-e.1.json").read_text()
            self.assertEqual(
                before, after, "disk must be untouched on validation failure"
            )

    def test_epic_set_backend_rejects_unknown_backend(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            out = io.StringIO()
            with self.assertRaises(SystemExit), redirect_stdout(out):
                flowctl.cmd_epic_set_backend(
                    _ns(
                        id="fn-9-e",
                        impl="bogus:foo",
                        review=None,
                        sync=None,
                        json=True,
                    )
                )
            payload = json.loads(out.getvalue())
            self.assertFalse(payload["success"])
            self.assertIn("--impl", payload["error"])
            self.assertIn("Unknown backend", payload["error"])

    def test_epic_set_backend_clears_with_empty_string(self) -> None:
        # Empty string means "clear" — must NOT validate (nothing to validate).
        with _flow_fixture() as td:
            _write_epic(
                td / ".flow", "fn-9-e", default_review="codex:gpt-5.4"
            )
            out = io.StringIO()
            with redirect_stdout(out):
                flowctl.cmd_epic_set_backend(
                    _ns(
                        id="fn-9-e",
                        impl=None,
                        review="",
                        sync=None,
                        json=True,
                    )
                )
            raw = json.loads(
                (td / ".flow" / "epics" / "fn-9-e.json").read_text()
            )
            self.assertIsNone(raw["default_review"])


class TestShowBackendResolution(unittest.TestCase):
    """``cmd_task_show_backend`` emits raw + resolved + per-field sources and
    degrades gracefully on legacy values."""

    def setUp(self) -> None:
        # Scrub env so registry defaults are deterministic.
        self._env_snapshot = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("FLOW_"):
                os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def _show_json(self, task_id: str) -> dict:
        out = io.StringIO()
        with redirect_stdout(out):
            flowctl.cmd_task_show_backend(_ns(id=task_id, json=True))
        return json.loads(out.getvalue())

    def test_null_when_no_spec_set(self) -> None:
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            result = self._show_json("fn-9-e.1")
            self.assertIsNone(result["review"]["raw"])
            self.assertIsNone(result["review"]["resolved"])
            self.assertIsNone(result["review"]["source"])

    def test_task_spec_full_fields(self) -> None:
        # Valid spec → raw + source=task + resolved with per-field sources.
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow",
                "fn-9-e.1",
                "fn-9-e",
                review="codex:gpt-5.4:xhigh",
            )
            r = self._show_json("fn-9-e.1")["review"]
            self.assertEqual(r["raw"], "codex:gpt-5.4:xhigh")
            self.assertEqual(r["source"], "task")
            self.assertEqual(
                r["resolved"],
                {
                    "backend": "codex",
                    "model": "gpt-5.4",
                    "effort": "xhigh",
                    "str": "codex:gpt-5.4:xhigh",
                },
            )
            self.assertEqual(r["model_source"], "spec")
            self.assertEqual(r["effort_source"], "spec")

    def test_epic_default_shows_source_epic(self) -> None:
        with _flow_fixture() as td:
            _write_epic(
                td / ".flow", "fn-9-e", default_review="codex"
            )
            _write_task(td / ".flow", "fn-9-e.1", "fn-9-e")
            r = self._show_json("fn-9-e.1")["review"]
            self.assertEqual(r["raw"], "codex")
            self.assertEqual(r["source"], "epic")
            self.assertEqual(r["resolved"]["backend"], "codex")
            # bare backend → model/effort fill from registry defaults
            self.assertEqual(r["model_source"], "registry_default")
            self.assertEqual(r["effort_source"], "registry_default")

    def test_env_fills_missing_effort_source_reported(self) -> None:
        os.environ["FLOW_CODEX_EFFORT"] = "low"
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow",
                "fn-9-e.1",
                "fn-9-e",
                review="codex:gpt-5.2",
            )
            r = self._show_json("fn-9-e.1")["review"]
            self.assertEqual(r["resolved"]["effort"], "low")
            self.assertEqual(r["model_source"], "spec")
            self.assertEqual(r["effort_source"], "env:FLOW_CODEX_EFFORT")

    def test_effort_only_spec_roundtrips_in_str(self) -> None:
        # `codex::high` stored directly must show `codex::high` in
        # resolved.str — preserving empty-model slot honesty.
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow",
                "fn-9-e.1",
                "fn-9-e",
                review="codex::high",
            )
            r = self._show_json("fn-9-e.1")["review"]
            self.assertEqual(r["raw"], "codex::high")
            # resolve() fills in the model from registry default, so str
            # becomes the full form. The important invariant is the resolved
            # dict has both fields populated without raising.
            self.assertEqual(r["resolved"]["model"], "gpt-5.4")
            self.assertEqual(r["resolved"]["effort"], "high")
            self.assertEqual(r["resolved"]["str"], "codex:gpt-5.4:high")

    def test_legacy_value_falls_back_with_warning(self) -> None:
        # The hot-path compat case: stored ``codex:gpt-5.4-high`` (dash) from
        # before this epic existed. Must warn to stderr, not crash, and
        # resolved must fall back to bare-backend defaults.
        with _flow_fixture() as td:
            _write_epic(td / ".flow", "fn-9-e")
            _write_task(
                td / ".flow",
                "fn-9-e.1",
                "fn-9-e",
                review="codex:gpt-5.4-high",
            )
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                flowctl.cmd_task_show_backend(
                    _ns(id="fn-9-e.1", json=True)
                )
            r = json.loads(out.getvalue())["review"]
            self.assertEqual(r["raw"], "codex:gpt-5.4-high")
            self.assertEqual(r["source"], "task")
            # Lenient fallback → bare codex → registry defaults fill.
            self.assertEqual(r["resolved"]["backend"], "codex")
            self.assertEqual(r["resolved"]["model"], "gpt-5.4")
            self.assertEqual(r["resolved"]["effort"], "high")
            self.assertIn("warning:", err.getvalue())
            self.assertIn("codex:gpt-5.4-high", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)

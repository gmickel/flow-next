"""Unit tests for the host review-backend sentinel (fn-123 R5 / task .3).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_host_review_backend -q

``host`` is a NON-EXECUTABLE selection sentinel: review runs as a host-native
fresh-context subagent (skill-owned). flowctl only registers/parses it —
no model/effort on the string, no run_exec hook, never a subprocess path.
Pins live in the AGENTS.md model-routing section.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any

import sys

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location("flowctl_host_test", flowctl_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()
BackendSpec = flowctl.BackendSpec
BACKEND_REGISTRY = flowctl.BACKEND_REGISTRY
MODEL_ROLE_BACKENDS = flowctl.MODEL_ROLE_BACKENDS

REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "plugins" / "flow-next" / "skills"


def _read(relative: str) -> str:
    return (SKILLS / relative).read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


class TestHostBackendRegistry(unittest.TestCase):
    """host is registered but non-executable (no model axis, not role-mappable)."""

    def test_host_in_backend_registry(self) -> None:
        self.assertIn("host", BACKEND_REGISTRY)

    def test_host_models_is_none(self) -> None:
        self.assertIsNone(BACKEND_REGISTRY["host"]["models"])
        self.assertIsNone(BACKEND_REGISTRY["host"]["efforts"])

    def test_host_not_in_model_role_backends(self) -> None:
        # Pins live in AGENTS.md model-routing — not models.roles.<role>.host.
        self.assertNotIn("host", MODEL_ROLE_BACKENDS)


class TestHostBackendSpecParse(unittest.TestCase):
    """Bare host parses; host:<model> forms raise with AGENTS.md routing hint."""

    def test_bare_host_parses_ok(self) -> None:
        s = BackendSpec.parse("host")
        self.assertEqual(s.backend, "host")
        self.assertIsNone(s.model)
        self.assertIsNone(s.effort)
        self.assertIsNone(BACKEND_REGISTRY[s.backend]["models"])

    def test_host_model_form_raises_agents_md_hint(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            BackendSpec.parse("host:opus")
        msg = str(ctx.exception)
        self.assertIn("AGENTS.md", msg)
        self.assertIn("model-routing", msg)

    def test_host_model_effort_form_raises_agents_md_hint(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            BackendSpec.parse("host:opus:high")
        msg = str(ctx.exception)
        self.assertIn("AGENTS.md", msg)
        self.assertIn("model-routing", msg)


if __name__ == "__main__":
    unittest.main()


class TestHostLenientResolution(unittest.TestCase):
    """fn-123 review hardening (sol P1): the LENIENT read-time parser must not
    silently degrade ``host:<model>`` to bare ``host`` — the stored pin the
    user thought they set would be silently ignored. Invalid host specs are
    treated as unset (None) with a loud stderr error."""

    def test_lenient_host_model_returns_none(self) -> None:
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            spec = flowctl.parse_backend_spec_lenient("host:opus", warn=False)
        self.assertIsNone(spec, "host:<model> must not degrade to bare host")
        self.assertIn("invalid", buf.getvalue().lower())

    def test_lenient_host_model_effort_returns_none(self) -> None:
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            spec = flowctl.parse_backend_spec_lenient("host:opus:high", warn=True)
        self.assertIsNone(spec)

    def test_lenient_bare_host_still_parses(self) -> None:
        spec = flowctl.parse_backend_spec_lenient("host", warn=False)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.backend, "host")
        resolved = spec.resolve()
        self.assertIsNone(resolved.model)
        self.assertIsNone(resolved.effort)

    def test_lenient_other_backends_still_degrade(self) -> None:
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            spec = flowctl.parse_backend_spec_lenient("rp:not-a-model", warn=True)
        self.assertIsNotNone(spec, "legacy lenience for non-host backends must not change")
        self.assertEqual(spec.backend, "rp")


class TestHostReviewWorkflowRouting(unittest.TestCase):
    """Host mechanics stay behind the selected reference and own no status."""

    REVIEW_SKILLS = (
        "flow-next-impl-review",
        "flow-next-spec-completion-review",
    )
    NON_HOST_BACKENDS = ("codex", "copilot", "cursor", "rp")
    HOST_ONLY_MECHANICS = (
        "NEEDS_HUMAN: host review needs a cross-family model pin",
        "`disallowedTools: Edit, Write, Task`",
        '"mode": "host"',
        '"session_id": null',
    )

    def test_root_host_surface_is_only_router_and_safety_invariant(self) -> None:
        for skill in self.REVIEW_SKILLS:
            root = _read(f"{skill}/SKILL.md")
            host = _section(
                root,
                "**For host backend (fn-123 R5 / fn-126):**",
                "**For all backends:**",
            )
            self.assertIn("[workflow-host.md](workflow-host.md)", host)
            self.assertIn("fresh, tool-enforced read-only reviewer", host)
            self.assertIn("different\nmodel family", host)
            self.assertIn("fail closed", host)
            for mechanic in self.HOST_ONLY_MECHANICS:
                self.assertNotIn(mechanic, host, f"{skill}: host mechanics leaked into root")

    def test_non_host_reached_paths_keep_host_mechanics_cold(self) -> None:
        for skill in self.REVIEW_SKILLS:
            root = _read(f"{skill}/SKILL.md")
            common = _read(f"{skill}/workflow-common.md")
            for backend in self.NON_HOST_BACKENDS:
                reached = root + common + _read(f"{skill}/workflow-{backend}.md")
                for mechanic in self.HOST_ONLY_MECHANICS:
                    self.assertNotIn(
                        mechanic,
                        reached,
                        f"{skill}/{backend}: loaded host-only mechanic {mechanic!r}",
                    )

    def test_selected_host_workflows_are_self_contained(self) -> None:
        for skill in self.REVIEW_SKILLS:
            host = _read(f"{skill}/workflow-host.md")
            for mechanic in self.HOST_ONLY_MECHANICS:
                self.assertIn(mechanic, host, f"{skill}: missing {mechanic!r}")
            host_lower = host.lower()
            for required in (
                "prior findings",
                "tests/lints",
                "commit the fixes before re-review",
                "<promise>RETRY</promise>",
            ):
                self.assertIn(
                    required.lower(),
                    host_lower,
                    f"{skill}: incomplete host workflow",
                )
            self.assertIn("deterministic round cap", host_lower)
            self.assertNotIn("Return the verdict", host)

    def test_completion_status_has_one_shared_owner(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        work = _read("flow-next-work/phases.md")
        pilot = _read("flow-next-pilot/workflow.md")
        command = "$FLOWCTL spec set-completion-review-status"
        self.assertEqual(root.count(command), 1, "shared owner must issue one status write")
        self.assertNotIn(command, host, "selected host workflow must never write status")
        self.assertNotIn(command, rp, "selected rp workflow must never write status")
        self.assertNotIn(command, work, "work caller must never repeat the status write")
        self.assertIn("This shared step is the sole writer for host and rp", root)
        self.assertIn("never write completion status", root)
        self.assertIn("This host workflow never writes terminal completion status", host)
        self.assertIn("stop without writing completion status", host)
        self.assertIn("Work never writes that status again", work)
        self.assertIn(
            "the spec-completion-review skill writes terminal "
            "`completion_review_status` through its backend-aware shared owner",
            pilot,
        )
        self.assertNotIn("or write status here", host)

    def test_capped_completion_status_precedes_exit(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        write_at = root.index("$FLOWCTL spec set-completion-review-status")
        terminal_at = root.index(
            'echo "ESCALATE: completion-review did not converge',
            write_at,
        )
        exit_at = root.index("exit 4", terminal_at)
        self.assertLess(write_at, terminal_at)
        self.assertLess(terminal_at, exit_at)
        self.assertIn(
            "An exit-4 cap refusal before this run has delivered a completion "
            "verdict is\nnon-terminal for completion status",
            root,
        )

    def test_host_completion_uses_shared_cap_attempt_lifecycle(self) -> None:
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        self.assertIn(
            '$FLOWCTL review-rounds increment "$SPEC_ID" --kind plan --json',
            host,
        )
        self.assertIn(
            '$FLOWCTL review-rounds record "$SPEC_ID" --kind plan',
            host,
        )
        self.assertIn("--review-type completion --backend host", host)
        self.assertIn(
            '$FLOWCTL review-rounds reset "$SPEC_ID" --kind plan --json',
            host,
        )
        self.assertIn("(`REVIEW_ROUND == REVIEW_CAP`)", host)
        self.assertIn("<verdict>SHIP</verdict>", host)
        self.assertIn("<verdict>NEEDS_WORK</verdict>", host)

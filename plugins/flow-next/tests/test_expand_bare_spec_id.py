"""Unit tests for `expand_bare_spec_id` — bare-id (fn-N) → slugged form
(fn-N-slug) resolution when no literal `<id>.json` file exists.

Covers: literal-wins (no expansion), unique slugged match, ambiguous prefix
(error_exit), no match (return unchanged), legacy .flow/epics/ fallback,
non-spec-id inputs (None / empty / task-id format)."""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("flowctl", ROOT / "scripts" / "flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
sys.modules["flowctl"] = flowctl
spec.loader.exec_module(flowctl)


class TestExpandBareSpecId(unittest.TestCase):
    def _setup_flow(self, tmp: Path) -> Path:
        flow_dir = tmp / ".flow"
        (flow_dir / "specs").mkdir(parents=True)
        (flow_dir / "epics").mkdir(parents=True)
        return flow_dir

    def test_literal_wins_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-1.json").write_text("{}")
            # Slugged sibling exists too — literal still wins.
            (flow_dir / "specs" / "fn-1-also-here.json").write_text("{}")
            self.assertEqual(
                flowctl.expand_bare_spec_id(flow_dir, "fn-1"), "fn-1"
            )

    def test_literal_wins_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "epics" / "fn-2.json").write_text("{}")
            self.assertEqual(
                flowctl.expand_bare_spec_id(flow_dir, "fn-2"), "fn-2"
            )

    def test_unique_slugged_match_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-43-rename-epic-spec.json").write_text("{}")
            self.assertEqual(
                flowctl.expand_bare_spec_id(flow_dir, "fn-43"),
                "fn-43-rename-epic-spec",
            )

    def test_unique_slugged_match_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "epics" / "fn-22-53k.json").write_text("{}")
            self.assertEqual(
                flowctl.expand_bare_spec_id(flow_dir, "fn-22"), "fn-22-53k"
            )

    def test_ambiguous_prefix_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-99-foo.json").write_text("{}")
            (flow_dir / "specs" / "fn-99-bar.json").write_text("{}")
            buf = io.StringIO()
            with redirect_stderr(buf):
                with self.assertRaises(SystemExit) as ctx:
                    flowctl.expand_bare_spec_id(flow_dir, "fn-99")
            self.assertEqual(ctx.exception.code, 1)
            err = buf.getvalue()
            self.assertIn("ambiguous", err)
            self.assertIn("fn-99-foo", err)
            self.assertIn("fn-99-bar", err)

    def test_ambiguous_canonical_plus_legacy(self) -> None:
        """Mixed locations during migration also trigger ambiguity."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-7-canon.json").write_text("{}")
            (flow_dir / "epics" / "fn-7-legacy.json").write_text("{}")
            with self.assertRaises(SystemExit):
                with redirect_stderr(io.StringIO()):
                    flowctl.expand_bare_spec_id(flow_dir, "fn-7")

    def test_no_match_returns_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            self.assertEqual(
                flowctl.expand_bare_spec_id(flow_dir, "fn-44"), "fn-44"
            )

    def test_none_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            self.assertIsNone(flowctl.expand_bare_spec_id(flow_dir, None))

    def test_empty_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            self.assertEqual(flowctl.expand_bare_spec_id(flow_dir, ""), "")

    def test_task_id_skipped(self) -> None:
        """fn-43.17 is a task id, not a spec id — return unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-43-rename-epic-spec.json").write_text("{}")
            self.assertEqual(
                flowctl.expand_bare_spec_id(flow_dir, "fn-43.17"), "fn-43.17"
            )

    def test_already_slugged_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-43-rename-epic-spec.json").write_text("{}")
            self.assertEqual(
                flowctl.expand_bare_spec_id(
                    flow_dir, "fn-43-rename-epic-spec"
                ),
                "fn-43-rename-epic-spec",
            )

    def test_json_mode_emits_json_error_on_ambiguity(self) -> None:
        """Ambiguous error in JSON mode emits a parseable JSON error."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / "fn-50-a.json").write_text("{}")
            (flow_dir / "specs" / "fn-50-b.json").write_text("{}")
            buf = io.StringIO()
            from contextlib import redirect_stdout
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit):
                    flowctl.expand_bare_spec_id(
                        flow_dir, "fn-50", use_json=True
                    )
            import json as _json
            payload = _json.loads(buf.getvalue())
            self.assertFalse(payload["success"])
            self.assertIn("ambiguous", payload["error"])

    def test_live_fn122_pair_bare_id_is_ambiguous(self) -> None:
        """R12 regression: live fn-122 pair disambiguates (no new resolver code).

        Verified 2026-07-25: expand_bare_spec_id ALREADY errors with
        "Spec id 'fn-122' is ambiguous. Matches: … Use the full slug to
        disambiguate." for the native-fn branch. This pins the two real
        slug names from the flow-next store; no resolver changes required.
        """
        a = "fn-122-flowctl-hardening-and-performance-completion-sweep"
        b = "fn-122-harden-verdict-graduate-recurring"
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = self._setup_flow(Path(tmp))
            (flow_dir / "specs" / f"{a}.json").write_text("{}")
            (flow_dir / "specs" / f"{b}.json").write_text("{}")
            buf = io.StringIO()
            with redirect_stderr(buf):
                with self.assertRaises(SystemExit) as ctx:
                    flowctl.expand_bare_spec_id(flow_dir, "fn-122")
            self.assertEqual(ctx.exception.code, 1)
            err = buf.getvalue()
            self.assertIn("ambiguous", err)
            self.assertIn(a, err)
            self.assertIn(b, err)
            self.assertIn("full slug", err)


if __name__ == "__main__":
    unittest.main()

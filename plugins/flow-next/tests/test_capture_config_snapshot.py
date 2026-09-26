"""fn-257 R8: capture reads its readiness and HTML-lens gates from the one
config snapshot it takes, and its duplicate check compares open specs only."""

from __future__ import annotations

import pathlib
import unittest

CAPTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "skills" / "flow-next-capture"
)


def _corpus() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(CAPTURE.rglob("*.md")))


class CaptureConfigSnapshot(unittest.TestCase):
    def test_gate_keys_come_from_the_snapshot(self) -> None:
        corpus = _corpus()
        for key in ("tracker.readyState", "artifacts.html.enabled"):
            self.assertNotIn(f"config get {key}", corpus)
            self.assertIn(f".value.{key}", corpus)

    def test_duplicate_check_compares_open_specs_only(self) -> None:
        workflow = (CAPTURE / "workflow.md").read_text(encoding="utf-8")
        self.assertIn('`status == "open"`', workflow)
        self.assertNotIn("status: closed", workflow)


if __name__ == "__main__":
    unittest.main()

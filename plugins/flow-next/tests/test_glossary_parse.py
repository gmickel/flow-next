"""`parse_glossary_file` metadata-line stripping (fn-242, #408).

An entry carrying BOTH `_Avoid_:` and `_Relates to_:` used to have its match
offsets computed against the original body and then applied cumulatively to
the shrinking string, so the second removal cut the wrong window and leaked a
metadata fragment into `definition`. `glossary add` then re-rendered every
such entry corrupted, compounding on each add.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_glossary_parse.py" -v
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

FLOWCTL_PY = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location("flowctl_glossary_parse_under_test", FLOWCTL_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()

CANONICAL = (
    "# Glossary\n"
    "\n"
    "## Spec\n"
    "\n"
    "A unit of planned work.\n"
    "\n"
    "_Avoid_: plan, ticket\n"
    "\n"
    "_Relates to_: Task, R-ID\n"
)

# Hand-authored order: `_Relates to_` before `_Avoid_`.
REVERSED = (
    "# Glossary\n"
    "\n"
    "## Spec\n"
    "\n"
    "A unit of planned work.\n"
    "\n"
    "_Relates to_: Task, R-ID\n"
    "\n"
    "_Avoid_: plan, ticket\n"
)


class BothMetadataLines(unittest.TestCase):
    def test_both_lines_parse_clean_in_either_order(self) -> None:
        for label, text in (("canonical", CANONICAL), ("reversed", REVERSED)):
            with self.subTest(order=label):
                entries = flowctl.parse_glossary_file(text)
                self.assertEqual(len(entries), 1)
                entry = entries[0]
                self.assertEqual(entry["term"], "Spec")
                self.assertEqual(entry["definition"], "A unit of planned work.")
                self.assertEqual(entry["avoid"], ["plan", "ticket"])
                self.assertEqual(entry["relates_to"], ["Task", "R-ID"])

    def test_canonical_rendering_round_trips(self) -> None:
        parsed = flowctl.parse_glossary_file(CANONICAL)
        self.assertEqual(flowctl.render_glossary_file(parsed), CANONICAL)
        # Re-parsing the rendering is a fixed point (what `glossary add` does
        # to every existing entry on each call).
        again = flowctl.parse_glossary_file(flowctl.render_glossary_file(parsed))
        self.assertEqual(again, parsed)

    def test_single_metadata_line_unchanged(self) -> None:
        text = "# Glossary\n\n## Spec\n\nA unit.\n\n_Avoid_: plan\n"
        entry = flowctl.parse_glossary_file(text)[0]
        self.assertEqual(entry["definition"], "A unit.")
        self.assertEqual(entry["avoid"], ["plan"])
        self.assertEqual(entry["relates_to"], [])


if __name__ == "__main__":
    unittest.main()

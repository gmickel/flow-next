"""Drift guard: the repo's own `.flow/` dogfood copies must stay byte-identical
to the canonical templates that `/flow-next:setup` ships to consumers (1.5.1).

`/flow-next:setup` copies two canonical templates into a consumer's `.flow/`:

    plugins/flow-next/skills/flow-next-setup/templates/usage.md  ->  .flow/usage.md
    plugins/flow-next/templates/spec.md                          ->  .flow/templates/spec.md

This repo dogfoods flow-next, so it carries its OWN `.flow/usage.md` and
`.flow/templates/spec.md`. Contributors naturally edit the lived-in dogfood
copy (it's the visible one) and forget the canonical template — exactly how
fn-52 (1.5.0) added the tracker-sync command block to `.flow/usage.md` but not
to the bundled template, so every fresh `/flow-next:setup` shipped a usage.md
with no `flowctl sync` docs.

This guard makes that class of drift a hard CI failure: dogfood ≡ canonical.
Edit one, you must edit the other (re-run `/flow-next:setup`, or `cp` the
template). Line endings are normalized (CRLF -> LF) so a Windows checkout with
`core.autocrlf` left on does not produce spurious failures.

Run:
    python3 -m unittest plugins.flow-next.tests.test_dogfood_template_parity -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent           # plugins/flow-next
REPO_ROOT = PLUGIN_DIR.parent.parent      # repo root

# (dogfood copy in `.flow/`, canonical template `/flow-next:setup` copies from)
PARITY_PAIRS = [
    (
        REPO_ROOT / ".flow" / "usage.md",
        PLUGIN_DIR / "skills" / "flow-next-setup" / "templates" / "usage.md",
    ),
    (
        REPO_ROOT / ".flow" / "templates" / "spec.md",
        PLUGIN_DIR / "templates" / "spec.md",
    ),
]


def _normalize(path: Path) -> str:
    # Compare on content, not line-ending flavor: a Windows runner with
    # core.autocrlf=true would otherwise diff every line.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


class TestDogfoodTemplateParity(unittest.TestCase):
    def test_dogfood_copies_match_canonical_templates(self) -> None:
        for dogfood, canonical in PARITY_PAIRS:
            with self.subTest(dogfood=str(dogfood.relative_to(REPO_ROOT))):
                self.assertTrue(
                    canonical.is_file(), f"canonical template missing: {canonical}"
                )
                self.assertTrue(
                    dogfood.is_file(), f"dogfood copy missing: {dogfood}"
                )
                self.assertEqual(
                    _normalize(dogfood),
                    _normalize(canonical),
                    f"\n{dogfood.relative_to(REPO_ROOT)} has drifted from its "
                    f"canonical template\n  {canonical.relative_to(REPO_ROOT)}\n"
                    f"Every `/flow-next:setup` ships the canonical copy — edit "
                    f"BOTH. Fix: re-run /flow-next:setup, or "
                    f"`cp {canonical.relative_to(REPO_ROOT)} "
                    f"{dogfood.relative_to(REPO_ROOT)}` (or the reverse).",
                )


if __name__ == "__main__":
    unittest.main()

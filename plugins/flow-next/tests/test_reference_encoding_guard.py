"""Encoding guard for gated `references/*.md` (canonical + Codex mirror).

Scope note — what this guard does and does NOT assert
-----------------------------------------------------
The repo's cp1252 story has two independent halves, and only one of them is a
contract on *file content*:

1. **Read side (a content contract).** Everything that consumes these files —
   the agent host reading a gated reference, `sync-codex.sh` copying it, and
   flowctl's own `read_text(encoding="utf-8")` call sites — decodes **strict
   UTF-8**. A file saved by a legacy Windows editor in cp1252 raises
   `UnicodeDecodeError` on the first smart quote or umlaut. This is the same
   hazard class `test_normalize_section_content.py` pins from the other side
   (its fixtures pass `encoding="utf-8"` explicitly because "a bare
   `write_text()` emits cp1252 on Windows and the CLI correctly exits 1"), and
   the read-side half of `test_cp1252_robustness.py` (`find_references` must
   tolerate non-UTF-8 bytes it did not author). Reference files are ours, so
   for them the contract is stronger: they must simply BE valid UTF-8.

2. **Write side (NOT a content contract).** `UnicodeEncodeError` when printing
   non-ASCII to a legacy cp1252 console is a *flowctl output-handling*
   concern, already fixed centrally by `flowctl._reconfigure_stdio_utf8()` and
   locked by `test_cp1252_robustness.StdioReconfigureUtf8`. It is therefore
   **not** a reason to ban non-ASCII from prose — the corpus deliberately uses
   `—`, `→`, `§`, and box-drawing characters, and this guard must not become a
   back-door ASCII-only rule that would fail on every one of them.

So the hazard class checked here is exactly "bytes that break the known cp1252
Windows path", mirrored from the definitions above:

* not decodable as strict UTF-8 (a genuinely cp1252-encoded file);
* C1 control characters U+0080–U+009F — the mojibake signature of cp1252 bytes
  0x80–0x9F (the smart-quote / en-dash / em-dash block: 0x96 U+2013 and 0x97
  U+2014 are named in `test_normalize_section_content`) round-tripped through
  latin-1 and re-saved as "valid" UTF-8. Such a file decodes without error but
  carries unprintable controls where punctuation belongs;
* a UTF-8 BOM (U+FEFF) — Windows editors add it, strict UTF-8 decoding keeps
  it, and it lands in front of the frontmatter `---` where it silently breaks
  the leading-token pins the prose contracts are made of;
* NUL bytes.

The Codex mirror twin is checked identically: `sync-codex.sh` copies the skill
dir wholesale, so a bad byte in either copy reaches a real host.
"""

from __future__ import annotations

import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parent.parent
SKILLS = PLUGIN / "skills"
CODEX_SKILLS = PLUGIN / "codex" / "skills"

# U+0080–U+009F. Present in text only as cp1252 mojibake — no prose needs them.
C1_CONTROLS = frozenset(range(0x80, 0xA0))
BOM = "\ufeff"


def _reference_files() -> list[Path]:
    return sorted(SKILLS.glob("*/references/*.md"))


class ReferenceEncodingGuard(unittest.TestCase):
    def test_corpus_is_non_empty(self) -> None:
        """A glob that silently matches nothing would pass every check below."""
        self.assertGreater(len(_reference_files()), 0)

    def test_every_reference_has_a_codex_mirror_twin(self) -> None:
        for path in _reference_files():
            rel = path.relative_to(SKILLS)
            with self.subTest(reference=str(rel)):
                self.assertTrue(
                    (CODEX_SKILLS / rel).is_file(),
                    f"missing Codex mirror for {rel} — run ./scripts/sync-codex.sh",
                )

    def test_references_and_mirrors_are_strict_utf8(self) -> None:
        for path in self._both_copies():
            with self.subTest(path=self._label(path)):
                raw = path.read_bytes()
                try:
                    raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    self.fail(
                        f"{self._label(path)} is not valid UTF-8 ({exc}); "
                        "re-save it as UTF-8 — production reads it strictly"
                    )

    def test_references_and_mirrors_carry_no_cp1252_mojibake(self) -> None:
        for path in self._both_copies():
            with self.subTest(path=self._label(path)):
                text = path.read_bytes().decode("utf-8", errors="replace")
                found = sorted({ord(ch) for ch in text} & C1_CONTROLS)
                self.assertEqual(
                    found,
                    [],
                    f"{self._label(path)} carries C1 control chars "
                    f"{[hex(cp) for cp in found]} — the signature of cp1252 "
                    "punctuation decoded as latin-1 and re-saved",
                )

    def test_references_and_mirrors_have_no_bom_or_nul(self) -> None:
        for path in self._both_copies():
            with self.subTest(path=self._label(path)):
                text = path.read_bytes().decode("utf-8", errors="replace")
                self.assertFalse(
                    text.startswith(BOM),
                    f"{self._label(path)} starts with a UTF-8 BOM — it shifts "
                    "the first pinned token (frontmatter `---`) by one char",
                )
                self.assertNotIn(BOM, text, self._label(path))
                self.assertNotIn("\x00", text, self._label(path))

    # ── helpers ──────────────────────────────────────────────────────────

    def _both_copies(self) -> list[Path]:
        paths: list[Path] = []
        for path in _reference_files():
            paths.append(path)
            twin = CODEX_SKILLS / path.relative_to(SKILLS)
            if twin.is_file():  # absence is reported by its own test
                paths.append(twin)
        return paths

    @staticmethod
    def _label(path: Path) -> str:
        return str(path.relative_to(PLUGIN))


if __name__ == "__main__":
    unittest.main()

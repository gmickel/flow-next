"""Task-section content normalization (fn-79, R1–R6).

`task set-acceptance` / `set-description` must replace the WHOLE section —
agent-supplied content beginning with its own `## …` H2 used to layer a rogue
sibling section (fn-78 damage shape). Covers:

- `normalize_section_content` (pure): leading title-variant strip, embedded
  H2→H3 demotion, fenced-code-block skip, `## Acceptance Tests` negative case,
  legacy `## Acceptance criteria` variant, byte-preservation of clean input.
- `patch_task_section`: idempotent set-acceptance (no layering), self-heal of
  singly- and doubly-layered files, unrelated-section preservation, unchanged
  duplicate/missing error semantics.
- CLI end-to-end: `task create --acceptance-file` with a leading-H2 file,
  `task set-acceptance` twice byte-idempotent.
- CLI `--file` path/encoding portability (fn-120.2, R4): long paths with
  spaces and a real Windows 8.3 short path (GetShortPathNameW) carrying UTF-8
  content through the production CLI. Fixture files are written with an
  explicit `encoding="utf-8"` because production reads them as strict UTF-8 —
  a bare `write_text()` emits cp1252 on Windows and the CLI correctly exits 1
  with "Acceptance file unreadable".

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_normalize_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ── normalize_section_content (pure) ───────────────────────────────────────


class NormalizeTestCase(unittest.TestCase):
    def test_leading_exact_title_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance\n- R1: thing\n"
        )
        self.assertEqual(out, "- R1: thing\n")

    def test_leading_decorated_variant_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance Criteria (fn-78 R1–R6)\n- R1: x\n"
        )
        self.assertEqual(out, "- R1: x\n")

    def test_legacy_lowercase_criteria_variant_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance criteria\n- R1: x\n"
        )
        self.assertEqual(out, "- R1: x\n")

    def test_separator_suffix_variants_stripped(self) -> None:
        for title in (
            "## Acceptance — updated",
            "## Acceptance: v2",
            "## Acceptance - old",
            "## Acceptance Criteria: final",
        ):
            out = flowctl.normalize_section_content(
                "## Acceptance", f"{title}\n- R1: x"
            )
            self.assertEqual(out, "- R1: x", f"title not stripped: {title!r}")

    def test_acceptance_tests_demoted_not_stripped(self) -> None:
        # Arbitrary different word after the section word is NOT a title
        # variant — it is content, demoted to H3.
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance Tests\n- t1\n"
        )
        self.assertEqual(out, "### Acceptance Tests\n- t1\n")

    def test_embedded_h2_demoted(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "- R1: x\n\n## Notes\nprose\n"
        )
        self.assertEqual(out, "- R1: x\n\n### Notes\nprose\n")

    def test_h2_inside_backtick_fence_untouched(self) -> None:
        content = "- R1: x\n```bash\n## not a heading\n```\n"
        self.assertEqual(
            flowctl.normalize_section_content("## Acceptance", content), content
        )

    def test_h2_inside_tilde_fence_untouched(self) -> None:
        content = "- R1: x\n~~~\n## not a heading\n~~~\n"
        self.assertEqual(
            flowctl.normalize_section_content("## Acceptance", content), content
        )

    def test_h2_after_closed_fence_demoted(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "```\n## fenced\n```\n## after\n"
        )
        self.assertEqual(out, "```\n## fenced\n```\n### after\n")

    def test_h3_and_prose_untouched_clean_roundtrip(self) -> None:
        content = "- R1: x\n### Sub\nprose ## not-a-heading\n"
        self.assertEqual(
            flowctl.normalize_section_content("## Acceptance", content), content
        )

    def test_description_variant_no_criteria_word(self) -> None:
        # `Criteria` is an Acceptance-only legacy word; for Description it is
        # content → demoted, not stripped.
        out = flowctl.normalize_section_content(
            "## Description", "## Description Criteria\nbody\n"
        )
        self.assertEqual(out, "### Description Criteria\nbody\n")

    def test_description_exact_and_suffix_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Description", "## Description — v2\nbody\n"
        )
        self.assertEqual(out, "body\n")


# ── patch_task_section (splice + self-heal) ────────────────────────────────


def _task_md(acceptance_block: str) -> str:
    return (
        "# fn-1.1 Title\n\n"
        "## Description\nDesc body\n\n"
        f"## Acceptance\n{acceptance_block}\n"
        "\n## Done summary\nTBD\n\n"
        "## Evidence\n- Commits:\n- Tests:\n- PRs:\n"
    )


class PatchTaskSectionTestCase(unittest.TestCase):
    def test_set_acceptance_idempotent_no_layering(self) -> None:
        current = _task_md("- [ ] old")
        new = "## Acceptance Criteria (fn-79 R1)\n- R1: new\n\n## Extra\nnote"
        once = flowctl.patch_task_section(current, "## Acceptance", new)
        self.assertEqual(once.count("\n## Acceptance"), 1)
        self.assertIn("### Extra", once)
        self.assertNotIn("\n## Extra", once)
        twice = flowctl.patch_task_section(once, "## Acceptance", new)
        self.assertEqual(once, twice)

    def test_self_heal_single_layered_file(self) -> None:
        # fn-78 damage shape: rogue title-variant section after the target.
        damaged = _task_md(
            "- R1: new\n\n## Acceptance Criteria (fn-78 R1–R6)\n- R1: old"
        )
        healed = flowctl.patch_task_section(
            damaged, "## Acceptance", "- R1: final"
        )
        self.assertNotIn("Acceptance Criteria", healed)
        self.assertNotIn("- R1: old", healed)
        self.assertIn("## Acceptance\n- R1: final", healed)
        self.assertEqual(healed.count("\n## Acceptance"), 1)

    def test_self_heal_doubly_layered_file(self) -> None:
        damaged = _task_md(
            "- R1: newest\n\n"
            "## Acceptance Criteria (round 2)\n- R1: mid\n\n"
            "## Acceptance criteria\n- R1: oldest"
        )
        healed = flowctl.patch_task_section(
            damaged, "## Acceptance", "- R1: final"
        )
        self.assertNotIn("Acceptance Criteria", healed)
        self.assertNotIn("Acceptance criteria", healed)
        self.assertNotIn("mid", healed)
        self.assertNotIn("oldest", healed)
        self.assertEqual(healed.count("\n## Acceptance"), 1)

    def test_self_heal_preserves_unrelated_sections(self) -> None:
        damaged = _task_md(
            "- R1: new\n\n## Acceptance Criteria (stale)\n- R1: old"
        )
        healed = flowctl.patch_task_section(
            damaged, "## Acceptance", "- R1: final"
        )
        for heading in ("## Description", "## Done summary", "## Evidence"):
            self.assertIn(heading, healed)
        self.assertIn("Desc body", healed)
        self.assertIn("- Commits:", healed)

    def test_rogue_variant_not_contiguous_is_boundary(self) -> None:
        # A title-variant H2 NOT directly after the target section stays a
        # hard boundary (fold is contiguity-scoped).
        content = (
            "# fn-1.1 T\n\n## Acceptance\n- new\n\n"
            "## Done summary\nTBD\n\n"
            "## Acceptance Criteria (orphan)\n- orphan\n"
        )
        out = flowctl.patch_task_section(content, "## Acceptance", "- final")
        self.assertIn("## Acceptance Criteria (orphan)", out)
        self.assertIn("- orphan", out)

    def test_fenced_h2_in_stored_section_not_a_boundary(self) -> None:
        # Content with a fence-preserved `## ` line persisted in the section:
        # the next patch must replace the WHOLE section (fenced line is not a
        # boundary — no stale content left behind) and stay idempotent.
        new = "- R1: x\n```bash\n## not a heading\n```\nafter fence"
        current = _task_md(new)
        once = flowctl.patch_task_section(current, "## Acceptance", new)
        self.assertEqual(once.count("\n## Acceptance"), 1)
        twice = flowctl.patch_task_section(once, "## Acceptance", new)
        self.assertEqual(once, twice)
        # Replacement with different content leaves no stale fenced remnant.
        replaced = flowctl.patch_task_section(once, "## Acceptance", "- fresh")
        self.assertNotIn("## not a heading", replaced)
        self.assertNotIn("after fence", replaced)
        self.assertIn("## Acceptance\n- fresh", replaced)

    def test_fenced_canonical_heading_no_duplicate_error(self) -> None:
        # A byte-exact `## Acceptance` INSIDE a fence is content, not a
        # duplicate heading — patching must succeed and replace cleanly.
        new = "- R1: x\n```\n## Acceptance\n```"
        current = _task_md(new)
        healed = flowctl.patch_task_section(current, "## Acceptance", "- ok")
        self.assertEqual(healed.count("\n## Acceptance"), 1)
        self.assertIn("## Acceptance\n- ok", healed)

    def test_get_task_section_fence_aware(self) -> None:
        body = "- R1: x\n```bash\n## not a heading\n```\ntail"
        content = _task_md(body)
        self.assertEqual(
            flowctl.get_task_section(content, "## Acceptance"), body
        )

    def test_validate_headings_fenced_canonical_not_duplicate(self) -> None:
        # A persisted fenced `## Acceptance` is content — validate must not
        # report it as a duplicate heading (write/read/validate parity).
        content = _task_md("- R1: x\n```\n## Acceptance\n```")
        self.assertEqual(flowctl.validate_task_spec_headings(content), [])

    def test_validate_headings_fenced_heading_does_not_satisfy(self) -> None:
        # A fenced heading must NOT satisfy the required-heading presence
        # check — the real section is missing.
        content = (
            "# fn-1.1 T\n\n## Description\nbody\n\n"
            "```\n## Acceptance\n```\n\n"
            "## Done summary\nTBD\n\n## Evidence\n- Commits:\n"
        )
        errors = flowctl.validate_task_spec_headings(content)
        self.assertIn("Missing required heading: ## Acceptance", errors)

    def test_duplicate_canonical_heading_still_raises(self) -> None:
        content = _task_md("- a") + "\n## Acceptance\n- dup\n"
        with self.assertRaises(ValueError) as ctx:
            flowctl.patch_task_section(content, "## Acceptance", "- x")
        self.assertIn("duplicate heading", str(ctx.exception))

    def test_missing_section_still_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            flowctl.patch_task_section(
                "# fn-1.1 T\n\n## Description\nbody\n", "## Acceptance", "- x"
            )
        self.assertIn("not found", str(ctx.exception))


# ── CLI end-to-end (create --acceptance-file, set-acceptance twice) ───────


def _ascii(text: str) -> str:
    """ASCII-safe rendering for FAILURE MESSAGES only (never for assertions).

    Windows CI pipes are cp1252, so a non-ASCII character inside a unittest
    failure message raises UnicodeEncodeError and hides the real defect
    (fn-120.1). Escaping the diagnostic keeps the assertion itself exact.
    """
    return text.encode("unicode_escape").decode("ascii")


def _windows_short_path(path: Path) -> Path:
    """The REAL 8.3 short form of `path` (Windows only), via GetShortPathNameW.

    fn-120.2: the observed windows-latest failures ran with `--acceptance-file
    C:\\Users\\RUNNER~1\\...`, so the short-path contract is exercised with the
    filesystem's own short name — never a hand-built or slash-swapped string.
    Returns the long path unchanged when the volume has 8.3 name generation
    disabled (`GetShortPathNameW` is then an identity function).
    """
    import ctypes
    from ctypes import wintypes

    get_short = ctypes.windll.kernel32.GetShortPathNameW
    get_short.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    get_short.restype = wintypes.DWORD
    needed = get_short(str(path), None, 0)
    if not needed:
        raise ctypes.WinError()
    buf = ctypes.create_unicode_buffer(needed)
    if not get_short(str(path), buf, needed):
        raise ctypes.WinError()
    return Path(buf.value)


class CliEndToEndTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self._run("init")
        out = self._run("spec", "create", "--title", "Normalize test", "--json")
        self.spec_id = json.loads(out)["id"]

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *argv: str) -> str:
        proc = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *argv],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        # fn-120.2: `--json` failures are reported as JSON on STDOUT, so a
        # stderr-only message left the original windows-latest failure
        # ("Acceptance file unreadable: ... 'utf-8' codec can't decode byte
        # 0x96") completely invisible — the assertion read `failed: ` with an
        # empty tail. Both streams are reported, ASCII-escaped so the failure
        # text itself can never raise UnicodeEncodeError on a cp1252 stdout
        # (fn-120.1's reveval failure shape).
        self.assertEqual(
            proc.returncode,
            0,
            "flowctl {} failed (rc={}):\nstdout: {}\nstderr: {}".format(
                " ".join(argv),
                proc.returncode,
                _ascii(proc.stdout),
                _ascii(proc.stderr),
            ),
        )
        return proc.stdout

    def test_create_with_leading_h2_acceptance_file(self) -> None:
        acc = self.tmpdir / "acc.md"
        # fn-120.2: `encoding="utf-8"` is load-bearing, not decoration. The en
        # dash below is U+2013; a bare write_text() encodes it as cp1252 (0x96)
        # on Windows, and production reads --acceptance-file as strict UTF-8,
        # so the CLI exited 1 with "Acceptance file unreadable". Reverting this
        # kwarg re-breaks the test on windows-latest.
        acc.write_text(
            "## Acceptance Criteria (fn-79 R1–R3)\n- R1: works\n\n## Notes\nn1\n",
            encoding="utf-8",
        )
        out = self._run(
            "task", "create", "--spec", self.spec_id,
            "--title", "T1", "--acceptance-file", str(acc), "--json",
        )
        task_id = json.loads(out)["id"]
        md = (self.tmpdir / ".flow" / "tasks" / f"{task_id}.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(md.count("\n## Acceptance"), 1)
        self.assertNotIn("Acceptance Criteria", md)
        self.assertIn("### Notes", md)
        # Skeleton stays well-formed: validate-critical headings all present.
        for heading in ("## Description", "## Done summary", "## Evidence"):
            self.assertIn(heading, md)

    def test_set_acceptance_twice_byte_idempotent(self) -> None:
        out = self._run(
            "task", "create", "--spec", self.spec_id, "--title", "T2", "--json"
        )
        task_id = json.loads(out)["id"]
        acc = self.tmpdir / "acc2.md"
        # Em dash U+2014 — same strict-UTF-8 contract as above (cp1252 0x97).
        acc.write_text(
            "## Acceptance Criteria — v2\n- R1: x\n\n## More\nm\n", encoding="utf-8"
        )
        md_path = self.tmpdir / ".flow" / "tasks" / f"{task_id}.md"
        self._run("task", "set-acceptance", task_id, "--file", str(acc), "--json")
        first = md_path.read_text(encoding="utf-8")
        self.assertEqual(first.count("\n## Acceptance"), 1)
        self.assertIn("### More", first)
        self._run("task", "set-acceptance", task_id, "--file", str(acc), "--json")
        self.assertEqual(md_path.read_text(encoding="utf-8"), first)

    # ── fn-120.2 path/encoding regressions for the real `--file` contract ──

    # Non-ASCII body of the fn-120.2 fixtures: en dash, em dash, umlaut, check
    # mark. Kept as one constant so the assertion needle and the written bytes
    # cannot drift apart.
    UTF8_BODY = "- R1: wörks — ünicode ✓"

    def _acceptance_fixture(self, directory: Path, name: str) -> Path:
        """A UTF-8 acceptance fixture whose content is deliberately non-ASCII."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(
            f"## Acceptance Criteria (fn-120 R4–R5)\n{self.UTF8_BODY}\n",
            encoding="utf-8",
        )
        return path

    def _assert_acceptance_roundtrip(self, task_id: str) -> None:
        md = (self.tmpdir / ".flow" / "tasks" / f"{task_id}.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(md.count("\n## Acceptance"), 1)
        self.assertNotIn("Acceptance Criteria", md)
        # assertTrue (not assertIn) so the failure message stays ASCII: see
        # _ascii() — a cp1252 stdout cannot render the needle or the file body.
        self.assertTrue(
            self.UTF8_BODY in md,
            "UTF-8 acceptance body missing from {}; needle={} md={}".format(
                task_id, _ascii(self.UTF8_BODY), _ascii(md)
            ),
        )

    def test_long_path_with_spaces_and_utf8_content(self) -> None:
        """Valid LONG `--file`/`--acceptance-file` path: spaces + UTF-8 body."""
        acc = self._acceptance_fixture(
            self.tmpdir / "a dir with spaces", "acceptance criteria.md"
        )
        self.assertIn(" ", str(acc))
        out = self._run(
            "task", "create", "--spec", self.spec_id,
            "--title", "Long", "--acceptance-file", str(acc), "--json",
        )
        task_id = json.loads(out)["id"]
        self._assert_acceptance_roundtrip(task_id)
        # …and the same path through `set-acceptance --file` (byte-idempotent).
        self._run("task", "set-acceptance", task_id, "--file", str(acc), "--json")
        self._assert_acceptance_roundtrip(task_id)

    @unittest.skipUnless(
        os.name == "nt", "8.3 short names are a Windows filesystem feature"
    )
    def test_real_windows_short_path_file_args(self) -> None:
        """The observed `RUNNER~1` failure shape: a REAL 8.3 path + drive letter.

        The path comes from GetShortPathNameW, so the fixture cannot degrade
        into a mocked separator/string swap.
        """
        acc = self._acceptance_fixture(
            self.tmpdir / "a dir with spaces", "acceptance criteria.md"
        )
        short = _windows_short_path(acc)
        if "~" not in str(short):
            self.skipTest(
                f"volume has 8.3 name generation disabled (short form: {short})"
            )
        self.assertTrue(short.drive, f"short path lost its drive letter: {short}")
        self.assertTrue(short.is_absolute())
        out = self._run(
            "task", "create", "--spec", self.spec_id,
            "--title", "Short", "--acceptance-file", str(short), "--json",
        )
        task_id = json.loads(out)["id"]
        self._assert_acceptance_roundtrip(task_id)
        self._run("task", "set-acceptance", task_id, "--file", str(short), "--json")
        self._assert_acceptance_roundtrip(task_id)


if __name__ == "__main__":
    unittest.main()

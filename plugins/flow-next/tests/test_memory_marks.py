"""Unit tests for `flowctl memory mark-*` transitions and the during-spec
null-safe memory window.

Consolidates the former micro-suites (zero assertion loss):
  - test_memory_mark_fresh.py    — `memory mark-fresh` (fn-34 task 2)
  - test_memory_mark_stale.py    — `memory mark-stale` (fn-34 task 2)
  - test_memory_mark_hardened.py — `memory mark-hardened` (fn-122 task 1)
  - test_memory_during_spec_null_safe.py — `_export_memory_during_epic`
    null-safe time-window fallback (fn-49.2)

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers (mark-fresh — fn-34 task 2):
  - mark-fresh on a stale entry: clears status (back to active default),
    clears audit_notes, stamps last_audited (today).
  - mark-fresh on a non-stale entry: stamps last_audited, no error.
  - --audited-by records `marked fresh (audited-by: X)` in audit_notes.
  - --json output shape.
  - Body preserved.
  - Unknown id → error.
  - Legacy id rejected with migrate hint.

Covers (mark-stale — fn-34 task 2):
  - Sets status: stale, last_audited (today), audit_notes from --reason.
  - --audited-by appends `(audited-by: X)` suffix to audit_notes.
  - --json output shape.
  - --reason missing → exit 2 (argparse `required=True`).
  - Re-marking already-stale entry is idempotent (last_audited + audit_notes
    update; no error).
  - Body content preserved across the write.
  - Unknown id → error.
  - Legacy id rejected with migrate hint.

Covers (mark-hardened — fn-122 task 1):
  - Sets status: hardened, hardened_into (verbatim), last_audited (today UTC).
  - --audited-by records audit_notes; --json output shape; human output.
  - Body content preserved across the write.
  - Idempotent: re-marking replaces `hardened_into` (asserted on the field,
    NOT on last_audited — a same-day re-mark cannot change a date stamp).
  - Transition matrix inbound: active -> hardened, stale -> hardened (the
    stale pair is cleared).
  - Errors: unknown id, missing --gate-ref (argparse), empty --gate-ref,
    legacy id rejected with migrate hint.
  - Filters: default list/search exclude hardened; --status hardened selects
    only them; --status all includes them; hardened_into surfaces in
    list / search / read JSON.
  - Write-side validation rejects an unknown status value by name.

  Every command runs through the real argparse routing (two-token
  `memory mark-hardened` form), not a mock-patched handler.

Covers (during-spec null-safe window — fn-49.2):
  When `spec.created_at` is null (specs created via `/flow-next:capture` in
  the same session as `flowctl init`, or pre-timestamp-population specs),
  the memory time-window filter walks a deterministic fallback chain so the
  returned set still approximates the spec lifetime:

  1. Spec `created_at` (primary, YYYY-MM-DD prefix).
  2. Earliest non-empty `tasks[].created_at` (Option A).
  3. First commit on the spec's branch via `git log <branch> --reverse
     --format=%cI --max-count=1` (Option B).
  4. Empty threshold → return all entries (graceful-degradation fallback,
     preserves pre-fn-49.2 no-signal behavior).

  Each step is deterministic; the chain stops at the first success.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import flowctl  # noqa: E402  (path-injected import)


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

GATE_REF = "pyproject.toml#DTZ -- ruff select entry, bans naive datetimes"
GATE_REF_2 = "CLAUDE.md#stamp timestamps in UTC ISO-8601 -- instruction-file floor gate"
ENTRY_ID = "bug/runtime-errors/null-deref-in-auth-2026-05-01"


def _init_repo(tmp: Path) -> Path:
    subprocess.check_call(
        [sys.executable, str(FLOWCTL_PY), "init", "--json"],
        cwd=tmp,
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [
            sys.executable,
            str(FLOWCTL_PY),
            "config",
            "set",
            "memory.enabled",
            "true",
            "--json",
        ],
        cwd=tmp,
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [sys.executable, str(FLOWCTL_PY), "memory", "init", "--json"],
        cwd=tmp,
        stdout=subprocess.DEVNULL,
    )
    return tmp / ".flow" / "memory"


def _seed_stale_entry(memory_dir: Path) -> Path:
    """Seed an entry already flagged stale."""
    entry_dir = memory_dir / "knowledge" / "conventions"
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / "old-rule-2026-01-01.md"
    flowctl.write_memory_entry(
        path,
        {
            "title": "Old convention",
            "date": "2026-01-01",
            "track": "knowledge",
            "category": "conventions",
            "tags": ["old"],
            "applies_when": "writing typescript",
            "status": "stale",
            "last_audited": "2026-04-01",
            "audit_notes": "stale because superseded",
        },
        "Convention body content.\n",
    )
    return path


def _seed_active_entry(memory_dir: Path) -> Path:
    entry_dir = memory_dir / "knowledge" / "conventions"
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / "fresh-rule-2026-04-01.md"
    flowctl.write_memory_entry(
        path,
        {
            "title": "Fresh convention",
            "date": "2026-04-01",
            "track": "knowledge",
            "category": "conventions",
            "applies_when": "writing typescript",
        },
        "Body.\n",
    )
    return path


def _seed_entry(memory_dir: Path) -> Path:
    """Drop one categorized entry; return its path."""
    entry_dir = memory_dir / "bug" / "runtime-errors"
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / "null-deref-in-auth-2026-05-01.md"
    flowctl.write_memory_entry(
        path,
        {
            "title": "Null deref in auth middleware",
            "date": "2026-05-01",
            "track": "bug",
            "category": "runtime-errors",
            "module": "src/auth.ts",
            "tags": ["auth", "null"],
            "problem_type": "runtime-error",
            "symptoms": "500 on /me",
            "root_cause": "user.role accessed without guard",
            "resolution_type": "fix",
        },
        "Body: user.role propagation issue; fix added a guard.\n",
    )
    return path


def _run(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    cmd = [sys.executable, str(FLOWCTL_PY), *args]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != expect_rc:
        raise AssertionError(
            f"rc={proc.returncode} (expected {expect_rc}): args={args} "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    out_text = proc.stdout.decode()
    if out_text.strip().startswith("{"):
        try:
            return json.loads(out_text)
        except json.JSONDecodeError:
            pass
    return {"_stdout": out_text, "_stderr": proc.stderr.decode()}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write_memory_entry(
    memory_dir: Path,
    track: str,
    category: str,
    slug: str,
    date: str,
    title: str = "",
) -> Path:
    """Write a minimal memory entry at `<track>/<category>/<slug>-<date>.md`.

    `_memory_parse_entry_filename` reads slug + date from the FILENAME
    (stem matches `^<slug>-YYYY-MM-DD$`), so the on-disk filename carries
    the canonical date even though frontmatter also stores it.
    """
    entry_dir = memory_dir / track / category
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / f"{slug}-{date}.md"
    title = title or slug.replace("-", " ")
    body = (
        f"---\n"
        f'title: "{title}"\n'
        f'date: "{date}"\n'
        f"track: {track}\n"
        f"category: {category}\n"
        f"module: synthetic\n"
        f"tags: []\n"
        f"---\n\n"
        f"## Problem\n\n"
        f"Synthetic body for {slug}.\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


# --- mark-fresh (fn-34 task 2) ---


class TestMarkFreshHappyPath(unittest.TestCase):
    def test_clears_stale_flag_and_stamps_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_stale_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "knowledge/conventions/old-rule-2026-01-01",
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "active")
            self.assertEqual(result["last_audited"], _today())
            self.assertEqual(result["audit_notes"], "")

            fm = flowctl.parse_memory_frontmatter(path)
            # status removed entirely (active is the default; minimal frontmatter).
            self.assertNotIn("status", fm)
            self.assertNotIn("audit_notes", fm)
            self.assertEqual(fm["last_audited"], _today())

    def test_no_op_on_non_stale_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_active_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "fresh-rule-2026-04-01",
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "active")
            self.assertEqual(result["last_audited"], _today())

            fm = flowctl.parse_memory_frontmatter(path)
            self.assertNotIn("status", fm)
            self.assertEqual(fm["last_audited"], _today())

    def test_audited_by_records_breadcrumb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_stale_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "old-rule-2026-01-01",
                "--audited-by",
                "audit-skill",
                "--json",
            )
            self.assertEqual(
                result["audit_notes"],
                "marked fresh (audited-by: audit-skill)",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(
                fm["audit_notes"],
                "marked fresh (audited-by: audit-skill)",
            )

    def test_body_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_stale_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "old-rule-2026-01-01",
                "--json",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("Convention body content.", text)


class TestMarkFreshErrors(unittest.TestCase):
    def test_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_stale_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "does-not-exist",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])

    def test_legacy_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_stale_entry(mem)
            (mem / "decisions.md").write_text(
                "## 2026-01-01 manual\nDecision body.\n", encoding="utf-8"
            )
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "legacy/decisions.md",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("legacy", result["error"].lower())


class TestMarkFreshRoundTrip(unittest.TestCase):
    def test_stale_then_fresh_roundtrip(self) -> None:
        """mark-stale then mark-fresh leaves entry in active default."""
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_active_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "fresh-rule-2026-04-01",
                "--reason",
                "test",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(fm["audit_notes"], "test")

            _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "fresh-rule-2026-04-01",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertNotIn("status", fm)
            self.assertNotIn("audit_notes", fm)
            self.assertEqual(fm["last_audited"], _today())


class TestMarkFreshUnHardens(unittest.TestCase):
    """hardened -> active (fn-122 R14): drops `hardened_into` + stale family."""

    def test_hardened_then_fresh_drops_gate_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_active_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "fresh-rule-2026-04-01",
                "--gate-ref",
                "CLAUDE.md#timestamps-utc -- stamp UTC",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "hardened")
            self.assertEqual(
                fm["hardened_into"], "CLAUDE.md#timestamps-utc -- stamp UTC"
            )

            _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "fresh-rule-2026-04-01",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertNotIn("status", fm)
            self.assertNotIn("hardened_into", fm)
            self.assertNotIn("stale_reason", fm)
            self.assertNotIn("stale_date", fm)
            self.assertEqual(fm["last_audited"], _today())


# --- mark-stale (fn-34 task 2) ---


class TestMarkStaleHappyPath(unittest.TestCase):
    def test_sets_status_audit_notes_and_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "bug/runtime-errors/null-deref-in-auth-2026-05-01",
                "--reason",
                "src/auth.ts moved to src/middleware/auth.ts",
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "stale")
            self.assertEqual(result["last_audited"], _today())
            self.assertEqual(
                result["audit_notes"],
                "src/auth.ts moved to src/middleware/auth.ts",
            )

            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(fm["last_audited"], _today())
            self.assertEqual(
                fm["audit_notes"],
                "src/auth.ts moved to src/middleware/auth.ts",
            )

    def test_body_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "x",
                "--json",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "user.role propagation issue; fix added a guard.", text
            )

    def test_audited_by_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth",
                "--reason",
                "code path removed",
                "--audited-by",
                "audit-skill",
                "--json",
            )
            self.assertEqual(
                result["audit_notes"],
                "code path removed (audited-by: audit-skill)",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertIn("(audited-by: audit-skill)", fm["audit_notes"])

    def test_human_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "x",
            )
            self.assertIn("Flagged stale", result["_stdout"])
            self.assertIn(_today(), result["_stdout"])


class TestMarkStaleErrors(unittest.TestCase):
    def test_missing_reason_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                expect_rc=2,
            )
            combined = result["_stdout"] + result["_stderr"]
            self.assertTrue(
                re.search(r"--reason", combined),
                f"expected argparse to mention --reason; got: {combined!r}",
            )

    def test_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "does-not-exist",
                "--reason",
                "x",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])

    def test_legacy_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            (mem / "pitfalls.md").write_text(
                "## 2026-01-01 manual\nLegacy entry.\n", encoding="utf-8"
            )
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "legacy/pitfalls.md",
                "--reason",
                "x",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("legacy", result["error"].lower())
            self.assertIn("migrate", result["error"])


class TestMarkStaleIdempotent(unittest.TestCase):
    def test_remark_updates_audit_notes_and_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "first reason",
                "--json",
            )
            second = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "second reason",
                "--audited-by",
                "second-pass",
                "--json",
            )
            self.assertTrue(second["success"])
            self.assertEqual(
                second["audit_notes"],
                "second reason (audited-by: second-pass)",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(
                fm["audit_notes"],
                "second reason (audited-by: second-pass)",
            )


class TestMarkStaleDropsHardenedPointer(unittest.TestCase):
    """hardened -> stale (fn-122 R14): `hardened_into` must not survive."""

    def test_hardened_then_stale_clears_gate_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "bug/runtime-errors/null-deref-in-auth-2026-05-01",
                "--gate-ref",
                "pyproject.toml#DTZ -- ruff select entry, bans naive datetimes",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "hardened")
            self.assertIn("hardened_into", fm)

            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "bug/runtime-errors/null-deref-in-auth-2026-05-01",
                "--reason",
                "the lint rule was reverted",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertNotIn("hardened_into", fm)
            self.assertEqual(fm["audit_notes"], "the lint rule was reverted")


# --- mark-hardened (fn-122 task 1) ---


class TestMarkHardenedHappyPath(unittest.TestCase):
    def test_sets_status_gate_ref_and_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                GATE_REF,
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "hardened")
            self.assertEqual(result["hardened_into"], GATE_REF)
            self.assertEqual(result["last_audited"], _today())

            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "hardened")
            self.assertEqual(fm["hardened_into"], GATE_REF)
            self.assertEqual(fm["last_audited"], _today())

    def test_gate_ref_stored_verbatim(self) -> None:
        """flowctl never parses the `<path>#<rule-id> -- <note>` convention."""
        weird = "not/a/real#convention: 42 -- but stored anyway"
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                weird,
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["hardened_into"], weird)

    def test_surrounding_whitespace_preserved_verbatim(self) -> None:
        """Only the emptiness check strips — storage is the raw value."""
        padded = f"  {GATE_REF}\t"
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                padded,
                "--json",
            )
            self.assertEqual(result["hardened_into"], padded)
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["hardened_into"], padded)

    def test_multiline_gate_ref_round_trips(self) -> None:
        """A newline in the value must not shred the frontmatter."""
        multiline = "pyproject.toml#DTZ -- bans\nnaive datetimes\ttab"
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                multiline,
                "--json",
            )
            self.assertEqual(result["hardened_into"], multiline)

            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["hardened_into"], multiline)
            # Frontmatter still parses (a raw newline would yield `{}`) and
            # the entry stays visible to the status filter.
            self.assertEqual(fm["status"], "hardened")
            self.assertEqual(fm["title"], "Null deref in auth middleware")

            # The no-PyYAML fallback parser must agree with PyYAML.
            envelope = flowctl._frontmatter_envelope(
                path.read_text(encoding="utf-8")
            )
            inline = flowctl._parse_inline_yaml(envelope.frontmatter)
            self.assertEqual(inline["hardened_into"], multiline)

    def test_body_segment_byte_identical(self) -> None:
        """The raw body segment after `---` is unchanged, byte for byte."""
        rich_body = (
            "Body: user.role propagation issue.\n"
            "\n"
            "## Update 2026-05-10\n"
            "\n"
            "Re-learned in fn-97.\n"
            "\n"
            "  indented line with trailing spaces   \n"
            "\n"
            "Final line.\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            data = flowctl._memory_read_entry(path)
            flowctl.write_memory_entry(path, data["frontmatter"], rich_body)

            before_raw = path.read_text(encoding="utf-8")
            before_segment = before_raw.split("---\n", 2)[2]

            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "null-deref-in-auth-2026-05-01",
                "--gate-ref",
                GATE_REF,
                "--json",
            )

            after_segment = path.read_text(encoding="utf-8").split("---\n", 2)[2]
            self.assertEqual(before_segment, after_segment)

    def test_noncanonical_body_preserved_byte_for_byte(self) -> None:
        """A hand-written body keeps its leading/trailing blank lines.

        Frontmatter-only mutations must not reflow a body they never edited.
        Asserted against `mark-stale` too, so the sibling handlers cannot
        drift apart.
        """
        padded = "---\n{fm}---\n\n\n\nPadded body.\n\n\n"
        fm_lines = (
            "title: T\n"
            "date: \"2026-01-01\"\n"
            "track: knowledge\n"
            "category: conventions\n"
            "applies_when: always\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            entry_dir = mem / "knowledge" / "conventions"
            entry_dir.mkdir(parents=True, exist_ok=True)

            hardened_path = entry_dir / "padded-hardened-2026-01-01.md"
            hardened_path.write_text(padded.format(fm=fm_lines), encoding="utf-8")
            stale_path = entry_dir / "padded-stale-2026-01-01.md"
            stale_path.write_text(padded.format(fm=fm_lines), encoding="utf-8")

            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "padded-hardened-2026-01-01",
                "--gate-ref",
                GATE_REF,
                "--json",
            )
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "padded-stale-2026-01-01",
                "--reason",
                "x",
                "--json",
            )

            hardened_segment = hardened_path.read_text(encoding="utf-8").split(
                "---\n", 2
            )[2]
            stale_segment = stale_path.read_text(encoding="utf-8").split("---\n", 2)[2]
            original_segment = padded.format(fm=fm_lines).split("---\n", 2)[2]
            self.assertEqual(hardened_segment, original_segment)
            self.assertEqual(stale_segment, original_segment)

    def test_crlf_body_preserved_byte_for_byte(self) -> None:
        """A CRLF-authored entry keeps its CRLF line endings.

        `Path.read_text` performs universal-newline translation, so the read
        path has to disable it or every frontmatter-only rewrite silently
        converts a Windows-authored body to LF (whole-file diff). Asserted on
        bytes, and across `mark-hardened` / `mark-stale` / `mark-fresh` so the
        sibling handlers cannot drift apart.
        """
        fm_lines = (
            "title: T\r\n"
            'date: "2026-01-01"\r\n'
            "track: knowledge\r\n"
            "category: conventions\r\n"
            "applies_when: always\r\n"
        )
        crlf = f"---\r\n{fm_lines}---\r\n\r\nCRLF body line one.\r\n\r\nAnd two.\r\n"
        original_segment = crlf.encode().split(b"---\r\n", 2)[2]

        cases = (
            ("hardened", ("--gate-ref", GATE_REF)),
            ("stale", ("--reason", "x")),
            ("fresh", ()),
        )
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            entry_dir = mem / "knowledge" / "conventions"
            entry_dir.mkdir(parents=True, exist_ok=True)

            for suffix, extra in cases:
                slug = f"crlf-{suffix}-2026-01-01"
                path = entry_dir / f"{slug}.md"
                path.write_bytes(crlf.encode())

                _run(Path(tmp), "memory", f"mark-{suffix}", slug, *extra, "--json")

                after = path.read_bytes()
                self.assertEqual(
                    after.split(b"---\r\n", 2)[2],
                    original_segment,
                    f"mark-{suffix} rewrote the CRLF body",
                )
                # The rewritten frontmatter keeps CRLF too — no stray LF.
                self.assertNotIn(b"\n", after.replace(b"\r\n", b""))

    def test_audited_by_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "null-deref-in-auth",
                "--gate-ref",
                GATE_REF,
                "--audited-by",
                "/flow-next:audit",
                "--json",
            )
            self.assertIn("(audited-by: /flow-next:audit)", result["audit_notes"])
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertIn("(audited-by: /flow-next:audit)", fm["audit_notes"])

    def test_human_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                GATE_REF,
            )
            self.assertIn("Hardened:", result["_stdout"])
            self.assertIn(GATE_REF, result["_stdout"])
            self.assertIn(_today(), result["_stdout"])


class TestMarkHardenedIdempotent(unittest.TestCase):
    def test_remark_replaces_gate_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                GATE_REF,
                "--json",
            )
            second = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                GATE_REF_2,
                "--json",
            )
            self.assertTrue(second["success"])
            self.assertEqual(second["hardened_into"], GATE_REF_2)
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "hardened")
            # `last_audited` is date precision, so a same-day re-mark is
            # unobservable there — the replacement is the observable effect.
            self.assertEqual(fm["hardened_into"], GATE_REF_2)


class TestMarkHardenedTransitions(unittest.TestCase):
    def test_active_to_hardened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            self.assertNotIn("status", flowctl.parse_memory_frontmatter(path))
            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                GATE_REF,
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "hardened")
            self.assertEqual(fm["hardened_into"], GATE_REF)
            self.assertNotIn("stale_reason", fm)
            self.assertNotIn("stale_date", fm)

    def test_stale_to_hardened_clears_stale_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                ENTRY_ID,
                "--reason",
                "src/auth.ts moved",
                "--json",
            )
            # `stale_date` is only ever set by hand/older writes; set it
            # explicitly so the clearing assertion is meaningful.
            data = flowctl._memory_read_entry(path)
            fm = dict(data["frontmatter"])
            fm["stale_reason"] = "src/auth.ts moved"
            fm["stale_date"] = "2026-05-02"
            flowctl.write_memory_entry(path, fm, data["body"])
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(fm["stale_reason"], "src/auth.ts moved")

            _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                GATE_REF,
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "hardened")
            self.assertEqual(fm["hardened_into"], GATE_REF)
            self.assertNotIn("stale_reason", fm)
            self.assertNotIn("stale_date", fm)


class TestMarkHardenedErrors(unittest.TestCase):
    def test_missing_gate_ref_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                expect_rc=2,
            )
            combined = result["_stdout"] + result["_stderr"]
            self.assertTrue(
                re.search(r"--gate-ref", combined),
                f"expected argparse to mention --gate-ref; got: {combined!r}",
            )

    def test_empty_gate_ref_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                ENTRY_ID,
                "--gate-ref",
                "   ",
                "--json",
                expect_rc=2,
            )
            self.assertFalse(result["success"])
            self.assertIn("--gate-ref", result["error"])
            self.assertNotIn("status", flowctl.parse_memory_frontmatter(path))

    def test_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "does-not-exist",
                "--gate-ref",
                GATE_REF,
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("does-not-exist", result["error"])
            self.assertIn("not found", result["error"])

    def test_legacy_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            (mem / "pitfalls.md").write_text(
                "## 2026-01-01 manual\nLegacy entry.\n", encoding="utf-8"
            )
            result = _run(
                Path(tmp),
                "memory",
                "mark-hardened",
                "legacy/pitfalls.md",
                "--gate-ref",
                GATE_REF,
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("legacy", result["error"].lower())
            self.assertIn("migrate", result["error"])


class TestHardenedWriteValidation(unittest.TestCase):
    def test_unknown_status_rejected_by_name(self) -> None:
        """WRITE-side guarantee only — `_memory_read_entry` never validates."""
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            data = flowctl._memory_read_entry(path)
            fm = dict(data["frontmatter"])
            fm["status"] = "graduated"
            with self.assertRaises(ValueError) as ctx:
                flowctl.write_memory_entry(path, fm, data["body"])
            self.assertIn("graduated", str(ctx.exception))

    def test_hardened_status_accepted_by_validator(self) -> None:
        self.assertIn("hardened", flowctl.MEMORY_STATUS)
        self.assertIn("hardened_into", flowctl.MEMORY_OPTIONAL_FIELDS)
        self.assertIn("hardened_into", flowctl.MEMORY_FIELD_ORDER)


class TestHardenedStatusFilters(unittest.TestCase):
    def _seed_and_harden(self, tmp: Path) -> Path:
        mem = _init_repo(tmp)
        path = _seed_entry(mem)
        _run(
            tmp,
            "memory",
            "mark-hardened",
            ENTRY_ID,
            "--gate-ref",
            GATE_REF,
            "--json",
        )
        return path

    def test_list_default_excludes_hardened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_and_harden(Path(tmp))
            default = _run(Path(tmp), "memory", "list", "--json")
            self.assertEqual(default["count"], 0)

            only = _run(
                Path(tmp), "memory", "list", "--status", "hardened", "--json"
            )
            self.assertEqual(only["count"], 1)
            self.assertEqual(only["entries"][0]["status"], "hardened")
            self.assertEqual(only["entries"][0]["hardened_into"], GATE_REF)

            every = _run(Path(tmp), "memory", "list", "--status", "all", "--json")
            self.assertEqual(every["count"], 1)

    def test_list_status_hardened_excludes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                ENTRY_ID,
                "--reason",
                "x",
                "--json",
            )
            only = _run(
                Path(tmp), "memory", "list", "--status", "hardened", "--json"
            )
            self.assertEqual(only["count"], 0)

    def test_search_default_excludes_hardened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_and_harden(Path(tmp))
            default = _run(Path(tmp), "memory", "search", "auth", "--json")
            self.assertEqual(default["count"], 0)

            only = _run(
                Path(tmp),
                "memory",
                "search",
                "auth",
                "--status",
                "hardened",
                "--json",
            )
            self.assertEqual(only["count"], 1)
            self.assertEqual(only["matches"][0]["hardened_into"], GATE_REF)

            every = _run(
                Path(tmp), "memory", "search", "auth", "--status", "all", "--json"
            )
            self.assertEqual(every["count"], 1)

    def test_read_json_surfaces_hardened_into(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_and_harden(Path(tmp))
            payload = _run(Path(tmp), "memory", "read", ENTRY_ID, "--json")
            self.assertEqual(
                payload["frontmatter"]["hardened_into"], GATE_REF
            )
            self.assertEqual(payload["frontmatter"]["status"], "hardened")


# --- during-spec null-safe window (fn-49.2) ---


class TestResolveMemoryThreshold(unittest.TestCase):
    """`_export_resolve_memory_threshold` walks the fallback chain deterministically."""

    def test_spec_created_wins(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            "2026-05-25T06:08:52.904959Z",
            task_created_ats=["2026-05-20T00:00:00Z"],
            branch_name="any",
        )
        self.assertEqual(threshold, "2026-05-25")
        self.assertEqual(source, "spec")

    def test_falls_back_to_earliest_task(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=[
                "2026-05-26T10:00:00Z",
                "2026-05-25T07:04:49Z",
                "2026-05-27T03:00:00Z",
            ],
        )
        self.assertEqual(threshold, "2026-05-25")
        self.assertEqual(source, "earliest_task")

    def test_falls_back_to_branch_when_tasks_empty(self) -> None:
        """No spec.created + no usable task timestamps → branch first commit."""
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=[],
            branch_name="HEAD",  # use HEAD so the test is git-repo-aware
        )
        self.assertEqual(source, "branch_first_commit")
        # Threshold is a real YYYY-MM-DD prefix.
        self.assertRegex(threshold, r"^\d{4}-\d{2}-\d{2}$")

    def test_no_signals_returns_empty(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            None, task_created_ats=None, branch_name=None
        )
        self.assertEqual(threshold, "")
        self.assertEqual(source, "")

    def test_empty_strings_in_task_list_filtered(self) -> None:
        """Empty/None task created_at values must not crash min()."""
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=["", "", "2026-05-25T07:04:49Z", ""],
        )
        self.assertEqual(threshold, "2026-05-25")
        self.assertEqual(source, "earliest_task")

    def test_all_empty_task_list_falls_through_to_branch(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=["", ""],
            branch_name="HEAD",
        )
        self.assertEqual(source, "branch_first_commit")

    def test_invalid_branch_falls_through(self) -> None:
        """git log on a nonexistent branch returns rc != 0 → fall through."""
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=None,
            branch_name="definitely-not-a-real-branch-fn-49-2",
        )
        # Should not raise; falls through to no-signal.
        self.assertEqual(threshold, "")
        self.assertEqual(source, "")

    def test_branch_first_commit_returns_root_not_tip(self) -> None:
        """Regression: multi-commit branch must return the ROOT commit's date,
        not the tip's.

        Caught by Codex bot review on PR #147 — `git log --reverse --format=%cI
        --max-count=1` is wrong because ``--max-count`` is a selection option
        applied BEFORE output ordering. Combined with ``--reverse`` it picks
        the most recent commit, then "reverses" a 1-element list (no-op),
        returning the branch TIP date instead of the root commit's date.

        Pre-fix this test would fail because the threshold returned would be
        2026-05-30 (tip) instead of 2026-05-25 (root). Pre-fix tests passed
        only because their fixtures had a SINGLE commit where root == tip.
        """
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            base_env = {
                **os.environ,
                "GIT_COMMITTER_NAME": "fn-49.2 regression",
                "GIT_COMMITTER_EMAIL": "regression@example.com",
                "GIT_AUTHOR_NAME": "fn-49.2 regression",
                "GIT_AUTHOR_EMAIL": "regression@example.com",
            }
            subprocess.run(
                ["git", "init", "-b", "fn-49-multi-commit-branch", "."],
                cwd=repo, env=base_env, check=True, capture_output=True,
            )
            # Commit 1: 2026-05-25 (the ROOT — what we want returned).
            env_root = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-25T12:00:00+00:00",
            }
            (repo / "a.txt").write_text("a", encoding="utf-8")
            subprocess.run(
                ["git", "add", "a.txt"],
                cwd=repo, env=env_root, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "root commit (2026-05-25)"],
                cwd=repo, env=env_root, check=True, capture_output=True,
            )
            # Commit 2: 2026-05-30 (the TIP — what the buggy form would return).
            env_tip = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-05-30T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-30T12:00:00+00:00",
            }
            (repo / "b.txt").write_text("b", encoding="utf-8")
            subprocess.run(
                ["git", "add", "b.txt"],
                cwd=repo, env=env_tip, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "tip commit (2026-05-30)"],
                cwd=repo, env=env_tip, check=True, capture_output=True,
            )

            cwd_before = os.getcwd()
            os.chdir(repo)
            try:
                threshold, source = flowctl._export_resolve_memory_threshold(
                    None,
                    task_created_ats=[],
                    branch_name="fn-49-multi-commit-branch",
                )
            finally:
                os.chdir(cwd_before)

        self.assertEqual(source, "branch_first_commit")
        # ROOT commit date — NOT the tip date. The buggy form would return
        # "2026-05-30" here, filtering out in-window memory entries dated
        # 2026-05-25 through 2026-05-29 — the exact regression class fn-49.2
        # was supposed to prevent.
        self.assertEqual(threshold, "2026-05-25")
        self.assertNotEqual(threshold, "2026-05-30")

    def test_branch_first_commit_excludes_base_history(self) -> None:
        """Regression: when ``base_ref`` is provided, the fallback uses
        ``git log {base_ref}..{branch_name}`` so only commits unique to the
        feature branch are walked.

        Caught by Codex bot P2 review on PR #147. Without ``base_ref``,
        ``git log <branch>`` walks ALL commits reachable from the branch
        tip — including inherited mainline history. ``--reverse`` then
        ``splitlines()[0]`` returns the REPOSITORY ROOT commit's date
        (way too old), defeating the purpose of "approximate the spec
        lifetime".

        Pre-fix this test would fail with threshold == 2026-01-01 (the
        repo root). Post-fix it returns 2026-05-25 (the feature branch's
        first commit).
        """
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            base_env = {
                **os.environ,
                "GIT_COMMITTER_NAME": "fn-49.2 base-history",
                "GIT_COMMITTER_EMAIL": "base-history@example.com",
                "GIT_AUTHOR_NAME": "fn-49.2 base-history",
                "GIT_AUTHOR_EMAIL": "base-history@example.com",
            }
            subprocess.run(
                ["git", "init", "-b", "trunk", "."],
                cwd=repo, env=base_env, check=True, capture_output=True,
            )
            # Trunk commit 1: 2026-01-01 (the REPO ROOT — what the buggy
            # form would return).
            env_t1 = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-01-01T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-01-01T12:00:00+00:00",
            }
            (repo / "trunk1.txt").write_text("t1", encoding="utf-8")
            subprocess.run(
                ["git", "add", "trunk1.txt"],
                cwd=repo, env=env_t1, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "trunk root (2026-01-01)"],
                cwd=repo, env=env_t1, check=True, capture_output=True,
            )
            # Trunk commit 2: 2026-04-01 (still on trunk).
            env_t2 = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-04-01T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-04-01T12:00:00+00:00",
            }
            (repo / "trunk2.txt").write_text("t2", encoding="utf-8")
            subprocess.run(
                ["git", "add", "trunk2.txt"],
                cwd=repo, env=env_t2, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "trunk advanced (2026-04-01)"],
                cwd=repo, env=env_t2, check=True, capture_output=True,
            )
            # Branch off trunk and add a feature commit: 2026-05-25
            # (the FORK POINT — what the correct form returns).
            subprocess.run(
                ["git", "checkout", "-b", "feature-fn-49"],
                cwd=repo, env=base_env, check=True, capture_output=True,
            )
            env_f1 = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-25T12:00:00+00:00",
            }
            (repo / "feature.txt").write_text("f", encoding="utf-8")
            subprocess.run(
                ["git", "add", "feature.txt"],
                cwd=repo, env=env_f1, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "feature commit (2026-05-25)"],
                cwd=repo, env=env_f1, check=True, capture_output=True,
            )

            cwd_before = os.getcwd()
            os.chdir(repo)
            try:
                # With base_ref — correct: feature commit date.
                t_with_base, source_with_base = flowctl._export_resolve_memory_threshold(
                    None,
                    task_created_ats=[],
                    branch_name="feature-fn-49",
                    base_ref="trunk",
                )
                # Without base_ref — buggy: repo root date.
                t_without_base, source_without_base = flowctl._export_resolve_memory_threshold(
                    None,
                    task_created_ats=[],
                    branch_name="feature-fn-49",
                )
            finally:
                os.chdir(cwd_before)

        self.assertEqual(source_with_base, "branch_first_commit")
        # WITH base_ref: returns the fork-point commit's date (2026-05-25).
        # This is the correct behavior — narrow window to commits unique to
        # the feature branch.
        self.assertEqual(t_with_base, "2026-05-25")
        # Sanity check: the pre-base-ref behavior is preserved when no
        # base_ref is supplied (best-effort for callers without a base).
        # In that case the returned date is the repo root (2026-01-01) —
        # demonstrably wrong for narrow-window purposes but documented as
        # the fallback when no base context is available.
        self.assertEqual(source_without_base, "branch_first_commit")
        self.assertEqual(t_without_base, "2026-01-01")
        # And of course the two diverge — that's the whole point.
        self.assertNotEqual(t_with_base, t_without_base)


class TestMemoryDuringEpicNullSafe(unittest.TestCase):
    """`_export_memory_during_epic` honors the fallback-resolved threshold."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.mem = self.tmp / "memory"
        # 3 decisions across a range: one before, one at, one after the window.
        _write_memory_entry(
            self.mem, "knowledge", "decisions", "decision-old", "2026-05-20"
        )
        _write_memory_entry(
            self.mem, "knowledge", "decisions", "decision-mid", "2026-05-25"
        )
        _write_memory_entry(
            self.mem, "knowledge", "decisions", "decision-new", "2026-05-26"
        )
        # 2 bugs.
        _write_memory_entry(
            self.mem, "bug", "build-errors", "bug-old", "2026-05-20"
        )
        _write_memory_entry(
            self.mem, "bug", "build-errors", "bug-new", "2026-05-26"
        )
        _write_memory_entry(
            self.mem,
            "knowledge",
            "architecture-patterns",
            "pattern-new",
            "2026-05-26",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_spec_created_drives_window(self) -> None:
        r = flowctl._export_memory_during_epic(self.mem, "2026-05-25T00:00:00Z")
        decision_ids = sorted(d["id"] for d in r["decisions"])
        # Date >= 2026-05-25 → decision-mid + decision-new.
        self.assertEqual(len(decision_ids), 2)
        self.assertTrue(all("decision-old" not in i for i in decision_ids))
        self.assertEqual(
            [d["first_sentence"] for d in r["decisions"]],
            [
                "Synthetic body for decision-mid.",
                "Synthetic body for decision-new.",
            ],
        )
        self.assertEqual(
            r["bugs"][0]["winning_hypothesis_first_sentence"],
            "Synthetic body for bug-new.",
        )
        self.assertEqual(
            r["architecture_patterns"][0]["first_sentence"],
            "Synthetic body for pattern-new.",
        )

    def test_null_spec_falls_back_to_earliest_task(self) -> None:
        """R3 — spec.created null + tasks have created_at → earliest task wins."""
        r = flowctl._export_memory_during_epic(
            self.mem,
            None,
            task_created_ats=["2026-05-26T10:00:00Z", "2026-05-25T07:00:00Z"],
        )
        decision_ids = sorted(d["id"] for d in r["decisions"])
        # Threshold = 2026-05-25 → decision-mid + decision-new survive.
        self.assertEqual(len(decision_ids), 2)
        self.assertTrue(all("decision-old" not in i for i in decision_ids))
        # Bugs filtered same way.
        self.assertEqual(len(r["bugs"]), 1)  # only bug-new

    def test_null_spec_null_tasks_falls_back_to_branch_first_commit(self) -> None:
        """R3 — spec.created null + tasks all null → branch first-commit fires."""
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            # Build a synthetic git repo: branch's first commit is the
            # branch first-commit timestamp that drives the threshold.
            env = {
                **os.environ,
                # Pin committer date so the test is deterministic across
                # machines. `git log --format=%cI` reads committer date.
                "GIT_COMMITTER_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_COMMITTER_NAME": "fn-49.2 test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                "GIT_AUTHOR_NAME": "fn-49.2 test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
            }
            subprocess.run(
                ["git", "init", "-b", "fn-49-test-branch", "."],
                cwd=repo, env=env, check=True, capture_output=True,
            )
            (repo / "f.txt").write_text("x", encoding="utf-8")
            subprocess.run(
                ["git", "add", "f.txt"],
                cwd=repo, env=env, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo, env=env, check=True, capture_output=True,
            )

            # Run the resolution from within the synthetic repo so
            # `_export_run_git` (which uses cwd=None → process cwd)
            # resolves the branch name correctly.
            cwd_before = os.getcwd()
            os.chdir(repo)
            try:
                r = flowctl._export_memory_during_epic(
                    self.mem,
                    None,
                    task_created_ats=[],
                    branch_name="fn-49-test-branch",
                )
            finally:
                os.chdir(cwd_before)

        decision_ids = sorted(d["id"] for d in r["decisions"])
        # Branch first commit was 2026-05-25 → decision-mid + decision-new.
        self.assertEqual(len(decision_ids), 2)
        self.assertTrue(all("decision-old" not in i for i in decision_ids))

    def test_no_signals_returns_all_entries(self) -> None:
        """Graceful-degradation contract — no usable timestamp → return all."""
        r = flowctl._export_memory_during_epic(
            self.mem,
            None,
            task_created_ats=None,
            branch_name=None,
        )
        self.assertEqual(len(r["decisions"]), 3)
        self.assertEqual(len(r["bugs"]), 2)

    def test_missing_memory_dir_returns_empty_structure(self) -> None:
        """No memory dir → empty structure, never crash."""
        r = flowctl._export_memory_during_epic(
            self.tmp / "nonexistent-memory",
            None,
            task_created_ats=["2026-05-25T00:00:00Z"],
        )
        self.assertEqual(r, {"decisions": [], "bugs": [], "architecture_patterns": []})


if __name__ == "__main__":
    unittest.main()

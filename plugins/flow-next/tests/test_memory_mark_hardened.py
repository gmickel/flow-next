"""Unit tests for `flowctl memory mark-hardened` (fn-122 task 1).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
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
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

GATE_REF = "pyproject.toml#tool.ruff.select:DTZ -- bans naive datetimes"
GATE_REF_2 = "CLAUDE.md#timestamps-utc -- always stamp UTC ISO-8601"
ENTRY_ID = "bug/runtime-errors/null-deref-in-auth-2026-05-01"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_mark_hardened_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


@contextmanager
def _chdir(target: Path):
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prev)


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


if __name__ == "__main__":
    unittest.main()

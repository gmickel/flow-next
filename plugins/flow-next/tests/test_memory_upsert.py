"""Unit tests for `flowctl memory upsert` — deterministic find-or-create (fn-212).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_memory_upsert -q

Covers (spec fn-212-flowctl-memory-upsert-deterministic R7):
  - create path: zero title matches in the track -> creates like `memory add`
  - update path: exactly one match -> updates in place like `add --update <id>`
  - ambiguous path: two same-titled entries -> exit nonzero, both ids listed,
    no write occurs
  - missing --title / --track -> exit 2 with a clear message
  - --json payload shape: `entry_id` + `action` (created | updated)
  - stale-entry match: an upsert on a stale entry updates it (no new sibling)

Review-round additions (codex NEEDS_WORK round 1):
  - cross-category unique match updates (title-within-track identity wins
    over the caller-supplied category)
  - over-80-char title rejected (stored titles truncate at 80, so a longer
    title cannot be a byte-for-byte identity)
  - non-JSON output is exactly one line on both create and update
  - concurrent same-title upserts serialize under the cross-process lock
    (no sibling duplicates)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _init_repo(tmp: Path) -> Path:
    """Initialize a fresh .flow/ repo with memory enabled + tree created."""
    for cmd in (
        ["init", "--json"],
        ["config", "set", "memory.enabled", "true", "--json"],
        ["memory", "init", "--json"],
    ):
        subprocess.check_call(
            [sys.executable, str(FLOWCTL_PY), *cmd],
            cwd=tmp,
            stdout=subprocess.DEVNULL,
        )
    return tmp / ".flow" / "memory"


def _run(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    """Run `flowctl <args...>` and return parsed JSON (success path).

    On an expected non-zero exit, returns {"_stdout": ..., "_stderr": ...}.
    """
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
            f"unexpected rc={proc.returncode} (expected {expect_rc}): "
            f"stdout={proc.stdout.decode()} stderr={proc.stderr.decode()}"
        )
    if proc.returncode == 0 and "--json" in args:
        return json.loads(proc.stdout.decode())
    return {"_stdout": proc.stdout.decode(), "_stderr": proc.stderr.decode()}


def _entry_files(memory_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in memory_dir.rglob("*.md")
        if p.name not in ("README.md",) and "legacy" not in p.parts
    )


TITLE = "drift: web/login sub-1"


class TestMemoryUpsert(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.memory_dir = _init_repo(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _body(self, text: str) -> str:
        body = self.tmp / "body.md"
        body.write_text(text, encoding="utf-8")
        return str(body)

    def _upsert(self, *extra: str, expect_rc: int = 0) -> dict[str, Any]:
        return _run(
            self.tmp,
            "memory",
            "upsert",
            "--track",
            "knowledge",
            "--category",
            "workflow",
            "--title",
            TITLE,
            "--tags",
            "feature-map-drift",
            "--json",
            *extra,
            expect_rc=expect_rc,
        )

    def test_zero_matches_creates_with_json_shape(self) -> None:
        out = self._upsert("--body-file", self._body("Expected: a\nObserved: b\n"))
        self.assertEqual(out["action"], "created")
        self.assertIn("entry_id", out)
        self.assertTrue(Path(out["path"]).is_file())
        self.assertEqual(len(_entry_files(self.memory_dir)), 1)

    def test_one_match_updates_in_place(self) -> None:
        first = self._upsert("--body-file", self._body("v1"))
        second = self._upsert("--body-file", self._body("v2"))
        self.assertEqual(second["action"], "updated")
        self.assertEqual(second["entry_id"], first["entry_id"])
        self.assertEqual(len(_entry_files(self.memory_dir)), 1)
        self.assertIn("v2", Path(second["path"]).read_text(encoding="utf-8"))

    def test_ambiguous_fails_closed_listing_ids(self) -> None:
        # Two same-titled entries in the track (memory add sibling-suffixes
        # the second slug, so both files coexist with an identical title).
        for _ in range(2):
            _run(
                self.tmp,
                "memory",
                "add",
                "--track",
                "knowledge",
                "--category",
                "workflow",
                "--title",
                TITLE,
                "--no-overlap-check",
                "--body-file",
                self._body("dup"),
                "--json",
            )
        before = [(p, p.read_text(encoding="utf-8")) for p in _entry_files(self.memory_dir)]
        self.assertEqual(len(before), 2)
        out = self._upsert("--body-file", self._body("v3"), expect_rc=1)
        err = json.loads(out["_stdout"])
        self.assertFalse(err["success"])
        for path, _ in before:
            self.assertIn(path.stem, err["error"])
        # No write occurred: same files, same contents.
        after = [(p, p.read_text(encoding="utf-8")) for p in _entry_files(self.memory_dir)]
        self.assertEqual(before, after)

    def test_missing_title_errors(self) -> None:
        out = _run(
            self.tmp,
            "memory",
            "upsert",
            "--track",
            "knowledge",
            "--category",
            "workflow",
            "--json",
            expect_rc=2,
        )
        err = json.loads(out["_stdout"])
        self.assertIn("--title", err["error"])

    def test_missing_track_errors(self) -> None:
        out = _run(
            self.tmp,
            "memory",
            "upsert",
            "--category",
            "workflow",
            "--title",
            TITLE,
            "--json",
            expect_rc=2,
        )
        err = json.loads(out["_stdout"])
        self.assertIn("--track", err["error"])

    def test_cross_category_unique_match_updates(self) -> None:
        first = self._upsert("--body-file", self._body("v1"))
        # Same track + title, different category: the title-within-track
        # identity wins - the matched entry is updated in its own category.
        out = _run(
            self.tmp,
            "memory",
            "upsert",
            "--track",
            "knowledge",
            "--category",
            "best-practices",
            "--title",
            TITLE,
            "--body-file",
            self._body("v2"),
            "--json",
        )
        self.assertEqual(out["action"], "updated")
        self.assertEqual(out["entry_id"], first["entry_id"])
        self.assertEqual(len(_entry_files(self.memory_dir)), 1)

    def test_invalid_category_rejected_when_match_exists(self) -> None:
        # Regression (PR #385 review): a match used to overwrite args.category
        # before validation, so a typo'd --category silently succeeded when an
        # exact-title match existed. It must fail identically on both paths.
        first = self._upsert("--body-file", self._body("v1"))
        before = Path(first["path"]).read_text(encoding="utf-8")
        out = _run(
            self.tmp,
            "memory",
            "upsert",
            "--track",
            "knowledge",
            "--category",
            "not-a-category",
            "--title",
            TITLE,
            "--body-file",
            self._body("v2"),
            "--json",
            expect_rc=2,
        )
        err = json.loads(out["_stdout"])
        self.assertIn("not-a-category", err["error"])
        # No mutation of the matched entry.
        self.assertEqual(Path(first["path"]).read_text(encoding="utf-8"), before)

    def test_invalid_category_rejected_when_no_match(self) -> None:
        out = _run(
            self.tmp,
            "memory",
            "upsert",
            "--track",
            "knowledge",
            "--category",
            "not-a-category",
            "--title",
            TITLE,
            "--body-file",
            self._body("v1"),
            "--json",
            expect_rc=2,
        )
        err = json.loads(out["_stdout"])
        self.assertIn("not-a-category", err["error"])
        self.assertEqual(len(_entry_files(self.memory_dir)), 0)

    def test_overlong_title_rejected(self) -> None:
        long_title = "x" * 81
        out = _run(
            self.tmp,
            "memory",
            "upsert",
            "--track",
            "knowledge",
            "--category",
            "workflow",
            "--title",
            long_title,
            "--json",
            expect_rc=2,
        )
        err = json.loads(out["_stdout"])
        self.assertIn("80", err["error"])
        self.assertEqual(len(_entry_files(self.memory_dir)), 0)

    def test_non_json_output_is_one_line(self) -> None:
        for expected_verb in ("Created", "Updated"):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "memory",
                    "upsert",
                    "--track",
                    "knowledge",
                    "--category",
                    "workflow",
                    "--title",
                    TITLE,
                    "--tags",
                    "feature-map-drift",
                    "--body-file",
                    self._body(expected_verb),
                ],
                cwd=self.tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            lines = proc.stdout.decode().strip().splitlines()
            self.assertEqual(len(lines), 1, lines)
            self.assertTrue(lines[0].startswith(expected_verb), lines[0])

    def test_concurrent_upserts_serialize(self) -> None:
        # Two same-title upserts launched together: the scan-to-write lock
        # serializes them, so exactly one entry exists and both succeed
        # (one created, one updated - never sibling duplicates).
        def _spawn() -> subprocess.Popen:
            return subprocess.Popen(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "memory",
                    "upsert",
                    "--track",
                    "knowledge",
                    "--category",
                    "workflow",
                    "--title",
                    TITLE,
                    "--no-overlap-check",
                    "--body-file",
                    self._body("racer"),
                    "--json",
                ],
                cwd=self.tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        procs = [_spawn(), _spawn()]
        payloads = []
        for proc in procs:
            stdout, stderr = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0, stderr.decode())
            payloads.append(json.loads(stdout.decode()))
        self.assertEqual(len(_entry_files(self.memory_dir)), 1)
        self.assertEqual(len({p["entry_id"] for p in payloads}), 1)
        self.assertIn("created", [p["action"] for p in payloads])

    def test_stale_entry_is_matched_and_updated(self) -> None:
        first = self._upsert("--body-file", self._body("v1"))
        _run(
            self.tmp,
            "memory",
            "mark-stale",
            first["entry_id"],
            "--reason",
            "route moved",
            "--json",
        )
        second = self._upsert("--body-file", self._body("v2"))
        self.assertEqual(second["action"], "updated")
        self.assertEqual(second["entry_id"], first["entry_id"])
        self.assertEqual(len(_entry_files(self.memory_dir)), 1)


if __name__ == "__main__":
    unittest.main()

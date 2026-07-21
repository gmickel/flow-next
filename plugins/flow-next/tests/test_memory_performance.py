"""Deterministic read budgets and direct-ID safety for categorized memory.

fn-122.8 evidence: on this 24-entry fixture, pre-change exact-ID resolution
performed 48 entry reads (the full corpus, twice per entry); it now performs
one validated target read. Metadata/search enumeration moves from 2N to N
entry reads. Same live-repo ``memory list --status all --json`` benchmark,
five runs on 2026-07-21: pre median 0.19 s (0.19-0.20), post 0.19 s
(0.19-0.19), so startup-dominated wall time is stable while I/O halves.
"""

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


class TestMemoryReadBudgets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.memory = Path(self._tmp.name) / "memory"
        self.paths: list[Path] = []
        for index in range(24):
            path = (
                self.memory
                / "knowledge"
                / "conventions"
                / f"entry-{index:02d}-2026-07-21.md"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            flowctl.write_memory_entry(
                path,
                {
                    "title": f"Entry {index:02d}",
                    "date": "2026-07-21",
                    "track": "knowledge",
                    "category": "conventions",
                    "applies_when": "testing read budgets",
                },
                f"Body {index:02d}.\n",
            )
            self.paths.append(path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _count_reads(self):
        real_read = Path.read_text
        counts: Counter[str] = Counter()

        def counting_read(path, *args, **kwargs):
            counts[str(path)] += 1
            return real_read(path, *args, **kwargs)

        return mock.patch.object(Path, "read_text", counting_read), counts

    def test_metadata_and_search_iterations_read_each_entry_once(self) -> None:
        patcher, counts = self._count_reads()
        with patcher:
            metadata = flowctl._memory_iter_entries(self.memory)
        self.assertEqual(len(metadata), len(self.paths))
        self.assertTrue(all(entry["body"] == "" for entry in metadata))
        self.assertTrue(all(entry["raw"] == "" for entry in metadata))
        self.assertEqual({counts[str(path)] for path in self.paths}, {1})

        patcher, counts = self._count_reads()
        with patcher:
            searchable = flowctl._memory_iter_entries(
                self.memory, include_body=True
            )
        self.assertEqual(len(searchable), len(self.paths))
        self.assertTrue(all(entry["body"].startswith("Body") for entry in searchable))
        self.assertTrue(all(entry["raw"] == "" for entry in searchable))
        self.assertEqual({counts[str(path)] for path in self.paths}, {1})

    def test_full_id_reads_only_the_validated_target(self) -> None:
        target_id = "knowledge/conventions/entry-17-2026-07-21"
        patcher, counts = self._count_reads()
        with patcher:
            resolved = flowctl._memory_resolve_read_target(self.memory, target_id)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["entry"]["entry_id"], target_id)
        self.assertTrue(resolved["entry"]["body"].startswith("Body"))
        self.assertTrue(resolved["entry"]["raw"].startswith("---\n"))
        self.assertEqual(sum(counts.values()), 1)
        self.assertEqual(counts[str(self.paths[17])], 1)

    def test_ambiguous_slug_scan_is_one_read_each_plus_selected_target(self) -> None:
        patcher, counts = self._count_reads()
        with patcher:
            resolved = flowctl._memory_resolve_read_target(self.memory, "entry-17")
            self.assertIsNotNone(resolved)
            selected = Path(resolved["entry"]["path"])
            flowctl._memory_read_entry(selected)
        self.assertEqual(counts[str(selected)], 2)
        self.assertEqual(
            {counts[str(path)] for path in self.paths if path != selected}, {1}
        )

    def test_full_id_grammar_and_containment_reject_traversal_and_symlink(self) -> None:
        self.assertIsNone(
            flowctl._memory_resolve_read_target(
                self.memory, "knowledge/conventions/../secret-2026-07-21"
            )
        )
        outside = Path(self._tmp.name) / "outside-2026-07-21.md"
        outside.write_text(self.paths[0].read_text(encoding="utf-8"), encoding="utf-8")
        link = self.memory / "knowledge" / "conventions" / "linked-2026-07-21.md"
        link.symlink_to(outside)
        self.assertIsNone(
            flowctl._memory_resolve_read_target(
                self.memory, "knowledge/conventions/linked-2026-07-21"
            )
        )


if __name__ == "__main__":
    unittest.main()

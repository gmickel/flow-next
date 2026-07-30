"""Performance and semantic budgets for cognitive-aid diff materialization.

fn-122.7 benchmark evidence (2026-07-21, Apple M-series macOS, Python 3.14.2):
the same live fn-122 cognitive-aid export against ``origin/main``, five timed
runs per implementation. Pre-change commit 7d072cbf median 0.51 s (range
0.50-0.52); post-change median 0.38 s (range 0.38-0.38), 25.5% faster. The
deterministic budget below pins one unified-diff spawn/parse (previously two
spawns/four parses); glossary tests pin zero whole-tree enumerations and one
batched base-object process for any number of changed glossary candidates.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


class TestSharedUnifiedDiff(unittest.TestCase):
    DIFF = (
        "diff --git a/src/lib.py b/src/lib.py\n"
        "--- a/src/lib.py\n"
        "+++ b/src/lib.py\n"
        "@@ -1,2 +1,2 @@ def helper(value):\n"
        "-def helper(value):\n"
        "+def helper(value, default=None):\n"
        "diff --git a/pkg/index.ts b/pkg/index.ts\n"
        "--- /dev/null\n"
        "+++ b/pkg/index.ts\n"
        "@@ -0,0 +1,2 @@\n"
        "+export const ready = true\n"
        "+import { helper } from 'src/lib'\n"
    )

    def test_one_unified_spawn_and_one_parse_feed_all_analyses(self) -> None:
        calls: list[list[str]] = []

        def fake_git(args, cwd=None):
            del cwd
            calls.append(list(args))
            if args == ["rev-parse", "HEAD"]:
                return 0, "head-sha\n", ""
            if "--numstat" in args:
                return 0, "1\t1\tsrc/lib.py\n2\t0\tpkg/index.ts\n", ""
            if "--name-status" in args:
                return 0, "M\tsrc/lib.py\nA\tpkg/index.ts\n", ""
            if "--unified=0" in args:
                return 0, self.DIFF, ""
            self.fail(f"unexpected git call: {args}")

        real_parse = flowctl._export_parse_unified_diff
        with (
            mock.patch.object(flowctl, "_export_run_git", side_effect=fake_git),
            mock.patch.object(
                flowctl,
                "_export_parse_unified_diff",
                wraps=real_parse,
            ) as parse_mock,
        ):
            materialized = flowctl._export_materialize_diff("base", REPO_ROOT)
            summary = flowctl._export_diff_summary(
                "origin/main", "base", REPO_ROOT, materialized=materialized
            )
            refs = flowctl._export_removed_export_refs(
                "base",
                REPO_ROOT,
                unified_diff=materialized.events,
            )

        unified_calls = [c for c in calls if "--unified=0" in c]
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(unified_calls), 1)
        for call in calls[1:]:
            self.assertIn("-C", call)
            self.assertIn("--find-copies-harder", call)
        self.assertIn("--diff-filter=AMRDC", calls[1])
        self.assertEqual(parse_mock.call_count, 1)
        self.assertEqual(summary["files_changed"], 2)
        self.assertEqual(
            summary["public_exports_changed"],
            [{"file": "pkg/index.ts", "added": ["ready"], "removed": []}],
        )
        self.assertEqual(refs, [])  # same-path signature re-add is not removal

    def test_unchanged_source_copy_materializes_as_copy(self) -> None:
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t.co",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t.co",
            }
        )

        def git(repo: Path, *args: str) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q")
            source = repo / "src" / "original.txt"
            source.parent.mkdir()
            source.write_text("alpha\nbeta\n", encoding="utf-8")
            git(repo, "add", "src/original.txt")
            git(repo, "commit", "-qm", "base")
            base_sha = git(repo, "rev-parse", "HEAD")

            (repo / "src" / "copied.txt").write_bytes(source.read_bytes())
            git(repo, "add", "src/copied.txt")
            git(repo, "commit", "-qm", "copy")

            materialized = flowctl._export_materialize_diff(base_sha, repo)
            summary = flowctl._export_diff_summary(
                "HEAD^",
                base_sha,
                repo,
                materialized=materialized,
            )

        copied = summary["files"][0]
        self.assertEqual(copied["path"], "src/copied.txt")
        self.assertEqual(copied["status"], "C")
        self.assertEqual((copied["additions"], copied["deletions"]), (0, 0))

    def test_add_delete_rename_and_readd_blocks_are_byte_stable(self) -> None:
        diff = (
            "diff --git a/api/index.ts b/api/index.ts\n"
            "--- /dev/null\n"
            "+++ b/api/index.ts\n"
            "@@ -0,0 +1 @@\n"
            "+export const Added = 1\n"
            "diff --git a/old/__init__.py b/old/__init__.py\n"
            "--- a/old/__init__.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@ def Removed():\n"
            "-def Removed():\n"
            "diff --git a/src/old.py b/src/new.py\n"
            "similarity index 70%\n"
            "rename from src/old.py\n"
            "rename to src/new.py\n"
            "--- a/src/old.py\n"
            "+++ b/src/new.py\n"
            "@@ -1 +1 @@ def helper(x):\n"
            "-def helper(x):\n"
            "+def helper(x, y=0):\n"
        )
        events = flowctl._export_parse_unified_diff(diff)
        payload = {
            "changed_symbols": flowctl._export_changed_symbols(events),
            "public_exports": flowctl._export_detect_public_exports(events),
            "removed_symbols": flowctl._export_extract_removed_symbols(events),
        }
        expected = {
            "changed_symbols": {
                "api/index.ts": [],
                "old/__init__.py": ["def Removed():"],
                "src/new.py": ["def helper(x):"],
            },
            "public_exports": [
                {"file": "api/index.ts", "added": ["Added"], "removed": []},
                {
                    "file": "old/__init__.py",
                    "added": [],
                    "removed": ["Removed"],
                },
            ],
            "removed_symbols": {"Removed": "old/__init__.py"},
        }
        # Empty-context hunks do not create a changed_symbols entry.
        expected["changed_symbols"].pop("api/index.ts")
        self.assertEqual(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            json.dumps(expected, sort_keys=True, separators=(",", ":")),
        )

    def test_root_level_numstat_rename_uses_destination_and_rename_status(
        self,
    ) -> None:
        materialized = flowctl._ExportDiffMaterialization(
            head_sha="head-sha",
            numstat_rc=0,
            numstat="2\t1\told.txt => new.txt\n",
            name_status_rc=0,
            name_status="R100\told.txt\tnew.txt\n",
            unified_rc=0,
            events=(),
        )

        summary = flowctl._export_diff_summary(
            "origin/main",
            "base-sha",
            REPO_ROOT,
            materialized=materialized,
        )

        self.assertEqual(
            summary["files"],
            [
                {
                    "path": "new.txt",
                    "status": "R",
                    "additions": 2,
                    "deletions": 1,
                    "module": "<root>",
                    "changed_symbols": [],
                    "derived": {"kind": "none", "source": None},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()

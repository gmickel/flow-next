"""Tests for the fn-86 deterministic traceability slice in
`flowctl spec export-cognitive-aid` — the four additive payload fields that
back fn-93's "Review plan" render with data:

  * R1  `diff_summary.files[].changed_symbols` — hunk-header function context
  * R2  `diff_summary.files[].derived`         — mirror/dual-copy/state class
  * R3  `removed_export_refs`                  — deleted symbols still referenced
  * R4  `tasks[].evidence.files`              — surfaced verbatim

All four are deterministic and reproducible from repo state — no LLM judgment.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402  (path-injected import)


def _git(cwd: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.co",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.co",
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


# --------------------------------------------------------------------------
# R1 — changed_symbols from hunk headers
# --------------------------------------------------------------------------
class TestChangedSymbols(unittest.TestCase):
    def test_extracts_function_context_per_file(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n"
            "--- a/m.py\n"
            "+++ b/m.py\n"
            "@@ -2,0 +3 @@ def alpha():\n"
            "+    x += 10\n"
            "@@ -8,1 +9,1 @@ def beta():\n"
            "-    y = 2\n"
            "+    y = 3\n"
        )
        self.assertEqual(
            flowctl._export_changed_symbols(diff),
            {"m.py": ["def alpha():", "def beta():"]},
        )

    def test_dedupes_repeated_context(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n"
            "--- a/m.py\n"
            "+++ b/m.py\n"
            "@@ -2,0 +3 @@ def alpha():\n"
            "+    a = 1\n"
            "@@ -5,0 +7 @@ def alpha():\n"
            "+    b = 2\n"
        )
        self.assertEqual(
            flowctl._export_changed_symbols(diff), {"m.py": ["def alpha():"]}
        )

    def test_no_detectable_context_yields_no_entry(self) -> None:
        # A hunk header with empty context (git couldn't detect a function).
        diff = (
            "diff --git a/n.md b/n.md\n"
            "--- a/n.md\n"
            "+++ b/n.md\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new\n"
        )
        # Caller does `.get(path, [])`; the map simply has no entry.
        self.assertEqual(flowctl._export_changed_symbols(diff), {})

    def test_deleted_file_anchors_under_old_path(self) -> None:
        diff = (
            "diff --git a/gone.py b/gone.py\n"
            "--- a/gone.py\n"
            "+++ /dev/null\n"
            "@@ -1,2 +0,0 @@ def doomed():\n"
            "-    return 1\n"
        )
        self.assertEqual(
            flowctl._export_changed_symbols(diff), {"gone.py": ["def doomed():"]}
        )

    def test_empty_diff(self) -> None:
        self.assertEqual(flowctl._export_changed_symbols(""), {})


# --------------------------------------------------------------------------
# R2 — derived classification
# --------------------------------------------------------------------------
class TestDerivedClassification(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.rules = flowctl._EXPORT_DEFAULT_DERIVED_PATHS

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, content: bytes) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)

    def test_dual_copy_identical_is_derived(self) -> None:
        body = b"print('hi')\n"
        self._write("plugins/flow-next/scripts/flowctl.py", body)
        self._write(".flow/bin/flowctl.py", body)
        got = flowctl._export_classify_derived(
            ".flow/bin/flowctl.py", self.rules, self.root
        )
        self.assertEqual(
            got,
            {"kind": "dual-copy", "source": "plugins/flow-next/scripts/flowctl.py"},
        )

    def test_dual_copy_drifted_is_not_derived(self) -> None:
        self._write("plugins/flow-next/scripts/flowctl.py", b"print('a')\n")
        self._write(".flow/bin/flowctl.py", b"print('DRIFTED')\n")
        got = flowctl._export_classify_derived(
            ".flow/bin/flowctl.py", self.rules, self.root
        )
        # Drift is a REAL review item, not safe-to-skim.
        self.assertEqual(got, {"kind": "none", "source": None})

    def test_dual_copy_missing_source_is_not_derived(self) -> None:
        self._write(".flow/bin/flowctl.py", b"print('a')\n")
        got = flowctl._export_classify_derived(
            ".flow/bin/flowctl.py", self.rules, self.root
        )
        self.assertEqual(got, {"kind": "none", "source": None})

    def test_mirror_prefix(self) -> None:
        got = flowctl._export_classify_derived(
            "plugins/flow-next/codex/skills/x.md", self.rules, self.root
        )
        self.assertEqual(got["kind"], "mirror")
        self.assertTrue(got["source"])

    def test_state_prefix(self) -> None:
        got = flowctl._export_classify_derived(
            ".flow/specs/fn-1.md", self.rules, self.root
        )
        self.assertEqual(got, {"kind": "state", "source": None})

    def test_plain_source_is_none(self) -> None:
        got = flowctl._export_classify_derived(
            "plugins/flow-next/scripts/flowctl.py", self.rules, self.root
        )
        self.assertEqual(got, {"kind": "none", "source": None})

    def test_config_override_replaces_default(self) -> None:
        rules = {"mirror": [{"prefix": "gen/", "source": "codegen"}]}
        self.assertEqual(
            flowctl._export_classify_derived("gen/out.ts", rules, self.root),
            {"kind": "mirror", "source": "codegen"},
        )
        # The default flow-next shapes no longer apply under an override.
        self.assertEqual(
            flowctl._export_classify_derived(".flow/specs/x.md", rules, self.root),
            {"kind": "none", "source": None},
        )


# --------------------------------------------------------------------------
# R3 — removed_export_refs
# --------------------------------------------------------------------------
class TestRemovedSymbolExtraction(unittest.TestCase):
    def test_python_defs_and_classes(self) -> None:
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,3 +1,0 @@\n"
            "-def gone_fn(x):\n"
            "-    return x\n"
            "-class GoneClass:\n"
        )
        self.assertEqual(
            flowctl._export_extract_removed_symbols(diff),
            {"gone_fn": "a.py", "GoneClass": "a.py"},
        )

    def test_ignores_non_source_files(self) -> None:
        diff = (
            "diff --git a/README.md b/README.md\n"
            "--- a/README.md\n"
            "+++ b/README.md\n"
            "@@ -1,1 +1,0 @@\n"
            "-def looks_like_code(): but markdown\n"
        )
        self.assertEqual(flowctl._export_extract_removed_symbols(diff), {})

    def test_added_only_extracts_nothing(self) -> None:
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -0,0 +1,1 @@\n"
            "+def brand_new():\n"
        )
        self.assertEqual(flowctl._export_extract_removed_symbols(diff), {})


class TestRemovedExportRefsGit(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _commit(self, msg: str) -> str:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", msg)
        return _git(self.root, "rev-parse", "HEAD").strip()

    def _write(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def test_removed_and_referenced(self) -> None:
        self._write("lib.py", "def removed_fn(x):\n    return x\n")
        self._write("use.py", "from lib import removed_fn\nremoved_fn(1)\n")
        base = self._commit("base")
        # Remove the definition; the reference in use.py survives.
        self._write("lib.py", "def other():\n    return 0\n")
        self._commit("remove removed_fn")
        refs = flowctl._export_removed_export_refs(
            base, self.root, [{"path": "lib.py"}, {"path": "use.py"}]
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["symbol"], "removed_fn")
        self.assertEqual(refs[0]["defined_in"], "lib.py")
        ref_paths = {r["path"] for r in refs[0]["refs"]}
        self.assertIn("use.py", ref_paths)

    def test_removed_and_unreferenced_is_clean(self) -> None:
        self._write("lib.py", "def solo_fn(x):\n    return x\n")
        base = self._commit("base")
        self._write("lib.py", "def other():\n    return 0\n")
        self._commit("remove solo_fn")
        refs = flowctl._export_removed_export_refs(
            base, self.root, [{"path": "lib.py"}]
        )
        self.assertEqual(refs, [])

    def test_added_only_is_clean(self) -> None:
        self._write("lib.py", "def existing():\n    return 1\n")
        base = self._commit("base")
        self._write("lib.py", "def existing():\n    return 1\n\n\ndef added():\n    return 2\n")
        self._commit("add function")
        refs = flowctl._export_removed_export_refs(
            base, self.root, [{"path": "lib.py"}]
        )
        self.assertEqual(refs, [])


# --------------------------------------------------------------------------
# R4 — tasks[].evidence.files surfacing
# --------------------------------------------------------------------------
class TestEvidenceBlock(unittest.TestCase):
    def test_surfaces_files_alongside_existing_keys(self) -> None:
        got = flowctl._export_task_evidence_block(
            {
                "commits": ["c1", "c2"],
                "tests": ["pytest"],
                "files_touched": ["x.py"],
                "files": ["a.py", "b.py"],
            }
        )
        self.assertEqual(
            got,
            {
                "commits": ["c1", "c2"],
                "tests": ["pytest"],
                "files_touched": ["x.py"],
                "files": ["a.py", "b.py"],
            },
        )

    def test_absent_files_key_is_empty_list(self) -> None:
        got = flowctl._export_task_evidence_block({"commits": ["c1"]})
        self.assertEqual(got["files"], [])
        self.assertEqual(got["commits"], ["c1"])

    def test_string_coercion_and_falsy_drop(self) -> None:
        got = flowctl._export_task_evidence_block(
            {"files": ["a.py", "", None, "b.py"]}
        )
        self.assertEqual(got["files"], ["a.py", "b.py"])


class TestRemovedRefsCrossExtension(RemovedExportRefsBase if 'RemovedExportRefsBase' in dir() else unittest.TestCase):
    """PR #205 review: a symbol removed from one extension but referenced from a
    SIBLING extension (.ts removal, .tsx caller) must still be caught — the
    grep pathspec covers all known source extensions, not diff-touched only."""

    def test_ts_removal_tsx_reference_found(self):
        import subprocess, tempfile
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as d:
            root = _P(d)
            subprocess.run(["git", "init", "-q"], cwd=d, check=True, capture_output=True)
            (root / "lib.ts").write_text("export function helper() {}\n")
            (root / "view.tsx").write_text("import { helper } from './lib';\nhelper();\n")
            subprocess.run(["git", "add", "-A"], cwd=d, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-qm", "base"], cwd=d, check=True, capture_output=True)
            base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, check=True,
                                  capture_output=True, text=True).stdout.strip()
            (root / "lib.ts").write_text("")  # symbol removed
            subprocess.run(["git", "add", "-A"], cwd=d, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-qm", "remove"], cwd=d, check=True, capture_output=True)
            files = [{"path": "lib.ts"}]  # diff touched ONLY .ts
            refs = flowctl._export_removed_export_refs(base, root, files)
            hits = [r for r in refs if r["symbol"] == "helper"]
            self.assertTrue(hits, "cross-extension .tsx reference must be found")
            self.assertTrue(any(x["path"] == "view.tsx" for x in hits[0]["refs"]))

if __name__ == "__main__":
    unittest.main()

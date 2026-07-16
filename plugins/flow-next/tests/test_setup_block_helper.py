"""Fixture coverage for flowctl setup-block (fn-99, R3/R8/R12)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
TESTS_DIR = HERE.parent
PLUGIN_DIR = TESTS_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
TEMPLATES = PLUGIN_DIR / "skills" / "flow-next-setup" / "templates"


def _hash(content: str) -> str:
    return hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()


class SetupBlockFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / ".flow").mkdir()
        self.meta_path = self.repo / ".flow" / "meta.json"
        self.meta_path.write_text(
            json.dumps({"next_spec": 1, "schema_version": 3}), encoding="utf-8"
        )
        self.v1 = self.repo / "v1.md"
        self.v2 = self.repo / "v2.md"
        self.v1.write_text("<!-- BEGIN FLOW-NEXT -->\nv1\n<!-- END FLOW-NEXT -->\n", encoding="utf-8")
        self.v2.write_text("<!-- BEGIN FLOW-NEXT -->\nv2\n<!-- END FLOW-NEXT -->\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _flowctl(self, command: str, target: str, template: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "setup-block",
                command,
                "--file",
                target,
                "--template",
                str(template),
                *extra,
                "--json",
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def _result(self, proc: subprocess.CompletedProcess) -> dict:
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        return json.loads(proc.stdout)

    def _meta(self) -> dict:
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def test_fresh_install_and_independent_targets(self) -> None:
        claude = self.repo / "CLAUDE.md"
        claude.write_text("Existing prose.\n", encoding="utf-8")
        result = self._result(self._flowctl("apply", "CLAUDE.md", TEMPLATES / "claude-md-snippet.md"))
        canonical = (TEMPLATES / "claude-md-snippet.md").read_text(encoding="utf-8")
        self.assertEqual(result["action"], "appended")
        self.assertEqual(claude.read_text(encoding="utf-8"), "Existing prose.\n\n" + canonical)
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"], _hash(canonical))

        agents = self.repo / "AGENTS.md"
        self._result(self._flowctl("apply", "AGENTS.md", TEMPLATES / "agents-md-snippet.md"))
        hashes = self._meta()["setup"]["block_hashes"]
        self.assertEqual(set(hashes), {"CLAUDE.md", "AGENTS.md"})
        self.assertNotEqual(hashes["CLAUDE.md"], hashes["AGENTS.md"])

    def test_pristine_refresh_and_idempotent_rerun(self) -> None:
        target = self.repo / "CLAUDE.md"
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write("above\r\n")
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        with open(target, "a", encoding="utf-8", newline="") as f:
            f.write("below\r\n")
        before = target.read_bytes()
        outside_before = before.replace(self.v1.read_bytes(), b"")

        refreshed = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual(refreshed["action"], "refreshed")
        after = target.read_bytes()
        self.assertEqual(after.replace(self.v2.read_bytes(), b""), outside_before)
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"], _hash(self.v2.read_text()))

        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        mtime_before = target.stat().st_mtime_ns
        unchanged = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual(unchanged["action"], "unchanged")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(target.stat().st_mtime_ns, mtime_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_customized_block_overwrite_preserves_outside_content(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("top\n", encoding="utf-8")
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        with open(target, "a", encoding="utf-8") as f:
            f.write("bottom\n")
        target.write_text(target.read_text(encoding="utf-8").replace("v1", "mine"), encoding="utf-8")
        asked = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual((asked["action"], asked["reason"]), ("ask", "customized"))
        overwritten = self._result(self._flowctl("resolve", "CLAUDE.md", self.v2, "--choice", "overwrite"))
        self.assertEqual(overwritten["action"], "overwritten")
        self.assertEqual(target.read_text(encoding="utf-8"), "top\n\n" + self.v2.read_text() + "bottom\n")
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"], _hash(self.v2.read_text()))

    def test_hash_absent_keep_never_reasks(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("before\n<!-- BEGIN FLOW-NEXT -->\nmine\n<!-- END FLOW-NEXT -->\nafter\n", encoding="utf-8")
        original = target.read_bytes()
        asked = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        self.assertEqual((asked["action"], asked["reason"]), ("ask", "hash-absent"))
        kept = self._result(self._flowctl("resolve", "CLAUDE.md", self.v1, "--choice", "keep"))
        self.assertEqual(kept["action"], "kept")
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"], "customized")
        rerun = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        self.assertEqual(rerun["action"], "kept")
        self.assertEqual(target.read_bytes(), original)

    def test_customized_keep_from_recorded_hash_sets_sentinel_and_never_reasks(self) -> None:
        # R12: the recorded-hash -> customized -> Keep -> sentinel transition
        # (distinct from the hash-absent Keep path already covered).
        target = self.repo / "CLAUDE.md"
        target.write_text("top\n", encoding="utf-8")
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))  # records v1 pristine hash
        # User edits inside the markers AFTER a pristine install: current now
        # differs from both the recorded hash and the new canonical.
        target.write_text(target.read_text(encoding="utf-8").replace("v1", "mine"), encoding="utf-8")
        edited = target.read_bytes()
        asked = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual((asked["action"], asked["reason"]), ("ask", "customized"))
        kept = self._result(self._flowctl("resolve", "CLAUDE.md", self.v2, "--choice", "keep"))
        self.assertEqual(kept["action"], "kept")
        self.assertEqual(target.read_bytes(), edited)  # bytes unchanged
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"], "customized")
        rerun = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual(rerun["action"], "kept")  # sentinel: never re-asks
        self.assertEqual(target.read_bytes(), edited)

    @unittest.skipIf(os.name == "nt", "POSIX symlinks required")
    def test_symlinked_instruction_file_is_rejected_without_touching_referent(self) -> None:
        # Major finding: a symlinked CLAUDE.md->AGENTS.md must NOT be followed;
        # its logical key must stay independent and the referent untouched.
        agents = self.repo / "AGENTS.md"
        agents.write_text(self.v1.read_text(encoding="utf-8"), encoding="utf-8")
        self._result(self._flowctl("apply", "AGENTS.md", self.v1))  # records AGENTS.md hash
        agents_before = agents.read_bytes()
        (self.repo / "CLAUDE.md").symlink_to("AGENTS.md")
        rejected = self._flowctl("apply", "CLAUDE.md", self.v2)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("symlink", (rejected.stdout + rejected.stderr).lower())
        self.assertEqual(agents.read_bytes(), agents_before)  # referent untouched
        # Key never collapsed onto the referent.
        self.assertNotIn("CLAUDE.md", self._meta()["setup"]["block_hashes"])

    def test_malformed_setup_metadata_repairs_on_overwrite(self) -> None:
        target = self.repo / "CLAUDE.md"
        for malformed in ({"block_hashes": "bad"}, ["bad"]):
            with self.subTest(malformed=malformed):
                target.write_text("<!-- BEGIN FLOW-NEXT -->\nmine\n<!-- END FLOW-NEXT -->\n", encoding="utf-8")
                self.meta_path.write_text(json.dumps({"next_spec": 1, "schema_version": 3, "setup": malformed}), encoding="utf-8")
                asked = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
                self.assertEqual((asked["action"], asked["reason"]), ("ask", "hash-absent"))
                self._result(self._flowctl("resolve", "CLAUDE.md", self.v1, "--choice", "overwrite"))
                meta = self._meta()
                self.assertEqual((meta["next_spec"], meta["schema_version"]), (1, 3))
                self.assertIsInstance(meta["setup"]["block_hashes"], dict)

    @unittest.skipIf(os.name == "nt", "POSIX directory permissions required")
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root ignores directory write permissions")
    def test_failed_target_write_leaves_hash_unchanged(self) -> None:
        locked = self.repo / "locked"
        locked.mkdir()
        target = locked / "CLAUDE.md"
        target.write_text(self.v1.read_text(encoding="utf-8"), encoding="utf-8")
        self._result(self._flowctl("apply", "locked/CLAUDE.md", self.v1))
        hash_before = self._meta()["setup"]["block_hashes"]["locked/CLAUDE.md"]
        locked.chmod(0o500)
        try:
            failed = self._flowctl("apply", "locked/CLAUDE.md", self.v2)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(self._meta()["setup"]["block_hashes"]["locked/CLAUDE.md"], hash_before)
        finally:
            locked.chmod(stat.S_IRWXU)

    def test_non_standalone_markers_are_rejected_without_writes(self) -> None:
        target = self.repo / "CLAUDE.md"
        for content in (
            "prose <!-- BEGIN FLOW-NEXT -->\nbody\n<!-- END FLOW-NEXT -->\n",
            "<!-- BEGIN FLOW-NEXT -->\nbody\n<!-- END FLOW-NEXT --> suffix\n",
            "leading <!-- END FLOW-NEXT -->\n",
        ):
            with self.subTest(content=content):
                target.write_text(content, encoding="utf-8")
                before = target.read_bytes()
                meta_before = self.meta_path.read_bytes()
                rejected = self._flowctl("apply", "CLAUDE.md", self.v1)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn("marker must be on its own line", rejected.stdout + rejected.stderr)
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_duplicate_marker_pairs_replace_first_block_only(self) -> None:
        target = self.repo / "CLAUDE.md"
        second = "<!-- BEGIN FLOW-NEXT -->\nsecond\n<!-- END FLOW-NEXT -->\n"
        target.write_text(self.v1.read_text(encoding="utf-8") + "middle\n" + second, encoding="utf-8")
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))  # records v1 hash
        refreshed = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual(refreshed["action"], "refreshed")
        self.assertEqual(
            target.read_text(encoding="utf-8"),
            self.v2.read_text(encoding="utf-8") + "middle\n" + second,
        )

    @unittest.skipIf(os.name == "nt", "POSIX permission bits required")
    def test_write_preserves_existing_mode_and_umask_for_new_files(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text(self.v1.read_text(encoding="utf-8"), encoding="utf-8")
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        target.chmod(0o640)
        refreshed = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual(refreshed["action"], "refreshed")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

        fresh = self.repo / "AGENTS.md"
        self._result(self._flowctl("apply", "AGENTS.md", self.v2))
        umask = os.umask(0)
        os.umask(umask)
        self.assertEqual(stat.S_IMODE(fresh.stat().st_mode), 0o666 & ~umask)

    def test_missing_meta_and_corrupt_block_do_not_write(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("prose\n", encoding="utf-8")
        self.meta_path.unlink()
        missing = self._flowctl("apply", "CLAUDE.md", self.v1)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("meta.json missing - run flowctl init first", missing.stdout + missing.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "prose\n")

        self.meta_path.write_text(json.dumps({"next_spec": 1, "schema_version": 3}), encoding="utf-8")
        target.write_text("<!-- BEGIN FLOW-NEXT -->\nno end\n", encoding="utf-8")
        target_before = target.read_bytes()
        meta_before = self.meta_path.read_bytes()
        corrupt = self._flowctl("apply", "CLAUDE.md", self.v1)
        self.assertNotEqual(corrupt.returncode, 0)
        self.assertEqual(target.read_bytes(), target_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)


if __name__ == "__main__":
    unittest.main()

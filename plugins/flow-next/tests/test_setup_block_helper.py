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
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"]["FLOW-NEXT"], _hash(canonical))

        self._result(self._flowctl("apply", "AGENTS.md", TEMPLATES / "agents-md-snippet.md"))
        hashes = self._meta()["setup"]["block_hashes"]
        self.assertEqual(set(hashes), {"CLAUDE.md", "AGENTS.md"})
        self.assertNotEqual(hashes["CLAUDE.md"]["FLOW-NEXT"], hashes["AGENTS.md"]["FLOW-NEXT"])

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
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"]["FLOW-NEXT"], _hash(self.v2.read_text()))

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
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"]["FLOW-NEXT"], _hash(self.v2.read_text()))

    def test_hash_absent_keep_never_reasks(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("before\n<!-- BEGIN FLOW-NEXT -->\nmine\n<!-- END FLOW-NEXT -->\nafter\n", encoding="utf-8")
        original = target.read_bytes()
        asked = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        self.assertEqual((asked["action"], asked["reason"]), ("ask", "hash-absent"))
        kept = self._result(self._flowctl("resolve", "CLAUDE.md", self.v1, "--choice", "keep"))
        self.assertEqual(kept["action"], "kept")
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"]["FLOW-NEXT"], "customized")
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
        self.assertEqual(self._meta()["setup"]["block_hashes"]["CLAUDE.md"]["FLOW-NEXT"], "customized")
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
        hash_before = self._meta()["setup"]["block_hashes"]["locked/CLAUDE.md"]["FLOW-NEXT"]
        locked.chmod(0o500)
        try:
            failed = self._flowctl("apply", "locked/CLAUDE.md", self.v2)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(
                self._meta()["setup"]["block_hashes"]["locked/CLAUDE.md"]["FLOW-NEXT"],
                hash_before,
            )
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

    def test_invalid_ids_rejected_before_any_file_touch(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("prose\n", encoding="utf-8")
        target_before = target.read_bytes()
        meta_before = self.meta_path.read_bytes()
        invalid_ids = (
            "",
            "x" * 65,
            "lowercase",
            "_LEADING",
            "HAS--DASHES",
            ".DOTSTART",
        )
        for bad_id in invalid_ids:
            for command, extra in (
                ("apply", ()),
                ("resolve", ("--choice", "overwrite")),
                ("check", ()),
            ):
                with self.subTest(command=command, bad_id=bad_id):
                    rejected = self._flowctl(
                        command, "CLAUDE.md", self.v1, *extra, "--id", bad_id
                    )
                    self.assertEqual(rejected.returncode, 1, rejected.stderr + rejected.stdout)
                    self.assertNotEqual(rejected.returncode, 2)
                    self.assertIn("invalid setup-block id", rejected.stdout + rejected.stderr)
                    self.assertEqual(target.read_bytes(), target_before)
                    self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_explicit_flow_next_id_matches_omitted(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("top\n", encoding="utf-8")
        omitted = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        after_omitted = target.read_bytes()
        meta_omitted = self.meta_path.read_bytes()
        hashes = self._meta()["setup"]["block_hashes"]["CLAUDE.md"]
        self.assertEqual(set(hashes), {"FLOW-NEXT"})
        self.assertEqual(hashes["FLOW-NEXT"], _hash(self.v1.read_text()))

        # Reset and apply with explicit --id FLOW-NEXT.
        target.write_text("top\n", encoding="utf-8")
        self.meta_path.write_text(
            json.dumps({"next_spec": 1, "schema_version": 3}), encoding="utf-8"
        )
        explicit = self._result(
            self._flowctl("apply", "CLAUDE.md", self.v1, "--id", "FLOW-NEXT")
        )
        self.assertEqual(explicit, omitted)
        self.assertEqual(target.read_bytes(), after_omitted)
        self.assertEqual(self.meta_path.read_bytes(), meta_omitted)
        self.assertEqual(
            set(self._meta()["setup"]["block_hashes"]["CLAUDE.md"]), {"FLOW-NEXT"}
        )

    def test_two_ids_on_one_file_tracked_independently(self) -> None:
        deploy_tmpl = self.repo / "deploy.md"
        flow_tmpl = self.repo / "flow.md"
        deploy_tmpl.write_text(
            "<!-- BEGIN DEPLOY -->\ndeploy-v1\n<!-- END DEPLOY -->\n", encoding="utf-8"
        )
        flow_tmpl.write_text(
            "<!-- BEGIN FLOW-NEXT -->\nflow-v1\n<!-- END FLOW-NEXT -->\n", encoding="utf-8"
        )
        target = self.repo / "CLAUDE.md"
        target.write_text("header\n", encoding="utf-8")

        self._result(self._flowctl("apply", "CLAUDE.md", flow_tmpl))
        self._result(self._flowctl("apply", "CLAUDE.md", deploy_tmpl, "--id", "DEPLOY"))
        text = target.read_text(encoding="utf-8")
        self.assertIn("<!-- BEGIN FLOW-NEXT -->\nflow-v1\n<!-- END FLOW-NEXT -->", text)
        self.assertIn("<!-- BEGIN DEPLOY -->\ndeploy-v1\n<!-- END DEPLOY -->", text)
        path_hashes = self._meta()["setup"]["block_hashes"]["CLAUDE.md"]
        self.assertEqual(set(path_hashes), {"FLOW-NEXT", "DEPLOY"})
        self.assertEqual(path_hashes["FLOW-NEXT"], _hash(flow_tmpl.read_text()))
        self.assertEqual(path_hashes["DEPLOY"], _hash(deploy_tmpl.read_text()))

        flow_v2 = self.repo / "flow-v2.md"
        flow_v2.write_text(
            "<!-- BEGIN FLOW-NEXT -->\nflow-v2\n<!-- END FLOW-NEXT -->\n", encoding="utf-8"
        )
        before_deploy = "<!-- BEGIN DEPLOY -->\ndeploy-v1\n<!-- END DEPLOY -->"
        refreshed = self._result(self._flowctl("apply", "CLAUDE.md", flow_v2))
        self.assertEqual(refreshed["action"], "refreshed")
        after = target.read_text(encoding="utf-8")
        self.assertIn("<!-- BEGIN FLOW-NEXT -->\nflow-v2\n<!-- END FLOW-NEXT -->", after)
        self.assertIn(before_deploy, after)
        self.assertEqual(
            self._meta()["setup"]["block_hashes"]["CLAUDE.md"]["DEPLOY"],
            _hash(deploy_tmpl.read_text()),
        )

    def test_stray_other_id_marker_is_opaque_and_scoped_fail_close(self) -> None:
        a_tmpl = self.repo / "a.md"
        a_tmpl.write_text(
            "<!-- BEGIN A -->\na-body\n<!-- END A -->\n", encoding="utf-8"
        )
        b_tmpl = self.repo / "b.md"
        b_tmpl.write_text(
            "<!-- BEGIN B -->\nb-body\n<!-- END B -->\n", encoding="utf-8"
        )
        target = self.repo / "CLAUDE.md"
        # Valid A pair plus a stray unpaired BEGIN B (corrupt for B only).
        target.write_text(
            "<!-- BEGIN A -->\na-body\n<!-- END A -->\n"
            "<!-- BEGIN B -->\norphan\n",
            encoding="utf-8",
        )
        self._result(self._flowctl("apply", "CLAUDE.md", a_tmpl, "--id", "A"))
        # Refresh A while stray B remains — succeeds; B content byte-preserved.
        a_v2 = self.repo / "a-v2.md"
        a_v2.write_text("<!-- BEGIN A -->\na-v2\n<!-- END A -->\n", encoding="utf-8")
        refreshed = self._result(self._flowctl("apply", "CLAUDE.md", a_v2, "--id", "A"))
        self.assertEqual(refreshed["action"], "refreshed")
        after_a = target.read_text(encoding="utf-8")
        self.assertIn("<!-- BEGIN A -->\na-v2\n<!-- END A -->", after_a)
        self.assertIn("<!-- BEGIN B -->\norphan\n", after_a)

        # Operating B on the stray unpaired marker fails closed; A's span untouched.
        before_bytes = target.read_bytes()
        meta_before = self.meta_path.read_bytes()
        rejected = self._flowctl("apply", "CLAUDE.md", b_tmpl, "--id", "B")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("corrupt", (rejected.stdout + rejected.stderr).lower())
        self.assertEqual(target.read_bytes(), before_bytes)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)
        self.assertIn("<!-- BEGIN A -->\na-v2\n<!-- END A -->", after_a)

    def test_legacy_string_hash_tolerant_read_and_write_through_upgrade(self) -> None:
        target = self.repo / "CLAUDE.md"
        v1_text = self.v1.read_text(encoding="utf-8")
        target.write_text(v1_text, encoding="utf-8")
        legacy_hash = _hash(v1_text)
        self.meta_path.write_text(
            json.dumps(
                {
                    "next_spec": 1,
                    "schema_version": 3,
                    "setup": {"block_hashes": {"CLAUDE.md": legacy_hash}},
                }
            ),
            encoding="utf-8",
        )
        unchanged = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        self.assertEqual(unchanged["action"], "unchanged")
        # No write on matching hash — legacy string shape preserved.
        self.assertEqual(
            self._meta()["setup"]["block_hashes"]["CLAUDE.md"], legacy_hash
        )

        refreshed = self._result(self._flowctl("apply", "CLAUDE.md", self.v2))
        self.assertEqual(refreshed["action"], "refreshed")
        entry = self._meta()["setup"]["block_hashes"]["CLAUDE.md"]
        self.assertIsInstance(entry, dict)
        self.assertEqual(entry, {"FLOW-NEXT": _hash(self.v2.read_text())})

    def test_malformed_per_path_repair_preserves_sibling_entries(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text(
            "<!-- BEGIN FLOW-NEXT -->\nmine\n<!-- END FLOW-NEXT -->\n", encoding="utf-8"
        )
        legacy_hash = _hash(self.v1.read_text())
        nested_hash = _hash(self.v2.read_text())
        for malformed in (123, ["bad"], {"FLOW-NEXT": 99}):
            with self.subTest(malformed=malformed):
                target.write_text(
                    "<!-- BEGIN FLOW-NEXT -->\nmine\n<!-- END FLOW-NEXT -->\n",
                    encoding="utf-8",
                )
                self.meta_path.write_text(
                    json.dumps(
                        {
                            "next_spec": 1,
                            "schema_version": 3,
                            "setup": {
                                "block_hashes": {
                                    "LEGACY.md": legacy_hash,
                                    "NESTED.md": {"FLOW-NEXT": nested_hash},
                                    "CLAUDE.md": malformed,
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                asked = self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
                self.assertEqual((asked["action"], asked["reason"]), ("ask", "hash-absent"))
                self._result(
                    self._flowctl("resolve", "CLAUDE.md", self.v1, "--choice", "overwrite")
                )
                hashes = self._meta()["setup"]["block_hashes"]
                self.assertEqual(hashes["LEGACY.md"], legacy_hash)
                self.assertEqual(hashes["NESTED.md"], {"FLOW-NEXT": nested_hash})
                self.assertEqual(
                    hashes["CLAUDE.md"], {"FLOW-NEXT": _hash(self.v1.read_text())}
                )

    def test_template_id_consistency_rejects_missing_marker_pair(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("header\n", encoding="utf-8")
        target_before = target.read_bytes()
        meta_before = self.meta_path.read_bytes()
        # Template only has FLOW-NEXT; operating DEPLOY must fail closed.
        for command, extra in (
            ("apply", ()),
            ("resolve", ("--choice", "overwrite")),
        ):
            with self.subTest(command=command):
                rejected = self._flowctl(
                    command, "CLAUDE.md", self.v1, *extra, "--id", "DEPLOY"
                )
                self.assertEqual(rejected.returncode, 1)
                combined = rejected.stdout + rejected.stderr
                self.assertIn(
                    "template does not contain the marker pair for id DEPLOY",
                    combined,
                )
                self.assertEqual(target.read_bytes(), target_before)
                self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_template_id_consistency_rejects_duplicated_marker_pair(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("header\n", encoding="utf-8")
        target_before = target.read_bytes()
        meta_before = self.meta_path.read_bytes()
        # "Exactly one" upper bound: a template with TWO derived pairs for the
        # operated id is rejected the same as zero pairs.
        doubled = self.repo / "doubled-template.md"
        doubled.write_text(
            "<!-- BEGIN FLOW-NEXT -->\none\n<!-- END FLOW-NEXT -->\n"
            "<!-- BEGIN FLOW-NEXT -->\ntwo\n<!-- END FLOW-NEXT -->\n",
            encoding="utf-8",
        )
        rejected = self._flowctl("apply", "CLAUDE.md", str(doubled))
        self.assertEqual(rejected.returncode, 1)
        combined = rejected.stdout + rejected.stderr
        self.assertIn(
            "template does not contain the marker pair for id FLOW-NEXT",
            combined,
        )
        self.assertEqual(target.read_bytes(), target_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    # -- fn-171.2: read-only `check` verdict verb -----------------------

    def test_check_unchanged_pristine_exit_zero_and_writes_nothing(self) -> None:
        target = self.repo / "CLAUDE.md"
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        mtime_before = target.stat().st_mtime_ns
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["action"], "unchanged")
        self.assertNotIn("command", result)
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(target.stat().st_mtime_ns, mtime_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_byte_pristine_with_customized_sentinel_is_unchanged(self) -> None:
        # Byte-equality first, matching apply's order: a hand-reverted block
        # reads clean even though the sentinel is still on record.
        target = self.repo / "CLAUDE.md"
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        meta = self._meta()
        meta["setup"]["block_hashes"]["CLAUDE.md"]["FLOW-NEXT"] = "customized"
        self.meta_path.write_text(json.dumps(meta), encoding="utf-8")
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "unchanged")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_template_drift_exit_two_writes_nothing(self) -> None:
        target = self.repo / "CLAUDE.md"
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        mtime_before = target.stat().st_mtime_ns
        proc = self._flowctl("check", "CLAUDE.md", self.v2)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "template-drift")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(target.stat().st_mtime_ns, mtime_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_customized_exit_two_writes_nothing(self) -> None:
        target = self.repo / "CLAUDE.md"
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        target.write_text(
            target.read_text(encoding="utf-8").replace("v1", "mine"), encoding="utf-8"
        )
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "customized")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_customized_sentinel_with_real_drift_exit_two(self) -> None:
        target = self.repo / "CLAUDE.md"
        self._result(self._flowctl("apply", "CLAUDE.md", self.v1))
        target.write_text(
            target.read_text(encoding="utf-8").replace("v1", "mine"), encoding="utf-8"
        )
        self._result(self._flowctl("resolve", "CLAUDE.md", self.v1, "--choice", "keep"))
        # Sentinel now on record; hand-edit again so the block is not pristine.
        target.write_text(
            target.read_text(encoding="utf-8").replace("mine", "mine2"), encoding="utf-8"
        )
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual((result["action"], result["reason"]), ("customized", "customized-sentinel"))
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_hash_absent_exit_two_writes_nothing(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text(
            "<!-- BEGIN FLOW-NEXT -->\nmine\n<!-- END FLOW-NEXT -->\n", encoding="utf-8"
        )
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        mtime_before = target.stat().st_mtime_ns
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "hash-absent")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(target.stat().st_mtime_ns, mtime_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_missing_file_exit_three(self) -> None:
        meta_before = self.meta_path.read_bytes()
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "missing-file")
        self.assertFalse((self.repo / "CLAUDE.md").exists())
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_missing_markers_exit_three_writes_nothing(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("just prose, no markers\n", encoding="utf-8")
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "missing-markers")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_corrupt_unpaired_marker_exit_three_writes_nothing(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("<!-- BEGIN FLOW-NEXT -->\norphan\n", encoding="utf-8")
        meta_before = self.meta_path.read_bytes()
        bytes_before = target.read_bytes()
        proc = self._flowctl("check", "CLAUDE.md", self.v1)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["action"], "corrupt")
        self.assertEqual(target.read_bytes(), bytes_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_template_id_consistency_rejects_missing_marker_pair(self) -> None:
        target = self.repo / "CLAUDE.md"
        target.write_text("header\n", encoding="utf-8")
        target_before = target.read_bytes()
        meta_before = self.meta_path.read_bytes()
        rejected = self._flowctl("check", "CLAUDE.md", self.v1, "--id", "DEPLOY")
        self.assertEqual(rejected.returncode, 1)
        combined = rejected.stdout + rejected.stderr
        self.assertIn(
            "template does not contain the marker pair for id DEPLOY", combined
        )
        self.assertEqual(target.read_bytes(), target_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)

    def test_check_two_blocks_one_file_end_to_end(self) -> None:
        a_tmpl = self.repo / "a.md"
        a_tmpl.write_text("<!-- BEGIN A -->\na-body\n<!-- END A -->\n", encoding="utf-8")
        b_tmpl = self.repo / "b.md"
        b_tmpl.write_text("<!-- BEGIN B -->\nb-body\n<!-- END B -->\n", encoding="utf-8")
        target = self.repo / "CLAUDE.md"
        target.write_text("header\n", encoding="utf-8")
        self._result(self._flowctl("apply", "CLAUDE.md", a_tmpl, "--id", "A"))
        self._result(self._flowctl("apply", "CLAUDE.md", b_tmpl, "--id", "B"))

        # Hand-edit B only, inside its own span; A's span is untouched.
        text = target.read_text(encoding="utf-8").replace("b-body", "b-mine")
        target.write_text(text, encoding="utf-8")

        check_a = self._flowctl("check", "CLAUDE.md", a_tmpl, "--id", "A")
        self.assertEqual(check_a.returncode, 0, check_a.stdout + check_a.stderr)
        self.assertEqual(json.loads(check_a.stdout)["action"], "unchanged")

        check_b = self._flowctl("check", "CLAUDE.md", b_tmpl, "--id", "B")
        self.assertEqual(check_b.returncode, 2, check_b.stdout + check_b.stderr)
        self.assertEqual(json.loads(check_b.stdout)["action"], "customized")

    def test_check_mixed_line_endings_across_two_spans_preserve_bytes(self) -> None:
        # write_bytes throughout: write_text newline-translates on Windows,
        # which would turn every span CRLF before the fixture's deliberate
        # mixed-endings setup (windows-latest CI failure).
        a_tmpl = self.repo / "a.md"
        a_tmpl.write_bytes(b"<!-- BEGIN A -->\na-body\n<!-- END A -->\n")
        b_tmpl = self.repo / "b.md"
        b_tmpl.write_bytes(b"<!-- BEGIN B -->\nb-body\n<!-- END B -->\n")
        target = self.repo / "CLAUDE.md"
        target.write_bytes(b"header\n")
        self._result(self._flowctl("apply", "CLAUDE.md", a_tmpl, "--id", "A"))
        self._result(self._flowctl("apply", "CLAUDE.md", b_tmpl, "--id", "B"))

        # Convert ONLY B's span to CRLF; A's span and the rest of the file
        # stay LF. A CRLF-only diff must not read as drift for either id.
        content = target.read_bytes()
        b_span_lf = b"<!-- BEGIN B -->\nb-body\n<!-- END B -->"
        b_span_crlf = b"<!-- BEGIN B -->\r\nb-body\r\n<!-- END B -->"
        self.assertIn(b_span_lf, content)
        mixed = content.replace(b_span_lf, b_span_crlf)
        target.write_bytes(mixed)
        outside_b_before = mixed.replace(b_span_crlf, b"")

        meta_before = self.meta_path.read_bytes()
        check_a = self._flowctl("check", "CLAUDE.md", a_tmpl, "--id", "A")
        self.assertEqual(check_a.returncode, 0, check_a.stdout + check_a.stderr)
        self.assertEqual(json.loads(check_a.stdout)["action"], "unchanged")
        check_b = self._flowctl("check", "CLAUDE.md", b_tmpl, "--id", "B")
        self.assertEqual(check_b.returncode, 0, check_b.stdout + check_b.stderr)
        self.assertEqual(json.loads(check_b.stdout)["action"], "unchanged")

        self.assertEqual(target.read_bytes(), mixed)
        self.assertEqual(target.read_bytes().replace(b_span_crlf, b""), outside_b_before)
        self.assertEqual(self.meta_path.read_bytes(), meta_before)


if __name__ == "__main__":
    unittest.main()

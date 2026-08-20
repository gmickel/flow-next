"""flowctl_tracker distribution: manifest, installer verifier, runtime smoke,
bridge-inactive byte parity (fn-139.5).

Runs on every CI OS row, so the Windows `flowctl.cmd` leg of the packaging
smoke is exercised on windows-latest without a separate job.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PKG = ROOT / "scripts" / "flowctl_tracker"
MANIFEST = PKG / "MANIFEST.json"
VERIFIER = ROOT / "scripts" / "lib" / "verify_tracker_manifest.py"
GENERATOR = REPO / "scripts" / "gen_tracker_manifest.py"


def _hashes(root: Path) -> dict:
    return {
        f"flowctl_tracker/{p.relative_to(root).as_posix()}":
            hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.py"))
    }


class ManifestIsCurrent(unittest.TestCase):
    def test_manifest_enumerates_members_explicitly(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        paths = [f["path"] for f in manifest["files"]]
        self.assertIn("flowctl_tracker/executor.py", paths)
        self.assertIn("flowctl_tracker/providers/jira.py", paths)
        for entry in manifest["files"]:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_manifest_matches_the_shipped_tree(self) -> None:
        """Stale manifest = the sync step was skipped. This is the CI teeth."""
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        recorded = {f["path"]: f["sha256"] for f in manifest["files"]}
        expected = _hashes(PKG)
        # The manifest REPLACED the single-file SOURCE_SHA256 pin: it covers
        # flowctl.py itself alongside the package (fn-139.5 completion gap 3).
        expected["flowctl.py"] = hashlib.sha256(
            (ROOT / "scripts" / "flowctl.py").read_bytes()).hexdigest()
        self.assertEqual(recorded, expected,
                         "run scripts/gen_tracker_manifest.py")

    def test_generator_check_mode_agrees(self) -> None:
        out = subprocess.run([sys.executable, str(GENERATOR), "--check"],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_verifier_passes_against_the_shipped_tree(self) -> None:
        out = subprocess.run([sys.executable, str(VERIFIER), str(PKG.parent)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)


class InstallerVerifier(unittest.TestCase):
    def _staged(self, tmp: str) -> Path:
        dest = Path(tmp) / "scripts"
        shutil.copytree(PKG, dest / "flowctl_tracker",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "scripts" / "flowctl.py", dest / "flowctl.py")
        return dest

    def test_clean_copy_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run(
                [sys.executable, str(VERIFIER), str(self._staged(tmp))],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("verified", out.stdout)

    def test_corrupt_file_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = self._staged(tmp)
            (dest / "flowctl_tracker" / "executor.py").write_text(
                "tampered\n", encoding="utf-8")
            out = subprocess.run(
                [sys.executable, str(VERIFIER), str(dest)],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 1)
            self.assertIn("executor.py", out.stderr)
            self.assertIn("mismatch", out.stderr)

    def test_missing_file_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = self._staged(tmp)
            (dest / "flowctl_tracker" / "states.py").unlink()
            out = subprocess.run(
                [sys.executable, str(VERIFIER), str(dest)],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 1)
            self.assertIn("missing", out.stderr)

    def test_every_installer_invokes_the_shared_verifier(self) -> None:
        for rel in ("scripts/install-codex.sh", "scripts/install-cursor.sh",
                    "scripts/install-cursor.ps1", "scripts/install-opencode.sh"):
            with self.subTest(installer=rel):
                self.assertIn("verify_tracker_manifest",
                              (REPO / rel).read_text(encoding="utf-8"))
        # fn-197: setup copies nothing into a repo, so it has no package to
        # verify. ralph-init still stages its own copy and keeps the check.
        for rel in ("plugins/flow-next/skills/flow-next-ralph-init/SKILL.md",):
            with self.subTest(skill=rel):
                self.assertIn("verify_tracker_manifest",
                              (REPO / rel).read_text(encoding="utf-8"))


class RuntimeSmoke(unittest.TestCase):
    """The packaging smoke: the REAL launcher for this OS resolves the package.
    On windows-latest this exercises flowctl.cmd; elsewhere the bash launcher.

    `--help` is NOT sufficient - argparse exits before `cmd_tracker_resolve`
    ever imports the package, so a help run passes with no package installed
    at all (reproduced). The smoke therefore runs a REAL `tracker resolve` in
    an inactive temp repo: the inactive envelope (exit 3) is only reachable
    AFTER `flowctl_tracker.resolve_verb` imported successfully.
    """

    def _launcher(self, scripts_dir: Path) -> list:
        if os.name == "nt":  # pragma: no cover - the Windows CI row
            return ["cmd", "/c", str(scripts_dir / "flowctl.cmd")]
        return [str(scripts_dir / "flowctl")]

    def _temp_repo(self, tmp: str) -> Path:
        repo = Path(tmp) / "repo"
        (repo / ".flow").mkdir(parents=True)
        (repo / ".flow" / "config.json").write_text("{}\n", encoding="utf-8")
        (repo / ".flow" / "meta.json").write_text(
            '{"schema_version": 3, "next_spec": 1}\n', encoding="utf-8")
        return repo

    def test_real_resolve_reaches_the_package_through_the_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._temp_repo(tmp)
            out = subprocess.run(
                self._launcher(ROOT / "scripts") + ["tracker", "resolve"],
                capture_output=True, text=True, timeout=180, cwd=repo)
            self.assertEqual(out.returncode, 3, out.stderr)
            self.assertEqual(json.loads(out.stdout.strip())["class"], "inactive")

    def test_staged_layouts_import_the_package(self) -> None:
        """Every named-files runtime layout: flowctl.py + bootstrap + package
        copied flat (the shape Codex installs, the Cursor installers, and ralph all
        produce), with and without the package - absence must FAIL loudly."""
        for with_package in (True, False):
            with self.subTest(with_package=with_package), \
                    tempfile.TemporaryDirectory() as tmp:
                staged = Path(tmp) / "bin"
                staged.mkdir()
                for name in ("flowctl.py", "flowctl_bootstrap.py"):
                    shutil.copy2(ROOT / "scripts" / name, staged / name)
                if with_package:
                    shutil.copytree(PKG, staged / "flowctl_tracker",
                                    ignore=shutil.ignore_patterns("__pycache__"))
                repo = self._temp_repo(tmp)
                out = subprocess.run(
                    [sys.executable, str(staged / "flowctl.py"),
                     "tracker", "resolve"],
                    capture_output=True, text=True, timeout=180, cwd=repo)
                if with_package:
                    self.assertEqual(out.returncode, 3, out.stderr)
                    self.assertEqual(json.loads(out.stdout.strip())["class"],
                                     "inactive")
                else:
                    self.assertNotEqual(out.returncode, 0)
                    self.assertIn("flowctl_tracker",
                                  out.stderr + out.stdout,
                                  "the gap must be named, not a bare traceback")

    def test_help_still_works(self) -> None:
        out = subprocess.run(
            self._launcher(ROOT / "scripts") + ["tracker", "resolve", "--help"],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("--select", out.stdout)

    def test_no_per_command_hashing(self) -> None:
        """Rejected by design: verifying at every invocation to catch what
        installers already cover. flowctl.py must not read the manifest."""
        src = (ROOT / "scripts" / "flowctl.py").read_text(encoding="utf-8")
        self.assertNotIn("MANIFEST.json", src)

    def test_residual_marketplace_gap_is_documented(self) -> None:
        docs = (ROOT / "docs" / "platforms.md").read_text(encoding="utf-8")
        self.assertIn("Residual gap", docs)
        self.assertIn("ImportError", docs)


class BridgeInactiveByteParity(unittest.TestCase):
    """The single most load-bearing promise: a repo with no tracker configured
    behaves byte-for-byte the same whether or not the package is present."""

    def _run_install(self, with_package: bool) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            for name in ("flowctl.py", "flowctl_bootstrap.py"):
                shutil.copy2(ROOT / "scripts" / name, bin_dir / name)
            if with_package:
                shutil.copytree(PKG, bin_dir / "flowctl_tracker",
                                ignore=shutil.ignore_patterns("__pycache__"))
            repo = Path(tmp) / "repo"
            (repo / ".flow").mkdir(parents=True)
            (repo / ".flow" / "config.json").write_text("{}\n", encoding="utf-8")
            (repo / ".flow" / "meta.json").write_text(
                '{"schema_version": 3, "next_spec": 1}\n', encoding="utf-8")
            out = subprocess.run(
                [sys.executable, str(bin_dir / "flowctl.py"), "sync", "active", "--json"],
                capture_output=True, cwd=repo, timeout=180,
                env={**os.environ, "PYTHONHASHSEED": "0"})
            return {"stdout": out.stdout, "stderr": out.stderr, "rc": out.returncode}

    def test_sync_active_is_identical_with_and_without_the_package(self) -> None:
        without = self._run_install(with_package=False)
        with_pkg = self._run_install(with_package=True)
        self.assertEqual(without, with_pkg,
                         "the package's presence must be invisible on the "
                         "bridge-inactive path")


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(os.name == "nt", "installer scripts are bash; the guard logic "
                                  "is identical cross-platform")
class ExecutableInstallerFailClosed(unittest.TestCase):
    """Run the REAL cursor installer against a staged source tree - presence
    strings prove nothing about behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._stage = tempfile.TemporaryDirectory()
        root = Path(cls._stage.name) / "repo"
        (root / "plugins").mkdir(parents=True)
        shutil.copytree(REPO / "scripts", root / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(REPO / "plugins" / "flow-next", root / "plugins" / "flow-next",
                        ignore=shutil.ignore_patterns(
                            "tests", "codex", "__pycache__", "*.pyc"))
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stage.cleanup()

    def _run(self, source_root: Path) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as home:
            return subprocess.run(
                ["bash", str(source_root / "scripts" / "install-cursor.sh")],
                capture_output=True, text=True, timeout=300,
                env={**os.environ, "HOME": home})

    def test_clean_install_verifies(self) -> None:
        out = self._run(self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("verified", out.stdout + out.stderr)

    def test_absent_package_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "repo"
            shutil.copytree(self.root, mutated)
            shutil.rmtree(mutated / "plugins" / "flow-next" / "scripts"
                          / "flowctl_tracker")
            out = self._run(mutated)
            self.assertNotEqual(out.returncode, 0,
                                "a truncated source must not install successfully")

    def test_absent_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "repo"
            shutil.copytree(self.root, mutated)
            (mutated / "plugins" / "flow-next" / "scripts" / "flowctl_tracker"
             / "MANIFEST.json").unlink()
            out = self._run(mutated)
            self.assertNotEqual(out.returncode, 0)

    def test_tampered_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "repo"
            shutil.copytree(self.root, mutated)
            (mutated / "plugins" / "flow-next" / "scripts" / "flowctl_tracker"
             / "executor.py").write_text("tampered\n", encoding="utf-8")
            out = self._run(mutated)
            self.assertNotEqual(out.returncode, 0)

    def test_codex_installer_fails_closed_on_absent_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "repo"
            shutil.copytree(self.root, mutated)
            shutil.rmtree(mutated / "plugins" / "flow-next" / "scripts"
                          / "flowctl_tracker")
            # install-codex.sh refuses to run without the pre-built mirror -
            # stage the real one so the run reaches the tracker-package guard.
            shutil.copytree(REPO / "plugins" / "flow-next" / "codex",
                            mutated / "plugins" / "flow-next" / "codex",
                            ignore=shutil.ignore_patterns("__pycache__"))
            with tempfile.TemporaryDirectory() as home:
                (Path(home) / ".codex").mkdir()  # installer probes for Codex CLI
                out = subprocess.run(
                    ["bash", str(mutated / "scripts" / "install-codex.sh")],
                    capture_output=True, text=True, timeout=300,
                    env={**os.environ, "HOME": home})
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("flowctl_tracker", out.stdout + out.stderr)

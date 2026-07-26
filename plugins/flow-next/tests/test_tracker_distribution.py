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
        self.assertEqual(recorded, _hashes(PKG),
                         "run scripts/gen_tracker_manifest.py")

    def test_generator_check_mode_agrees(self) -> None:
        out = subprocess.run([sys.executable, str(GENERATOR), "--check"],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_flow_bin_copy_matches_the_manifest_too(self) -> None:
        """The dual-copy invariant extends to the package."""
        bin_pkg = REPO / ".flow" / "bin" / "flowctl_tracker"
        self.assertTrue(bin_pkg.is_dir(), ".flow/bin ships the package")
        self.assertEqual(_hashes(bin_pkg), _hashes(PKG))


class InstallerVerifier(unittest.TestCase):
    def _staged(self, tmp: str) -> Path:
        dest = Path(tmp) / "scripts"
        shutil.copytree(PKG, dest / "flowctl_tracker",
                        ignore=shutil.ignore_patterns("__pycache__"))
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
                    "scripts/install-cursor.ps1"):
            with self.subTest(installer=rel):
                self.assertIn("verify_tracker_manifest",
                              (REPO / rel).read_text(encoding="utf-8"))
        for rel in ("plugins/flow-next/skills/flow-next-setup/workflow.md",
                    "plugins/flow-next/skills/flow-next-ralph-init/SKILL.md"):
            with self.subTest(skill=rel):
                self.assertIn("verify_tracker_manifest",
                              (REPO / rel).read_text(encoding="utf-8"))


class RuntimeSmoke(unittest.TestCase):
    """The packaging smoke: the REAL launcher for this OS resolves the package.
    On windows-latest this exercises flowctl.cmd; elsewhere the bash launcher."""

    def _launcher(self) -> list:
        if os.name == "nt":  # pragma: no cover - the Windows CI row
            return ["cmd", "/c", str(ROOT / "scripts" / "flowctl.cmd")]
        return [str(ROOT / "scripts" / "flowctl")]

    def test_tracker_resolve_help_runs_through_the_launcher(self) -> None:
        out = subprocess.run(self._launcher() + ["tracker", "resolve", "--help"],
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

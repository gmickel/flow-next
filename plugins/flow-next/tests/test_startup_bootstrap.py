"""Startup cache, source-fallback, path, and usage-fast-path contracts."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "flowctl_bootstrap.py"
DOGFOOD_BOOTSTRAP = ROOT.parents[1] / ".flow" / "bin" / "flowctl_bootstrap.py"
SCRIPT_LAUNCHER = ROOT / "scripts" / "flowctl"
BIN_LAUNCHER = ROOT / "bin" / "flowctl"
BUNDLED_USAGE = ROOT / "templates" / "usage.md"

spec = importlib.util.spec_from_file_location("flowctl_bootstrap", BOOTSTRAP)
bootstrap = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bootstrap)


class StartupBootstrapTest(unittest.TestCase):
    def test_dogfood_bootstrap_is_byte_identical(self) -> None:
        self.assertEqual(
            BOOTSTRAP.read_bytes(),
            DOGFOOD_BOOTSTRAP.read_bytes(),
            "canonical and dogfood bootstrap copies must stay byte-identical",
        )

    def _install(self, root: Path, source: str, *, nested: bool = False) -> tuple[Path, Path]:
        scripts = root / "plugin" / "scripts" if nested else root / "bin"
        scripts.mkdir(parents=True)
        boot = scripts / "flowctl_bootstrap.py"
        flowctl = scripts / "flowctl.py"
        shutil.copy2(BOOTSTRAP, boot)
        flowctl.write_text(source, encoding="utf-8")
        return boot, flowctl

    def _run(self, boot: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(boot), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )

    def test_checked_hash_cache_created_and_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, source = self._install(root, 'def main():\n    print("CACHE-OK")\n')
            first = self._run(boot, root)
            second = self._run(boot, root)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.stdout, "CACHE-OK\n")
            cache = Path(importlib.util.cache_from_source(str(source)))
            data = cache.read_bytes()
            self.assertEqual(data[:4], importlib.util.MAGIC_NUMBER)
            self.assertEqual(int.from_bytes(data[4:8], "little") & 0b11, 0b11)
            self.assertEqual(data[8:16], importlib.util.source_hash(source.read_bytes()))

    def test_same_size_same_mtime_source_change_invalidates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = 'def main():\n    print("VERSION-A")\n'
            two = 'def main():\n    print("VERSION-B")\n'
            self.assertEqual(len(one), len(two))
            boot, source = self._install(root, one)
            first = self._run(boot, root)
            original_stat = source.stat()
            source.write_text(two, encoding="utf-8")
            os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            second = self._run(boot, root)
            self.assertEqual(first.stdout, "VERSION-A\n")
            self.assertEqual(second.stdout, "VERSION-B\n")

    def test_corrupt_cache_recovers_from_source_and_refreshes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, source = self._install(root, 'def main():\n    print("RECOVERED")\n')
            self.assertEqual(self._run(boot, root).returncode, 0)
            cache = Path(importlib.util.cache_from_source(str(source)))
            cache.write_bytes(b"corrupt")
            recovered = self._run(boot, root)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertEqual(recovered.stdout, "RECOVERED\n")
            self.assertEqual(cache.read_bytes()[:4], importlib.util.MAGIC_NUMBER)

    def test_unwritable_cache_path_compiles_source_in_memory(self) -> None:
        source = Path("/tmp/logical/flowctl.py")
        source_bytes = b'def main():\n    print("SOURCE")\n'
        with mock.patch("py_compile.compile", side_effect=PermissionError("read-only")):
            code = bootstrap._source_code(source, source_bytes)
        namespace: dict = {}
        exec(code, namespace)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            namespace["main"]()
        self.assertEqual(out.getvalue(), "SOURCE\n")

    def test_cached_execution_preserves_logical_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, source = self._install(
                root,
                'def main():\n    print(__file__)\n',
            )
            self.assertEqual(self._run(boot, root).returncode, 0)
            result = self._run(boot, root)
            self.assertEqual(Path(result.stdout.strip()), source.resolve())

    def test_usage_fast_path_prefers_bundled_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, _source = self._install(root, 'def main():\n    raise AssertionError\n', nested=True)
            templates = root / "plugin" / "templates"
            templates.mkdir()
            (templates / "usage.md").write_text("BUNDLED\n", encoding="utf-8")
            repo = root / "repo"
            (repo / ".flow").mkdir(parents=True)
            (repo / ".flow" / "usage.md").write_text("LOCAL\n", encoding="utf-8")
            result = self._run(boot, repo, "usage")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "BUNDLED\n")

    def test_usage_fast_path_copy_fallback_and_missing_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, _source = self._install(root, 'def main():\n    raise AssertionError\n')
            repo = root / "repo"
            (repo / ".flow").mkdir(parents=True)
            local = repo / ".flow" / "usage.md"
            local.write_text("LOCAL\n", encoding="utf-8")
            found = self._run(boot, repo, "usage")
            self.assertEqual(found.returncode, 0, found.stderr)
            self.assertEqual(found.stdout, "LOCAL\n")
            local.unlink()
            missing = self._run(boot, repo, "usage")
            self.assertEqual(missing.returncode, 1)
            self.assertIn("No usage guide found", missing.stderr)

    def test_runtime_guard_runs_before_source_load(self) -> None:
        err = io.StringIO()
        with mock.patch.object(bootstrap.sys, "version_info", (3, 10, 14)):
            with mock.patch.object(bootstrap, "_load_flowctl") as load:
                with contextlib.redirect_stderr(err):
                    result = bootstrap.main()
        self.assertEqual(result, 1)
        load.assert_not_called()
        self.assertIn("Python 3.11 or newer is required", err.getvalue())

    def test_plugin_launchers_share_exact_usage_fast_path(self) -> None:
        expected = BUNDLED_USAGE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            for launcher in (SCRIPT_LAUNCHER, BIN_LAUNCHER):
                result = subprocess.run(
                    [str(launcher), "usage"],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)

    def test_copy_launcher_uses_local_usage_and_preserves_help(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bindir = root / "repo" / ".flow" / "bin"
            bindir.mkdir(parents=True)
            for source in (SCRIPT_LAUNCHER, BOOTSTRAP, ROOT / "scripts" / "flowctl.py"):
                target = bindir / source.name
                shutil.copy2(source, target)
            launcher = bindir / "flowctl"
            launcher.chmod(0o755)
            usage = bindir.parent / "usage.md"
            usage.write_text("COPY-USAGE\n", encoding="utf-8")
            found = subprocess.run(
                [str(launcher), "usage"],
                cwd=root / "repo",
                capture_output=True,
                text=True,
            )
            self.assertEqual(found.returncode, 0, found.stderr)
            self.assertEqual(found.stdout, "COPY-USAGE\n")
            help_result = subprocess.run(
                [str(launcher), "--help"],
                cwd=root / "repo",
                capture_output=True,
                text=True,
            )
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertTrue(help_result.stdout.startswith("usage: flowctl.py"))
            (bindir.parent / "meta.json").write_text("{}\n", encoding="utf-8")
            setup_mode = subprocess.run(
                [str(launcher), "setup-mode", "set", "copy", "--json"],
                cwd=root / "repo",
                capture_output=True,
                text=True,
            )
            self.assertEqual(setup_mode.returncode, 0, setup_mode.stderr)
            self.assertIn('"mode": "copy"', setup_mode.stdout)

    def test_bootstrap_preserves_help_scope_rewrite_and_error_contracts(self) -> None:
        source = ROOT / "scripts" / "flowctl.py"
        cases = (
            ("--help",),
            ("task", "--help"),
            ("scope", "resolve", "--json", "--raw", "--biz fn-1"),
            ("scope", "resolve", "--biz", "--tech"),
            ("not-a-command",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for args in cases:
                direct = subprocess.run(
                    [sys.executable, str(source), *args],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                )
                accelerated = subprocess.run(
                    [sys.executable, str(BOOTSTRAP), *args],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(accelerated.returncode, direct.returncode, args)
                self.assertEqual(accelerated.stdout, direct.stdout, args)
                self.assertEqual(accelerated.stderr, direct.stderr, args)


if __name__ == "__main__":
    unittest.main()

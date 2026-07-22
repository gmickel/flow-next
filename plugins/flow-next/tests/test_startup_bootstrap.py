"""Source-authoritative startup, launcher, help, and usage contracts."""

from __future__ import annotations

import contextlib
import hashlib
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
HELP_TEXT = ROOT / "scripts" / "flowctl-help.txt"
DOGFOOD_HELP_TEXT = ROOT.parents[1] / ".flow" / "bin" / "flowctl-help.txt"
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
        self.assertEqual(
            HELP_TEXT.read_bytes(),
            DOGFOOD_HELP_TEXT.read_bytes(),
            "canonical and dogfood help fast-path copies must stay byte-identical",
        )

    def _install(self, root: Path, source: str, *, nested: bool = False) -> tuple[Path, Path]:
        scripts = root / "plugin" / "scripts" if nested else root / "bin"
        scripts.mkdir(parents=True)
        boot = scripts / "flowctl_bootstrap.py"
        flowctl = scripts / "flowctl.py"
        shutil.copy2(BOOTSTRAP, boot)
        flowctl.write_text(source, encoding="utf-8")
        return boot, flowctl

    def _run(
        self,
        boot: Path,
        cwd: Path,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(boot), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_non_static_commands_never_create_executable_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, source = self._install(root, 'def main():\n    print("SOURCE-OK")\n')
            first = self._run(boot, root)
            second = self._run(boot, root)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.stdout, "SOURCE-OK\n")
            cache = Path(importlib.util.cache_from_source(str(source)))
            self.assertFalse(cache.exists())

    def test_same_size_same_mtime_source_change_is_authoritative(self) -> None:
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

    def test_forged_executable_cache_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, source = self._install(root, 'def main():\n    print("TRACKED-SOURCE")\n')
            cache = Path(importlib.util.cache_from_source(str(source)))
            cache.parent.mkdir()
            attacker = root / "attacker.py"
            attacker.write_text('def main():\n    print("FORGED-CACHE")\n', encoding="utf-8")
            import py_compile

            py_compile.compile(str(attacker), cfile=str(cache), doraise=True)
            result = self._run(boot, root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "TRACKED-SOURCE\n")

    def test_source_execution_preserves_logical_source_file(self) -> None:
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
            for source in (
                SCRIPT_LAUNCHER,
                BOOTSTRAP,
                HELP_TEXT,
                ROOT / "scripts" / "flowctl.py",
            ):
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

    def test_static_output_reconfigures_legacy_ascii_streams_to_utf8(self) -> None:
        env = {**os.environ, "PYTHONIOENCODING": "ascii"}
        env.pop("COLUMNS", None)
        with tempfile.TemporaryDirectory() as tmp:
            for args in (("usage",), ("--help",)):
                result = self._run(BOOTSTRAP, Path(tmp), *args, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("flowctl", result.stdout)

    def test_stale_or_corrupt_help_falls_back_to_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot, source = self._install(root, 'def main():\n    print("LIVE-HELP")\n')
            help_path = source.with_name("flowctl-help.txt")
            for payload in (b"STALE-HELP\n", b"\xff\xfe"):
                help_path.write_bytes(payload)
                result = self._run(boot, root, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "LIVE-HELP\n")

    def test_columns_override_falls_back_to_width_aware_argparse(self) -> None:
        env = {**os.environ, "COLUMNS": "120"}
        with tempfile.TemporaryDirectory() as tmp:
            direct = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "flowctl.py"), "--help"],
                cwd=tmp,
                capture_output=True,
                text=True,
                env=env,
            )
            accelerated = self._run(BOOTSTRAP, Path(tmp), "--help", env=env)
        self.assertEqual(accelerated.returncode, direct.returncode)
        self.assertEqual(accelerated.stdout, direct.stdout)
        self.assertEqual(accelerated.stderr, direct.stderr)

    def test_interactive_tty_falls_back_to_width_aware_argparse(self) -> None:
        with mock.patch.object(bootstrap.sys.stdout, "isatty", return_value=True):
            self.assertFalse(
                bootstrap._root_help_fast_path(ROOT / "scripts" / "flowctl.py")
            )

    def test_help_snapshot_falls_back_across_python_minor_versions(self) -> None:
        other_minor = bootstrap.HELP_PYTHON[1] - 1
        with mock.patch.object(
            bootstrap.sys,
            "version_info",
            (*bootstrap.HELP_PYTHON[:1], other_minor, 0),
        ):
            self.assertFalse(
                bootstrap._root_help_fast_path(ROOT / "scripts" / "flowctl.py")
            )

    def test_tracked_root_help_matches_argparse_byte_for_byte(self) -> None:
        self.assertEqual(
            bootstrap.SOURCE_SHA256,
            hashlib.sha256((ROOT / "scripts" / "flowctl.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            bootstrap.HELP_SHA256,
            hashlib.sha256(HELP_TEXT.read_bytes()).hexdigest(),
        )
        direct = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "flowctl.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        if sys.version_info[:2] == bootstrap.HELP_PYTHON:
            self.assertEqual(HELP_TEXT.read_text(encoding="utf-8"), direct.stdout)
        else:
            self.assertFalse(
                bootstrap._root_help_fast_path(ROOT / "scripts" / "flowctl.py")
            )


if __name__ == "__main__":
    unittest.main()

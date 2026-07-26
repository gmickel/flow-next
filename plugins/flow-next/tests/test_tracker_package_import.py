"""The tracker package must import the same way under test as in production (fn-139.1).

The launcher runs `flowctl_bootstrap.py` as a script, so `sys.path[0]` is that
file's directory and a sibling package imports naturally. Under a *test* module
`sys.path[0]` is the tests directory instead, so without an explicit insert the
package is invisible - which is why 63 of the 68 modules that load flowctl via
`spec_from_file_location` needed patching.

These tests pin both halves: the package is importable, and every module that
loads flowctl can actually reach it.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class TrackerPackageImports(unittest.TestCase):
    def test_package_imports_under_test(self) -> None:
        import flowctl_tracker  # noqa: PLC0415

        self.assertTrue(flowctl_tracker.__version__)

    def test_providers_subpackage_imports(self) -> None:
        from flowctl_tracker import providers  # noqa: PLC0415

        self.assertEqual(providers.__all__, [], "providers is intentionally empty until .4/.6")

    def test_name_is_namespaced(self) -> None:
        """A bare `tracker/` would collide on sys.path with anything similarly named."""
        self.assertFalse(
            (ROOT / "scripts" / "tracker").exists(),
            "package must be `flowctl_tracker`, never a generic top-level `tracker`",
        )

    def test_imports_from_the_real_launcher_context(self) -> None:
        """Production path: sys.path[0] is the bootstrap's dir, no insert needed."""
        r = subprocess.run(
            [sys.executable, "-c",
             "import flowctl_tracker, flowctl_tracker.providers; print(flowctl_tracker.__version__)"],
            cwd=str(ROOT / "scripts"), capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip())

    def test_package_does_not_import_flowctl(self) -> None:
        """Dependency runs one way: flowctl may use the package, never the reverse."""
        for f in (ROOT / "scripts" / "flowctl_tracker").rglob("*.py"):
            src = f.read_text(encoding="utf-8")
            self.assertNotIn("import flowctl", src, f"{f.name} must not import flowctl")


class EveryFlowctlLoadingTestCanReachThePackage(unittest.TestCase):
    def test_all_spec_from_file_location_modules_insert_scripts_path(self) -> None:
        tests_dir = Path(__file__).resolve().parent
        missing = [
            f.name
            for f in sorted(tests_dir.glob("test_*.py"))
            if "spec_from_file_location" in f.read_text(encoding="utf-8")
            and "sys.path.insert" not in f.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            missing, [],
            "these modules load flowctl but cannot import flowctl_tracker; "
            "sys.path[0] is the tests dir under unittest",
        )


if __name__ == "__main__":
    unittest.main()

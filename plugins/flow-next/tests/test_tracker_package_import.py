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

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _inserts_scripts_path(source: str) -> bool:
    """True when some `sys.path.insert(...)` statement references `scripts`.

    Deliberately statement-scoped rather than a naive regex: the canonical form
    contains nested parentheses (`resolve()`), so a `[^)]*` pattern stops short
    and reports a false negative on every correct module.
    """
    for line in source.splitlines():
        idx = line.find("sys.path.insert")
        if idx != -1 and "scripts" in line[idx:]:
            return True
    return False


class TrackerPackageImports(unittest.TestCase):
    def test_package_imports_under_test(self) -> None:
        import flowctl_tracker  # noqa: PLC0415

        self.assertEqual(flowctl_tracker.__all__, [])

    def test_no_version_field_until_distribution_lands(self) -> None:
        """A truthiness assertion previously masked a __version__ that contradicted
        the manifests. Version wiring is task .5; until then there is no field."""
        import flowctl_tracker  # noqa: PLC0415

        self.assertFalse(hasattr(flowctl_tracker, "__version__"))

    def test_providers_subpackage_imports(self) -> None:
        from flowctl_tracker import providers  # noqa: PLC0415

        # .4 shipped GitHub + GitLab behind resolver_for; .6 adds Linear + Jira.
        self.assertEqual(providers.__all__, ["resolver_for"])

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
             "import flowctl_tracker, flowctl_tracker.providers; print('ok')"],
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
        # A bare "contains sys.path.insert" check is NOT sufficient and was the
        # original bug here: test_backend_spec.py inserts optimization/reached-path
        # and nothing else, so it passed the string check while scripts/ stayed
        # unreachable. Require an insert that actually references scripts/.
        missing = [
            f.name
            for f in sorted(tests_dir.glob("test_*.py"))
            if "spec_from_file_location" in f.read_text(encoding="utf-8")
            and not _inserts_scripts_path(f.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            missing, [],
            "these modules load flowctl but do not put scripts/ on sys.path, so "
            "flowctl_tracker is unreachable from them; sys.path[0] is the tests dir",
        )

    def test_the_guard_itself_rejects_an_unrelated_insert(self) -> None:
        """Mutation guard: the check must not be satisfiable by any old insert.

        The first version of this guard only looked for the string
        `sys.path.insert`, so `test_backend_spec.py` passed while inserting
        `optimization/reached-path` and leaving scripts/ unreachable. The second
        version used `insert\\([^)]*scripts`, which can never match the canonical
        form because `[^)]*` stops at the `)` of `resolve()`. Both failure modes
        are pinned here.
        """
        self.assertFalse(_inserts_scripts_path("sys.path.insert(0, str(harness_dir))"))
        self.assertTrue(
            _inserts_scripts_path(
                'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))'
            )
        )
        self.assertTrue(_inserts_scripts_path('sys.path.insert(0, str(ROOT / "scripts"))'))


if __name__ == "__main__":
    unittest.main()

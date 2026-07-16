"""Unit tests for the spec JSON write-location selector + read-fallback (fn-43.17 / R33).

`get_specs_json_write_dir(flow_dir)` resolves where new spec JSON metadata
should land based on the three-state migration matrix:

    sentinel exists                  → .flow/specs/   (post-migration)
    no sentinel + .flow/epics/ dir   → .flow/epics/   (alias-mode 0.x repo)
    no sentinel + no .flow/epics/    → .flow/specs/   (fresh post-1.0 init)

`find_spec_json_path(flow_dir, spec_id)` is the read-side fallback that probes
canonical → legacy → write-target-as-error-anchor.

Tests cover all three layouts for write-resolution and both directions of
read-fallback (canonical-only → finds, legacy-only → finds, neither → returns
the canonical write target so error messages are deterministic).

Run:
    python3 -m unittest plugins.flow-next.tests.test_write_location -v
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_writeloc_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


class TestGetSpecsJsonWriteDir(unittest.TestCase):
    """Three layouts, three deterministic outcomes."""

    def test_fresh_init_no_epics_no_sentinel_writes_to_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            target = flowctl.get_specs_json_write_dir(flow_dir)
            self.assertEqual(target.name, flowctl.SPECS_JSON_DIR)
            self.assertEqual(target, flow_dir / flowctl.SPECS_JSON_DIR)

    def test_alias_mode_no_sentinel_with_epics_writes_to_epics(self) -> None:
        """0.x repo not yet migrated — preserve 'alias mode = no migration' (R5)."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.EPICS_DIR).mkdir()
            target = flowctl.get_specs_json_write_dir(flow_dir)
            self.assertEqual(target, flow_dir / flowctl.EPICS_DIR)

    def test_post_migration_sentinel_writes_to_specs(self) -> None:
        """Sentinel present → canonical 1.0 layout regardless of epics/ presence."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            # Both epics/ and specs/ may exist transiently mid-migration; in
            # practice migrate-rename rmdir's epics/ at the end. Either way,
            # sentinel beats epics/.
            (flow_dir / flowctl.EPICS_DIR).mkdir()
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir()
            (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
                flowctl.FLOW_VERSION_PAYLOAD + "\n", encoding="utf-8"
            )
            target = flowctl.get_specs_json_write_dir(flow_dir)
            self.assertEqual(target, flow_dir / flowctl.SPECS_JSON_DIR)

    def test_post_migration_no_epics_writes_to_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
                flowctl.FLOW_VERSION_PAYLOAD + "\n", encoding="utf-8"
            )
            target = flowctl.get_specs_json_write_dir(flow_dir)
            self.assertEqual(target, flow_dir / flowctl.SPECS_JSON_DIR)


class TestFindSpecJsonPath(unittest.TestCase):
    """Read fallback probes canonical first, legacy second, write-target third."""

    def test_canonical_only_returns_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir(parents=True)
            target_path = flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json"
            target_path.write_text("{}", encoding="utf-8")
            self.assertEqual(
                flowctl.find_spec_json_path(flow_dir, "fn-1"),
                target_path,
            )

    def test_legacy_only_returns_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            target_path = flow_dir / flowctl.EPICS_DIR / "fn-1.json"
            target_path.write_text("{}", encoding="utf-8")
            # No specs/ dir or sentinel — alias-mode read.
            self.assertEqual(
                flowctl.find_spec_json_path(flow_dir, "fn-1"),
                target_path,
            )

    def test_canonical_wins_over_legacy_when_both_present(self) -> None:
        """Post-migration edge case: stale legacy file shadowing a fresh canonical one."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir(parents=True)
            (flow_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            canonical = flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json"
            legacy = flow_dir / flowctl.EPICS_DIR / "fn-1.json"
            canonical.write_text("{}", encoding="utf-8")
            legacy.write_text("{}", encoding="utf-8")
            self.assertEqual(
                flowctl.find_spec_json_path(flow_dir, "fn-1"),
                canonical,
            )

    def test_neither_present_returns_canonical_write_target(self) -> None:
        """Missing spec → returns the path the next write would land at."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            # Fresh layout: write-target is .flow/specs/.
            self.assertEqual(
                flowctl.find_spec_json_path(flow_dir, "fn-99"),
                flow_dir / flowctl.SPECS_JSON_DIR / "fn-99.json",
            )

    def test_neither_present_returns_legacy_write_target_in_alias_mode(self) -> None:
        """Alias-mode (epics/ exists, no sentinel) → write target IS epics/."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            # No specs/ dir, no sentinel, no fn-99 anywhere.
            self.assertEqual(
                flowctl.find_spec_json_path(flow_dir, "fn-99"),
                flow_dir / flowctl.EPICS_DIR / "fn-99.json",
            )


class TestIterSpecJsonFiles(unittest.TestCase):
    """Iterating must surface specs from BOTH dirs with canonical winning collisions."""

    def test_iter_yields_from_specs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir(parents=True)
            (flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json").write_text("{}", encoding="utf-8")
            (flow_dir / flowctl.SPECS_JSON_DIR / "fn-2.json").write_text("{}", encoding="utf-8")
            stems = sorted(p.stem for p in flowctl.iter_spec_json_files(flow_dir))
            self.assertEqual(stems, ["fn-1", "fn-2"])

    def test_iter_yields_from_epics_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            (flow_dir / flowctl.EPICS_DIR / "fn-1.json").write_text("{}", encoding="utf-8")
            stems = sorted(p.stem for p in flowctl.iter_spec_json_files(flow_dir))
            self.assertEqual(stems, ["fn-1"])

    def test_iter_dedupes_with_canonical_winning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir(parents=True)
            (flow_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            (flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json").write_text("{}", encoding="utf-8")
            (flow_dir / flowctl.EPICS_DIR / "fn-1.json").write_text("{}", encoding="utf-8")
            paths = list(flowctl.iter_spec_json_files(flow_dir))
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].parent.name, flowctl.SPECS_JSON_DIR)


if __name__ == "__main__":
    unittest.main()

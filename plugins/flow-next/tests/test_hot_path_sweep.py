"""fn-109.2: hot-path cache sweep - version-getter memo + prospect single-read.

Covers the spec's R7 acceptance criterion:

- Version getters (`get_copilot_version` / `get_cursor_version`) cache
  SUCCESSFUL probes only, keyed by the `shutil.which()`-resolved executable
  path: repeat-success spawns once, a failed probe is never sticky
  (failure-then-success spawns twice), and a PATH change (new resolved
  path) re-probes because the key changes.
- Prospect descriptor construction (`_prospect_iter_artifacts` enumeration,
  including `_prospect_detect_corruption` and `_prospect_artifact_status`)
  reads + frontmatter-parses each artifact exactly ONCE per enumeration
  (was 3 reads / 3 parses). `_prospect_resolve_id` on an exact filename hit
  reads only that one file instead of enumerating the whole directory, with
  walk-filter parity for the ids the enumeration would have skipped.

The flowctl module is loaded once at module scope under a test-local name so
its module-level caches never collide with other suites.
"""

import importlib.util
import os
import subprocess
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest import mock


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location(
        "flowctl_hot_path_sweep_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ------------------- R7: version-getter per-process memo -------------------


class _FakeCompleted:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.returncode = 0


@contextmanager
def _scripted_subprocess(module, outcomes):
    """Replace ``subprocess.run`` as seen by the flowctl module with a
    scripted delegate. ``outcomes`` is a list consumed per call: a string is
    returned as stdout; the ``FAIL`` sentinel raises CalledProcessError.
    Yields the recorded argv list per spawn."""
    real_run = module.subprocess.run
    calls = []
    remaining = list(outcomes)

    def scripted_run(cmd, **kwargs):
        calls.append(list(cmd))
        if not remaining:
            raise AssertionError(f"unexpected extra subprocess spawn: {cmd}")
        outcome = remaining.pop(0)
        if outcome is FAIL:
            raise subprocess.CalledProcessError(returncode=1, cmd=list(cmd))
        return _FakeCompleted(outcome)

    module.subprocess.run = scripted_run
    try:
        yield calls
    finally:
        module.subprocess.run = real_run


FAIL = object()


class _VersionGetterCase(unittest.TestCase):
    """Shared fixture: controlled ``shutil.which`` + cleared version memo."""

    def setUp(self) -> None:
        flowctl._CLI_VERSION_CACHE.clear()

    @contextmanager
    def _which(self, mapping):
        """Patch ``shutil.which`` (as flowctl sees it) with a dict lookup."""
        with mock.patch.object(
            flowctl.shutil, "which", side_effect=lambda name: mapping.get(name)
        ):
            yield


class TestVersionGetterMemo(_VersionGetterCase):
    def test_copilot_repeat_success_spawns_once(self) -> None:
        with self._which({"copilot": "/fake/bin/copilot"}):
            with _scripted_subprocess(
                flowctl, ["GitHub Copilot CLI 1.0.34."]
            ) as calls:
                self.assertEqual(flowctl.get_copilot_version(), "1.0.34")
                self.assertEqual(flowctl.get_copilot_version(), "1.0.34")
                self.assertEqual(flowctl.get_copilot_version(), "1.0.34")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], ["/fake/bin/copilot", "--version"])

    def test_cursor_repeat_success_spawns_once(self) -> None:
        with self._which({"cursor-agent": "/fake/bin/cursor-agent"}):
            with _scripted_subprocess(
                flowctl, ["2026.06.13-abc1234"]
            ) as calls:
                self.assertEqual(
                    flowctl.get_cursor_version(), "2026.06.13-abc1234"
                )
                self.assertEqual(
                    flowctl.get_cursor_version(), "2026.06.13-abc1234"
                )
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                calls[0], ["/fake/bin/cursor-agent", "--version"]
            )

    def test_failure_then_success_is_not_sticky(self) -> None:
        with self._which({"copilot": "/fake/bin/copilot"}):
            with _scripted_subprocess(flowctl, [FAIL, "1.0.35"]) as calls:
                # Transient failure: None, and NOT cached...
                self.assertIsNone(flowctl.get_copilot_version())
                self.assertEqual(flowctl._CLI_VERSION_CACHE, {})
                # ...so the next call re-probes and succeeds (2 spawns)...
                self.assertEqual(flowctl.get_copilot_version(), "1.0.35")
                # ...and THAT success is cached (no third spawn).
                self.assertEqual(flowctl.get_copilot_version(), "1.0.35")
            self.assertEqual(len(calls), 2)

    def test_path_change_reprobes_new_executable(self) -> None:
        with _scripted_subprocess(flowctl, ["1.0.34", "2.0.0"]) as calls:
            with self._which({"copilot": "/fake/a/copilot"}):
                self.assertEqual(flowctl.get_copilot_version(), "1.0.34")
            # PATH change: which() now resolves a different executable -
            # the key changes, so the memo re-probes.
            with self._which({"copilot": "/fake/b/copilot"}):
                self.assertEqual(flowctl.get_copilot_version(), "2.0.0")
            # Back to the first path: its entry is still cached (no spawn).
            with self._which({"copilot": "/fake/a/copilot"}):
                self.assertEqual(flowctl.get_copilot_version(), "1.0.34")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "/fake/a/copilot")
        self.assertEqual(calls[1][0], "/fake/b/copilot")

    def test_missing_executable_never_spawns_or_caches(self) -> None:
        with self._which({}):
            with _scripted_subprocess(flowctl, []) as calls:
                self.assertIsNone(flowctl.get_copilot_version())
                self.assertIsNone(flowctl.get_cursor_version())
            self.assertEqual(calls, [])
            self.assertEqual(flowctl._CLI_VERSION_CACHE, {})


# ------------------- R7: prospect single-read enumeration ------------------


def _valid_artifact_text(artifact_id: str, day: str = "2026-04-24") -> str:
    """Minimal artifact passing `_prospect_detect_corruption` (all required
    frontmatter fields + Grounding snapshot / Survivors sections)."""
    return (
        "---\n"
        f'title: "Sweep fixture {artifact_id}"\n'
        f'date: "{day}"\n'
        'focus_hint: "DX improvements"\n'
        "volume: 22\n"
        "survivor_count: 6\n"
        "rejected_count: 16\n"
        "rejection_rate: 0.73\n"
        f'artifact_id: "{artifact_id}"\n'
        "promoted_ideas: []\n"
        'status: "active"\n'
        "---\n"
        "\n"
        "## Focus\n\nDX wins.\n\n"
        "## Grounding snapshot\n\n- git log: 12 files\n\n"
        "## Survivors\n\n### High leverage (1-3)\n\n_(none)_\n\n"
        "## Rejected\n\n- none\n"
    )


@contextmanager
def _counting_reads():
    """Count ``Path.read_text`` invocations per path (delegating to the real
    method) and ``_prospect_parse_frontmatter`` invocations (total)."""
    real_read = Path.read_text
    read_counts: Counter = Counter()

    def counting_read(self, *args, **kwargs):
        read_counts[str(self)] += 1
        return real_read(self, *args, **kwargs)

    real_parse = flowctl._prospect_parse_frontmatter
    parse_count = Counter()

    def counting_parse(text):
        parse_count["n"] += 1
        return real_parse(text)

    with mock.patch.object(Path, "read_text", counting_read):
        with mock.patch.object(
            flowctl, "_prospect_parse_frontmatter", counting_parse
        ):
            yield read_counts, parse_count


class _ProspectDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.prospects = Path(self._tmp.name) / "prospects"
        self.archive = self.prospects / flowctl.PROSPECTS_ARCHIVE_DIR
        self.archive.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, text: str, archived: bool = False) -> Path:
        base = self.archive if archived else self.prospects
        p = base / f"{name}.md"
        p.write_text(text, encoding="utf-8")
        return p


class TestProspectSingleReadEnumeration(_ProspectDirCase):
    def test_each_artifact_read_and_parsed_exactly_once(self) -> None:
        ids = ["alpha-2026-04-24", "beta-2026-04-25", "gamma-2026-04-26"]
        paths = [self._write(i, _valid_artifact_text(i)) for i in ids]
        arch = self._write(
            "old-2026-01-01", _valid_artifact_text("old-2026-01-01"),
            archived=True,
        )
        # One corrupt (empty) artifact: still exactly one read + one parse.
        corrupt = self._write("empty-2026-04-24", "")

        with _counting_reads() as (read_counts, parse_count):
            out = flowctl._prospect_iter_artifacts(
                self.prospects, include_archive=True
            )

        self.assertEqual(len(out), 5)
        for p in [*paths, arch, corrupt]:
            self.assertEqual(
                read_counts[str(p)], 1,
                f"{p.name} read {read_counts[str(p)]}x (expected exactly 1)",
            )
        # Frontmatter parsed exactly once per READABLE artifact (the build
        # step parses once; corruption/status consume the passed-down
        # result instead of re-parsing). 5 artifacts, 5 parses (was 3 each).
        self.assertEqual(parse_count["n"], 5)

    def test_enumeration_descriptor_semantics_unchanged(self) -> None:
        self._write("alpha-2026-04-24", _valid_artifact_text("alpha-2026-04-24"))
        corrupt = self._write("bad-2026-04-24", "no frontmatter here\n")
        out = flowctl._prospect_iter_artifacts(self.prospects)
        by_id = {d["artifact_id"]: d for d in out}
        self.assertEqual(by_id["alpha-2026-04-24"]["status"], "stale")
        self.assertIsNone(by_id["alpha-2026-04-24"]["corruption"])
        self.assertEqual(
            by_id["alpha-2026-04-24"]["frontmatter"]["focus_hint"],
            "DX improvements",
        )
        self.assertEqual(by_id["alpha-2026-04-24"]["survivor_count"], 6)
        self.assertEqual(by_id["bad-2026-04-24"]["status"], "corrupt")
        self.assertEqual(
            by_id["bad-2026-04-24"]["corruption"],
            flowctl.PROSPECT_CORRUPT_NO_FRONTMATTER,
        )
        self.assertEqual(str(corrupt), by_id["bad-2026-04-24"]["path"])


class TestProspectResolveIdExactHit(_ProspectDirCase):
    def test_exact_hit_reads_only_the_target(self) -> None:
        ids = ["alpha-2026-04-24", "beta-2026-04-25", "gamma-2026-04-26"]
        paths = {i: self._write(i, _valid_artifact_text(i)) for i in ids}

        with _counting_reads() as (read_counts, _):
            got = flowctl._prospect_resolve_id(
                self.prospects, "beta-2026-04-25"
            )

        assert got is not None
        self.assertEqual(got["artifact_id"], "beta-2026-04-25")
        self.assertEqual(read_counts[str(paths["beta-2026-04-25"])], 1)
        self.assertEqual(read_counts[str(paths["alpha-2026-04-24"])], 0)
        self.assertEqual(read_counts[str(paths["gamma-2026-04-26"])], 0)

    def test_exact_hit_descriptor_matches_enumeration(self) -> None:
        self._write("alpha-2026-04-24", _valid_artifact_text("alpha-2026-04-24"))
        self._write(
            "old-2026-01-01", _valid_artifact_text("old-2026-01-01"),
            archived=True,
        )
        for target in ("alpha-2026-04-24", "old-2026-01-01"):
            resolved = flowctl._prospect_resolve_id(
                self.prospects, target, include_archive=True
            )
            enumerated = [
                d
                for d in flowctl._prospect_iter_artifacts(
                    self.prospects, include_archive=True
                )
                if d["artifact_id"] == target
            ]
            self.assertEqual(resolved, enumerated[0])

    def test_walk_filter_parity_for_skipped_ids(self) -> None:
        # A top-level underscore-prefixed file exists but the enumeration
        # skips it - resolve must NOT shortcut to it (pre-fn-109 behavior).
        self._write("_hidden-2026-04-24", _valid_artifact_text("_hidden-2026-04-24"))
        self.assertIsNone(
            flowctl._prospect_resolve_id(self.prospects, "_hidden-2026-04-24")
        )
        # Dot-prefixed likewise.
        self._write(".dotted-2026-04-24", _valid_artifact_text(".dotted-2026-04-24"))
        self.assertIsNone(
            flowctl._prospect_resolve_id(self.prospects, ".dotted-2026-04-24")
        )
        # An UNDERSCORE-prefixed file inside _archive/ IS enumerated (the
        # archive walk only skips dot-prefixed names) - exact hit resolves.
        self._write(
            "_arch-note-2026-04-24",
            _valid_artifact_text("_arch-note-2026-04-24"),
            archived=True,
        )
        got = flowctl._prospect_resolve_id(
            self.prospects, "_arch-note-2026-04-24", include_archive=True
        )
        assert got is not None
        self.assertTrue(got["in_archive"])

    def test_separator_id_keeps_enumerate_and_match_path(self) -> None:
        # Pre-fn-109 the exact-hit loop resolved `_archive/<id>` by textual
        # path equality against the enumeration; that must keep working.
        self._write(
            "old-2026-01-01", _valid_artifact_text("old-2026-01-01"),
            archived=True,
        )
        got = flowctl._prospect_resolve_id(
            self.prospects, "_archive/old-2026-01-01", include_archive=True
        )
        assert got is not None
        self.assertEqual(got["artifact_id"], "old-2026-01-01")
        self.assertTrue(got["in_archive"])
        # Without include_archive the enumeration has no archive entries -
        # falls through and returns None (unchanged).
        self.assertIsNone(
            flowctl._prospect_resolve_id(
                self.prospects, "_archive/old-2026-01-01",
                include_archive=False,
            )
        )


if __name__ == "__main__":
    unittest.main()

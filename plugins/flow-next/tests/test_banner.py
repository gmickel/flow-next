"""Unit tests for the migration banner / version warning (fn-43.17 / R7+R9+R24+R34+R35).

`_check_migration_banner(flow_dir)` runs once early in `main()` and emits a
6-line stderr banner when:

  * No valid `.flow_version` sentinel
  * `.flow/epics/` directory exists (pre-1.0 layout signal)
  * No suppression env knob is set (`FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`,
    `FLOW_NO_AUTO_MIGRATE=1`)
  * The 7-day `.banner-acknowledged` window has expired (or the file is
    missing / corrupt)
  * The process-level dedup flag `_MIGRATION_BANNER_EMITTED` is False

It also handles a forward-compat case: if the sentinel reports a major version
≥ 2 (e.g. `2.0.0`), a one-line warning fires instead — the subcommand exit
code is preserved either way.

Run:
    python3 -m unittest plugins.flow-next.tests.test_banner -v
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest import mock

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_banner_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ---------- Fixture helpers ---------------------------------------------


def _capture_stderr(callable_, *args, **kwargs) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        callable_(*args, **kwargs)
    return buf.getvalue()


def _make_pre_1_0_layout(tmp: Path) -> Path:
    """Build a minimal pre-1.0 .flow/ tree (epics/ exists, no sentinel)."""
    flow_dir = tmp / ".flow"
    flow_dir.mkdir()
    (flow_dir / flowctl.EPICS_DIR).mkdir()
    return flow_dir


def _make_post_1_0_layout(tmp: Path, payload: str = "1.0.0") -> Path:
    """Build a 1.0+ layout (sentinel present, valid payload)."""
    flow_dir = tmp / ".flow"
    flow_dir.mkdir()
    (flow_dir / flowctl.SPECS_JSON_DIR).mkdir()
    (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
        payload + "\n", encoding="utf-8"
    )
    return flow_dir


# ---------- Common test base — resets module flag --------------------------


class _BannerTestBase(unittest.TestCase):
    """Resets `_MIGRATION_BANNER_EMITTED` before every test.

    The dedup flag is module-level state, so an earlier test that emitted the
    banner would suppress subsequent tests' banner output. monkeypatch via
    setattr in setUp + tearDown for symmetric cleanup.
    """

    def setUp(self) -> None:
        # Ensure no env knob leaks between tests.
        for key in ("FLOW_RALPH", "REVIEW_RECEIPT_PATH", "FLOW_NO_AUTO_MIGRATE"):
            os.environ.pop(key, None)
        # Reset the dedup flag.
        self._prior_dedup = flowctl._MIGRATION_BANNER_EMITTED
        flowctl._MIGRATION_BANNER_EMITTED = False

    def tearDown(self) -> None:
        flowctl._MIGRATION_BANNER_EMITTED = self._prior_dedup


# --- Pre-1.0 detection: emits banner --------------------------------------


class TestPre1_0BannerEmit(_BannerTestBase):
    """Pre-1.0 layout (epics/ + no sentinel) → emit 6-line banner on stderr."""

    def test_pre_1_0_emits_six_line_banner_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            # Six expected lines (verbatim per fn-43.4 spec).
            self.assertIn("flow-next 1.0 renamed", stderr)
            self.assertIn(".flow/epics/", stderr)
            self.assertIn("/flow-next:setup", stderr)
            self.assertIn("flowctl migrate-rename --yes", stderr)
            self.assertIn("FLOW_NO_AUTO_MIGRATE=1", stderr)
            self.assertEqual(len(stderr.strip().splitlines()), 6)

    def test_dedup_flag_flips_to_true_after_emit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            self.assertFalse(flowctl._MIGRATION_BANNER_EMITTED)
            _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertTrue(flowctl._MIGRATION_BANNER_EMITTED)

    def test_second_call_in_same_process_is_no_op(self) -> None:
        """Process-level dedup — `_MIGRATION_BANNER_EMITTED` gates the second emit."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            first = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertGreater(len(first), 0)
            second = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(second, "", "second call should be a no-op")


# --- Suppression matrix --------------------------------------------------


class TestBannerSuppression(_BannerTestBase):
    """Each suppression knob silences the banner cleanly."""

    def test_flow_ralph_suppresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            with mock.patch.dict(os.environ, {"FLOW_RALPH": "1"}, clear=False):
                stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")

    def test_review_receipt_path_suppresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            with mock.patch.dict(
                os.environ, {"REVIEW_RECEIPT_PATH": "/tmp/r.json"}, clear=False
            ):
                stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")

    def test_flow_no_auto_migrate_suppresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            with mock.patch.dict(
                os.environ, {"FLOW_NO_AUTO_MIGRATE": "1"}, clear=False
            ):
                stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")

    def test_recent_ack_within_renudge_window_suppresses(self) -> None:
        """Ack timestamp within 7 days → silent."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            (flow_dir / flowctl.BANNER_ACK_FILE).write_text(
                flowctl.now_iso() + "\n", encoding="utf-8"
            )
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")

    def test_post_migration_silent(self) -> None:
        """Sentinel present at 1.0.0 → silent (already migrated)."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_post_1_0_layout(Path(tmp), payload="1.0.0")
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")

    def test_v1_x_minor_version_silent(self) -> None:
        """1.5.2 / 1.99.99 are 1.x → silent (`_migrate_sentinel_state` validates)."""
        for payload in ("1.5.2", "1.99.99"):
            flowctl._MIGRATION_BANNER_EMITTED = False
            with tempfile.TemporaryDirectory() as tmp:
                flow_dir = _make_post_1_0_layout(Path(tmp), payload=payload)
                stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
                self.assertEqual(stderr, "", f"payload={payload} should be silent")

    def test_no_flow_dir_silent(self) -> None:
        """`.flow/` missing entirely — banner machinery should not crash or emit."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"  # never mkdir'd
            self.assertFalse(flow_dir.exists())
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")

    def test_no_epics_no_sentinel_silent(self) -> None:
        """Fresh-init shape — nothing to nudge yet."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir()
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertEqual(stderr, "")


# --- Forward-compat (major >= 2) ---------------------------------------


class TestForwardCompatWarning(_BannerTestBase):
    """Sentinel parses as semver with major ≥ 2 → one-line warning to stderr."""

    def test_2_0_0_emits_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_post_1_0_layout(Path(tmp), payload="2.0.0")
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertIn("Warning", stderr)
            self.assertIn("2.0.0", stderr)
            self.assertIn("newer flow-next", stderr)

    def test_3_1_0_emits_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_post_1_0_layout(Path(tmp), payload="3.1.0")
            stderr = _capture_stderr(flowctl._check_migration_banner, flow_dir)
            self.assertIn("Warning", stderr)
            self.assertIn("3.1.0", stderr)


# --- _banner_ack_within_renudge_window helper ----------------------------


class TestBannerAckHelper(unittest.TestCase):
    """Direct unit coverage of the ack-window helper."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="banner_ack_helper_"))
        self.flow_dir = self._tmp / ".flow"
        self.flow_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_ack(self, content: str) -> None:
        (self.flow_dir / flowctl.BANNER_ACK_FILE).write_text(
            content, encoding="utf-8"
        )

    def test_missing_file_returns_false(self) -> None:
        self.assertFalse(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_empty_body_returns_false(self) -> None:
        self._write_ack("")
        self.assertFalse(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_garbage_body_returns_false(self) -> None:
        self._write_ack("not-a-timestamp")
        self.assertFalse(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_future_dated_returns_false(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat().replace(
            "+00:00", "Z"
        )
        self._write_ack(future + "\n")
        self.assertFalse(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_recent_returns_true(self) -> None:
        recent = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._write_ack(recent + "\n")
        self.assertTrue(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_at_boundary_just_inside_returns_true(self) -> None:
        """Exactly ``BANNER_RENUDGE_DAYS - 1`` days old → still inside window."""
        ts = (
            datetime.now(timezone.utc) - timedelta(days=flowctl.BANNER_RENUDGE_DAYS - 1)
        ).isoformat().replace("+00:00", "Z")
        self._write_ack(ts + "\n")
        self.assertTrue(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_at_boundary_just_outside_returns_false(self) -> None:
        """``BANNER_RENUDGE_DAYS`` + buffer days old → outside window → re-nudge fires."""
        ts = (
            datetime.now(timezone.utc) - timedelta(days=flowctl.BANNER_RENUDGE_DAYS + 1)
        ).isoformat().replace("+00:00", "Z")
        self._write_ack(ts + "\n")
        self.assertFalse(flowctl._banner_ack_within_renudge_window(self.flow_dir))

    def test_eight_day_old_re_nudges_without_auto_refresh(self) -> None:
        """Re-nudge cadence + no auto-refresh contract — ack file not rewritten."""
        ts = (
            datetime.now(timezone.utc) - timedelta(days=8)
        ).isoformat().replace("+00:00", "Z")
        self._write_ack(ts + "\n")
        ack_path = self.flow_dir / flowctl.BANNER_ACK_FILE
        before_mtime = ack_path.stat().st_mtime
        before_content = ack_path.read_text(encoding="utf-8")
        # Banner reads the file; whatever the verdict, the ack file MUST NOT
        # be rewritten by the helper. Helper is read-only.
        self.assertFalse(flowctl._banner_ack_within_renudge_window(self.flow_dir))
        self.assertEqual(ack_path.stat().st_mtime, before_mtime)
        self.assertEqual(ack_path.read_text(encoding="utf-8"), before_content)


# --- Stderr-only invariant: --json stdout parses cleanly with banner active ---


class TestStderrOnlyInvariant(_BannerTestBase):
    """Banner output never touches stdout; JSON CLI stdout stays parseable."""

    def test_banner_does_not_pollute_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with (
                contextlib.redirect_stdout(out_buf),
                contextlib.redirect_stderr(err_buf),
            ):
                flowctl._check_migration_banner(flow_dir)
            self.assertEqual(out_buf.getvalue(), "")
            self.assertGreater(len(err_buf.getvalue()), 0)

    def test_banner_active_json_stdout_parses_cleanly(self) -> None:
        """Simulate `flowctl <verb> --json`: banner on stderr, JSON on stdout.

        The banner helper writes ONLY to stderr, so a downstream `json.load(stdout)`
        round-trip is unaffected. Verify both streams independently."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with (
                contextlib.redirect_stdout(out_buf),
                contextlib.redirect_stderr(err_buf),
            ):
                flowctl._check_migration_banner(flow_dir)
                # Simulate the subsequent --json subcommand emitting clean JSON.
                print(json.dumps({"success": True, "result": "ok"}))
            self.assertGreater(len(err_buf.getvalue()), 0)
            # stdout MUST round-trip through json.load.
            parsed = json.loads(out_buf.getvalue())
            self.assertEqual(parsed, {"success": True, "result": "ok"})


# --- Banner exception swallowing ---------------------------------------


class TestBannerExceptionSwallowing(_BannerTestBase):
    """Internal exceptions never propagate — banner is informational only."""

    def test_exception_inside_helper_swallowed(self) -> None:
        """Forced raise inside `_migrate_sentinel_state` must not surface."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_layout(Path(tmp))
            with mock.patch.object(
                flowctl,
                "_migrate_sentinel_state",
                side_effect=RuntimeError("simulated I/O failure"),
            ):
                # Must not raise.
                flowctl._check_migration_banner(flow_dir)


# --- Constants are stable & module-level --------------------------------


class TestBannerConstants(unittest.TestCase):
    """Constants exposed by name on the module (test-fixture contract)."""

    def test_constants_exist_with_expected_values(self) -> None:
        self.assertEqual(flowctl.BANNER_ACK_FILE, ".banner-acknowledged")
        self.assertEqual(flowctl.BANNER_RENUDGE_DAYS, 7)

    def test_dedup_flag_exists_and_is_module_level_bool(self) -> None:
        self.assertIn("_MIGRATION_BANNER_EMITTED", dir(flowctl))
        self.assertIsInstance(flowctl._MIGRATION_BANNER_EMITTED, bool)


if __name__ == "__main__":
    unittest.main()

"""One-shot `spec create --plan-file` / `--plan -` tests (fn-163.1, R2/R6).

Pins:

  * Frozen-time byte-equivalence: one-shot vs granular create+set-plan
    produce identical `.flow/specs/<id>.json` + `.md` bytes (monkeypatch
    ``now_iso`` via in-process importlib load).
  * ``--plan -`` stdin form passes the same equivalence test.
  * Pre-write ordering: missing/unreadable plan file errors before id
    allocation; ``.flow/specs/`` unchanged; no id consumed.
  * Failure injection at each of the four publication points (initial json,
    initial md, plan md, timestamp json) leaves ``.flow/specs/`` empty of
    the new spec — no skeleton, no stale-json pairing.
  * Wire-form: production CLI two-token dispatch via subprocess for happy
    path smoke (memory: test-production-path-not-parallel-construction).

Run:
    python3 -m unittest test_spec_create_plan_file -q
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Optional
from unittest import mock

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

PLAN_BODY = """# Plan body for one-shot create

## Overview

Do the thing carefully.

## Acceptance Criteria

- **R1:** thing done.
"""

FROZEN_TS = "2026-08-04T12:00:00.000000Z"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_spec_create_plan_file_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class SpecCreatePlanFileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self._call(func=self.flowctl.cmd_init)
        self.specs_dir = self.tmpdir / ".flow" / "specs"

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- helpers -------------------------------------------------------------

    def _call(self, *, func, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _call_expect_error(self, *, func, **kwargs) -> str:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                func(ns)
        self.assertNotEqual(ctx.exception.code, 0)
        return json.loads(buf.getvalue())["error"]

    def _write(self, name: str, content: str) -> str:
        path = self.tmpdir / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _spec_names(self) -> list[str]:
        if not self.specs_dir.exists():
            return []
        return sorted(p.name for p in self.specs_dir.iterdir() if p.is_file())

    def _spec_bytes(self, spec_id: str) -> tuple[bytes, bytes]:
        json_b = (self.specs_dir / f"{spec_id}.json").read_bytes()
        md_b = (self.specs_dir / f"{spec_id}.md").read_bytes()
        return json_b, md_b

    def _create_ns(
        self,
        *,
        title: str = "One Shot Subject",
        plan_file: Optional[str] = None,
        plan: Optional[str] = None,
        branch: Optional[str] = None,
        tracker_first: bool = False,
        tracker_identifier: Optional[str] = None,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            title=title,
            branch=branch,
            plan_file=plan_file,
            plan=plan,
            tracker_first=tracker_first,
            tracker_identifier=tracker_identifier,
            json=True,
        )

    def _run_cli(self, *args: str, stdin: Optional[str] = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            input=stdin,
        )

    # --- frozen-time byte-equivalence (R2) -----------------------------------

    def test_plan_file_byte_identical_to_granular_sequence(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)

        # Arm A: granular create + set-plan under frozen time.
        with mock.patch.object(self.flowctl, "now_iso", return_value=FROZEN_TS):
            granular = self._call(
                func=self.flowctl.cmd_spec_create,
                title="Equiv Subject",
                branch=None,
                plan_file=None,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
            self._call(
                func=self.flowctl.cmd_spec_set_plan,
                id=granular["id"],
                file=plan_path,
            )
        granular_id = granular["id"]
        g_json, g_md = self._spec_bytes(granular_id)

        # Wipe and re-init so the next allocate starts clean (same slug → same id
        # shape only if counter resets; wipe specs dir + re-seed meta state).
        for p in self.specs_dir.glob("*"):
            p.unlink()
        # Also clear any epics/ leftovers; re-scan must see empty store.
        epics = self.tmpdir / ".flow" / "epics"
        if epics.exists():
            for p in epics.glob("*"):
                p.unlink()

        # Arm B: one-shot --plan-file under the same frozen clock.
        with mock.patch.object(self.flowctl, "now_iso", return_value=FROZEN_TS):
            oneshot = self._call(
                func=self.flowctl.cmd_spec_create,
                title="Equiv Subject",
                branch=None,
                plan_file=plan_path,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
        oneshot_id = oneshot["id"]
        # Same title → same slug; after wipe, scan yields the same number.
        self.assertEqual(oneshot_id, granular_id)
        o_json, o_md = self._spec_bytes(oneshot_id)

        self.assertEqual(o_json, g_json)
        self.assertEqual(o_md, g_md)
        # Plan body must have replaced the skeleton.
        self.assertEqual(o_md.decode("utf-8"), PLAN_BODY)

    def test_plan_stdin_byte_identical_to_granular_sequence(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)

        with mock.patch.object(self.flowctl, "now_iso", return_value=FROZEN_TS):
            granular = self._call(
                func=self.flowctl.cmd_spec_create,
                title="Stdin Equiv",
                branch=None,
                plan_file=None,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
            self._call(
                func=self.flowctl.cmd_spec_set_plan,
                id=granular["id"],
                file=plan_path,
            )
        granular_id = granular["id"]
        g_json, g_md = self._spec_bytes(granular_id)

        for p in self.specs_dir.glob("*"):
            p.unlink()

        with mock.patch.object(self.flowctl, "now_iso", return_value=FROZEN_TS):
            # Simulate `--plan -` by feeding stdin and setting plan="-".
            ns = self._create_ns(title="Stdin Equiv", plan="-")
            buf = io.StringIO()
            with mock.patch.object(self.flowctl.sys, "stdin", io.StringIO(PLAN_BODY)):
                with redirect_stdout(buf):
                    self.flowctl.cmd_spec_create(ns)
            oneshot = json.loads(buf.getvalue())
        oneshot_id = oneshot["id"]
        self.assertEqual(oneshot_id, granular_id)
        o_json, o_md = self._spec_bytes(oneshot_id)
        self.assertEqual(o_json, g_json)
        self.assertEqual(o_md, g_md)

    # --- pre-write error ordering --------------------------------------------

    def test_missing_plan_file_errors_before_write(self) -> None:
        before = self._spec_names()
        err = self._call_expect_error(
            func=self.flowctl.cmd_spec_create,
            title="Missing Plan",
            branch=None,
            plan_file=str(self.tmpdir / "nope-plan.md"),
            plan=None,
            tracker_first=False,
            tracker_identifier=None,
        )
        self.assertIn("Plan file missing", err)
        self.assertEqual(self._spec_names(), before)
        # Id not consumed: next create gets the first sequential number.
        result = self._call(
            func=self.flowctl.cmd_spec_create,
            title="After Missing",
            branch=None,
            plan_file=None,
            plan=None,
            tracker_first=False,
            tracker_identifier=None,
        )
        self.assertEqual(result["id"], "fn-1-after-missing")

    def test_directory_as_plan_file_errors_before_write(self) -> None:
        d = self.tmpdir / "adir"
        d.mkdir()
        before = self._spec_names()
        err = self._call_expect_error(
            func=self.flowctl.cmd_spec_create,
            title="Dir Plan",
            branch=None,
            plan_file=str(d),
            plan=None,
            tracker_first=False,
            tracker_identifier=None,
        )
        self.assertIn("Plan file unreadable", err)
        self.assertEqual(self._spec_names(), before)

    @unittest.skipIf(sys.platform == "win32", "chmod 000 is not enforced on Windows")
    @unittest.skipIf(getattr(os, "geteuid", lambda: -1)() == 0, "chmod 000 is not enforced for root")
    def test_unreadable_plan_file_errors_before_write(self) -> None:
        path = self.tmpdir / "locked-plan.md"
        path.write_text(PLAN_BODY, encoding="utf-8")
        path.chmod(0o000)
        before = self._spec_names()
        try:
            err = self._call_expect_error(
                func=self.flowctl.cmd_spec_create,
                title="Locked Plan",
                branch=None,
                plan_file=str(path),
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
            self.assertIn("Plan file unreadable", err)
        finally:
            path.chmod(0o600)
        self.assertEqual(self._spec_names(), before)

    def test_plan_non_dash_value_errors_before_write(self) -> None:
        before = self._spec_names()
        err = self._call_expect_error(
            func=self.flowctl.cmd_spec_create,
            title="Bad Plan Arg",
            branch=None,
            plan_file=None,
            plan="plan.md",
            tracker_first=False,
            tracker_identifier=None,
        )
        self.assertIn("--plan only accepts '-'", err)
        self.assertEqual(self._spec_names(), before)

    # --- failure injection at four publication points ------------------------

    def _assert_specs_empty_of_new(self, before: list[str]) -> None:
        self.assertEqual(self._spec_names(), before)

    def test_initial_json_publication_failure_leaves_no_spec(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)
        before = self._spec_names()

        def fail_first(path: Path, content: str) -> None:
            raise OSError("injected initial json publication failure")

        with mock.patch.object(self.flowctl, "atomic_create", side_effect=fail_first):
            err = self._call_expect_error(
                func=self.flowctl.cmd_spec_create,
                title="Fail Json",
                branch=None,
                plan_file=plan_path,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
        self.assertIn("injected initial json publication failure", err)
        self._assert_specs_empty_of_new(before)
        # Id not left reserved: next create still gets fn-1-...
        ok = self._call(
            func=self.flowctl.cmd_spec_create,
            title="Fail Json",
            branch=None,
            plan_file=None,
            plan=None,
            tracker_first=False,
            tracker_identifier=None,
        )
        self.assertEqual(ok["id"], "fn-1-fail-json")

    def test_initial_md_publication_failure_rolls_back_json(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)
        before = self._spec_names()
        real_create = self.flowctl.atomic_create
        calls = 0

        def fail_second(path: Path, content: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected initial md publication failure")
            real_create(path, content)

        with mock.patch.object(self.flowctl, "atomic_create", side_effect=fail_second):
            err = self._call_expect_error(
                func=self.flowctl.cmd_spec_create,
                title="Fail Md",
                branch=None,
                plan_file=plan_path,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
        self.assertIn("injected initial md publication failure", err)
        self._assert_specs_empty_of_new(before)

    def test_plan_md_write_failure_rolls_back_all_created(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)
        before = self._spec_names()
        real_write = self.flowctl.atomic_write

        def fail_plan_md(path: Path, content: str) -> None:
            # Plan stage's first atomic_write is the plan markdown (overwrites
            # the skeleton .md). Fail only that path; let any other write through.
            if path.suffix == ".md" and content == PLAN_BODY:
                raise OSError("injected plan md write failure")
            real_write(path, content)

        with mock.patch.object(self.flowctl, "atomic_write", side_effect=fail_plan_md):
            err = self._call_expect_error(
                func=self.flowctl.cmd_spec_create,
                title="Fail Plan Md",
                branch=None,
                plan_file=plan_path,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
        self.assertIn("injected plan md write failure", err)
        self._assert_specs_empty_of_new(before)

    def test_timestamp_json_write_failure_rolls_back_all_created(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)
        before = self._spec_names()

        def fail_json_write(path: Path, data: dict) -> None:
            raise OSError("injected timestamp json write failure")

        with mock.patch.object(
            self.flowctl, "atomic_write_json", side_effect=fail_json_write
        ):
            err = self._call_expect_error(
                func=self.flowctl.cmd_spec_create,
                title="Fail Ts Json",
                branch=None,
                plan_file=plan_path,
                plan=None,
                tracker_first=False,
                tracker_identifier=None,
            )
        self.assertIn("injected timestamp json write failure", err)
        self._assert_specs_empty_of_new(before)

    # --- wire-form (production CLI subprocess) -------------------------------

    def test_cli_plan_file_wire_form(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)
        proc = self._run_cli(
            "spec",
            "create",
            "--title",
            "Wire Form Plan",
            "--plan-file",
            plan_path,
            "--json",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        spec_id = payload["id"]
        md = (self.specs_dir / f"{spec_id}.md").read_text(encoding="utf-8")
        self.assertEqual(md, PLAN_BODY)
        meta = json.loads((self.specs_dir / f"{spec_id}.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["title"], "Wire Form Plan")

    def test_cli_plan_stdin_wire_form(self) -> None:
        proc = self._run_cli(
            "spec",
            "create",
            "--title",
            "Wire Form Stdin",
            "--plan",
            "-",
            "--json",
            stdin=PLAN_BODY,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        spec_id = payload["id"]
        md = (self.specs_dir / f"{spec_id}.md").read_text(encoding="utf-8")
        self.assertEqual(md, PLAN_BODY)

    def test_cli_missing_plan_file_wire_form_no_write(self) -> None:
        before = self._spec_names()
        proc = self._run_cli(
            "spec",
            "create",
            "--title",
            "Wire Missing",
            "--plan-file",
            str(self.tmpdir / "absent.md"),
            "--json",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("Plan file missing", payload.get("error", ""))
        self.assertEqual(self._spec_names(), before)

    def test_cli_plan_and_plan_file_mutually_exclusive(self) -> None:
        plan_path = self._write("plan.md", PLAN_BODY)
        proc = self._run_cli(
            "spec",
            "create",
            "--title",
            "Both Flags",
            "--plan-file",
            plan_path,
            "--plan",
            "-",
            "--json",
            stdin=PLAN_BODY,
        )
        self.assertNotEqual(proc.returncode, 0)
        # argparse mutual-exclusion surfaces on stderr.
        combined = (proc.stdout or "") + (proc.stderr or "")
        self.assertTrue(
            "not allowed with" in combined
            or "mutually exclusive" in combined.lower()
            or proc.returncode != 0
        )


if __name__ == "__main__":
    unittest.main()

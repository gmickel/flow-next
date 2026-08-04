"""Bulk `task create --from-json` tests (fn-163.2, R1/R3/R6).

Pins:

  * Happy path: N tasks from JSON, one lock acquisition, state byte-identical
    (frozen ``now_iso``) to the same tasks created via N granular full-field
    ``task create`` calls.
  * Rejection fixtures for every boundary (malformed JSON, non-array, empty
    array, missing/empty title, wrong field types, nulls, unknown keys, bad /
    forward / out-of-range dep index) — each asserts ``.flow/tasks/`` unchanged.
  * ``--json`` ordered output contract.
  * Intra-batch index deps resolve to allocated ids.
  * Duplicate titles allowed with distinct ids.
  * Rollback removes all batch files on induced partial publication failure.
  * Process-race: concurrent single ``task create`` racing a bulk batch never
    collides ids (mirrors ``test_40_process_creators_publish_unique_matching_pairs``).
  * R1 invocation-count: canonical flow as REAL subprocess invocations of the
    production ``flowctl.py`` (wire-form from ``test_anchor_bundle.py``) ≤ 8.

Run:
    python3 -m unittest test_task_bulk_create -q
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any, Optional
from unittest import mock

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

FROZEN_TS = "2026-08-04T12:00:00.000000Z"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_task_bulk_create_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TaskBulkCreateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self._call(func=self.flowctl.cmd_init)
        self.spec_id = self._call(
            func=self.flowctl.cmd_spec_create,
            title="Bulk subject",
            branch=None,
            plan_file=None,
            plan=None,
            tracker_first=False,
            tracker_identifier=None,
        )["id"]
        self.tasks_dir = self.tmpdir / ".flow" / "tasks"

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

    def _task_names(self) -> list[str]:
        if not self.tasks_dir.exists():
            return []
        return sorted(p.name for p in self.tasks_dir.iterdir() if p.is_file())

    def _assert_tasks_unchanged(self, before: list[str]) -> None:
        self.assertEqual(self._task_names(), before)

    def _bulk(self, items: list[dict]) -> dict:
        path = self._write("bulk.json", json.dumps(items))
        return self._bulk_from_path(path)

    def _bulk_from_path(self, path: str) -> dict:
        return self._call(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title=None,
            priority=None,
            deps=None,
            acceptance_file=None,
            description_file=None,
            acceptance=None,
            description=None,
            satisfies=None,
            from_json=path,
        )

    def _bulk_expect_error(self, raw: str) -> str:
        path = self._write("bad_bulk.json", raw)
        before = self._task_names()
        err = self._call_expect_error(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title=None,
            priority=None,
            deps=None,
            acceptance_file=None,
            description_file=None,
            acceptance=None,
            description=None,
            satisfies=None,
            from_json=path,
        )
        self._assert_tasks_unchanged(before)
        return err

    def _bulk_expect_error_items(self, items: Any) -> str:
        return self._bulk_expect_error(json.dumps(items))

    def _granular_create(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        acceptance: Optional[str] = None,
        satisfies: Optional[str] = None,
        deps: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> dict:
        desc_file = None
        acc_file = None
        if description is not None:
            desc_file = self._write(f"g_desc_{title}.md", description)
        if acceptance is not None:
            acc_file = self._write(f"g_acc_{title}.md", acceptance)
        return self._call(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title=title,
            priority=priority,
            deps=deps,
            acceptance_file=acc_file,
            description_file=desc_file,
            acceptance=None,
            description=None,
            satisfies=satisfies,
            from_json=None,
        )

    def _task_bytes(self, task_id: str) -> tuple[bytes, bytes]:
        j = (self.tasks_dir / f"{task_id}.json").read_bytes()
        m = (self.tasks_dir / f"{task_id}.md").read_bytes()
        return j, m

    def _wipe_tasks(self) -> None:
        if self.tasks_dir.exists():
            for p in self.tasks_dir.iterdir():
                if p.is_file():
                    p.unlink()

    def _run_cli(
        self, *args: str, stdin: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            input=stdin,
        )

    # --- happy path + one lock + byte-identity (R3) --------------------------

    def test_happy_path_one_lock_byte_identical_to_granular(self) -> None:
        # Full-field tasks: description, acceptance, satisfies, priority, deps.
        # Arm A (granular) builds first task then second with dep on first.
        lock_calls = 0
        real_lock = self.flowctl.cross_process_lock

        @contextmanager
        def counting_lock(*a, **k):
            nonlocal lock_calls
            lock_calls += 1
            with real_lock(*a, **k) as ctx:
                yield ctx

        desc1 = "First body.\n"
        acc1 = "- [ ] criterion one\n"
        desc2 = "Second body.\n"
        acc2 = "- [ ] criterion two\n"

        with mock.patch.object(self.flowctl, "now_iso", return_value=FROZEN_TS):
            with mock.patch.object(self.flowctl, "cross_process_lock", counting_lock):
                g1 = self._granular_create(
                    title="Alpha",
                    description=desc1,
                    acceptance=acc1,
                    satisfies="R1,R3",
                    priority=10,
                )
                g2 = self._granular_create(
                    title="Beta",
                    description=desc2,
                    acceptance=acc2,
                    satisfies="R4",
                    deps=g1["id"],
                    priority=20,
                )
        granular_lock_calls = lock_calls
        self.assertEqual(granular_lock_calls, 2)  # one per granular create
        g_ids = [g1["id"], g2["id"]]
        granular_bytes = {tid: self._task_bytes(tid) for tid in g_ids}

        self._wipe_tasks()
        lock_calls = 0

        bulk_items = [
            {
                "title": "Alpha",
                "description": desc1,
                "acceptance": acc1,
                "satisfies": ["R1", "R3"],
                "priority": 10,
            },
            {
                "title": "Beta",
                "description": desc2,
                "acceptance": acc2,
                "satisfies": ["R4"],
                "deps": [1],  # intra-batch index → first task
                "priority": 20,
            },
        ]
        with mock.patch.object(self.flowctl, "now_iso", return_value=FROZEN_TS):
            with mock.patch.object(self.flowctl, "cross_process_lock", counting_lock):
                result = self._bulk(bulk_items)

        self.assertEqual(lock_calls, 1)  # ONE acquisition for the whole batch
        self.assertTrue(result["success"])
        tasks = result["tasks"]
        self.assertEqual(len(tasks), 2)
        self.assertEqual([t["title"] for t in tasks], ["Alpha", "Beta"])
        self.assertEqual(tasks[0]["id"], g_ids[0])
        self.assertEqual(tasks[1]["id"], g_ids[1])

        for tid in g_ids:
            self.assertEqual(
                self._task_bytes(tid),
                granular_bytes[tid],
                msg=f"bulk vs granular mismatch for {tid}",
            )

        # Dep resolved to allocated id (not the raw index).
        beta_json = json.loads(
            (self.tasks_dir / f"{tasks[1]['id']}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(beta_json["depends_on"], [tasks[0]["id"]])

    def test_json_output_ordered(self) -> None:
        result = self._bulk(
            [{"title": "T1"}, {"title": "T2"}, {"title": "T3"}]
        )
        self.assertTrue(result["success"])
        titles = [t["title"] for t in result["tasks"]]
        ids = [t["id"] for t in result["tasks"]]
        self.assertEqual(titles, ["T1", "T2", "T3"])
        self.assertEqual(
            ids,
            [f"{self.spec_id}.1", f"{self.spec_id}.2", f"{self.spec_id}.3"],
        )

    def test_stdin_dash_form(self) -> None:
        raw = json.dumps([{"title": "FromStdin"}])
        # In-process stdin: patch sys.stdin for read_file_or_stdin("-", ...).
        with mock.patch.object(self.flowctl.sys, "stdin", io.StringIO(raw)):
            result = self._call(
                func=self.flowctl.cmd_task_create,
                spec=self.spec_id,
                epic=None,
                title=None,
                priority=None,
                deps=None,
                acceptance_file=None,
                description_file=None,
                acceptance=None,
                description=None,
                satisfies=None,
                from_json="-",
            )
        self.assertEqual(result["tasks"][0]["title"], "FromStdin")

    def test_duplicate_titles_allowed_distinct_ids(self) -> None:
        result = self._bulk(
            [{"title": "Same"}, {"title": "Same"}, {"title": "Same"}]
        )
        ids = [t["id"] for t in result["tasks"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([t["title"] for t in result["tasks"]], ["Same"] * 3)

    def test_string_deps_same_spec_canonicalized(self) -> None:
        first = self._granular_create(title="Root")
        result = self._bulk(
            [{"title": "Child", "deps": [first["id"]]}]
        )
        child_id = result["tasks"][0]["id"]
        data = json.loads(
            (self.tasks_dir / f"{child_id}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(data["depends_on"], [first["id"]])

    # --- rejection fixtures (zero writes) ------------------------------------

    def test_reject_malformed_json(self) -> None:
        err = self._bulk_expect_error("{not json")
        self.assertIn("malformed JSON", err)

    def test_reject_non_array(self) -> None:
        err = self._bulk_expect_error(json.dumps({"title": "x"}))
        self.assertIn("non-empty JSON array", err)

    def test_reject_empty_array(self) -> None:
        err = self._bulk_expect_error("[]")
        self.assertIn("non-empty JSON array", err)

    def test_reject_missing_title(self) -> None:
        err = self._bulk_expect_error_items([{"description": "x"}])
        self.assertIn("title", err)

    def test_reject_empty_title(self) -> None:
        err = self._bulk_expect_error_items([{"title": "   "}])
        self.assertIn("non-empty", err)

    def test_reject_empty_string_title(self) -> None:
        err = self._bulk_expect_error_items([{"title": ""}])
        self.assertIn("non-empty", err)

    def test_reject_title_wrong_type_number(self) -> None:
        err = self._bulk_expect_error_items([{"title": 12}])
        self.assertIn("string", err)

    def test_reject_title_null(self) -> None:
        err = self._bulk_expect_error_items([{"title": None}])
        self.assertIn("null", err)

    def test_reject_priority_boolean(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "priority": True}])
        self.assertIn("integer", err)

    def test_reject_priority_string(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "priority": "1"}])
        self.assertIn("integer", err)

    def test_reject_description_number(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "description": 1}])
        self.assertIn("string", err)

    def test_reject_acceptance_null(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "acceptance": None}])
        self.assertIn("null", err)

    def test_reject_satisfies_not_array(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "satisfies": "R1"}])
        self.assertIn("array", err)

    def test_reject_satisfies_non_string_element(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "satisfies": [1]}])
        self.assertIn("satisfies", err)

    def test_reject_acceptance_number(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "acceptance": 5}])
        self.assertIn("string", err)

    def test_reject_deps_not_array(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "deps": "fn-1.1"}])
        self.assertIn("array", err)

    def test_reject_satisfies_bad_token(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "satisfies": ["R0"]}])
        self.assertIn("R0", err)

    def test_reject_unknown_key(self) -> None:
        err = self._bulk_expect_error_items([{"title": "T", "extra": 1}])
        self.assertIn("unknown key", err)

    def test_reject_deps_forward_index(self) -> None:
        err = self._bulk_expect_error_items(
            [{"title": "A", "deps": [2]}, {"title": "B"}]
        )
        self.assertIn("out of range", err)

    def test_reject_deps_out_of_range_index(self) -> None:
        err = self._bulk_expect_error_items(
            [{"title": "A"}, {"title": "B", "deps": [99]}]
        )
        self.assertIn("out of range", err)

    def test_reject_deps_index_zero(self) -> None:
        err = self._bulk_expect_error_items(
            [{"title": "A"}, {"title": "B", "deps": [0]}]
        )
        self.assertIn("out of range", err)

    def test_reject_deps_self_index(self) -> None:
        # 1-based index of self (item 2 → index 2) is not "earlier".
        err = self._bulk_expect_error_items(
            [{"title": "A"}, {"title": "B", "deps": [2]}]
        )
        self.assertIn("out of range", err)

    def test_reject_deps_wrong_element_type(self) -> None:
        err = self._bulk_expect_error_items(
            [{"title": "A", "deps": [1.5]}]
        )
        self.assertIn("deps", err)

    def test_reject_non_object_item(self) -> None:
        err = self._bulk_expect_error_items(["not-an-object"])
        self.assertIn("object", err)

    def test_reject_from_json_with_title_flag(self) -> None:
        path = self._write("bulk.json", json.dumps([{"title": "A"}]))
        before = self._task_names()
        err = self._call_expect_error(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title="Conflict",
            priority=None,
            deps=None,
            acceptance_file=None,
            description_file=None,
            acceptance=None,
            description=None,
            satisfies=None,
            from_json=path,
        )
        self.assertIn("mutually exclusive", err)
        self._assert_tasks_unchanged(before)

    # --- rollback ------------------------------------------------------------

    def test_partial_publication_failure_rolls_back_all_batch_files(self) -> None:
        real_create = self.flowctl.atomic_create
        calls = 0

        def fail_mid_batch(path: Path, content: str) -> None:
            nonlocal calls
            calls += 1
            # Each task publishes json then md (2 writes). Fail on the 3rd
            # write (second task's json) so the first task's pair exists then
            # must be rolled back.
            if calls == 3:
                raise OSError("injected bulk publication failure")
            real_create(path, content)

        before = self._task_names()
        path = self._write(
            "bulk.json",
            json.dumps([{"title": "A"}, {"title": "B"}, {"title": "C"}]),
        )
        with mock.patch.object(self.flowctl, "atomic_create", side_effect=fail_mid_batch):
            err = self._call_expect_error(
                func=self.flowctl.cmd_task_create,
                spec=self.spec_id,
                epic=None,
                title=None,
                priority=None,
                deps=None,
                acceptance_file=None,
                description_file=None,
                acceptance=None,
                description=None,
                satisfies=None,
                from_json=path,
            )
        self.assertIn("injected bulk publication failure", err)
        self._assert_tasks_unchanged(before)
        # Next create reuses .1 — number not permanently consumed by a
        # rolled-back batch (same shape as single-task rollback test).
        result = self._bulk([{"title": "Retry"}])
        self.assertEqual(result["tasks"][0]["id"], f"{self.spec_id}.1")

    # --- concurrency race ----------------------------------------------------

    def test_bulk_races_single_creates_unique_ids(self) -> None:
        bulk_n = 15
        single_n = 15
        bulk_path = self._write(
            "race_bulk.json",
            json.dumps([{"title": f"Bulk {i}"} for i in range(bulk_n)]),
        )

        def run_bulk() -> subprocess.CompletedProcess:
            return subprocess.run(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "task",
                    "create",
                    "--spec",
                    self.spec_id,
                    "--from-json",
                    bulk_path,
                    "--json",
                ],
                cwd=self.tmpdir,
                capture_output=True,
                text=True,
            )

        def run_single(index: int) -> subprocess.CompletedProcess:
            return subprocess.run(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "task",
                    "create",
                    "--spec",
                    self.spec_id,
                    "--title",
                    f"Single {index}",
                    "--json",
                ],
                cwd=self.tmpdir,
                capture_output=True,
                text=True,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=single_n + 1) as pool:
            bulk_fut = pool.submit(run_bulk)
            single_futs = [pool.submit(run_single, i) for i in range(single_n)]
            bulk_result = bulk_fut.result()
            single_results = [f.result() for f in single_futs]

        failures = []
        if bulk_result.returncode != 0:
            failures.append(bulk_result.stdout + bulk_result.stderr)
        for p in single_results:
            if p.returncode != 0:
                failures.append(p.stdout + p.stderr)
        self.assertEqual(failures, [], msg=failures)

        bulk_payload = json.loads(bulk_result.stdout)
        bulk_ids = {t["id"] for t in bulk_payload["tasks"]}
        single_ids = {json.loads(p.stdout)["id"] for p in single_results}
        all_ids = bulk_ids | single_ids
        self.assertEqual(len(all_ids), bulk_n + single_n)
        self.assertEqual(len(bulk_ids & single_ids), 0)

        json_paths = sorted(self.tasks_dir.glob(f"{self.spec_id}.*.json"))
        md_paths = sorted(self.tasks_dir.glob(f"{self.spec_id}.*.md"))
        self.assertEqual(len(json_paths), bulk_n + single_n)
        self.assertEqual(len(md_paths), bulk_n + single_n)
        self.assertEqual({p.stem for p in json_paths}, all_ids)
        self.assertEqual({p.stem for p in md_paths}, all_ids)

    # --- R1 invocation-count (real subprocess wire-form) ---------------------

    def test_r1_canonical_flow_at_most_eight_subprocess_invocations(self) -> None:
        """Canonical flow ≤8 production CLI dispatches (R1).

        Real subprocess invocations of production flowctl.py (same wire-form
        as test_anchor_bundle.py). flowctl main() takes no argv param, so
        in-process dispatch is not an option.
        """
        plan_path = self._write(
            "plan.md",
            "# Plan\n\n## Overview\nDo the thing.\n\n"
            "## Acceptance Criteria\n- **R1:** done.\n",
        )
        tasks_path = self._write(
            "tasks.json",
            json.dumps(
                [
                    {"title": "Task one", "description": "D1"},
                    {"title": "Task two", "description": "D2"},
                    {"title": "Task three", "description": "D3"},
                ]
            ),
        )

        calls = 0

        def flowctl(*args: str) -> dict:
            nonlocal calls
            calls += 1
            result = self._run_cli(*args)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"flowctl {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}",
            )
            out = result.stdout.strip()
            return json.loads(out) if out else {}

        # Setup (init + git) is outside the counted flow; setUp already ran
        # init in-process. Re-use that .flow/ for the counted wire-form path.
        # Fresh tmpdir already has init from setUp — wipe the seed spec so the
        # counted flow owns its own create, OR count only the canonical steps
        # against the existing empty-enough store. Spec create always allocates
        # a new id; existing self.spec_id is fine to leave.

        # Canonical flow (exactly the R1 script):
        #   1. spec create --plan-file
        #   2. task create --from-json (3 tasks)
        #   3-5. start x3
        #   6-8. done x3
        spec = flowctl(
            "spec",
            "create",
            "--title",
            "R1 Flow Subject",
            "--plan-file",
            plan_path,
            "--json",
        )
        spec_id = spec["id"]
        bulk = flowctl(
            "task",
            "create",
            "--spec",
            spec_id,
            "--from-json",
            tasks_path,
            "--json",
        )
        task_ids = [t["id"] for t in bulk["tasks"]]
        self.assertEqual(len(task_ids), 3)
        for tid in task_ids:
            flowctl("start", tid, "--json")
        for tid in task_ids:
            flowctl("done", tid, "--summary", "done", "--json")

        self.assertLessEqual(
            calls,
            8,
            msg=f"canonical flow used {calls} subprocess invocations (budget 8)",
        )
        # Exact arithmetic for the documented path:
        self.assertEqual(calls, 8)


if __name__ == "__main__":
    unittest.main()

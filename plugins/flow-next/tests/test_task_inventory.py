"""Unified task inventory, bulk runtime, and reverse-graph regressions."""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl():
    spec = importlib.util.spec_from_file_location(
        "flowctl_task_inventory_under_test", FLOWCTL_PY
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


flowctl = _load_flowctl()


class TaskInventoryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.previous_cwd = Path.cwd()
        self.previous_state_dir = os.environ.get("FLOW_STATE_DIR")
        os.chdir(self.tmp)
        self.flow = self.tmp / ".flow"
        for relative in ("specs", "epics", "tasks", "memory"):
            (self.flow / relative).mkdir(parents=True)
        (self.flow / "meta.json").write_text(
            json.dumps({"schema_version": 3}), encoding="utf-8"
        )
        self.state_dir = self.tmp / "state"
        os.environ["FLOW_STATE_DIR"] = str(self.state_dir)

    def tearDown(self) -> None:
        os.chdir(self.previous_cwd)
        if self.previous_state_dir is None:
            os.environ.pop("FLOW_STATE_DIR", None)
        else:
            os.environ["FLOW_STATE_DIR"] = self.previous_state_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_spec(
        self,
        spec_id: str,
        *,
        title: str | None = None,
        directory: str = "specs",
        status: str = "open",
    ) -> None:
        data = {
            "id": spec_id,
            "title": title or spec_id,
            "status": status,
            "depends_on_epics": [],
            "spec_path": f".flow/specs/{spec_id}.md",
        }
        (self.flow / directory / f"{spec_id}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        if directory == "specs":
            (self.flow / "specs" / f"{spec_id}.md").write_text(
                f"# {spec_id}\n", encoding="utf-8"
            )

    def write_task(
        self,
        task_id: str,
        *,
        spec_id: str | None = None,
        status: str = "todo",
        depends_on: list[str] | None = None,
        legacy: bool = False,
        with_markdown: bool = False,
    ) -> None:
        owning_spec = spec_id or task_id.rsplit(".", 1)[0]
        data = {
            "id": task_id,
            ("epic" if legacy else "spec"): owning_spec,
            "title": task_id,
            "status": status,
            ("deps" if legacy else "depends_on"): depends_on or [],
            "spec_path": f".flow/tasks/{task_id}.md",
        }
        (self.flow / "tasks" / f"{task_id}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        if with_markdown:
            (self.flow / "tasks" / f"{task_id}.md").write_text(
                f"# {task_id}\n\n"
                "## Description\nX\n\n"
                "## Acceptance\n- [ ] X\n\n"
                "## Done summary\nTBD\n\n"
                "## Evidence\n- Commits:\n- Tests:\n- PRs:\n",
                encoding="utf-8",
            )

    def write_runtime(self, task_id: str, data: dict) -> None:
        state_tasks = self.state_dir / "tasks"
        state_tasks.mkdir(parents=True, exist_ok=True)
        (state_tasks / f"{task_id}.state.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def call(self, function, **kwargs):
        kwargs.setdefault("json", True)
        output = io.StringIO()
        with redirect_stdout(output):
            function(argparse.Namespace(**kwargs))
        text = output.getvalue().strip()
        return json.loads(text) if text else None

    def call_human(self, function, **kwargs) -> str:
        kwargs["json"] = False
        output = io.StringIO()
        with redirect_stdout(output):
            function(argparse.Namespace(**kwargs))
        return output.getvalue()


class TestUnifiedTaskUniverse(TaskInventoryCase):
    def seed_mixed_universe(self) -> None:
        self.write_spec("fn-1", title="canonical")
        self.write_spec("fn-1", title="legacy shadow", directory="epics")
        self.write_spec("wor-7-tracker", title="tracker")
        self.write_task("fn-1.1", legacy=True)
        self.write_task("wor-7-tracker.1")
        self.write_runtime("fn-1.1", {"status": "done"})
        # Task-shaped artifact: eligible filename, non-task payload.
        (self.flow / "tasks" / "fn-1.2.json").write_text(
            json.dumps({"review": "artifact"}), encoding="utf-8"
        )
        (self.flow / "tasks" / "fn-1.1-review.json").write_text(
            json.dumps({"id": "not-a-task"}), encoding="utf-8"
        )

    def test_all_backlog_surfaces_share_mixed_task_universe(self) -> None:
        self.seed_mixed_universe()

        inventory = flowctl.TaskInventory.load(self.flow)
        self.assertEqual(
            [task["id"] for task in inventory.ordered],
            ["fn-1.1", "wor-7-tracker.1"],
        )
        self.assertEqual(inventory.by_id["fn-1.1"]["status"], "done")
        self.assertEqual(inventory.by_id["fn-1.1"]["spec"], "fn-1")

        tasks = self.call(flowctl.cmd_tasks, spec=None, status=None)
        listed = self.call(flowctl.cmd_list)
        specs = self.call(flowctl.cmd_specs)
        status = self.call(flowctl.cmd_status)

        expected_ids = ["fn-1.1", "wor-7-tracker.1"]
        self.assertEqual([task["id"] for task in tasks["tasks"]], expected_ids)
        self.assertEqual([task["id"] for task in listed["tasks"]], expected_ids)
        self.assertEqual(listed["task_count"], 2)
        self.assertEqual(status["tasks"]["done"], 1)
        self.assertEqual(status["tasks"]["todo"], 1)
        self.assertEqual(
            [(spec["id"], spec["title"], spec["tasks"], spec["done"])
             for spec in specs["specs"]],
            [
                ("fn-1", "canonical", 1, 1),
                ("wor-7-tracker", "tracker", 1, 0),
            ],
        )

    def test_bulk_runtime_factory_and_delete_contract(self) -> None:
        self.write_spec("fn-1")
        self.write_task("fn-1.1")
        self.write_task("fn-1.2")
        self.write_runtime("fn-1.1", {"status": "done"})

        real_factory = flowctl.get_state_store
        with mock.patch.object(
            flowctl, "get_state_store", wraps=real_factory
        ) as factory:
            inventory = flowctl.TaskInventory.load(self.flow)
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(inventory.by_id["fn-1.1"]["status"], "done")
        self.assertEqual(inventory.by_id["fn-1.2"]["status"], "todo")

        store = real_factory()
        store.delete_runtime("fn-1.1")
        self.assertIsNone(store.load_runtime("fn-1.1"))

    def test_bulk_runtime_exact_ids_avoid_directory_walk_and_bad_utf8(self) -> None:
        self.write_spec("fn-1")
        self.write_task("fn-1.1")
        state_tasks = self.state_dir / "tasks"
        state_tasks.mkdir(parents=True)
        bad_state = state_tasks / "fn-1.1.state.json"
        bad_state.write_bytes(b"\xff\xfe")

        store = flowctl.get_state_store()
        with mock.patch.object(
            Path, "glob", side_effect=AssertionError("unexpected state scan")
        ):
            self.assertEqual(store.load_all_runtime({"fn-1.1"}), {})
        self.assertIsNone(store.load_runtime("fn-1.1"))
        inventory = flowctl.TaskInventory.load(self.flow)
        self.assertEqual(inventory.by_id["fn-1.1"]["status"], "todo")

    def test_scoped_commands_ignore_unrelated_malformed_task(self) -> None:
        self.write_spec("fn-1")
        self.write_spec("fn-2")
        self.write_task("fn-1.1", with_markdown=True)
        (self.flow / "tasks" / "fn-2.1.json").write_text(
            "{broken", encoding="utf-8"
        )

        shown = self.call(flowctl.cmd_show, id="fn-1")
        tasks = self.call(flowctl.cmd_tasks, spec="fn-1", status=None)
        with mock.patch.object(flowctl, "get_actor", return_value="tester"):
            ready = self.call(flowctl.cmd_ready, spec="fn-1", all=False)
            next_task = self.call(
                flowctl.cmd_next,
                specs_file=None,
                require_plan_review=False,
                require_completion_review=False,
            )
        validated = self.call(
            flowctl.cmd_validate, spec="fn-1", all=False
        )

        self.assertEqual([task["id"] for task in shown["tasks"]], ["fn-1.1"])
        self.assertEqual([task["id"] for task in tasks["tasks"]], ["fn-1.1"])
        self.assertEqual([task["id"] for task in ready["ready"]], ["fn-1.1"])
        self.assertEqual(next_task["task"], "fn-1.1")
        self.assertTrue(validated["valid"])

    def test_known_spec_commands_ignore_malformed_tasks_for_unknown_specs(self) -> None:
        self.write_spec("fn-1")
        self.write_task("fn-1.1", with_markdown=True)
        (self.flow / "tasks" / "fn-99.1.json").write_text(
            "{broken", encoding="utf-8"
        )

        specs = self.call(flowctl.cmd_specs)
        validated = self.call(
            flowctl.cmd_validate, spec=None, all=True
        )

        task_reads: list[str] = []
        real_load = flowctl.load_json

        def record_load(path: Path):
            if path.parent.name == "tasks":
                task_reads.append(path.name)
            return real_load(path)

        with mock.patch.object(flowctl, "load_json", side_effect=record_load):
            with mock.patch.object(flowctl, "get_actor", return_value="tester"):
                next_task = self.call(
                    flowctl.cmd_next,
                    specs_file=None,
                    require_plan_review=False,
                    require_completion_review=False,
                )

        self.assertEqual(
            [
                (spec["id"], spec["tasks"], spec["done"])
                for spec in specs["specs"]
            ],
            [("fn-1", 1, 0)],
        )
        self.assertTrue(validated["valid"])
        self.assertEqual(validated["total_tasks"], 1)
        self.assertEqual(next_task["task"], "fn-1.1")
        self.assertEqual(task_reads, ["fn-1.1.json"])

    def test_payload_identity_and_owner_corruption_is_diagnosable(self) -> None:
        self.write_spec("fn-1")
        task_path = self.flow / "tasks" / "fn-1.1.json"
        corrupt_payloads = (
            ({"id": "fn-1.2", "spec": "fn-1"}, "payload id is fn-1.2"),
            ({"id": "fn-1.1"}, "owning spec is None"),
            ({"id": 1, "spec": "fn-1"}, "invalid payload id 1"),
        )
        for payload, expected in corrupt_payloads:
            with self.subTest(expected=expected):
                task_path.write_text(
                    json.dumps(
                        {
                            **payload,
                            "title": "corrupt",
                            "status": "todo",
                            "depends_on": [],
                        }
                    ),
                    encoding="utf-8",
                )
                inventory = flowctl.TaskInventory.load(
                    self.flow,
                    spec_id="fn-1",
                    collect_consistency_errors=True,
                )
                self.assertEqual(inventory.ordered, [])
                (issue,) = inventory.issues_by_spec["fn-1"]
                self.assertIn(expected, issue)
                errors, _, count = flowctl.validate_epic(
                    self.flow,
                    "fn-1",
                    inventory=inventory,
                )
                self.assertEqual(count, 0)
                self.assertIn(issue, errors)

    def test_human_output_order_is_golden(self) -> None:
        self.seed_mixed_universe()
        self.assertEqual(
            self.call_human(flowctl.cmd_specs),
            "Specs (2):\n\n"
            "  [open] fn-1: canonical (1/1 tasks done)\n"
            "  [open] wor-7-tracker: tracker (0/1 tasks done)\n",
        )
        self.assertEqual(
            self.call_human(flowctl.cmd_tasks, spec=None, status=None),
            "Tasks (2):\n\n"
            "  [done] fn-1.1: fn-1.1\n"
            "  [todo] wor-7-tracker.1: wor-7-tracker.1\n",
        )
        self.assertEqual(
            self.call_human(flowctl.cmd_list),
            "Flow Status: 2 specs, 2 tasks (1 done)\n\n"
            "[open] fn-1: canonical (1/1 done)\n"
            "    [done] fn-1.1: fn-1.1\n\n"
            "[open] wor-7-tracker: tracker (0/1 done)\n"
            "    [todo] wor-7-tracker.1: wor-7-tracker.1\n\n",
        )


class TestReverseDependencyInventory(TaskInventoryCase):
    def seed_graph(self) -> list[str]:
        for spec_id in ("fn-1", "fn-2", "wor-7-track"):
            self.write_spec(spec_id)
        self.write_task("fn-1.1")
        self.write_task("fn-1.2", depends_on=["fn-1.1"], legacy=True)
        self.write_task("fn-1.3", depends_on=["fn-1.1"])
        self.write_task("fn-1.4", depends_on=["fn-1.2", "fn-1.3"])
        self.write_task("fn-1.5", depends_on=["fn-1.4", "fn-1.6"])
        self.write_task("fn-1.6", depends_on=["fn-1.5"])
        self.write_task("fn-2.1", depends_on=["fn-1.3"])
        self.write_task("wor-7-track.1", depends_on=["fn-2.1"])
        malformed_dependencies = {
            "fn-1.20": None,
            "fn-1.21": {"not": "a list"},
            "fn-1.22": [{"not": "hashable"}, "bad", "fn-1.1"],
        }
        for task_id, dependencies in malformed_dependencies.items():
            (self.flow / "tasks" / f"{task_id}.json").write_text(
                json.dumps(
                    {
                        "id": task_id,
                        "spec": "fn-1",
                        "title": task_id,
                        "status": "todo",
                        "depends_on": dependencies,
                    }
                ),
                encoding="utf-8",
            )
        malformed = self.flow / "tasks" / "fn-1.99.json"
        malformed.write_text("{broken", encoding="utf-8")
        return [path.name for path in flowctl.iter_task_json_files(self.flow)]

    def assert_single_read_graph(self, *, same_spec: bool, expected: list[str]) -> None:
        eligible = self.seed_graph()
        real_load = flowctl.load_json
        reads: Counter[str] = Counter()

        def counting_load(path: Path):
            reads[path.name] += 1
            return real_load(path)

        with mock.patch.object(flowctl, "load_json", side_effect=counting_load):
            actual = flowctl.find_dependents("fn-1.1", same_epic=same_spec)

        self.assertEqual(actual, expected)
        self.assertEqual(set(reads), set(eligible))
        self.assertTrue(all(count == 1 for count in reads.values()), reads)

    def test_chain_diamond_cycle_malformed_same_spec(self) -> None:
        self.assert_single_read_graph(
            same_spec=True,
            expected=[
                "fn-1.2",
                "fn-1.22",
                "fn-1.3",
                "fn-1.4",
                "fn-1.5",
                "fn-1.6",
            ],
        )

    def test_cross_spec_and_tracker_dependents(self) -> None:
        self.assert_single_read_graph(
            same_spec=False,
            expected=[
                "fn-1.2",
                "fn-1.22",
                "fn-1.3",
                "fn-1.4",
                "fn-1.5",
                "fn-1.6",
                "fn-2.1",
                "wor-7-track.1",
            ],
        )


class TestCommandScanBudgets(TaskInventoryCase):
    def seed_valid(self) -> None:
        self.write_spec("fn-1")
        self.write_task("fn-1.1", with_markdown=True)

    def test_specs_next_and_validate_all_scan_tasks_once_each(self) -> None:
        self.seed_valid()
        commands = [
            (flowctl.cmd_specs, {"json": True}),
            (
                flowctl.cmd_next,
                {
                    "json": True,
                    "specs_file": None,
                    "require_plan_review": False,
                    "require_completion_review": False,
                },
            ),
            (flowctl.cmd_validate, {"json": True, "spec": None, "all": True}),
        ]
        for function, kwargs in commands:
            with self.subTest(command=function.__name__):
                with mock.patch.object(
                    flowctl,
                    "iter_task_json_files",
                    wraps=flowctl.iter_task_json_files,
                ) as scanner:
                    with mock.patch.object(flowctl, "get_actor", return_value="tester"):
                        self.call(function, **kwargs)
                self.assertEqual(scanner.call_count, 1)

    def test_next_plan_review_fast_path_does_not_scan_tasks(self) -> None:
        self.seed_valid()
        with mock.patch.object(
            flowctl,
            "iter_task_json_files",
            wraps=flowctl.iter_task_json_files,
        ) as scanner:
            with mock.patch.object(flowctl, "get_actor", return_value="tester"):
                result = self.call(
                    flowctl.cmd_next,
                    specs_file=None,
                    require_plan_review=True,
                    require_completion_review=False,
                )
        self.assertEqual(result["status"], "plan")
        self.assertEqual(scanner.call_count, 0)

    def test_404_task_status_and_list_read_and_spawn_budgets(self) -> None:
        for spec_number in range(1, 5):
            spec_id = f"fn-{spec_number}"
            self.write_spec(spec_id)
            for task_number in range(1, 102):
                self.write_task(f"{spec_id}.{task_number}")

        def assert_budget(function) -> None:
            reads: Counter[str] = Counter()
            real_load = flowctl.load_json
            real_load_or_exit = flowctl.load_json_or_exit

            def count_load(path: Path):
                if path.parent.name == "tasks":
                    reads[path.name] += 1
                return real_load(path)

            def count_load_or_exit(path: Path, *args, **kwargs):
                if path.parent.name == "tasks":
                    reads[path.name] += 1
                return real_load_or_exit(path, *args, **kwargs)

            with mock.patch.object(flowctl, "load_json", side_effect=count_load):
                with mock.patch.object(
                    flowctl, "load_json_or_exit", side_effect=count_load_or_exit
                ):
                    with mock.patch.object(
                        flowctl.subprocess,
                        "run",
                        side_effect=AssertionError("unexpected subprocess"),
                    ):
                        with mock.patch.object(
                            flowctl, "get_repo_root", return_value=self.tmp
                        ):
                            payload = self.call(function)

            self.assertEqual(len(reads), 404)
            self.assertTrue(all(count == 1 for count in reads.values()), reads)
            observed = (
                payload["task_count"]
                if function is flowctl.cmd_list
                else sum(payload["tasks"].values())
            )
            self.assertEqual(observed, 404)

        assert_budget(flowctl.cmd_status)
        assert_budget(flowctl.cmd_list)


if __name__ == "__main__":
    unittest.main()

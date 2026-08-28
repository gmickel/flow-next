"""fn-209 R8: flowctl next surfaces the zero-task (never-planned) spec state."""

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
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl():
    spec = importlib.util.spec_from_file_location(
        "flowctl_next_zero_task_under_test", FLOWCTL_PY
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


flowctl = _load_flowctl()


class NextZeroTaskCase(unittest.TestCase):
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

    def _cmd_next(self, **kwargs):
        kwargs.setdefault("specs_file", None)
        kwargs.setdefault("require_plan_review", False)
        kwargs.setdefault("require_completion_review", False)
        with mock.patch.object(flowctl, "get_actor", return_value="tester"):
            return self.call(flowctl.cmd_next, **kwargs)

    def _cmd_next_human(self, **kwargs):
        kwargs.setdefault("specs_file", None)
        kwargs.setdefault("require_plan_review", False)
        kwargs.setdefault("require_completion_review", False)
        with mock.patch.object(flowctl, "get_actor", return_value="tester"):
            return self.call_human(flowctl.cmd_next, **kwargs)

    def test_zero_task_open_spec_surfaces_plan_needs_tasks(self) -> None:
        self.write_spec("fn-1")
        result = self._cmd_next()
        self.assertEqual(
            result,
            {
                "success": True,
                "status": "plan",
                "spec": "fn-1",
                "task": None,
                "reason": "needs_tasks",
            },
        )

    def test_zero_task_human_output(self) -> None:
        self.write_spec("fn-1")
        output = self._cmd_next_human()
        self.assertEqual(output.strip(), "plan fn-1 needs_tasks")

    def test_zero_task_spec_selected_before_later_ready_task(self) -> None:
        self.write_spec("fn-1")
        self.write_spec("fn-2")
        self.write_task("fn-2.1", with_markdown=True)
        result = self._cmd_next()
        self.assertEqual(result["status"], "plan")
        self.assertEqual(result["spec"], "fn-1")
        self.assertEqual(result["reason"], "needs_tasks")

    def test_done_spec_with_zero_tasks_still_skipped(self) -> None:
        self.write_spec("fn-1", status="done")
        result = self._cmd_next()
        self.assertEqual(result["status"], "none")

    def test_spec_with_ready_task_unaffected(self) -> None:
        self.write_spec("fn-1")
        self.write_task("fn-1.1", with_markdown=True)
        result = self._cmd_next()
        self.assertEqual(result["status"], "work")
        self.assertEqual(result["task"], "fn-1.1")
        self.assertEqual(result["reason"], "ready_task")

    def test_all_done_completion_review_not_swallowed(self) -> None:
        self.write_spec("fn-1")
        self.write_task("fn-1.1", status="done")
        result = self._cmd_next(require_completion_review=True)
        self.assertEqual(result["status"], "completion_review")
        self.assertEqual(result["spec"], "fn-1")
        self.assertEqual(result["reason"], "needs_completion_review")


if __name__ == "__main__":
    unittest.main()

"""Live route facts and explain output, using observed PR and task fixtures."""
import importlib.util
import io
from contextlib import redirect_stdout
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
spec = importlib.util.spec_from_file_location("flowctl_judge_route_test", SCRIPTS / "flowctl.py")
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)


class JudgeRouteTests(unittest.TestCase):
    def live(self, **overrides):
        return dict(view="live", spec_body="Build a bounded feature", ready=True,
                    tasks_total=0, tasks_done=0, pr_exists=False, pr_ref=None,
                    **overrides)

    def test_live_precedence(self):
        cases = [
            ({"pr_exists": None}, "host"),
            ({"pr_exists": True, "tasks_total": 2, "tasks_done": 2}, "existing_pr_tail"),
            ({"tasks_total": 2, "tasks_done": 2}, "all_done_make_pr"),
            ({"tasks_total": 2}, "work_planned"),
            ({"tasks_total": 1, "no_plan": True}, "work_planned"),
            ({}, "work_no_plan_default"),
            ({"no_plan": False}, "work_no_plan_default"),
            ({"no_plan": True, "spec_body": "task plan"}, "work_no_plan_default"),
            ({"spec_body": "Please plan this out"}, "plan"),
            ({"spec_body": "Separate owners implement each part"}, "plan"),
            ({"spec_body": "Ship in two PRs"}, "plan"),
            ({"ready": False}, "host"),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                state = self.live()
                state.update(overrides)
                self.assertEqual(f.judge_route_lifecycle(state)["value"], expected)
        self.assertIsNone(f.judge_route_lifecycle({"view": "intent"}))

    def test_probe_observations_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = repo / "spec.md"
            body.write_text("Implement feature", encoding="utf-8")
            spec_data = {"title": "Feature", "status": "open", "branch_name": "fn-1-feature"}
            for status in ("OPEN", "MERGED", "CLOSED", "absent", "failed", "truncated", "ambiguous"):
                with self.subTest(status=status):
                    rows = [] if status == "absent" else [{"number": 1, "state": status, "url": "https://example.test/pr/1"}]
                    if status in {"truncated", "ambiguous"}:
                        rows = [{"number": i, "state": "OPEN" if status == "ambiguous" else "CLOSED", "url": f"pr/{i}"}
                                for i in range(100 if status == "truncated" else 2)]
                    probe = SimpleNamespace(returncode=int(status == "failed"), stdout=json.dumps(rows))
                    with patch.dict(f.os.environ, {"TYPESAFE_API_KEY": "test-key"}), patch.object(f, "get_config", return_value=True), patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), patch.object(f, "load_json_or_exit", return_value=spec_data), patch.object(f, "normalize_epic", side_effect=lambda x: x), patch.object(f, "find_spec_md_path", return_value=body), patch.object(f.TaskInventory, "load", return_value=SimpleNamespace(by_spec={})), patch.object(f.subprocess, "run", return_value=probe) as run:
                        state = f.judge_route_state({}, "fn-1-feature")
                    self.assertIn("--state", run.call_args.args[0])
                    self.assertIn("all", run.call_args.args[0])
                    self.assertEqual(state["pr_exists"], None if status in {"failed", "truncated", "ambiguous"} else status != "absent")
                    if status in {"OPEN", "MERGED", "CLOSED"}:
                        self.assertEqual(state["pr_ref"]["state"], status)
                        self.assertEqual(f.judge_route_lifecycle(state)["value"], "existing_pr_tail")
                    self.assertFalse(state["no_plan"])

    def test_standalone_qa_assembles_target_without_pr_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = repo / "spec.md"
            body.write_text("Acceptance: the modal opens.\nDev server: `pnpm dev`\n")
            args = SimpleNamespace(preset="qa-gate", spec="fn-1", state_file=None, explain=False, json=True)
            with patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), patch.object(f, "resolve_spec_id_arg", return_value="fn-1"), patch.object(f, "find_spec_md_path", return_value=body), patch.object(f, "judge_evaluate", return_value={"available": False, "reason": "no_key"}) as evaluate, patch.object(f.subprocess, "run") as process, redirect_stdout(io.StringIO()):
                f.cmd_judge(args)
            self.assertEqual(evaluate.call_args.args[0], "qa-gate")
            self.assertEqual(evaluate.call_args.args[1]["startable_target_fact"], "pnpm dev")
            self.assertEqual(evaluate.call_args.args[1]["acceptance"], body.read_text())
            process.assert_not_called()

    def test_dependency_scan_names_only_unrecorded_mentions(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text('{"dependencies":{"react":"1"}}')
            (repo / "app.py").write_text("import sqlite3\n")
            with patch.object(f, "get_repo_root", return_value=repo), patch.object(f.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="app.py\n")):
                tokens = f.judge_dependency_tokens({"intent": "Use the react library, `import sqlite3`, run `npm install newlib` and `pip install typesafe`; keep `flowctl` unchanged"})
            self.assertEqual(tokens, ["newlib", "typesafe"])

    def test_presentation_skip_cells_match_matrix(self):
        matrix = (SCRIPTS.parent / "skills/flow-next-flow/references/route-matrix.md").read_text()
        rows = [[cell.strip() for cell in line.split("|")[1:-1]] for line in matrix.splitlines() if line.startswith("| ")][1:]
        indices = {"discovery": 0, "theme": 3, "build": 4, "capture_brief": 5, "defect": 6,
                   "cleanup": 7, "slowness": 8, "hillclimb": 9, "question": 10, "fork": 11,
                   "tiny": 12, "refine": 13, "plan_review": 14, "work_no_plan_default": 15,
                   "plan": 15, "work_planned": 16, "all_done_make_pr": 17, "existing_pr_tail": 18}
        for kind, index in indices.items():
            self.assertEqual(f.JUDGE_ROUTE_PRESENTATION[kind][1], rows[index][3])

    def test_target_and_trimming(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.assertIsNone(f.judge_startable_target(repo, "UI acceptance only"))
            (repo / "README.md").write_text("```sh\npnpm dev\n```", encoding="utf-8")
            self.assertEqual(f.judge_startable_target(repo), "pnpm dev")
            self.assertEqual(f.judge_startable_target(repo, "Deploy URL: https://example.test/app"), "https://example.test/app")
            with patch.object(f, "get_repo_root", return_value=repo):
                state = f.judge_route_state({"view": "brief", "spec_body": "x" * 100001})
            self.assertEqual(len(state["spec_body"]), 100000)
            self.assertTrue(state["spec_body_truncated"])
            self.assertEqual(state["startable_target_fact"], "pnpm dev")

    def test_explain_uses_same_answers(self):
        result = {"available": True, "decision": {"value": "defect", "candidates": [["defect", .91], ["build", .06], ["tiny", .02]]}, "answers": {"kind": {"confidence": .91}, "reports_defect": {"type": "noul", "noul": .94}, "tiny_one_context_change": {"type": "noul", "noul": .99}}}
        lines = f.judge_route_explain(result, {"view": "intent"})
        self.assertEqual([line.split(":", 1)[0] for line in lines], ["Next", "Route", "Signal", "Skip/narrow", "Why not the alternatives"])
        self.assertIn("reports_defect (jev 0.94)", lines[2])
        self.assertNotIn("tiny_one_context_change", lines[2])
        self.assertIn("build 0.06, tiny 0.02", lines[4])
        unavailable = f.judge_route_explain({"available": False, "reason": "timeout"}, {"view": "intent"})
        self.assertEqual(unavailable[1], "Route: host (jev-unavailable(timeout))")


if __name__ == "__main__":
    unittest.main()

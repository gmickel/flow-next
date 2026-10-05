"""Live route facts, decided in code, using observed PR and task fixtures; routing never asks Jev."""
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
            ({"spec_body": "Please decompose this into tasks"}, "plan"),
            # Isolated vocabulary and negated requests are not plan signals.
            ({"spec_body": "Implement a decompose() helper for matrix factorization."}, "work_no_plan_default"),
            ({"spec_body": "Do not decompose this into tasks; deliver one PR."}, "work_no_plan_default"),
            ({"spec_body": "Don't plan this out; never break it down into tasks."}, "work_no_plan_default"),
            ({"ready": False}, "host"),
            ({"ready": False, "no_plan": True}, "work_no_plan_default"),
            ({"ready": False, "tasks_total": 1}, "work_planned"),
            # #514: a stale plan SHIP re-reviews before work at any task count;
            # never-reviewed specs route as before.
            ({"tasks_total": 2, "plan_review_status": "stale"}, "plan_review"),
            ({"tasks_total": 1, "no_plan": True, "plan_review_status": "stale"}, "plan_review"),
            ({"plan_review_status": "stale"}, "plan_review"),
            ({"tasks_total": 2, "tasks_done": 2, "plan_review_status": "stale"}, "all_done_make_pr"),
            ({"tasks_total": 2, "plan_review_status": "unknown"}, "work_planned"),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                state = self.live()
                state.update(overrides)
                self.assertEqual(f.judge_route_lifecycle(state)["value"], expected)

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
                        # make-pr now closes the spec before opening its PR. Keep
                        # every observed PR on the tail route so the host can land,
                        # end after merge, or stop on an unmerged closure.
                        state["status"] = "done"
                        self.assertEqual(f.judge_route_lifecycle(state)["value"], "existing_pr_tail")
                    self.assertFalse(state["no_plan"])

    def test_closed_spec_without_observed_pr_never_routes_to_replacement(self):
        scratch = SCRIPTS.parents[2] / ".flow" / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            repo = Path(tmp)
            body = repo / "spec.md"
            body.write_text("Implement feature", encoding="utf-8")
            spec_path = repo / "spec.json"
            # This is the persisted status written by spec close. Exercise the
            # real JSON reader and normalizer rather than inventing route facts.
            spec_path.write_text(json.dumps({
                "id": "fn-1-feature", "title": "Feature", "status": "done",
                "branch_name": "fn-1-feature", "ready": True, "plan_review_status": "stale",
            }), encoding="utf-8")
            probe = SimpleNamespace(returncode=0, stdout="[]")
            with patch.dict(f.os.environ, {"TYPESAFE_API_KEY": "test-key"}), patch.object(f, "get_config", return_value=True), patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), patch.object(f, "find_spec_json_path", return_value=spec_path), patch.object(f, "find_spec_md_path", return_value=body), patch.object(f.TaskInventory, "load", return_value=SimpleNamespace(by_spec={"fn-1-feature": [{"status": "done"}]})), patch.object(f.subprocess, "run", return_value=probe):
                state = f.judge_route_state({}, "fn-1-feature")
            self.assertEqual(state["status"], "done")
            self.assertEqual(state["plan_review_status"], "stale")
            self.assertEqual((state["tasks_total"], state["tasks_done"]), (1, 1))
            self.assertIs(state["pr_exists"], False)
            route = f.judge_route_lifecycle(state)
            self.assertEqual(route["value"], "host")
            self.assertEqual(route["rule"], "closed spec without observed PR")

    def test_missing_branch_is_nothing_to_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = repo / "spec.md"
            body.write_text("Implement feature", encoding="utf-8")
            planned = [{"status": "todo"}, {"status": "done"}]
            for branch, tasks, expected in ((None, planned, "work_planned"), ("", [], "work_no_plan_default")):
                with self.subTest(branch=branch):
                    spec_data = {"title": "Feature", "status": "open", "ready": True, "branch_name": branch}
                    with patch.dict(f.os.environ, {"TYPESAFE_API_KEY": "test-key"}), patch.object(f, "get_config", return_value=True), patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), patch.object(f, "load_json_or_exit", return_value=spec_data), patch.object(f, "normalize_epic", side_effect=lambda x: x), patch.object(f, "find_spec_md_path", return_value=body), patch.object(f.TaskInventory, "load", return_value=SimpleNamespace(by_spec={"fn-1-feature": tasks})), patch.object(f.subprocess, "run") as run:
                        state = f.judge_route_state({}, "fn-1-feature")
                        result = f.judge_route(state)
                    run.assert_not_called()
                    self.assertIs(state["pr_exists"], False)
                    self.assertIsNone(state["pr_ref"])
                    self.assertEqual(result["decision"]["value"], expected)
                    self.assertEqual((result["available"], result["reason"]), (False, "routing_is_code"))
                    self.assertNotIn("pr_probe_failed", result)

    def test_target_scan_skips_non_utf8_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "README.md").write_bytes("Dev server: `pnpm dev`\nCaf\xe9\n".encode("latin-1"))
            (repo / "AGENTS.md").write_text("Launch command: `make serve`\n", encoding="utf-8")
            self.assertEqual(f.judge_startable_target(repo), "make serve")

    def test_target_from_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.assertIsNone(f.judge_startable_target(repo, "UI acceptance only"))
            (repo / "README.md").write_text("```sh\npnpm dev\n```", encoding="utf-8")
            self.assertEqual(f.judge_startable_target(repo), "pnpm dev")
            self.assertEqual(f.judge_startable_target(repo, "Deploy URL: https://example.test/app"), "https://example.test/app")

    def test_target_preserves_documented_commands_and_rejects_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cases = [
                ("Start command: make dev", "make dev"),
                ("Start command: pnpm dev:web", "pnpm dev:web"),
                ("run `pnpm dev:web` locally", "pnpm dev:web"),
                ("- Launch target: `http://127.0.0.1:<port>` on a port this run owns.", None),
                ("- Start command: `npm run dev -- --port <port> --host 127.0.0.1`.", None),
                ("Launch target: `http://127.0.0.1:8787`.", "http://127.0.0.1:8787"),
            ]
            for text, expected in cases:
                with self.subTest(text=text):
                    self.assertEqual(f.judge_startable_target(repo, text), expected)

    def route_command(self, key, **args):
        """Run `judge --preset route` through cmd_judge with a live spec fixture."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = repo / "spec.md"
            body.write_text("Implement feature. Dev server: `pnpm dev`", encoding="utf-8")
            spec_data = {"title": "Feature", "status": "open", "ready": True, "branch_name": None}
            inventory = SimpleNamespace(by_spec={"fn-1-feature": [{"status": "todo"}, {"status": "done"}]})
            namespace = SimpleNamespace(preset="route", spec="fn-1-feature", state_file=None, task=None, json=True)
            vars(namespace).update(args)
            out = io.StringIO()
            with patch.dict(f.os.environ, {"TYPESAFE_API_KEY": key}), patch.object(f, "get_config", return_value=True), \
                    patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), \
                    patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), \
                    patch.object(f, "load_json_or_exit", return_value=spec_data), \
                    patch.object(f, "normalize_epic", side_effect=lambda x: x), \
                    patch.object(f, "find_spec_md_path", return_value=body), \
                    patch.object(f.TaskInventory, "load", return_value=inventory), \
                    patch("http.client.HTTPSConnection") as https, \
                    patch.object(f, "judge_https_connection") as connect, redirect_stdout(out):
                try:
                    f.cmd_judge(namespace)
                finally:
                    https.assert_not_called()
                    connect.assert_not_called()
            return json.loads(out.getvalue())

    def test_route_command_sends_no_request_with_or_without_a_key(self):
        keyed = self.route_command("test-key-never-sent")
        self.assertEqual(keyed, self.route_command(""))
        self.assertEqual(keyed, {
            "success": True, "available": False, "preset": "route", "reason": "routing_is_code",
            "decision": {"value": "work_planned", "rule": "recorded task route", "met": True,
                         "pr_ref": None, "startable_target_fact": "pnpm dev"},
        })
        self.assertNotIn("test-key-never-sent", json.dumps(keyed))

    def test_route_rejects_intake_state_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for written in ({"view": "intent", "intent": "Fix the crash on save"},
                            {"view": "brief", "spec_title": "Crash", "spec_body": "Fix the crash"}):
                state = Path(tmp) / "state.json"
                state.write_text(json.dumps(written), encoding="utf-8")
                for spec_arg in (None, "fn-1-feature"):
                    with self.subTest(view=written["view"], spec=spec_arg), self.assertRaises(SystemExit) as raised:
                        self.route_command("test-key-never-sent", spec=spec_arg, state_file=str(state))
                    self.assertNotEqual(raised.exception.code, 0)

    def test_route_is_not_a_judge_preset(self):
        self.assertNotIn("route", f.JUDGE_PRESETS)
        with self.assertRaisesRegex(ValueError, "registered presets"):
            f.judge_evaluate("route", {})


if __name__ == "__main__":
    unittest.main()

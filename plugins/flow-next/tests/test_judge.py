"""Typed judge transport and decisions; all HTTP is stubbed, including retries."""
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
spec = importlib.util.spec_from_file_location("flowctl_judge_test", SCRIPTS / "flowctl.py")
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)


def state_for(preset):
    states = {
        "route": {"view": "intent", "view_meaning": "An intent at intake", "repo": ".", "intent": "Fix the crash",
                  "status": None, "ready": False, "no_plan": False, "tasks_total": 0,
                  "tasks_done": 0, "pr_exists": False, "pr_ref": None, "startable_target_fact": "npm run dev"},
        "qa-gate": {"acceptance": "The button opens a modal", "startable_target_fact": "npm run dev"},
        "fork-gate": {"text": "Should this be a modal or a separate page?"},
        "memory-rerank": {"query": "auth", "entries": [{"entry_id": str(i)} for i in range(15)]},
        "tier": {"task_title": "Rename field", "task_body": "Rename field in fixture", "acceptance": "Updated fixture",
                 "touches_count": 1, "has_quick_commands": True, "repo": "."},
    }
    return states[preset]


def payload_for(preset, state=None):
    answers = {}
    for qid, q in f.judge_questions(preset, state or state_for(preset)).items():
        if q["type"] == "noul":
            answers[qid] = {"type": "noul", "noul": 0.9}
        elif q["type"] == "score":
            answers[qid] = {"type": "score", "score": 1.5, "confidence": 0.8,
                            "probabilities": {"0": 0, "1": 0.5, "2": 0.5}}
        else:
            options = list(q["criteria"])
            answers[qid] = {"type": "choice", "choice": options[0], "confidence": 0.9,
                            "probabilities": {k: 1.0 if k == options[0] else 0.0 for k in options}}
    return {"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 15, "output_tokens": 10}}


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-secret-never-output"})
        self.env.start()
        self.config = patch.object(f, "get_config", side_effect=lambda key, default=None: "auto" if key == "pipeline.qa" else True)
        self.config.start()
        self.http = patch.object(f.http.client, "HTTPSConnection")
        self.connection = self.http.start().return_value
        self.sleep = patch.object(f.time, "sleep")
        self.sleeper = self.sleep.start()
        self.addCleanup(patch.stopall)

    def request(self, preset, state=None, payload=None):
        state = state or state_for(preset)
        self.connection.getresponse.return_value = Mock(status=200, read=lambda: json.dumps(payload or payload_for(preset, state)).encode())
        return f.judge_evaluate(preset, state)

    def test_registered_presets_send_one_complete_fanout(self):
        for preset in f.JUDGE_PRESETS:
            with self.subTest(preset=preset):
                self.connection.reset_mock()
                result = self.request(preset)
                self.assertTrue(result["available"])
                self.assertEqual(result["model"], "jev-1.13.0")
                self.assertIn("latency_ms", result)
                self.connection.request.assert_called_once()
                args, kwargs = self.connection.request.call_args
                self.assertEqual(args, ("POST", "/v1/systemone"))
                body = json.loads(kwargs["body"])
                self.assertEqual(body["state"], state_for(preset))
                self.assertEqual(body["questions"], f.judge_questions(preset, state_for(preset)))
                self.assertEqual(body["model"], "jev-latest")
                self.assertEqual("candidates" in result["decision"], preset in ("route", "tier"))

    def test_availability_never_sends(self):
        for enabled, key, reason in [(True, "", "no_key"), (False, "secret", "disabled")]:
            with patch.object(f, "get_config", return_value=enabled), patch.dict(os.environ, TYPESAFE_API_KEY=key):
                self.assertEqual(f.judge_evaluate("fork-gate", state_for("fork-gate")),
                                 {"success": True, "available": False, "preset": "fork-gate", "reason": reason})
        self.connection.request.assert_not_called()

    def test_invalid_config_warns_and_is_enabled(self):
        stderr = io.StringIO()
        with patch.object(f, "get_config", return_value="false"), redirect_stderr(stderr):
            self.assertTrue(self.request("fork-gate")["available"])
        self.assertIn("treating it as true", stderr.getvalue())

    def test_retry_only_overload_and_exact_backoffs(self):
        for status in (429, 529):
            self.connection.reset_mock()
            self.sleeper.reset_mock()
            self.connection.getresponse.side_effect = [Mock(status=status), Mock(status=status), Mock(status=200, read=lambda: json.dumps(payload_for("fork-gate")).encode())]
            self.assertTrue(f.judge_evaluate("fork-gate", state_for("fork-gate"))["available"])
            self.assertEqual(self.connection.request.call_count, 3)
            self.assertEqual([c.args[0] for c in self.sleeper.call_args_list], [1, 2])
        self.connection.getresponse.side_effect = None
        for status in (400, 401, 500, 429, 529):
            self.connection.reset_mock()
            self.connection.getresponse.return_value = Mock(status=status)
            self.assertEqual(f.judge_evaluate("fork-gate", state_for("fork-gate"))["reason"], f"http_{status}")
            self.assertEqual(self.connection.request.call_count, 3 if status in (429, 529) else 1)

    def test_timeout_transport_budget_and_no_exception_leaks(self):
        for exception, reason in [(TimeoutError("test-secret-never-output"), "timeout"), (OSError("test-secret-never-output"), "transport")]:
            self.connection.request.side_effect = exception
            result = f.judge_evaluate("fork-gate", state_for("fork-gate"))
            self.assertEqual(result["reason"], reason)
            self.assertNotIn("test-secret", json.dumps(result))
        self.connection.reset_mock()
        self.assertEqual(f.judge_evaluate("fork-gate", {"text": "x" * 128001})["reason"], "over_budget")
        self.connection.request.assert_not_called()

    def test_bad_answers_fail_closed(self):
        for mutation in (lambda p: p["answers"].pop("kind"),
                         lambda p: p["answers"]["kind"]["probabilities"].pop("tiny"),
                         lambda p: p["answers"]["kind"].update(confidence=float("nan")),
                         lambda p: p["answers"]["kind"].update(choice="imaginary"),
                         lambda p: p["answers"]["reports_defect"].update(noul=True),
                         lambda p: p.update(model=None)):
            payload = payload_for("route")
            mutation(payload)
            self.assertEqual(self.request("route", payload=payload)["reason"], "bad_answer")
        payload = payload_for("memory-rerank")
        del payload["answers"]["entry_3"]["probabilities"]["1"]
        self.assertEqual(self.request("memory-rerank", payload=payload)["reason"], "bad_answer")

    def test_state_contract_errors(self):
        with self.assertRaisesRegex(ValueError, "registered presets"):
            f.judge_evaluate("not-a-preset", {})
        for preset in f.JUDGE_PRESETS:
            state = state_for(preset)
            missing = f.JUDGE_PRESETS[preset]["required"][-1]
            del state[missing]
            with self.assertRaisesRegex(ValueError, missing):
                f.judge_evaluate(preset, state)
        self.connection.request.assert_not_called()

    def test_r9_retired_clean_review_preset_rejected(self):
        with self.assertRaisesRegex(ValueError, "registered presets"):
            f.judge_evaluate("clean-review", {"body": "No findings"})
        self.connection.request.assert_not_called()

    def test_route_floor_and_no_match_fallback_only_candidates(self):
        for choice, confidence, expected in [("defect", .7, "defect"), ("build", .699, "host"), ("none_of_the_above", 1, "host")]:
            answers = payload_for("route")["answers"]
            answers["kind"].update(choice=choice, confidence=confidence)
            result = f.judge_decide("route", state_for("route"), answers)
            self.assertEqual(result["value"], expected)
            self.assertEqual(len(result["candidates"]), 3)

    def test_qa_requires_both_halves(self):
        for ui, target, expected, reason in [(.5, "npm run dev", "qa_runs", None), (.49, "npm run dev", "qa_skipped", "no UI-observable criteria"), (.9, None, "qa_skipped", "no startable target")]:
            decision = f.judge_decide("qa-gate", {"startable_target_fact": target}, {"ui_observable_criteria": {"noul": ui}})
            self.assertEqual(decision["value"], expected)
            self.assertEqual(decision.get("reason"), reason)

    def test_fork_gate_none_and_host_residue(self):
        for gate, choice, confidence, expected in [(.49, "observable", 1, "none"), (.5, "observable", .5, "observable"), (.9, "product_or_preference", .8, "product_or_preference"), (.9, "observable", .49, "host"), (.9, "none_of_the_above", 1, "host")]:
            decision = f.judge_decide("fork-gate", {}, {"fork_present": {"noul": gate}, "fork_kind": {"choice": choice, "confidence": confidence}})
            self.assertEqual(decision["value"], expected)

    def test_tier_only_extremes_act(self):
        for tier, confidence, expected in [("mechanical", .8, "mechanical"), ("long_running", .8, "long_running"), ("mechanical", .79, "session"), ("moderate", 1, "session"), ("intelligent", 1, "session")]:
            answers = payload_for("tier")["answers"]
            answers["tier"].update(choice=tier, confidence=confidence)
            self.assertEqual(f.judge_decide("tier", {}, answers)["value"], expected)

    def test_memory_stable_order_floor_cap_and_empty(self):
        state = state_for("memory-rerank")
        answers = payload_for("memory-rerank")["answers"]
        answers["entry_0"]["score"] = .99
        answers["entry_5"]["score"] = 2
        ranked = f.judge_decide("memory-rerank", state, answers)["value"]
        self.assertEqual([p[0] for p in ranked], ["5", "1", "2", "3", "4", "6", "7", "8", "9", "10"])
        result = f.judge_evaluate("memory-rerank", {"query": "auth", "entries": []})
        self.assertEqual(result["decision"]["value"], [])
        self.connection.request.assert_not_called()

    def test_kind_criteria_match_route_matrix_verbatim(self):
        matrix = (SCRIPTS.parent / "skills/flow-next-flow/references/route-matrix.md").read_text()
        rows = [tuple(c.strip() for c in line.strip("|").split("|")) for line in matrix.splitlines() if line.startswith("| ")][1:]
        indices = {"build": [4], "capture_brief": [5], "defect": [6], "cleanup": [7], "slowness": [8], "hillclimb": [9], "question": [10], "fork": [11], "tiny": [12], "theme": [3], "discovery": [0, 1, 2], "refine": [13], "plan_review": [14]}
        actual = f.JUDGE_PRESETS["route"]["questions"]["kind"]["criteria"]
        for kind, indices_for_kind in indices.items():
            self.assertEqual(actual[kind], "; ".join(rows[i][0] + ". " + rows[i][2] for i in indices_for_kind))
        self.assertEqual(set(actual), set(indices) | {"none_of_the_above"})

    def test_route_qa_off_sends_no_qa_question(self):
        with patch.object(f, "get_config", side_effect=lambda key, default=None: "off" if key == "pipeline.qa" else True):
            result = self.request("route")
        self.assertTrue(result["available"])
        self.assertNotIn("qa", result["decision"])
        self.assertNotIn("ui_observable_criteria", json.loads(self.connection.request.call_args.kwargs["body"])["questions"])

    def test_memory_command_applies_rerank_and_preserves_unavailable_order(self):
        entries = [{"entry_id": str(i), "title": "auth pitfall", "track": "bug", "category": "runtime-errors",
                    "module": "auth", "tags": ["auth"], "body": "auth lesson", "status": "active",
                    "frontmatter": {}, "path": f"memory/{i}.md"} for i in range(3)]
        args = argparse.Namespace(query="auth", track=None, category=None, module=None, tags=None,
                                  status="active", limit=None, json=True, rerank=True)
        with tempfile.TemporaryDirectory() as directory, patch.object(f, "require_memory_enabled", return_value=Path(directory)), patch.object(f, "_memory_iter_entries", return_value=entries):
            def run():
                output = io.StringIO()
                with redirect_stdout(output):
                    f.cmd_memory_search(args)
                return json.loads(output.getvalue()) if args.json else output.getvalue()
            args.rerank = False
            original = run()
            args.rerank = True
            with patch.dict(os.environ, TYPESAFE_API_KEY=""):
                unavailable = run()
            self.assertEqual(unavailable["matches"], original["matches"])
            self.assertEqual(unavailable["rerank"], "bm25")
            self.assertEqual(unavailable["stage_line"], "memory: bm25 (jev-unavailable(no_key))")
            payload = payload_for("memory-rerank", {"entries": entries})
            for i, score in enumerate([.4, 1.2, 1.8]):
                payload["answers"][f"entry_{i}"]["score"] = score
            self.connection.getresponse.return_value = Mock(status=200, read=lambda: json.dumps(payload).encode())
            ranked = run()
            self.assertEqual([m["entry_id"] for m in ranked["matches"]], ["2", "1"])
            self.assertEqual([m["jev_rank"] for m in ranked["matches"]], [1, 2])
            self.assertEqual(ranked["stage_line"], "memory: reranked (jev, 3 -> 2)")
            args.json = False
            self.assertIn("| Track | Category | Entry | Why relevant |", run())
            with patch.object(f, "_memory_iter_entries", return_value=[]):
                args.json = True
                self.connection.reset_mock()
                self.assertEqual(run()["matches"], [])
                self.connection.request.assert_not_called()

    def test_cli_ascii_and_no_key_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps({"text": "No issues — très bien"}))
            args = argparse.Namespace(preset="fork-gate", state_file=str(path), spec=None, explain=False, json=True)
            before = {p.name: p.read_bytes() for p in Path(directory).iterdir()}
            stdout, stderr = io.StringIO(), io.StringIO()
            self.connection.getresponse.return_value = Mock(status=401)
            with redirect_stdout(stdout), redirect_stderr(stderr):
                f.cmd_judge(args)
            stdout.getvalue().encode("ascii")
            self.assertNotIn("test-secret-never-output", stdout.getvalue() + stderr.getvalue())
            self.assertEqual(before, {p.name: p.read_bytes() for p in Path(directory).iterdir()})
            for bad in ("missing.json",):
                args.state_file = str(Path(directory) / bad)
                with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    f.cmd_judge(args)
                self.assertNotEqual(raised.exception.code, 0)
            proc = subprocess.run([sys.executable, str(SCRIPTS / "flowctl.py"), "judge", "--preset", "bad", "--state-file", str(path)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("fork-gate", proc.stderr)

    def test_intake_state_as_the_skill_writes_it_reaches_the_judge(self):
        """The host supplies only view and its text; code assembles every other route fact."""
        workflow = (SCRIPTS.parent / "skills/flow-next-flow/workflow.md").read_text()
        self.assertIn('{"view": "intent", "intent": "<text>"}', workflow)
        self.assertIn('{"view": "brief", "spec_title": "<title>", "spec_body": "<body>"}', workflow)
        for written in ({"view": "intent", "intent": "Fix the crash on save"},
                        {"view": "brief", "spec_title": "Crash on save", "spec_body": "Fix the crash on save"}):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "state.json"
                path.write_text(json.dumps(written))
                args = argparse.Namespace(preset="route", state_file=str(path), spec=None, explain=False, json=True)
                self.connection.reset_mock()
                self.connection.getresponse.return_value = Mock(
                    status=200, read=lambda: json.dumps(payload_for("route", state_for("route"))).encode())
                stdout = io.StringIO()
                with patch.object(f, "get_repo_root", return_value=Path(directory)), redirect_stdout(stdout):
                    f.cmd_judge(args)
                self.assertTrue(json.loads(stdout.getvalue())["available"])
                sent = json.loads(self.connection.request.call_args.kwargs["body"])["state"]
                self.assertEqual(set(f.JUDGE_PRESETS["route"]["required"]) - set(sent), set())
                self.assertEqual((sent["status"], sent["tasks_total"], sent["pr_exists"]), (None, 0, False))

    def test_spec_flag_reaches_the_live_route_through_the_command(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            body = repo / "spec.md"
            body.write_text("Implement feature")
            spec_data = {"title": "Feature", "status": "open", "ready": True, "branch_name": None}
            inventory = Mock(by_spec={"fn-1-feature": [{"status": "todo"}]})
            args = argparse.Namespace(preset="route", state_file=None, spec="fn-1-feature", explain=False, json=True)
            live = {"view": "live", "spec_title": "Feature", "spec_body": "Implement feature"}
            self.connection.getresponse.return_value = Mock(
                status=200, read=lambda: json.dumps(payload_for("route", live)).encode())
            stdout = io.StringIO()
            with patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), \
                    patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), \
                    patch.object(f, "load_json_or_exit", return_value=spec_data), \
                    patch.object(f, "normalize_epic", side_effect=lambda x: x), \
                    patch.object(f, "find_spec_md_path", return_value=body), \
                    patch.object(f.TaskInventory, "load", return_value=inventory), redirect_stdout(stdout):
                f.cmd_judge(args)
            result = json.loads(stdout.getvalue())
            self.assertTrue(result["available"])
            self.assertEqual(result["decision"]["value"], "work_planned")

    def test_every_missing_field_is_named_at_once(self):
        for preset in ("route", "tier"):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "state.json"
                path.write_text(json.dumps({"view": "live"} if preset == "route" else {}))
                args = argparse.Namespace(preset=preset, state_file=str(path), spec=None, explain=False, json=True)
                stdout = io.StringIO()
                with patch.object(f, "get_repo_root", return_value=Path(directory)), redirect_stdout(stdout), self.assertRaises(SystemExit):
                    f.cmd_judge(args)
                for field in ("task_title", "repo") if preset == "tier" else ("status", "pr_ref", "spec_body"):
                    self.assertIn(field, stdout.getvalue())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps({"view": "intent", "intent": 5}))
            args = argparse.Namespace(preset="route", state_file=str(path), spec=None, explain=False, json=True)
            stdout = io.StringIO()
            with patch.object(f, "get_repo_root", return_value=Path(directory)), redirect_stdout(stdout), self.assertRaises(SystemExit):
                f.cmd_judge(args)
            self.assertIn("must be a string: intent", stdout.getvalue())
        self.connection.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()

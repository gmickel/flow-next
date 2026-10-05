"""Typed judge transport and decisions; all HTTP is stubbed, including retries."""
import argparse
import importlib.util
import io
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
spec = importlib.util.spec_from_file_location("flowctl_judge_test", SCRIPTS / "flowctl.py")
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)


def state_for(preset):
    states = {
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
        self.http = patch.object(http.client, "HTTPSConnection")
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
                self.assertEqual("candidates" in result["decision"], preset == "tier")

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
        for mutation in (lambda p: p["answers"].pop("tier"),
                         lambda p: p["answers"]["tier"]["probabilities"].pop("moderate"),
                         lambda p: p["answers"]["tier"].update(confidence=float("nan")),
                         lambda p: p["answers"]["tier"].update(choice="imaginary"),
                         lambda p: p["answers"]["purely_mechanical_edit"].update(noul=True),
                         lambda p: p.update(model=None)):
            payload = payload_for("tier")
            mutation(payload)
            self.assertEqual(self.request("tier", payload=payload)["reason"], "bad_answer")
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

    def test_retired_qa_gate_preset_rejected(self):
        # The QA gate never asks Jev: the host judges the UI half, code resolves the target.
        with self.assertRaisesRegex(ValueError, "registered presets"):
            f.judge_evaluate("qa-gate", {"acceptance": "The button opens a modal", "startable_target_fact": "npm run dev"})
        self.connection.request.assert_not_called()

    def test_fork_gate_is_a_kind_hint_and_never_cancels_a_fork(self):
        self.assertEqual(list(f.judge_questions("fork-gate", state_for("fork-gate"))), ["fork_kind"])
        for choice, confidence, expected in [("observable", .5, "observable"), ("product_or_preference", .8, "product_or_preference"),
                                             ("observable", .49, "host"), ("none_of_the_above", 1, "host")]:
            decision = f.judge_decide("fork-gate", {}, {"fork_kind": {"choice": choice, "confidence": confidence}})
            self.assertEqual(decision["value"], expected)
            self.assertNotEqual(decision["value"], "none")

    def test_tier_only_extremes_act(self):
        for tier, confidence, expected in [("mechanical", .8, "mechanical"), ("long_running", .8, "long_running"), ("mechanical", .79, "session"), ("moderate", 1, "session"), ("intelligent", 1, "session")]:
            answers = payload_for("tier")["answers"]
            answers["tier"].update(choice=tier, confidence=confidence)
            self.assertEqual(f.judge_decide("tier", {}, answers)["value"], expected)

    def test_memory_reorders_every_entry_stably_and_empty(self):
        state = state_for("memory-rerank")
        answers = payload_for("memory-rerank")["answers"]
        answers["entry_0"]["score"] = .1
        answers["entry_5"]["score"] = 2
        ranked = f.judge_decide("memory-rerank", state, answers)["value"]
        # Reorder only: a low score moves an entry down, never out of the host's list.
        self.assertEqual([p[0] for p in ranked], ["5"] + [str(i) for i in range(1, 15) if i != 5] + ["0"])
        result = f.judge_evaluate("memory-rerank", {"query": "auth", "entries": []})
        self.assertEqual(result["decision"]["value"], [])
        self.connection.request.assert_not_called()

    def test_route_is_code_only_and_never_sends_with_a_key(self):
        live = {"spec_body": "Build it", "status": "open", "ready": True, "no_plan": False,
                "tasks_total": 0, "tasks_done": 0, "pr_exists": False, "pr_ref": None,
                "startable_target_fact": "npm run dev"}
        cases = [({"pr_exists": True}, "existing_pr_tail"), ({"tasks_total": 2}, "work_planned"),
                 ({"ready": False}, "host"), ({"tasks_total": 2, "tasks_done": 2}, "all_done_make_pr"),
                 ({}, "work_no_plan_default"), ({"spec_body": "Ship in two PRs"}, "plan")]
        for overrides, value in cases:
            with self.subTest(value=value):
                result = f.judge_route({**live, **overrides})
                self.assertEqual((result["available"], result["reason"]), (False, "routing_is_code"))
                self.assertEqual(result["decision"]["value"], value)
                self.assertEqual(set(result["decision"]), {"value", "rule", "met", "pr_ref", "startable_target_fact"})
                self.assertNotIn("answers", result)
        failed = f.judge_route({**live, "pr_exists": None})
        self.assertTrue(failed["pr_probe_failed"])
        self.assertNotIn("decision", failed)
        with self.assertRaisesRegex(ValueError, "registered presets"):
            f.judge_evaluate("route", live)
        self.connection.request.assert_not_called()

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
            self.assertEqual([m["entry_id"] for m in ranked["matches"]], ["2", "1", "0"])
            self.assertEqual([m["jev_rank"] for m in ranked["matches"]], [1, 2, 3])
            self.assertEqual(ranked["stage_line"], "memory: reranked (jev, 3 entries)")
            sent = json.loads(self.connection.request.call_args.kwargs["body"])["state"]["entries"]
            self.assertTrue(all("path" not in e and "score" not in e for e in sent))
            self.assertTrue(all("path" in m and "score" in m for m in ranked["matches"]))
            args.limit = 2
            self.assertEqual([m["entry_id"] for m in run()["matches"]], ["2", "1"])
            args.limit = None
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
            args = argparse.Namespace(preset="fork-gate", state_file=str(path), spec=None, json=True)
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
            proc = subprocess.run([*FLOWCTL_CMD, "judge", "--preset", "bad", "--state-file", str(path)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("fork-gate", proc.stderr)

    def test_spec_flag_reaches_the_live_route_through_the_command(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            body = repo / "spec.md"
            body.write_text("Implement feature")
            spec_data = {"title": "Feature", "status": "open", "ready": True, "branch_name": None}
            inventory = Mock(by_spec={"fn-1-feature": [{"status": "todo"}]})
            args = argparse.Namespace(preset="route", state_file=None, spec="fn-1-feature", json=True)
            stdout = io.StringIO()
            with patch.object(f, "get_repo_root", return_value=repo), patch.object(f, "get_flow_dir", return_value=repo), \
                    patch.object(f, "resolve_spec_id_arg", return_value="fn-1-feature"), \
                    patch.object(f, "load_json_or_exit", return_value=spec_data), \
                    patch.object(f, "normalize_epic", side_effect=lambda x: x), \
                    patch.object(f, "find_spec_md_path", return_value=body), \
                    patch.object(f.TaskInventory, "load", return_value=inventory), redirect_stdout(stdout):
                f.cmd_judge(args)
            result = json.loads(stdout.getvalue())
            self.assertEqual((result["available"], result["reason"]), (False, "routing_is_code"))
            self.assertEqual(result["decision"]["value"], "work_planned")
            self.connection.request.assert_not_called()

    def test_every_missing_field_is_named_at_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps({}))
            args = argparse.Namespace(preset="tier", state_file=str(path), spec=None, json=True)
            stdout = io.StringIO()
            with patch.object(f, "get_repo_root", return_value=Path(directory)), redirect_stdout(stdout), self.assertRaises(SystemExit):
                f.cmd_judge(args)
            for field in ("task_title", "repo"):
                self.assertIn(field, stdout.getvalue())
        self.connection.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()


class JudgeTierStateTests(unittest.TestCase):
    def test_fenced_heading_inside_acceptance_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            def run(*a):
                res = subprocess.run([*FLOWCTL_CMD, *a, "--json"], cwd=tmp, capture_output=True, text=True,
                                     encoding="utf-8", env={**os.environ, "HOME": tmp})
                self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
                return json.loads(res.stdout)
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            run("init")
            spec_id = run("spec", "create", "--title", "Fenced acceptance")["id"]
            acceptance = "- [ ] Output keeps the block:\n\n```md\n## Not a heading\n```\n\n- [ ] Tail criterion"
            task_id = run("task", "create", "--spec", spec_id, "--title", "Keep fences",
                          "--acceptance", acceptance)["id"]
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                state = f.judge_tier_state(task_id)
            finally:
                os.chdir(previous)
            self.assertIn("Tail criterion", state["acceptance"])

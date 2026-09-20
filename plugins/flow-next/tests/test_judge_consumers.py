"""Run the shipped consumer fences against typed judge fixtures; no network."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
spec = importlib.util.spec_from_file_location("flowctl_judge_consumers_test", PLUGIN / "scripts/flowctl.py")
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)


def fence(path, marker):
    text = (PLUGIN / path).read_text()
    return next(block for block in re.findall(r"```(?:python|bash)\n(.*?)```", text, re.S) if marker in block)


def result(preset, answers, state=None):
    return {"available": True, "answers": answers,
            "decision": f.judge_decide(preset, state or {}, answers)}


def execute(path, marker, **inputs):
    exec(compile(fence(path, marker), str(path), "exec"), inputs)  # noqa: S102 - execute trusted, shipped consumer fences
    return inputs


class JudgeConsumerTests(unittest.TestCase):
    def test_route_applies_decision_and_projects_only_candidates_on_fallback(self):
        path = "skills/flow-next-flow/workflow.md"
        for value, met, expected in [("defect", True, "defect"), ("host", False, "host")]:
            answer = {"available": True, "answers": {"kind": {"confidence": 0.91}, "reports_defect": {"noul": 0.99}},
                      "decision": {"value": value, "met": met, "candidates": [["defect", 0.52], ["build", 0.31], ["tiny", 0.1]]}}
            out = execute(path, "fence:judge-route-consumer", result=answer)
            self.assertEqual(out["route_value"], expected)
            self.assertNotIn("answers", out["host_route"])
            self.assertNotIn("reports_defect", json.dumps(out["host_route"]))
            if not met:
                self.assertEqual(out["host_route"]["candidates"], answer["decision"]["candidates"])
                self.assertIn("jev below floor", out["host_route"]["line"])
        out = execute(path, "fence:judge-route-consumer", result={"available": False, "reason": "timeout"})
        self.assertEqual(out["route_value"], "host")
        self.assertEqual(out["host_route"]["line"], "Route: host (jev-unavailable(timeout))")

    def test_qa_enabled_and_unavailable_apply_stage(self):
        path = "skills/flow-next-flow/references/gate-selection.md"
        for ui, target, runs, reason in [(0.84, "npm run dev", True, "ran"),
                                         (0.12, "npm run dev", False, "no UI-observable criteria"),
                                         (0.84, "", False, "no startable target")]:
            answer = result("qa-gate", {"ui_observable_criteria": {"noul": ui}}, {"startable_target_fact": target})
            out = execute(path, "fence:judge-qa-consumer", result=answer, target=target)
            self.assertEqual(out["qa_runs"], runs)
            self.assertIn(reason, out["qa_line"])
            self.assertIn(str(ui), out["qa_line"])
        for prior in (True, False):
            out = execute(path, "fence:judge-qa-consumer", result={"available": False, "reason": "timeout"},
                          host_qa_runs=prior, host_skip_reason="no drivable surface")
            self.assertEqual(out["qa_runs"], prior)
            self.assertIn("jev-unavailable(timeout)", out["qa_line"])

    def test_fork_enabled_and_unavailable_apply_action(self):
        path = "skills/flow-next-flow/references/prototype-before-ask.md"
        for gate, kind, confidence, action in [(0.08, "observable", 0.9, "none"),
                                              (0.9, "observable", 0.77, "observable"),
                                              (0.9, "product_or_preference", 0.71, "product_or_preference"),
                                              (0.9, "observable", 0.49, "host"),
                                              (0.9, "none_of_the_above", 0.99, "host")]:
            answer = result("fork-gate", {"fork_present": {"noul": gate}, "fork_kind": {"choice": kind, "confidence": confidence}})
            out = execute(path, "fence:judge-fork-consumer", result=answer)
            self.assertEqual(out["fork_action"], action)
            self.assertTrue(out["fork_line"].startswith("fork-gate: "))
        out = execute(path, "fence:judge-fork-consumer", result={"available": False, "reason": "no_key"})
        self.assertEqual(out["fork_action"], "host")
        self.assertEqual(out["fork_line"], "fork-gate: host (jev-unavailable(no_key))")

    def test_memory_applies_returned_order_and_spawn_fallback(self):
        path = "skills/flow-next-plan/references/judge-memory.md"
        matches = [{"entry_id": "b", "jev_score": 2, "jev_rank": 1},
                   {"entry_id": "a", "jev_score": 1, "jev_rank": 2}]
        out = execute(path, "fence:judge-memory-consumer", result={"matches": matches, "rerank": "jev", "stage_line": "memory: reranked (jev, 3 -> 2)"})
        self.assertEqual([m["entry_id"] for m in out["memory_matches"]], ["b", "a"])
        self.assertFalse(out["spawn_memory_scout"])
        fallback = {"matches": list(reversed(matches)), "rerank": "bm25", "stage_line": "memory: bm25 (jev-unavailable(no_key))"}
        out = execute(path, "fence:judge-memory-consumer", result=fallback)
        self.assertTrue(out["spawn_memory_scout"])
        self.assertEqual([m["entry_id"] for m in out["memory_matches"]], ["a", "b"])
        self.assertIn("jev-unavailable(no_key)", out["memory_line"])
        # An empty first search on an unavailable judge still gets the scout's refinement.
        fallback["matches"] = []
        out = execute(path, "fence:judge-memory-consumer", result=fallback)
        self.assertTrue(out["spawn_memory_scout"])
        self.assertEqual(out["memory_matches"], [])
        empty = {"matches": [], "rerank": "jev", "stage_line": "memory: reranked (jev, 0 -> 0)"}
        self.assertFalse(execute(path, "fence:judge-memory-consumer", result=empty)["spawn_memory_scout"])

    def test_shared_route_gate_decisions_are_consumed(self):
        answers = {"ui_observable_criteria": {"noul": 0.84}, "fork_present": {"noul": 0.8},
                   "fork_kind": {"choice": "observable", "confidence": 0.77}}
        route = {"available": True, "answers": answers, "decision": {
            "value": "build", "qa": f.judge_decide("qa-gate", {"startable_target_fact": "dev"}, answers),
            "fork": f.judge_decide("fork-gate", {}, answers)}}
        qa = execute("skills/flow-next-flow/references/gate-selection.md", "fence:judge-qa-consumer", result=route, target="dev")
        fork = execute("skills/flow-next-flow/references/prototype-before-ask.md", "fence:judge-fork-consumer", result=route)
        self.assertTrue(qa["qa_runs"])
        self.assertEqual(fork["fork_action"], "observable")

    @unittest.skipIf(sys.platform == "win32" or not shutil.which("bash") or not shutil.which("jq"), "requires POSIX bash and jq")
    def test_auto_reuses_probe_and_preserves_failed_observation(self):
        block = fence("skills/flow-next-flow/auto.md", "PR_PROBE_FAILED=0")
        for route, expected in [
            ({"available": True, "decision": {"pr_ref": {"url": "pr1", "state": "OPEN"}}}, "OPEN=pr1 FAIL=0"),
            ({"available": True, "decision": {"pr_ref": None}}, "OPEN= FAIL=0"),
            ({"available": False, "pr_probe_failed": True}, "OPEN= FAIL=1"),
            ({"available": False, "reason": "no_key"}, "OPEN=legacy FAIL=0"),
        ]:
            env = dict(os.environ, ROUTE_JSON=json.dumps(route), SPEC_JSON='{"branch_name":"test"}')
            stub = "gh() { printf '%s\\n' '[{\"url\":\"legacy\",\"state\":\"OPEN\"}]'; }\n"
            proc = subprocess.run(["bash", "-c", stub + block + '\nprintf "OPEN=%s FAIL=%s\n" "$OPEN_PR" "$PR_PROBE_FAILED"'],
                                  env=env, capture_output=True, text=True, check=True)
            self.assertEqual(proc.stdout.strip(), expected)


    def tier(self, choice="mechanical", confidence=0.88, **overrides):
        args = dict(result=result("tier", {"tier": {"choice": choice, "confidence": confidence, "probabilities": {choice: confidence}}}),
                    explicit_model=None, fast_model="fast-test-model", can_spawn_model=True, can_bridge=False,
                    role_model=None)
        args.update(overrides)
        return execute("skills/flow-next-work/references/judge-tier.md", "fence:judge-tier-dispatch", **args)

    def test_tier_selects_spawn_model_not_only_prompt(self):
        out = self.tier()
        # Host tool boundary: the selected field must reach the spawn parameter.
        calls = []
        def spawn(**kwargs):
            calls.append(kwargs)
        spawn(**out["spawn_model_args"], prompt="IMPLEMENTER: " + out["implementer"])
        self.assertEqual(calls[0]["model"], "fast-test-model")
        self.assertEqual(calls[0]["prompt"], "IMPLEMENTER: fast-test-model")
        self.assertIn("Tier: mechanical", out["tier_line"])

    def test_tier_pinned_role_wins_over_spawn_parameter(self):
        # Codex reach: a role's declared model beats the spawn parameter (reach/codex.md).
        def effective_model(role_model, **spawn_kwargs):
            return role_model or spawn_kwargs.get("model") or "session"
        for role_model in ("gpt-5.6-terra", None):
            with self.subTest(role_model=role_model):
                out = self.tier(role_model=role_model)
                actual = effective_model(role_model, **out["spawn_model_args"])
                self.assertIn(actual, out["tier_line"])
                self.assertEqual(out["selected_model"], None if role_model else "fast-test-model")
        pinned = self.tier(role_model="gpt-5.6-terra")
        self.assertIsNone(pinned["implementer"])
        self.assertIn("(role pins model)", pinned["tier_line"])
        pinned = self.tier(role_model="gpt-5.6-terra", explicit_model="user-model")
        self.assertIn("explicit IMPLEMENTER preserved", pinned["tier_line"])

    def test_tier_preserves_explicit_and_unreachable_and_unavailable(self):
        for kwargs in ({"explicit_model": "user-model"}, {"fast_model": None},
                       {"can_spawn_model": False}, {"confidence": 0.79},
                       {"choice": "moderate"}, {"choice": "intelligent"},
                       {"result": {"available": False, "reason": "disabled"}}):
            out = self.tier(**kwargs)
            self.assertIsNone(out["selected_model"])
            self.assertEqual(out["implementer"], kwargs.get("explicit_model"))
        self.assertIn("jev-unavailable(disabled)", out["tier_line"])
        out = self.tier(can_spawn_model=False, can_bridge=True)
        self.assertIsNone(out["selected_model"])
        self.assertEqual(out["implementer"], "fast-test-model")
        out = self.tier(choice="long_running", confidence=0.86)
        self.assertIsNone(out["selected_model"])
        self.assertIn("bridge recommended", out["tier_line"])


if __name__ == "__main__":
    unittest.main()

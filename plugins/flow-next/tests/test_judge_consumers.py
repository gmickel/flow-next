"""Run the shipped consumer fences against typed judge fixtures; no network."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
spec = importlib.util.spec_from_file_location("flowctl_judge_consumers_test", PLUGIN / "scripts/flowctl.py")
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD  # noqa: E402

FLOWCTL = PLUGIN / "scripts" / "flowctl"
WORKFLOW = "skills/flow-next-flow/SKILL.md"
SHELL = os.name != "nt" and shutil.which("bash") and shutil.which("jq")


def fence(path, marker):
    text = (PLUGIN / path).read_text()
    return next(block for block in re.findall(r"```(?:python|bash)\n(.*?)```", text, re.S) if marker in block)


def result(preset, answers, state=None):
    return {"available": True, "answers": answers,
            "decision": f.judge_decide(preset, state or {}, answers)}


def execute(path, marker, **inputs):
    exec(compile(fence(path, marker), str(path), "exec"), inputs)  # noqa: S102 - execute trusted, shipped consumer fences
    return inputs


def live_state(**overrides):
    state = {"spec_body": "Build it", "status": "open", "ready": True, "no_plan": False, "tasks_total": 0, "tasks_done": 0,
             "pr_exists": False, "pr_ref": None, "startable_target_fact": "npm run dev"}
    state.update(overrides)
    return state


def keep(judge_output):
    """Project a route result through the flow skill's shipped jq filter."""
    program = re.search(r"jq -c '(.*?)'", fence(WORKFLOW, "--preset route"), re.S).group(1)
    out = subprocess.run(["jq", "-c", program], input=json.dumps(judge_output), capture_output=True,
                         text=True, check=True)
    return json.loads(out.stdout)


class JudgeConsumerTests(unittest.TestCase):
    @unittest.skipUnless(SHELL, "POSIX shell and jq")
    def test_judge_check_runs_once_and_never_prints_the_key(self):
        check = fence("skills/flow-next-flow/references/prototype-before-ask.md", "JUDGE=on")
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([*FLOWCTL_CMD, "init", "--json"], cwd=tmp, check=True, capture_output=True)
            for key, enabled, expected in (("secret-never-printed", "true", "on"), ("", "true", "off"),
                                           (None, "true", "off"), ("secret-never-printed", "false", "off")):
                with self.subTest(key=bool(key), enabled=enabled):
                    subprocess.run([*FLOWCTL_CMD, "config", "set", "judge.enabled", enabled, "--json"],
                                   cwd=tmp, check=True, capture_output=True)
                    env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
                    if key is not None:
                        env["TYPESAFE_API_KEY"] = key
                    env["FLOWCTL"] = str(FLOWCTL)
                    run = subprocess.run(["bash", "-c", check + '\necho "state=$JUDGE"'], cwd=tmp, env=env,
                                         capture_output=True, text=True)
                    self.assertIn(f"state={expected}", run.stdout)
                    self.assertEqual(run.stdout.count("judge: off"), int(expected == "off"))
                    self.assertNotIn("secret-never-printed", run.stdout + run.stderr)

    @unittest.skipUnless(SHELL, "jq")
    def test_route_projection_is_the_code_lifecycle_with_or_without_a_key(self):
        cases = (({"pr_exists": True}, "existing_pr_tail"), ({"tasks_total": 2}, "work_planned"),
                 ({"tasks_total": 2, "tasks_done": 2}, "all_done_make_pr"),
                 ({}, "work_no_plan_default"), ({"ready": False}, "host"))
        for key in ("", "test-key-never-sent"):
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": key}), patch.object(f, "get_config", return_value=True), \
                    patch.object(f, "judge_https_connection") as connect:
                for overrides, value in cases:
                    with self.subTest(key=bool(key), value=value):
                        out = keep(f.judge_route(live_state(**overrides)))
                        self.assertEqual(set(out), {"available", "reason", "pr_probe_failed", "decision"})
                        self.assertEqual((out["available"], out["reason"]), (False, "routing_is_code"))
                        self.assertEqual(out["decision"]["value"], value)
                        self.assertEqual(out["decision"]["met"], value != "host")
                out = keep(f.judge_route(live_state(pr_exists=None)))
                connect.assert_not_called()
            self.assertTrue(out["pr_probe_failed"])
            self.assertIsNone(out["decision"])

    def test_memory_fence_is_one_search_that_runs_without_a_key(self):
        command = fence("skills/flow-next-plan/references/judge-memory.md", "memory search")
        argv = command.strip().replace('"<task sentence>"', "").split()
        self.assertEqual(argv[:3], ["$FLOWCTL", "memory", "search"])
        with tempfile.TemporaryDirectory() as tmp:
            for args in (["init"], ["config", "set", "memory.enabled", "true"], ["memory", "init"]):
                subprocess.run([*FLOWCTL_CMD, *args, "--json"], cwd=tmp, check=True, capture_output=True)
            body = Path(tmp) / "body.md"
            for i in range(17):
                body.write_text(f"Saving a unicode file name crashes the settings page, case {i}.\n")
                subprocess.run([*FLOWCTL_CMD, "memory", "add", "--track", "bug", "--category", "runtime-errors",
                                "--title", f"Unicode save crash {i}", "--body-file", str(body),
                                "--no-overlap-check", "--json"], cwd=tmp, check=True, capture_output=True)
            env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
            run = subprocess.run([*FLOWCTL_CMD, "memory", "search", "unicode save crash", *argv[3:]], cwd=tmp,
                                 env=env, check=True, capture_output=True, text=True)
        out = json.loads(run.stdout)
        self.assertEqual((out["rerank"], out["stage_line"]), ("bm25", "memory: bm25 (jev-unavailable(no_key))"))
        self.assertEqual(out["count"], 15)
        self.assertTrue(all(m["title"] and "snippet" in m for m in out["matches"]))

    def tier(self, choice="mechanical", confidence=0.88, **overrides):
        args = dict(result=result("tier", {"tier": {"choice": choice, "confidence": confidence, "probabilities": {choice: confidence}}}),
                    explicit_model=None, fast_model="fast-test-model", can_spawn_model=True, can_bridge=False,
                    role_model=None)
        args.update(overrides)
        out = f.judge_tier_dispatch(args.pop("result"), argparse.Namespace(**args))
        out["spawn_model_args"] = {"model": out["spawn_model"]} if out["spawn_model"] else {}
        return out

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
                self.assertEqual(out["spawn_model"], None if role_model else "fast-test-model")
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
            self.assertIsNone(out["spawn_model"])
            self.assertEqual(out["implementer"], kwargs.get("explicit_model"))
        self.assertIn("jev-unavailable(disabled)", out["tier_line"])
        out = self.tier(can_spawn_model=False, can_bridge=True)
        self.assertIsNone(out["spawn_model"])
        self.assertEqual(out["implementer"], "fast-test-model")
        out = self.tier(choice="long_running", confidence=0.86)
        self.assertIsNone(out["spawn_model"])
        self.assertIn("bridge recommended", out["tier_line"])


if __name__ == "__main__":
    unittest.main()

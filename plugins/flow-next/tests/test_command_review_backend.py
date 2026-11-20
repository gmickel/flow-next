"""fn-337: a configured command answers the review execution contract.

Every review here runs a real subprocess (a stand-in wrapper) through the
public CLI, so the request on stdin, the response on stdout, the receipt and
the round accounting are what a user would see. The argv comes only from the
machine-local ``FLOW_REVIEW_COMMAND_<LABEL>`` variable.
"""

import json
import os
from pathlib import Path
import re
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flowctl  # noqa: E402
from test_claude_review_commands import (  # noqa: E402
    EPIC_ID, TASK_ID, _commit_change, _flow_repo, _run_cli,
)

WRAPPER = textwrap.dedent("""
    import json, os, sys, pathlib, time
    plan_path, log_dir = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    request = json.loads(sys.stdin.read())
    # One file per call, numbered by exclusive create: fan-out draws run
    # concurrently, and appends to a shared file can clobber each other on Windows.
    log_dir.mkdir(exist_ok=True)
    seq = 0
    while True:
        try:
            fd = os.open(log_dir / f"{seq:06d}.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            seq += 1
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"argv": sys.argv, "request": request, "cwd": os.getcwd(),
                             "token": "FLOW_REVIEW_EXECUTION_TOKEN" in os.environ}))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if len(plan) > 1:
        step = plan.pop(0)
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
    else:
        step = plan[0]
    time.sleep(step.get("sleep", 0))
    if step.get("linger"):
        import subprocess
        # Outside the repo: Windows cannot delete a directory a live process sits in.
        subprocess.Popen([sys.executable, "-c", f"import time; time.sleep({step['linger']})"],
                         cwd=os.path.dirname(sys.executable))
    sys.stderr.write(step.get("stderr", ""))
    if "flood" in step:
        sys.stdout.write("x" * step["flood"])
    elif "raw" in step:
        sys.stdout.write(step["raw"])
    else:
        response = {"schemaVersion": 1, "output": "", "stderr": "", "exitCode": 0}
        response.update(step.get("response", {}))
        if response.get("sessionId") == "ECHO":
            response["sessionId"] = request["sessionId"]
        sys.stdout.write(json.dumps(response))
    sys.exit(step.get("exit", 0))
""")

SHIP = {"response": {"output": "Looks right.\n<verdict>SHIP</verdict>\n",
                     "sessionId": "cmd-1", "observedModel": "gemini-9-pro"}}
NEEDS_WORK = {"response": {
    "output": "1. Major: off by one in a().\n<verdict>NEEDS_WORK</verdict>\n",
    "sessionId": "cmd-1", "observedModel": "gemini-9-pro"}}


def command_var(label):
    return "FLOW_REVIEW_COMMAND_" + label.upper().replace("-", "_")


def _alive(pid):
    """True while ``pid`` runs (a reaped or zombie process is not running)."""
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000 | 0x1000, False, pid)
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x102   # WAIT_TIMEOUT
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            return fh.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


class CommandTest(unittest.TestCase):
    """Each test's environment changes are undone when it ends."""

    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ))


class CommandRepo:
    """A flow repo whose environment labels the stand-in wrapper ``fake``.

    ``commands`` maps a label to its variable's value (a list is JSON-encoded,
    a string is set verbatim); ``tracked`` writes ``review.commands`` into the
    checked-out config.
    """

    def __init__(self, repo: Path, plan, commands=None, backend=None, extra_labels=(),
                 tracked=None):
        self.repo = repo
        self.plan = repo / "plan.json"
        self.log = repo / "requests"
        wrapper = repo / "wrapper.py"
        wrapper.write_text(WRAPPER, encoding="utf-8")
        self.set_plan(plan)
        self.argv = [sys.executable, str(wrapper), str(self.plan), str(self.log)]
        if commands is None:
            commands = {"fake": self.argv, **{label: self.argv for label in extra_labels}}
        for name in [k for k in os.environ if k.startswith("FLOW_REVIEW_COMMAND_")]:
            del os.environ[name]
        for label, value in commands.items():
            os.environ[command_var(label)] = value if isinstance(value, str) else json.dumps(value)
        review = {}
        if tracked is not None:
            review["commands"] = tracked
        if backend:
            review["backend"] = backend
        (repo / ".flow" / "config.json").write_text(
            json.dumps({"review": review}), encoding="utf-8")

    def set_plan(self, plan):
        self.plan.write_text(json.dumps(plan), encoding="utf-8")

    def requests(self):
        if not self.log.exists():
            return []
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(self.log.glob("*.json"))]

    def rounds(self):
        return flowctl._current_review_rounds(EPIC_ID, "impl", task_id=TASK_ID, use_json=True)


def impl_review(base, receipt, *extra):
    return _run_cli("command", "impl-review", TASK_ID, "--base", base,
                    "--receipt", str(receipt), "--json", *extra)


LABELS_ACCEPTED = ("gemini", "kimi-pro", "a_b", "x9", "-", "_")
LABELS_REJECTED = ("Gemini", "kimi.pro", "a/b", "a$b", "k\u00e9", "a b")


class CommandSpecGrammar(CommandTest):
    def test_label_round_trips_and_resolves_to_itself(self):
        spec = flowctl.BackendSpec.parse("command:gemini")
        self.assertEqual((spec.backend, spec.model, spec.effort), ("command", "gemini", None))
        self.assertEqual(str(spec), "command:gemini")
        with mock.patch.dict(os.environ, {"FLOW_COMMAND_MODEL": "other"}):
            self.assertEqual(str(spec.resolve()), "command:gemini")

    def test_bare_empty_or_extra_parts_are_rejected(self):
        for raw in ("command", "command:", "command:gemini:high"):
            with self.subTest(raw=raw), self.assertRaises(ValueError) as ctx:
                flowctl.BackendSpec.parse(raw)
            self.assertIn("command:<label>", str(ctx.exception))
            self.assertNotIn("review.commands", str(ctx.exception))

    def test_label_characters_match_the_schema(self):
        schema = json.loads((Path(flowctl.__file__).resolve().parents[1] / "schema"
                             / "flow-config.schema.json").read_text(encoding="utf-8"))
        backend = schema["properties"]["review"]["properties"]["backend"]
        patterns = [branch["pattern"] for branch in backend["anyOf"]
                    if branch.get("pattern", "").startswith("^command")]
        self.assertEqual(len(patterns), 1)
        for label in LABELS_ACCEPTED + LABELS_REJECTED:
            with self.subTest(label=label):
                try:
                    flowctl.BackendSpec.parse(f"command:{label}")
                    runtime = True
                except ValueError as exc:
                    runtime = False
                    self.assertIn(label, str(exc))
                    self.assertIn("FLOW_REVIEW_COMMAND_", str(exc))
                self.assertEqual(runtime, label in LABELS_ACCEPTED)
                self.assertEqual(bool(re.fullmatch(patterns[0], f"command:{label}")), runtime)

    def test_whitespace_is_refused_by_runtime_and_schema_alike(self):
        schema = json.loads((Path(flowctl.__file__).resolve().parents[1] / "schema"
                             / "flow-config.schema.json").read_text(encoding="utf-8"))
        backend = schema["properties"]["review"]["properties"]["backend"]
        patterns = [branch["pattern"] for branch in backend["anyOf"] if "pattern" in branch]
        for raw in ("command: grok", "command:grok ", " command:grok", "command :grok",
                    "command:\tgrok", "command:grok\n"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError) as ctx:
                    flowctl.BackendSpec.parse(raw)
                self.assertIn("command:<label>", str(ctx.exception))
                # fullmatch: JSON Schema's `$` never matches before a trailing newline.
                self.assertFalse(any(re.fullmatch(p, raw) for p in patterns))
        self.assertEqual(flowctl.BackendSpec.parse("command:grok").model, "grok")

    def test_padded_command_spec_never_runs_from_env_or_draw(self):
        for padded in (" command:fake", "command:fake ", "command:fake\n"):
            with self.subTest(padded=padded), _flow_repo() as (repo, base), \
                    mock.patch.dict(os.environ, {"FLOW_REVIEW_BACKEND": padded}):
                env = CommandRepo(repo, [SHIP])
                resolved = json.loads(_run_cli("review-backend", "--json")[1])
                self.assertNotEqual(resolved.get("spec"), "command:fake")
                code, out, err = impl_review(base, repo / "r.json")
                self.assertNotEqual(code, 0)
                self.assertNotIn('"verdict": "SHIP"', out)
                code, out, err = _run_cli("command", "impl-review-fanout", TASK_ID, "--base", base,
                                          "--spec", "command:fake", "--draw", "correctness",
                                          "--draw", f"contracts={padded}", "--json")
                self.assertEqual(code, 2, out)
                self.assertIn("command:<label>", out + err)
                self.assertEqual(env.requests(), [])

    def test_config_set_refuses_a_command_without_a_label(self):
        with _flow_repo() as (repo, _base):
            for raw in ("command", "command:", "command: grok"):
                with self.subTest(raw=raw):
                    code, out, err = _run_cli("config", "set", "review.backend", raw, "--json")
                    self.assertNotEqual(code, 0, out)
                    self.assertIn("command:<label>", out + err)
                    config_file = repo / ".flow" / "config.json"
                    config = json.loads(config_file.read_text()) if config_file.exists() else {}
                    self.assertNotEqual(config.get("review", {}).get("backend"), raw)
            # A label whose variable is not set yet is accepted: it may be added afterwards.
            os.environ.pop("FLOW_REVIEW_COMMAND_LATER", None)
            code, out, err = _run_cli("config", "set", "review.backend", "command:later", "--json")
            self.assertEqual(code, 0, out + err)
            config = json.loads((repo / ".flow" / "config.json").read_text())
            self.assertEqual(config["review"]["backend"], "command:later")


class CommandImplReview(CommandTest):
    def test_request_receipt_and_observed_model(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [NEEDS_WORK])
            receipt = repo / "receipt.json"
            code, out, err = impl_review(base, receipt, "--spec", "command:fake")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["verdict"], "NEEDS_WORK")
            published = json.loads(receipt.read_text())
            self.assertEqual(published["mode"], "command")
            self.assertEqual(published["label"], "fake")
            self.assertEqual(published["spec"], "command:fake")
            self.assertEqual(published["model"], "gemini-9-pro")
            self.assertEqual(published["session_id"], "cmd-1")
            self.assertNotIn("effort", published)
            (call,) = env.requests()
            request = call["request"]
            # Python drops the interpreter from sys.argv; the rest arrives verbatim.
            self.assertEqual(call["argv"], [str(repo / "wrapper.py"), str(env.plan), str(env.log)])
            self.assertEqual((request["backend"], request["model"], request["effort"]),
                             ("command", None, None))
            self.assertEqual(request["permissionMode"], "read-only")
            self.assertEqual(request["repositoryPath"], str(repo))
            # The command starts outside the checkout, so a relative path never reaches it.
            self.assertEqual(Path(call["cwd"]).resolve(), Path.home().resolve())
            self.assertIsNone(request["sessionId"])
            self.assertFalse(request["resumeOnly"])
            self.assertEqual(request["schemaVersion"], 1)
            self.assertTrue(request["requestId"])
            self.assertIsInstance(request["timeoutSeconds"], int)
            self.assertIn("Diff delivery (command backend)", request["prompt"])
            self.assertEqual(env.rounds(), 1)

    def test_selected_from_config_env_and_task_pin(self):
        with _flow_repo() as (repo, base):
            CommandRepo(repo, [SHIP], backend="command:fake")
            self.assertEqual(_run_cli("review-backend", TASK_ID)[1].strip(), "command")
            code, _, err = impl_review(base, repo / "config.json")
            self.assertEqual(code, 0, err)
        with _flow_repo() as (repo, base):
            CommandRepo(repo, [SHIP])
            with mock.patch.dict(os.environ, {"FLOW_REVIEW_BACKEND": "command:fake"}):
                self.assertEqual(_run_cli("review-backend")[1].strip(), "command")
                code, _, err = impl_review(base, repo / "env.json")
            self.assertEqual(code, 0, err)
        with _flow_repo() as (repo, base):
            CommandRepo(repo, [SHIP])
            (repo / ".flow" / "tasks" / f"{TASK_ID}.json").write_text(json.dumps({
                "id": TASK_ID, "spec": EPIC_ID, "status": "in_progress",
                "review": "command:fake"}), encoding="utf-8")
            self.assertEqual(_run_cli("review-backend", TASK_ID)[1].strip(), "command")
            code, _, err = impl_review(base, repo / "pin.json")
            self.assertEqual(code, 0, err)

    def test_set_backend_accepts_label_and_rejects_bare_command(self):
        with _flow_repo() as (repo, _base):
            CommandRepo(repo, [SHIP])
            code, _, err = _run_cli("spec", "set-backend", EPIC_ID, "--review", "command:fake", "--json")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads((repo / ".flow" / "specs" / f"{EPIC_ID}.json").read_text())
                             ["default_review"], "command:fake")
            code, out, _ = _run_cli("spec", "set-backend", EPIC_ID, "--review", "command", "--json")
            self.assertNotEqual(code, 0)
            self.assertIn("command:<label>", out)

    def test_bad_selection_fails_before_dispatch_naming_label_and_variable(self):
        secret = "SECRET-VALUE-7731"
        var = "FLOW_REVIEW_COMMAND_FAKE"
        cases = [
            ({"fake": []}, "command:fake", [var, "command:fake"]),
            ({"fake": [""]}, "command:fake", [var, "command:fake"]),
            ({"fake": json.dumps(secret)}, "command:fake", [var, "command:fake"]),
            ({"fake": ["x", 3]}, "command:fake", [var, "command:fake"]),
            ({"fake": ["python3", "a\u0000b"]}, "command:fake", [var, "command:fake"]),
            ({"fake": "[" * 8000 + "]" * 8000}, "command:fake", [var, "command:fake"]),
            ({"fake": f"not json {secret}"}, "command:fake", [var, "command:fake"]),
            ({"fake": ""}, "command:fake", [var, "command:fake", "not set"]),
            ({}, "command:fake", [var, "command:fake", "not set"]),
            ({"fake": "wrapper"}, "command:nope", ["FLOW_REVIEW_COMMAND_NOPE", "command:nope"]),
            ({}, "command:Bad.Label", ["FLOW_REVIEW_COMMAND_", "Bad.Label"]),
            ({}, "command", ["command:<label>"]),
        ]
        if os.name != "nt":
            # POSIX argv is bytes: a lone surrogate cannot be encoded for the spawn.
            cases.append(({"fake": json.dumps(["python3", "\ud800"])}, "command:fake",
                          [var, "command:fake"]))
        for commands, backend, needles in cases:
            with self.subTest(backend=backend, commands=str(commands)[:60]), \
                    _flow_repo() as (repo, base):
                env = CommandRepo(repo, [SHIP], commands=commands, backend=backend)
                code, out, err = impl_review(base, repo / "r.json")
                self.assertEqual(code, 2, out + err)
                # A stored label that fails to parse is named in the warning on stderr.
                for needle in needles:
                    self.assertIn(needle, json.loads(out)["error"] + err)
                self.assertNotIn(secret, out + err)
                self.assertEqual(env.requests(), [])
                self.assertEqual(env.rounds(), 0)
                self.assertFalse((repo / "r.json").exists())

    def test_label_maps_to_one_variable(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [SHIP], commands={})
            os.environ["FLOW_REVIEW_COMMAND_KIMI_PRO"] = json.dumps(env.argv)
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:kimi-pro")
            self.assertEqual(code, 0, out + err)
            self.assertEqual(json.loads((repo / "r.json").read_text())["label"], "kimi-pro")
            self.assertEqual(len(env.requests()), 1)

    def test_relative_paths_never_resolve_in_the_checkout(self):
        with _flow_repo() as (repo, base):
            marker = repo / "ran-relative"
            (repo / "planted.py").write_text(
                f"open({str(marker)!r}, 'w').write('x')\n", encoding="utf-8")
            env = CommandRepo(repo, [SHIP], commands={"fake": [sys.executable, "planted.py"]})
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:fake")
            self.assertNotEqual(code, 0)
            self.assertFalse(marker.exists())
            self.assertEqual(env.rounds(), 0)

    def test_program_inside_the_checkout_is_refused_before_dispatch(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [SHIP])
            os.environ["FLOW_REVIEW_COMMAND_FAKE"] = json.dumps([str(repo / "wrapper.py")])
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:fake")
            self.assertEqual(code, 2, out + err)
            error = json.loads(out)["error"]
            self.assertIn("FLOW_REVIEW_COMMAND_FAKE", error)
            self.assertIn("inside the checkout", error)
            self.assertEqual(env.requests(), [])
            self.assertEqual(env.rounds(), 0)

    def test_bare_program_resolves_on_path_never_in_the_current_directory(self):
        exe = ".exe" if os.name == "nt" else ""   # Windows finds it through PATHEXT
        with _flow_repo() as (repo, _base), tempfile.TemporaryDirectory() as td:
            tools = Path(td).resolve()
            for where in (tools, repo):   # the checkout is the current directory
                program = where / f"reviewer{exe}"
                program.write_text("", encoding="utf-8")
                program.chmod(0o755)
            os.environ["FLOW_REVIEW_COMMAND_G"] = json.dumps(["reviewer", "--flag"])
            os.environ["PATH"] = str(tools)
            first, *rest = flowctl._review_command_argv("g")
            self.assertEqual(os.path.normcase(os.path.dirname(first)), os.path.normcase(str(tools)))
            self.assertEqual(rest, ["--flag"])
            # A relative PATH entry is the current directory again: never searched.
            for path in (os.curdir, "", os.pathsep.join([os.curdir, "nonexistent-dir"])):
                os.environ["PATH"] = path
                with self.subTest(path=path), self.assertRaises(ValueError) as ctx:
                    flowctl._review_command_argv("g")
                self.assertIn("not found on PATH", str(ctx.exception))
                self.assertNotIn("reviewer", str(ctx.exception))

    @unittest.skipIf(os.name == "nt", "symlinks need privileges on Windows")
    def test_checkout_symlink_to_an_outside_program_is_refused(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [SHIP])
            (repo / "bin").mkdir()
            (repo / "bin" / "py").symlink_to(sys.executable)
            os.environ["FLOW_REVIEW_COMMAND_FAKE"] = json.dumps(
                [str(repo / "bin" / "py"), *env.argv[1:]])
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:fake")
            self.assertEqual(code, 2, out + err)
            self.assertIn("inside the checkout", json.loads(out)["error"])
            self.assertEqual(env.requests(), [])
            self.assertEqual(env.rounds(), 0)

    def test_relative_program_resolves_against_the_home_directory(self):
        os.environ.update({"HOME": "/home/someone", "USERPROFILE": "/home/someone",
                           "FLOW_REVIEW_COMMAND_G": json.dumps(["bin/review"])})
        self.assertEqual(flowctl._review_command_argv("g"),
                         [os.path.join(os.path.expanduser("~"), "bin/review")])

    def test_tracked_commands_never_supply_or_change_the_argv(self):
        """A branch's config names a program; reviewing the branch never runs it."""
        for with_variable in (False, True):
            with self.subTest(with_variable=with_variable), _flow_repo() as (repo, base):
                marker = repo / "ran-tracked"
                tracked_argv = [sys.executable, "-c",
                                f"open({str(marker)!r}, 'w').write('x')"]
                env = CommandRepo(repo, [SHIP], commands=None if with_variable else {},
                                  backend="command:fake", tracked={"fake": tracked_argv})
                code, out, err = impl_review(base, repo / "r.json")
                self.assertEqual(code, 2, out + err)
                error = json.loads(out)["error"]
                self.assertIn("review.commands", error)
                self.assertIn("no longer read", error)
                self.assertIn("FLOW_REVIEW_COMMAND_FAKE", error)
                self.assertFalse(marker.exists())
                self.assertEqual(env.requests(), [])
                self.assertEqual(env.rounds(), 0)

    def test_transport_failures_refund_and_never_publish_a_verdict(self):
        verdict = "<verdict>SHIP</verdict>"
        cases = [
            ("exit", {"raw": verdict, "exit": 3, "stderr": "quota exceeded\n"}, "quota exceeded"),
            ("malformed", {"raw": f"not json {verdict}"}, "invalid response"),
            ("wrong shape", {"raw": json.dumps({"output": verdict})}, "invalid response"),
            ("reported failure", {"response": {"output": verdict, "exitCode": 4,
                                               "stderr": "model gone"}}, "reported exit code 4"),
            ("timeout", {"sleep": 5, "response": {"output": verdict}}, "timed out"),
        ]
        for name, step, needle in cases:
            with self.subTest(name), _flow_repo() as (repo, base), \
                    mock.patch.dict(os.environ, {"FLOW_REVIEW_EXEC_TIMEOUT": "1"}):
                env = CommandRepo(repo, [step])
                receipt = repo / "r.json"
                code, out, err = impl_review(base, receipt, "--spec", "command:fake")
                self.assertNotEqual(code, 0)
                self.assertNotIn('"verdict": "SHIP"', out)
                self.assertFalse(receipt.exists())
                self.assertEqual(env.rounds(), 0)
                self.assertIn(needle, out + err)
                spec = json.loads((repo / ".flow" / "specs" / f"{EPIC_ID}.json").read_text())
                self.assertIn(needle, json.dumps(spec))

    def test_missing_executable_is_a_transport_failure(self):
        with _flow_repo() as (repo, base):
            missing = repo.parent / f"{repo.name}-no-such-wrapper"   # outside the checkout
            env = CommandRepo(repo, [SHIP], commands={"fake": [str(missing)]})
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:fake")
            self.assertNotEqual(code, 0)
            self.assertIn("not found", out + err)
            # The message names the variable and the label, never any of its value.
            self.assertIn("FLOW_REVIEW_COMMAND_FAKE", out + err)
            self.assertIn("command:fake", out + err)
            self.assertNotIn(missing.name, out + err)
            self.assertEqual(env.rounds(), 0)

    def test_timeout_stops_the_whole_process_tree(self):
        with _flow_repo() as (repo, base), \
                mock.patch.dict(os.environ, {"FLOW_REVIEW_EXEC_TIMEOUT": "3"}):
            pid_file = repo.parent / f"{repo.name}-helper.pid"
            spawner = repo.parent / f"{repo.name}-spawner.py"
            # Outside the repo: Windows cannot delete a directory a live process sits in.
            # One helper in the wrapper's group, one that left it for a session of its own.
            spawner.write_text(textwrap.dedent("""
                import os, subprocess, sys, time
                sleeper = [sys.executable, "-c", "import time; time.sleep(60)"]
                where = os.path.dirname(sys.executable)
                helpers = [subprocess.Popen(sleeper, cwd=where)]
                if os.name != "nt":
                    helpers.append(subprocess.Popen(sleeper, cwd=where, start_new_session=True))
                with open(sys.argv[1], "w", encoding="utf-8") as fh:
                    fh.write(" ".join(str(h.pid) for h in helpers))
                time.sleep(60)
            """), encoding="utf-8")
            env = CommandRepo(repo, [SHIP], commands={
                "fake": [sys.executable, str(spawner), str(pid_file)]})
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:fake")
            helpers = [int(pid) for pid in pid_file.read_text(encoding="utf-8").split()]
            try:
                self.assertNotEqual(code, 0)
                self.assertIn("timed out", out + err)
                self.assertNotIn("not stopped", out + err)
                self.assertEqual(env.rounds(), 0)
                deadline = time.monotonic() + 10
                while any(map(_alive, helpers)) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertEqual([pid for pid in helpers if _alive(pid)], [],
                                 "the wrapper's helpers outlived the timeout")
            finally:
                for pid in helpers:
                    if _alive(pid) and os.name != "nt":
                        os.kill(pid, 9)

    @unittest.skipIf(os.name == "nt", "the POSIX process-group kill is what is refused here")
    def test_a_tree_that_cannot_be_stopped_is_named_in_the_reason(self):
        argv = [sys.executable, "-c", "import time; time.sleep(30)"]
        with mock.patch.object(flowctl.os, "killpg", side_effect=PermissionError(1, "Operation not permitted")):
            returncode, _, _, problem, stop_error = flowctl._run_review_command(
                argv, b"{}", timeout=1, cwd=Path.home(), env=dict(os.environ))
        self.assertEqual(problem, "timeout")
        self.assertIn("Operation not permitted", stop_error)
        # Helpers outside the group cannot be found without a process listing.
        with mock.patch.object(flowctl, "_review_command_lookup", return_value=None):
            _, _, _, problem, stop_error = flowctl._run_review_command(
                argv, b"{}", timeout=1, cwd=Path.home(), env=dict(os.environ))
        self.assertEqual(problem, "timeout")
        self.assertIn("cannot list its processes", stop_error)

    def test_leading_tilde_expands_in_every_element(self):
        os.environ.update({"HOME": "/home/someone", "USERPROFILE": "/home/someone",
                           "FLOW_REVIEW_COMMAND_G": json.dumps(
                               ["~/bin/review", "~/conf.json", "a~b"])})
        self.assertEqual(flowctl._review_command_argv("g"),
                         [os.path.expanduser("~/bin/review"),
                          os.path.expanduser("~/conf.json"), "a~b"])

    def test_windows_refuses_a_batch_file_first(self):
        # pathlib refuses WindowsPath on POSIX, so the config and repo reads are stubbed.
        self.enterContext(mock.patch.object(flowctl, "load_flow_config", return_value={}))
        self.enterContext(mock.patch.object(flowctl, "get_repo_root",
                                            return_value="/nonexistent-checkout"))
        for first in ("C:/tools/review.cmd", "/opt/review.BAT", "~/bin/review.Cmd"):
            os.environ["FLOW_REVIEW_COMMAND_G"] = json.dumps([first])
            with self.subTest(first=first), mock.patch.object(flowctl.os, "name", "nt"):
                with self.assertRaises(ValueError) as ctx:
                    flowctl._review_command_argv("g")
                self.assertIn("interpreter", str(ctx.exception))
                self.assertIn("FLOW_REVIEW_COMMAND_G", str(ctx.exception))
        os.environ["FLOW_REVIEW_COMMAND_G"] = json.dumps(["reviewer"])
        with mock.patch.object(flowctl.os, "name", "nt"), mock.patch.object(
                flowctl, "_review_command_lookup", return_value="/opt/tools/reviewer.CMD"):
            with self.assertRaises(ValueError) as ctx:
                flowctl._review_command_argv("g")
            self.assertIn("interpreter", str(ctx.exception))
        os.environ["FLOW_REVIEW_COMMAND_G"] = json.dumps(["/opt/py/python", "review.cmd"])
        with mock.patch.object(flowctl.os, "name", "nt"):
            self.assertEqual(flowctl._review_command_argv("g"), ["/opt/py/python", "review.cmd"])

    def test_missing_observed_model_is_recorded_as_not_reported(self):
        with _flow_repo() as (repo, base):
            CommandRepo(repo, [{"response": {"output": "<verdict>SHIP</verdict>"}}])
            receipt = repo / "r.json"
            code, _, err = impl_review(base, receipt, "--spec", "command:fake")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(receipt.read_text())["model"], "not reported")


class CommandResume(CommandTest):
    def test_rereview_resumes_the_returned_session(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [NEEDS_WORK, {"response": {
                "output": "<verdict>SHIP</verdict>", "sessionId": "ECHO",
                "observedModel": "gemini-9-pro"}}])
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            _commit_change(repo, "def a(x):\n    return x + 2\n", "fix")
            code, out, err = impl_review(base, receipt, "--spec", "command:fake")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["verdict"], "SHIP")
            second = env.requests()[1]["request"]
            self.assertEqual(second["sessionId"], "cmd-1")
            self.assertFalse(second["resumeOnly"])
            # Findings travel even on resume: a wrapper's CLI may silently start
            # a new session under the requested id.
            self.assertIn("off by one", second["prompt"])

    def test_failed_resume_reruns_fresh_with_prior_findings(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [
                NEEDS_WORK,
                {"response": {"exitCode": 2, "resumeFailed": True, "stderr": "no session"}},
                {"response": {"output": "<verdict>SHIP</verdict>", "sessionId": "cmd-2"}},
            ])
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            _commit_change(repo, "def a(x):\n    return x + 2\n", "fix")
            code, out, err = impl_review(base, receipt, "--spec", "command:fake")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["verdict"], "SHIP")
            calls = [c["request"] for c in env.requests()]
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[1]["sessionId"], "cmd-1")
            self.assertIsNone(calls[2]["sessionId"])
            self.assertIn("off by one", calls[2]["prompt"])
            self.assertEqual(json.loads(receipt.read_text())["session_id"], "cmd-2")


class CommandOtherReviews(CommandTest):
    def test_plan_and_completion_reviews_run_through_the_command(self):
        for sub in ("plan-review", "completion-review"):
            with self.subTest(sub=sub), _flow_repo() as (repo, base):
                env = CommandRepo(repo, [SHIP])
                receipt = repo / f"{sub}.json"
                code, out, err = _run_cli("command", sub, EPIC_ID, "--base", base,
                                          "--receipt", str(receipt), "--spec", "command:fake",
                                          "--json")
                self.assertEqual(code, 0, err)
                self.assertEqual(json.loads(out)["verdict"], "SHIP")
                published = json.loads(receipt.read_text())
                self.assertEqual((published["mode"], published["label"], published["model"]),
                                 ("command", "fake", "gemini-9-pro"))
                self.assertEqual(len(env.requests()), 1)

    def test_fanout_receipt_keeps_label_and_observed_model(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [SHIP])
            receipt = repo / "fanout.json"
            code, out, err = _run_cli("command", "impl-review-fanout", TASK_ID, "--base", base,
                                      "--receipt", str(receipt), "--spec", "command:fake",
                                      "--json")
            self.assertEqual(code, 0, err)
            result = json.loads(out)
            self.assertEqual(len(env.requests()), 3)
            merged = repo / "merged.md"
            merged.write_text("No findings.\n<verdict>SHIP</verdict>\n", encoding="utf-8")
            code, out, err = _run_cli("command", "impl-review-fanout-finalize", TASK_ID,
                                      "--base", base, "--rid", result["rid"],
                                      "--merged-file", str(merged), "--receipt", str(receipt),
                                      "--json")
            self.assertEqual(code, 0, err)
            published = json.loads(receipt.read_text())
            self.assertEqual((published["mode"], published["label"], published["model"],
                              published["spec"]),
                             ("command", "fake", "gemini-9-pro", "command:fake"))

    def test_draw_with_unknown_label_fails_before_dispatch(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [SHIP])
            code, out, _ = _run_cli("command", "impl-review-fanout", TASK_ID, "--base", base,
                                    "--spec", "command:fake", "--draw", "correctness",
                                    "--draw", "contracts=command:nope", "--json")
            self.assertEqual(code, 2)
            self.assertIn("FLOW_REVIEW_COMMAND_NOPE", json.loads(out)["error"])
            self.assertEqual(env.requests(), [])
            self.assertEqual(env.rounds(), 0)


class CommandSessionPass(CommandTest):
    def test_validate_continues_the_session_and_never_restarts(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [NEEDS_WORK])
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            findings = repo / "findings.jsonl"
            findings.write_text(json.dumps({"id": "f1", "title": "off by one"}) + "\n",
                                encoding="utf-8")
            env.set_plan([{"response": {"exitCode": 2, "resumeFailed": True,
                                        "stderr": "session gone"}}])
            code, out, err = _run_cli("command", "validate", "--findings-file", str(findings),
                                      "--receipt", str(receipt), "--spec", "command:fake",
                                      "--json")
            self.assertNotEqual(code, 0)
            last = env.requests()[-1]["request"]
            self.assertEqual((last["sessionId"], last["resumeOnly"]), ("cmd-1", True))
            self.assertEqual(len(env.requests()), 2)

    def test_validate_without_spec_continues_the_receipt_label(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [NEEDS_WORK], extra_labels=("other",),
                              backend="command:other")
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            findings = repo / "findings.jsonl"
            findings.write_text(json.dumps({"id": "f1", "title": "off by one"}) + "\n",
                                encoding="utf-8")
            env.set_plan([{"response": {"output": "Validated.", "sessionId": "ECHO"}}])
            _run_cli("command", "validate", "--findings-file", str(findings),
                     "--receipt", str(receipt), "--json")
            self.assertEqual(len(env.requests()), 2)
            self.assertEqual(env.requests()[-1]["request"]["sessionId"], "cmd-1")


    def test_explicit_spec_cannot_move_the_session_to_another_label(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [NEEDS_WORK], extra_labels=("other",))
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            findings = repo / "findings.jsonl"
            findings.write_text(json.dumps({"id": "f1", "title": "off by one"}) + "\n",
                                encoding="utf-8")
            for sub, extra in (("validate", ("--findings-file", str(findings))),
                               ("deep-pass", ("--pass", "adversarial"))):
                with self.subTest(sub=sub):
                    code, out, _ = _run_cli("command", sub, *extra, "--receipt", str(receipt),
                                            "--spec", "command:other", "--json")
                    self.assertEqual(code, 2)
                    self.assertIn("own label", json.loads(out)["error"])
            self.assertEqual(len(env.requests()), 1)


class CommandReviewFixes(CommandTest):
    def test_fresh_retry_never_inherits_the_failed_calls_model(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [
                NEEDS_WORK,
                {"response": {"exitCode": 2, "resumeFailed": True, "observedModel": "old-model"}},
                {"response": {"output": "<verdict>SHIP</verdict>", "sessionId": "cmd-2"}},
            ])
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            _commit_change(repo, "def a(x):\n    return x + 2\n", "fix")
            code, _, err = impl_review(base, receipt, "--spec", "command:fake")
            self.assertEqual(code, 0, err)
            self.assertEqual(len(env.requests()), 3)
            self.assertEqual(json.loads(receipt.read_text())["model"], "not reported")

    def test_another_label_never_receives_the_previous_session(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [NEEDS_WORK, SHIP], extra_labels=("other",))
            receipt = repo / "r.json"
            self.assertEqual(impl_review(base, receipt, "--spec", "command:fake")[0], 0)
            _commit_change(repo, "def a(x):\n    return x + 2\n", "fix")
            code, _, err = impl_review(base, receipt, "--spec", "command:other")
            self.assertEqual(code, 0, err)
            second = env.requests()[1]["request"]
            self.assertIsNone(second["sessionId"])
            self.assertIn("off by one", second["prompt"])
            self.assertEqual(json.loads(receipt.read_text())["label"], "other")

    def test_managed_only_completion_is_not_offered(self):
        with _flow_repo() as (repo, _base):
            env = CommandRepo(repo, [SHIP])
            code, out, _ = _run_cli("command", "completion-review", "--help")
            self.assertEqual(code, 0)
            self.assertNotIn("--require-managed-execution", out)
            code, _, err = _run_cli("command", "completion-review", EPIC_ID, "--spec",
                                    "command:fake", "--require-managed-execution", "--json")
            self.assertEqual(code, 2)
            self.assertIn("--require-managed-execution", err)
            self.assertEqual(env.requests(), [])

    def test_managed_provider_token_does_not_reach_the_wrapper(self):
        with _flow_repo() as (repo, base), mock.patch.dict(
                os.environ, {"FLOW_REVIEW_EXECUTION_TOKEN": "scoped-secret"}):
            env = CommandRepo(repo, [SHIP])
            self.assertEqual(impl_review(base, repo / "r.json", "--spec", "command:fake")[0], 0)
            self.assertFalse(env.requests()[0]["token"])

    def test_oversized_output_is_a_transport_failure(self):
        with _flow_repo() as (repo, base):
            env = CommandRepo(repo, [{"flood": flowctl.REVIEW_EXECUTION_RESPONSE_MAX + 10}])
            receipt = repo / "r.json"
            code, out, err = impl_review(base, receipt, "--spec", "command:fake")
            self.assertNotEqual(code, 0)
            self.assertIn("exceeds 16 MiB", out + err)
            self.assertFalse(receipt.exists())
            self.assertEqual(env.rounds(), 0)

    def test_response_flushed_before_a_lingering_helper_is_kept(self):
        with _flow_repo() as (repo, base), \
                mock.patch.object(flowctl, "COMMAND_PIPE_GRACE", 0.5):
            CommandRepo(repo, [dict(SHIP, linger=4)])
            code, out, err = impl_review(base, repo / "r.json", "--spec", "command:fake")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["verdict"], "SHIP")

    def test_command_draw_rows_name_their_label(self):
        with _flow_repo() as (repo, base):
            CommandRepo(repo, [SHIP], extra_labels=("other",))
            receipt = repo / "fanout.json"
            code, out, err = _run_cli("command", "impl-review-fanout", TASK_ID, "--base", base,
                                      "--receipt", str(receipt), "--spec", "command:fake",
                                      "--draw", "correctness", "--draw",
                                      "contracts=command:other", "--json")
            self.assertEqual(code, 0, err)
            merged = repo / "merged.md"
            merged.write_text("No findings.\n<verdict>SHIP</verdict>\n", encoding="utf-8")
            code, _, err = _run_cli("command", "impl-review-fanout-finalize", TASK_ID,
                                    "--base", base, "--rid", json.loads(out)["rid"],
                                    "--merged-file", str(merged), "--receipt", str(receipt),
                                    "--json")
            self.assertEqual(code, 0, err)
            rows = {row["axis"]: row for row in json.loads(receipt.read_text())["draws"]}
            self.assertEqual((rows["correctness"]["backend"], rows["correctness"]["label"]),
                             ("command", "fake"))
            self.assertEqual(rows["contracts"]["label"], "other")

    def test_session_passes_never_continue_another_labels_draw(self):
        cases = (
            # (primary draw's step, the session the receipt and the passes may use)
            (dict(SHIP, response=dict(SHIP["response"], sessionId="fake-1")), "fake-1"),
            ({"raw": "", "exit": 3, "stderr": "quota exceeded\n"}, None),
        )
        for primary_step, expected in cases:
            with self.subTest(expected=expected), _flow_repo() as (repo, base):
                env = CommandRepo(repo, [primary_step])
                other_plan = repo / "plan-other.json"
                other_plan.write_text(json.dumps(
                    [dict(SHIP, response=dict(SHIP["response"], sessionId="other-1"))]),
                    encoding="utf-8")
                os.environ[command_var("other")] = json.dumps(
                    [env.argv[0], env.argv[1], str(other_plan), str(env.log)])
                receipt = repo / "fanout.json"
                code, out, err = _run_cli("command", "impl-review-fanout", TASK_ID, "--base",
                                          base, "--receipt", str(receipt), "--spec",
                                          "command:fake", "--draw", "correctness", "--draw",
                                          "contracts=command:other", "--json")
                self.assertEqual(code, 0, out + err)
                merged = repo / "merged.md"
                merged.write_text("No findings.\n<verdict>SHIP</verdict>\n", encoding="utf-8")
                code, out, err = _run_cli("command", "impl-review-fanout-finalize", TASK_ID,
                                          "--base", base, "--rid", json.loads(out)["rid"],
                                          "--merged-file", str(merged), "--receipt",
                                          str(receipt), "--json")
                self.assertEqual(code, 0, out + err)
                published = json.loads(receipt.read_text())
                self.assertEqual(published["spec"], "command:fake")
                self.assertEqual(published["session_id"] or None, expected)
                calls_before = len(env.requests())
                findings = repo / "findings.jsonl"
                findings.write_text(json.dumps({"id": "f1", "title": "x"}) + "\n",
                                    encoding="utf-8")
                env.set_plan([{"response": {"output": "Validated.", "sessionId": "ECHO"}}])
                for sub, extra in (("validate", ("--findings-file", str(findings))),
                                   ("deep-pass", ("--pass", "adversarial"))):
                    code, out, err = _run_cli("command", sub, *extra, "--receipt", str(receipt),
                                              "--json")
                    # With no session on the primary's label, the passes do not run
                    # (they only continue a session, never start one).
                    self.assertEqual(code == 0, expected is not None, out + err)
                continued = [call["request"]["sessionId"]
                             for call in env.requests()[calls_before:]]
                self.assertNotIn("other-1", continued)
                self.assertEqual(continued, [expected] * 2 if expected else [])


if __name__ == "__main__":
    unittest.main()

"""`flow --auto` behaviour and contract checks (R13).

The unattended driver lives in `skills/flow-next-flow/auto.md`, read only when
flow's mode detection parsed the exact `--auto` token; `--tick` runs one hop.
Covered here: the verdict grammar line, reference mentions that
resolve, and executable runs of the argument-parse, hard-guard, snapshot and
make-pr verify fences. No sentence pins, no size or hash baselines.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_flow_auto -q
"""

from __future__ import annotations

import os
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent

FLOW_DIR = PLUGIN / "skills" / "flow-next-flow"
AUTO_MD = FLOW_DIR / "auto.md"
FLOW_REFERENCES = FLOW_DIR / "references"

VERDICT_GRAMMAR_LINE = (
    "PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> "
    'spec=<id> stage=<stage> reason="<one line>"'
)

LOCAL_REF_MENTION_RE = re.compile(r"references/([A-Za-z0-9_.-]+\.md)")
PARSED_VARS = (
    "PILOT_SPEC",
    "AUTO_TICK",
    "PILOT_BACKLOG_OVERRIDE",
    "PILOT_DRY_RUN",
    "PILOT_REVIEW",
    "PILOT_DEPTH",
    "PILOT_GOAL_MODE",
    "PILOT_GOAL",
    "PILOT_FROM_ISSUE",
)

_POSIX_BASH = unittest.skipIf(
    sys.platform == "win32" or shutil.which("bash") is None,
    "executable fence tests need a POSIX bash",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fence_from(text: str, first_line: str) -> str:
    """The bash fence body starting at `first_line` up to its closing ```."""
    start = text.index(first_line)
    end = text.index("```", start)
    return text[start:end]


class VerdictGrammar(unittest.TestCase):
    """(1) One terminal line, grammar unchanged from pilot, in both shapes."""

    def test_grammar_line(self) -> None:
        text = _read(AUTO_MD)
        self.assertIn(VERDICT_GRAMMAR_LINE, text)

    def test_goal_mode_grammar_adds_goal_met(self) -> None:
        self.assertIn(
            "PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN|GOAL_MET> "
            'spec=<id> stage=<stage> reason="goal <goal-id>; <one line>"',
            _read(FLOW_REFERENCES / "goal-mode.md"),
        )

    def test_issue_start_refusal_ends_asked(self) -> None:
        # A --from-issue run that asked on the issue ends ASKED with stage capture.
        self.assertIn("PILOT_VERDICT=ASKED spec=<identifier> stage=capture",
                      _read(FLOW_REFERENCES / "issue-start.md"))

    def test_already_merged_closed_spec_names_no_work(self) -> None:
        # A driver keyed on NO_WORK must stop on an already-merged scoped spec.
        self.assertIn("PILOT_VERDICT=NO_WORK", _read(AUTO_MD))


class ReferenceMentions(unittest.TestCase):

    def test_every_reference_mention_resolves(self) -> None:
        for name in sorted(set(LOCAL_REF_MENTION_RE.findall(_read(AUTO_MD)))):
            with self.subTest(reference=name):
                self.assertTrue((FLOW_REFERENCES / name).is_file(), f"auto.md names references/{name}, missing")

class HardGuardFence(unittest.TestCase):
    """The hard-guard and snapshot fences, run for real."""

    def _hard_guard_fence(self) -> str:
        return _fence_from(_read(AUTO_MD), '# fence:pilot-guards')

    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_snapshot_guard_consumer_stops_before_dispatch(self) -> None:
        for dirty, rc, expected in (
            ([' M code.py'], 0, 'dirty working tree at tick start'),
            ([], 0, 'PASSED'),
        ):
            result = subprocess.run(['bash', '-c', self._hard_guard_fence() + '\nprintf PASSED'],
                                    env={**os.environ, 'PILOT_SNAPSHOT': json.dumps({'guards': {'dirty': dirty}})},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, rc)
            self.assertIn(expected, result.stdout)
            if dirty:
                self.assertNotIn('PASSED', result.stdout)


    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_guard_stop_carries_the_goal_prefix_only_in_goal_mode(self) -> None:
        snapshot = json.dumps({'guards': {'dirty': [' M code.py']}})
        for prefix, expected in (
            ('goal fn-40; ', 'spec=fn-40 stage=- reason="goal fn-40; dirty working tree at tick start"'),
            (None, 'spec=- stage=- reason="dirty working tree at tick start"'),
        ):
            env = {**os.environ, 'PILOT_SNAPSHOT': snapshot}
            env.pop('GOAL_REASON_PREFIX', None)
            env.pop('GOAL_SPEC', None)
            if prefix is not None:
                env['GOAL_REASON_PREFIX'] = prefix
                env['GOAL_SPEC'] = 'fn-40'
            result = subprocess.run(['bash', '-c', self._hard_guard_fence()], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout.splitlines()[-1])

    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_snapshot_fences_fail_closed_in_a_fresh_shell(self) -> None:
        # Shell variables do not survive between tool calls: a fence run in a
        # fresh shell reads the snapshot file and stops when it is absent.
        env = {k: v for k, v in os.environ.items() if k != "PILOT_SNAPSHOT"}
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            script = self._hard_guard_fence() + "\nprintf PASSED"
            missing = subprocess.run(["bash", "-c", script], cwd=tmp, env=env,
                                     capture_output=True, text=True)
            self.assertEqual(missing.returncode, 1)
            self.assertIn("pilot snapshot missing or unreadable", missing.stdout)
            self.assertNotIn("PASSED", missing.stdout)
            snap = Path(tmp) / ".flow" / "tmp" / "pilot-snapshot.json"
            snap.parent.mkdir(parents=True)
            snap.write_text(json.dumps({"guards": {"dirty": []}}))
            present = subprocess.run(["bash", "-c", script], cwd=tmp, env=env,
                                     capture_output=True, text=True)
            self.assertEqual(present.returncode, 0, present.stderr)
            self.assertIn("PASSED", present.stdout)


    @_POSIX_BASH
    @unittest.skipUnless(shutil.which("jq"), "requires jq")
    def test_snapshot_write_failure_stops(self) -> None:
        fence = _fence_from(_read(AUTO_MD), "SNAPSHOT_ARGS=()")
        env = {k: v for k, v in os.environ.items() if k != "PILOT_SNAPSHOT"}
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            (Path(tmp) / ".flow").mkdir()
            (Path(tmp) / ".flow" / "tmp").write_text("not a directory")
            stub = Path(tmp) / "flowctl-stub"
            stub.write_text('#!/usr/bin/env bash\nprintf \'{"guards":{}}\'\n')
            stub.chmod(0o755)
            result = subprocess.run(["bash", "-c", fence + "\nprintf PASSED"], cwd=tmp,
                                    env={**env, "FLOWCTL": str(stub), "PILOT_SPEC": ""},
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("NEEDS_HUMAN", result.stdout)
        self.assertNotIn("PASSED", result.stdout)


class ArgumentParseFence(unittest.TestCase):
    """(8) The argument-parse fence, run for real."""

    def _fence(self) -> str:
        return _fence_from(_read(AUTO_MD), 'RAW_ARGS="$ARGUMENTS"')

    def _parse(self, arguments: str) -> tuple[dict[str, str], str]:
        script = self._fence() + "\n" + "\n".join(f'printf "%s=%s\\n" {v} "${v}"' for v in PARSED_VARS)
        res = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            env={**os.environ, "ARGUMENTS": arguments},
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        parsed = dict(line.split("=", 1) for line in res.stdout.splitlines() if "=" in line)
        return parsed, res.stderr

    DEFAULTS = {
        "PILOT_SPEC": "",
        "AUTO_TICK": "0",
        "PILOT_BACKLOG_OVERRIDE": "",
        "PILOT_DRY_RUN": "0",
        "PILOT_REVIEW": "",
        "PILOT_DEPTH": "short",
        "PILOT_GOAL_MODE": "0",
        "PILOT_GOAL": "",
        "PILOT_FROM_ISSUE": "",
    }

    @_POSIX_BASH
    def test_fence_exports_every_parsed_variable(self) -> None:
        # Dispatched stages read these from the environment: run the fence and
        # check a child process sees every parsed variable.
        res = subprocess.run(
            ["bash", "-c", self._fence() + "\nenv"],
            capture_output=True,
            text=True,
            env={**os.environ, "ARGUMENTS": "fn-1 --tick"},
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        exported = {line.split("=", 1)[0] for line in res.stdout.splitlines() if "=" in line}
        for var in PARSED_VARS:
            with self.subTest(var=var):
                self.assertIn(var, exported)

    @_POSIX_BASH
    def test_argument_shapes(self) -> None:
        # arguments -> the values that differ from DEFAULTS
        cases = (
            (
                "fn-12 --tick --backlog --explain --review=codex --depth=long",
                {
                    "PILOT_SPEC": "fn-12",
                    "AUTO_TICK": "1",
                    "PILOT_BACKLOG_OVERRIDE": "1",
                    "PILOT_DRY_RUN": "1",
                    "PILOT_REVIEW": "codex",
                    "PILOT_DEPTH": "long",
                },
            ),
            ("wor-17-x", {"PILOT_SPEC": "wor-17-x"}),
            ("--auto fn-4 --tick", {"PILOT_SPEC": "fn-4", "AUTO_TICK": "1"}),
            ("--review codex --depth long", {"PILOT_REVIEW": "codex", "PILOT_DEPTH": "long"}),
            ("", {}),
            ("--goal fn-40 --until=merge", {"PILOT_GOAL_MODE": "1", "PILOT_GOAL": "fn-40"}),
            ("--goal docs/linux port.md --tick", {"PILOT_GOAL_MODE": "1", "PILOT_GOAL": "docs/linux port.md", "AUTO_TICK": "1"}),
            ("fn-40 --goal --review=codex", {"PILOT_GOAL_MODE": "1", "PILOT_GOAL": "fn-40", "PILOT_REVIEW": "codex"}),
            ("--from-issue SCF-12 --until=merge", {"PILOT_FROM_ISSUE": "SCF-12"}),
            ("--from-issue=https://linear.app/x/issue/SCF-12 --tick",
             {"PILOT_FROM_ISSUE": "https://linear.app/x/issue/SCF-12", "AUTO_TICK": "1"}),
        )
        for arguments, overrides in cases:
            with self.subTest(arguments=arguments):
                parsed, _ = self._parse(arguments)
                self.assertEqual(parsed, {**self.DEFAULTS, **overrides})

    @_POSIX_BASH
    def test_retired_flags_warn_and_change_nothing(self) -> None:
        # --research chose a research backend that no longer exists and --dry-run was
        # --explain's alias: both are unknown flags now.
        cases = (
            ("fn-9 --research=grep", "--research=grep", {"PILOT_SPEC": "fn-9"}),
            ("fn-9 --dry-run", "--dry-run", {"PILOT_SPEC": "fn-9"}),
            ("--research grep fn-9", "--research", {"PILOT_SPEC": "fn-9"}),
            ("--goal fn-9 --research grep", "--research", {"PILOT_GOAL_MODE": "1", "PILOT_GOAL": "fn-9"}),
        )
        for arguments, flag, overrides in cases:
            with self.subTest(arguments=arguments):
                parsed, stderr = self._parse(arguments)
                self.assertEqual(parsed, {**self.DEFAULTS, **overrides})
                self.assertIn(f"Unknown flag: {flag}", stderr)

    @_POSIX_BASH
    def test_lookalike_flags_do_not_set_the_flags(self) -> None:
        # Exact tokens only: a prefix or suffix lookalike is an unknown flag,
        # warned to stderr and ignored.
        for arguments in ("--ticket", "--auto-x", "--explainer", "--backlogs", "--spec", "--goals"):
            with self.subTest(arguments=arguments):
                parsed, stderr = self._parse(arguments)
                self.assertEqual(parsed, self.DEFAULTS)
                self.assertIn(arguments, stderr)

    @_POSIX_BASH
    def test_backlog_does_not_apply_with_goal(self) -> None:
        parsed, stderr = self._parse("--goal fn-40 --backlog")
        self.assertEqual(parsed["PILOT_BACKLOG_OVERRIDE"], "")
        self.assertEqual(parsed["PILOT_GOAL"], "fn-40")
        self.assertIn("--backlog", stderr)

    @_POSIX_BASH
    def test_from_issue_without_an_issue_or_beside_another_start_stops(self) -> None:
        # An empty --from-issue must never fall back to unscoped selection.
        cases = (
            ("--from-issue", "--from-issue needs an issue key or URL"),
            ("--from-issue= --until=merge", "--from-issue needs an issue key or URL"),
            ("fn-1 --from-issue SCF-12", "--from-issue takes no other starting point"),
            ("--goal fn-40 --from-issue SCF-12", "--from-issue takes no other starting point"),
            ("--from-issue SCF-12 --backlog", "--from-issue takes no other starting point"),
        )
        for arguments, reason in cases:
            with self.subTest(arguments=arguments):
                res = subprocess.run(["bash", "-c", self._fence()], capture_output=True, text=True,
                                     env={**os.environ, "ARGUMENTS": arguments})
                self.assertEqual(res.returncode, 1, res.stderr)
                self.assertIn(f'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="{reason}"', res.stdout)

    @_POSIX_BASH
    def test_second_positional_id_does_not_double_assign(self) -> None:
        parsed, stderr = self._parse("fn-9 fn-10")
        self.assertEqual(parsed["PILOT_SPEC"], "fn-9")
        self.assertIn("fn-10", stderr)

    @_POSIX_BASH
    def test_dangling_value_flag_warns(self) -> None:
        parsed, stderr = self._parse("fn-2 --review")
        self.assertEqual(parsed["PILOT_REVIEW"], "")
        self.assertIn("--review", stderr)


class MakePrVerifyProbe(unittest.TestCase):
    @unittest.skipIf(shutil.which("jq") is None, "verify fence needs jq")
    @_POSIX_BASH
    def test_make_pr_verify_probe_parse_failure_is_flagged(self) -> None:
        # A malformed body must set PR_VERIFY_FAILED=1 (jq is the
        # status-bearing command); a valid body yields the first OPEN url; no
        # OPEN row yields "" with the flag still 0.
        cases = {
            '[{"state":"CLOSED","url":"c"},{"state":"OPEN","url":"https://x/1"}]': ("https://x/1", "0"),
            '[{"state":"CLOSED","url":"c"}]': ("", "0"),
            '{not json': ("", "1"),
        }
        line = next(l for l in _read(AUTO_MD).splitlines() if l.startswith("OPEN_PR_URL=$(printf"))
        for body, (url, failed) in cases.items():
            with self.subTest(body=body):
                script = f"PR_VERIFY_FAILED=0\nPR_VERIFY_JSON={body!r}\n{line}\nprintf '%s|%s' \"$OPEN_PR_URL\" \"$PR_VERIFY_FAILED\""
                out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
                self.assertEqual(out, f"{url}|{failed}")

    @_POSIX_BASH
    def test_make_pr_verify_probe_flags_a_gh_failure(self) -> None:
        # A failing gh must set PR_VERIFY_FAILED=1 rather than yield an empty
        # URL that reads as a healthy no-advance strike.
        text = _read(AUTO_MD)
        fence = _fence_from(text, "PR_VERIFY_FAILED=0\n")
        with tempfile.TemporaryDirectory() as tmp:
            gh = Path(tmp) / "gh"
            gh.write_text("#!/bin/sh\nexit 1\n")
            gh.chmod(0o755)
            env = {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ['PATH']}", "BRANCH_NAME": "b"}
            out = subprocess.run(["bash", "-c", fence + 'printf "%s" "$PR_VERIFY_FAILED"'],
                                 capture_output=True, text=True, env=env, check=True).stdout
        self.assertEqual(out, "1")

    @unittest.skipIf(shutil.which("jq") is None, "verify fence needs jq")
    @_POSIX_BASH
    def test_make_pr_verify_off_github_reads_the_snapshot(self) -> None:
        # Off GitHub the verify takes its own fresh snapshot in a fresh shell, never
        # a stale persisted one: a failed snapshot or probe, a missing row or a
        # malformed body is a failure, never a healthy no-advance.
        stale = '{"selected":{"pr":{"probe_failed":false,"open":null}}}'
        cases = {
            ('{"selected":{"pr":{"probe_failed":false,"open":{"url":"https://gl/-/merge_requests/4"}}}}', 0):
                ("https://gl/-/merge_requests/4", "0"),
            ('{"selected":{"pr":{"probe_failed":false,"open":null}}}', 0): ("", "0"),
            ('{"selected":{"pr":{"probe_failed":true,"open":null}}}', 0): ("", "1"),
            ('{"selected":null}', 0): ("", "1"),
            ('{not json', 0): ("", "1"),
            ('', 1): ("", "1"),
        }
        text = _read(AUTO_MD)
        fence = _fence_from(text[text.index("On a forge other than GitHub (the snapshot's `forge`"):],
                            "PR_VERIFY_FAILED=0\n")
        env = {k: v for k, v in os.environ.items() if k != "PILOT_SNAPSHOT"}
        for (body, rc), (url, failed) in cases.items():
            with self.subTest(body=body, rc=rc), tempfile.TemporaryDirectory() as tmp:
                subprocess.run(["git", "init", "-q", tmp], check=True)
                snap = Path(tmp) / ".flow" / "tmp" / "pilot-snapshot.json"
                snap.parent.mkdir(parents=True)
                snap.write_text(stale)
                flowctl = Path(tmp) / "flowctl"
                flowctl.write_text(f"#!/usr/bin/env bash\nprintf '%s' {shlex.quote(body)}\nexit {rc}\n")
                flowctl.chmod(0o755)
                out = subprocess.run(["bash", "-c", fence + "printf '%s|%s' \"$OPEN_PR_URL\" \"$PR_VERIFY_FAILED\""],
                                     cwd=tmp, env={**env, "FLOWCTL": str(flowctl), "SELECTED_SPEC": "fn-1"},
                                     capture_output=True, text=True, check=True).stdout
                self.assertEqual(out, f"{url}|{failed}")
                if rc == 0:
                    self.assertEqual(snap.read_text(), body)


def _flat(text: str) -> str:
    return " ".join(text.split())


class IssueStartContract(unittest.TestCase):
    """--from-issue rules that live in prose (fn-326 R1, R4, R5)."""

    def test_interrupted_capture_is_finished_before_work(self) -> None:
        text = _flat(_read(FLOW_REFERENCES / "issue-start.md"))
        for token in ("`git log -1 -- .flow/specs/<spec-id>.md`", "interrupted", "design review"):
            self.assertIn(token, text)

    def test_jira_url_from_another_site_stops_before_writes(self) -> None:
        text = _flat(_read(FLOW_REFERENCES / "issue-start.md"))
        for token in ("Jira URL", "`tracker.perTracker.baseUrl`"):
            self.assertIn(token, text)

    def test_every_work_hop_runs_implementation_review(self) -> None:
        self.assertIn("risk rule", _flat(_read(FLOW_REFERENCES / "issue-start.md")))
        # The literal context work receives under --from-issue.
        self.assertIn("`issue start: run implementation review on every task; the risk rule does not skip it`",
                      _read(AUTO_MD))


class IssueStartFinalAuditContract(unittest.TestCase):
    """fn-327 R2-R4: tokens the issue-start, capture and working-rules contracts carry."""

    def test_a_remote_only_link_fast_forwards_the_local_branch(self) -> None:
        text = _flat(_read(FLOW_REFERENCES / "issue-start.md"))
        for token in ("`git merge --ff-only origin/<name>`", "`tracker.id`"):
            self.assertIn(token, text)

    def test_every_task_review_lives_in_the_spec_and_the_working_rules(self) -> None:
        self.assertIn("Every task gets implementation review",
                      _read(PLUGIN / "skills/flow-next-capture/references/from-issue.md"))
        self.assertIn("every task gets implementation review", _flat(_read(PLUGIN / "references/working-rules.md")))

    def test_question_slug_carries_the_issue_body_digest(self) -> None:
        text = _flat(_read(FLOW_REFERENCES / "issue-start.md"))
        for token in ("SHA-256", "issue body", "--question-slug"):
            self.assertIn(token, text)


@unittest.skipUnless(shutil.which("git"), "requires git")
class IssueStartLinkedSpecAcrossRefs(unittest.TestCase):
    """R2: a link only a remote branch's JSON carries is found before capture."""

    def _git(self, repo: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@example.com", "-c", "user.name=t",
                        "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)

    def test_json_only_link_on_a_remote_branch_is_found(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from flowctl_test_support import FLOWCTL_CMD  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            origin, author, runner = Path(tmp) / "origin.git", Path(tmp) / "author", Path(tmp) / "runner"
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
            subprocess.run(["git", "clone", "-q", str(origin), str(author)], check=True, capture_output=True)
            specs = author / ".flow" / "specs"
            specs.mkdir(parents=True)
            (specs / "fn-1-login.md").write_text("# Login\n", encoding="utf-8")
            sidecar = {"id": "fn-1-login", "title": "Login", "status": "open"}
            (specs / "fn-1-login.json").write_text(json.dumps(sidecar), encoding="utf-8")
            self._git(author, "add", "-A")
            self._git(author, "commit", "-q", "-m", "spec on main")
            self._git(author, "push", "-q", "origin", "HEAD:main")
            subprocess.run(["git", "clone", "-q", str(origin), str(runner)], check=True, capture_output=True)
            # The link lands on a branch by a JSON-only change; the body stays as on main.
            self._git(author, "switch", "-q", "-c", "fn-1-login")
            linked = {**sidecar, "tracker": {"id": "issue-uuid-7", "identifier": "SCF-7"}}
            (specs / "fn-1-login.json").write_text(json.dumps(linked), encoding="utf-8")
            self._git(author, "commit", "-q", "-am", "link")
            self._git(author, "push", "-q", "origin", "fn-1-login")

            result = subprocess.run([*FLOWCTL_CMD, "specs", "--refs", "--fetch", "--tracker-id", "issue-uuid-7",
                                     "--json"], cwd=runner, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            found = json.loads(result.stdout)
            self.assertIsNone(found["fetch_error"])
            self.assertEqual(found["linked"], [
                {"id": "fn-1-login", "checkout": False, "refs": ["refs/remotes/origin/fn-1-login"]},
            ])

    def test_an_unreadable_spec_json_stops_the_lookup(self) -> None:
        # A partial clone can lack a ref's spec JSON blob; that is never "no link".
        sys.path.insert(0, str(PLUGIN / "scripts"))
        import flowctl  # noqa: PLC0415
        from unittest import mock  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            specs = repo / ".flow" / "specs"
            specs.mkdir(parents=True)
            (specs / "fn-1-login.md").write_text("# Login\n", encoding="utf-8")
            (specs / "fn-1-login.json").write_text(json.dumps({"id": "fn-1-login"}), encoding="utf-8")
            self._git(repo, "add", "-A")
            self._git(repo, "commit", "-q", "-m", "spec")
            (specs / "fn-1-login.json").unlink()  # only the committed copy remains
            for blobs in ({}, None):
                with self.subTest(blobs="missing" if blobs == {} else "unparseable"):
                    read = (lambda _root, _oids: {}) if blobs == {} else (
                        lambda _root, oids: {oid: b"{not json" for oid in oids})
                    with mock.patch.object(flowctl, "_spec_ref_blobs", read):
                        with self.assertRaises(flowctl.SpecRefIndexError):
                            flowctl.find_linked_specs(repo, "issue-uuid-7", fetch=False)
            # A tree-filtered partial clone can lack a ref's tree, or the ref listing can fail.
            real = flowctl._spec_ref_git
            for verb in ("ls-tree", "for-each-ref"):
                def failing(root, *args, _verb=verb, **kwargs):
                    if args and args[0] == _verb:
                        return subprocess.CompletedProcess(args, 128, "", "fatal: missing tree")
                    return real(root, *args, **kwargs)
                with self.subTest(unreadable=verb), mock.patch.object(flowctl, "_spec_ref_git", failing):
                    with self.assertRaises(flowctl.SpecRefIndexError):
                        flowctl.find_linked_specs(repo, "issue-uuid-7", fetch=False)


class IssueStartQuestionRounds(unittest.TestCase):
    """R3: refusal, plain reply, re-promotion, follow-up posts once."""

    def test_plain_reply_settles_the_round_and_a_rerun_dedupes(self) -> None:
        sys.path.insert(0, str(PLUGIN / "scripts"))
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from flowctl_tracker import wire  # noqa: PLC0415
        from test_tracker_wire import LN_ISSUE, LN_UUID, fake_execute, gql_issue, ln_cfg, loc, ok  # noqa: PLC0415

        def comment(number: int, body: str, at: str) -> dict:
            return {"id": str(number), "body": body, "createdAt": at, "url": f"https://linear.test/c/{number}"}

        def ask(comments: list, *, reply_settles: bool = True):
            added = comment(99, "posted", "2026-11-15T12:00:00Z")
            ex = fake_execute({
                "wire-comment-list": ok({"data": {"issue": {"id": LN_UUID, "comments": {
                    "nodes": comments, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}),
                "wire-parent-read": gql_issue(LN_ISSUE),
                "wire-comment-add": ok({"data": {"commentCreate": {
                    "success": True, "comment": {**added, "issue": {"id": LN_UUID}}}}}),
            })
            with tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                flow.mkdir()
                out = wire.dispatch(
                    "question", ln_cfg(), locator=loc(LN_UUID, "WOR-17"), subject_id=LN_UUID,
                    blocked_stage="capture", reason_code="not-buildable", question_slug="login-scope",
                    reply_settles=reply_settles, body="Which login?", flow_dir=flow, execute=ex)
            self.assertIsInstance(out, dict, out)
            posts = sum(call.op == "wire-comment-add" for call in ex.calls)
            self.assertEqual(posts, 1 if out["posted"] else 0)
            return out

        first = ask([])
        self.assertTrue(first["posted"])
        marker = f"<!-- flow-next:question id={first['question_id']} status=open -->\n\nWhich login?"
        refused = comment(1, marker, "2026-11-15T08:00:00Z")
        reply = comment(2, "Email login only.", "2026-11-15T09:00:00Z")

        follow_up = ask([refused, reply])
        self.assertTrue(follow_up["posted"])
        self.assertTrue(follow_up["reopened"])
        # Without the flag the answer-marker protocol (backlog mode) still dedupes.
        self.assertFalse(ask([refused, reply], reply_settles=False)["posted"])
        # A rerun of the follow-up round, nobody having replied, posts nothing.
        rerun = ask([refused, reply, comment(3, marker, "2026-11-15T10:00:00Z")])
        self.assertFalse(rerun["posted"])


@_POSIX_BASH
@unittest.skipUnless(shutil.which("git"), "requires git")
class PostMergeCheckout(unittest.TestCase):
    """R11: after land merged and deleted the spec branch, the next run starts on the default branch."""

    FENCE = "# fence:post-merge-checkout"

    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@example.com", "-c", "user.name=t",
                               "-c", "commit.gpgsign=false", *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def _merged_checkout(self, tmp: Path) -> Path:
        """The state a run leaves: on the squash-merged, remote-deleted branch, make-pr's sync write uncommitted."""
        origin, co, merger = tmp / "origin.git", tmp / "co", tmp / "merger"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(origin), str(co)], check=True, capture_output=True)
        (co / ".flow" / "specs").mkdir(parents=True)
        (co / ".flow" / ".gitignore").write_text("tmp/\n", encoding="utf-8")
        (co / "a.txt").write_text("base\n", encoding="utf-8")
        self._git(co, "add", "-A")
        self._git(co, "commit", "-q", "-m", "base")
        self._git(co, "push", "-q", "origin", "main")
        self._git(co, "remote", "set-head", "origin", "main")
        self._git(co, "switch", "-q", "-c", "fn-1-add")
        sidecar = co / ".flow" / "specs" / "fn-1-add.json"
        sidecar.write_text('{"tracker": {"lastSyncedAt": "capture"}}\n', encoding="utf-8")
        (co / "a.txt").write_text("base\nadd\n", encoding="utf-8")
        self._git(co, "add", "-A")
        self._git(co, "commit", "-q", "-m", "fn-1-add")
        self._git(co, "push", "-q", "-u", "origin", "fn-1-add")
        sidecar.write_text('{"tracker": {"lastSyncedAt": "make-pr"}}\n', encoding="utf-8")
        subprocess.run(["git", "clone", "-q", str(origin), str(merger)], check=True, capture_output=True)
        self._git(merger, "merge", "-q", "--squash", "origin/fn-1-add")
        self._git(merger, "commit", "-q", "-m", "fn-1-add (#1)")
        self._git(merger, "push", "-q", "origin", "main")
        self.merge_commit = self._git(merger, "rev-parse", "HEAD")
        self._git(merger, "push", "-q", "origin", "--delete", "fn-1-add")
        (co / ".flow" / "tmp").mkdir()
        (co / ".flow" / "tmp" / "pilot-snapshot.json").write_text(
            json.dumps({"selected": {"id": "fn-1-add", "branch_name": "fn-1-add"}}), encoding="utf-8")
        return co

    def _run_fence(self, co: Path, subdir: str = "", merged: bool = True) -> subprocess.CompletedProcess:
        text = _read(AUTO_MD)
        self.assertIn(self.FENCE, text)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
               "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign", "GIT_CONFIG_VALUE_0": "false"}
        env.pop("MERGE_COMMIT", None)
        if merged:  # the merge commit land confirmed this run
            env["MERGE_COMMIT"] = self.merge_commit
        cwd = co / subdir
        cwd.mkdir(parents=True, exist_ok=True)
        return subprocess.run(["bash", "-c", _fence_from(text, self.FENCE)], cwd=cwd, env=env,
                              capture_output=True, text=True)

    def test_returns_to_the_default_branch_keeping_the_sync_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            co = self._merged_checkout(Path(tmp))
            result = self._run_fence(co)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._git(co, "branch", "--show-current"), "main")
            self.assertEqual(self._git(co, "rev-parse", "HEAD"), self._git(co, "rev-parse", "origin/main"))
            self.assertEqual(self._git(co, "status", "--porcelain"), "")
            self.assertIn('"make-pr"', self._git(co, "show", "fn-1-add:.flow/specs/fn-1-add.json"))

    def test_a_hop_without_a_confirmed_merge_leaves_everything(self) -> None:
        # Phase 6 runs after every hop; only a confirmed merge may move the checkout.
        with tempfile.TemporaryDirectory() as tmp:
            co = self._merged_checkout(Path(tmp))
            result = self._run_fence(co, merged=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._git(co, "branch", "--show-current"), "fn-1-add")
            self.assertEqual(self._git(co, "status", "--porcelain"), "M .flow/specs/fn-1-add.json")

    def test_a_run_from_a_subdirectory_still_commits_the_sync_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            co = self._merged_checkout(Path(tmp))
            result = self._run_fence(co, subdir="src")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._git(co, "branch", "--show-current"), "main")
            self.assertIn('"make-pr"', self._git(co, "show", "fn-1-add:.flow/specs/fn-1-add.json"))

    def test_a_local_default_branch_that_cannot_fast_forward_keeps_the_checkout(self) -> None:
        # Work keeps planning commits on local main; after the squash merge that main has diverged.
        with tempfile.TemporaryDirectory() as tmp:
            co = self._merged_checkout(Path(tmp))
            self._git(co, "commit", "-q", "--only", "-m", "sync", "--", ".flow/specs/fn-1-add.json")
            self._git(co, "switch", "-q", "main")
            (co / ".flow" / "specs").mkdir(exist_ok=True)
            (co / ".flow" / "specs" / "fn-2-next.json").write_text("{}\n", encoding="utf-8")
            self._git(co, "add", "-A")
            self._git(co, "commit", "-q", "-m", "plan fn-2-next")
            self._git(co, "switch", "-q", "fn-1-add")
            result = self._run_fence(co)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._git(co, "branch", "--show-current"), "fn-1-add")
            self.assertIn("left on fn-1-add", result.stdout)

    def test_another_change_keeps_the_checkout_where_it_is(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            co = self._merged_checkout(Path(tmp))
            (co / "a.txt").write_text("someone's edit\n", encoding="utf-8")
            result = self._run_fence(co)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._git(co, "branch", "--show-current"), "fn-1-add")
            self.assertEqual((co / "a.txt").read_text(encoding="utf-8"), "someone's edit\n")
            self.assertIn("a.txt", result.stdout)


if __name__ == "__main__":
    unittest.main()

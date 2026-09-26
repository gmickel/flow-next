"""Execute every tracker lifecycle caller gate against an instrumented flowctl."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_COMMIT = "410756ef8f27d14c3cfbcbffe66356c67fd255ad"
ORACLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "tracker_callers"
    / f"oracle-{SOURCE_COMMIT}.json"
)
VALUES = ("off", "pull", "push", "reconcile", "comment")
WORK_EVENTS = {"work.firstClaim", "work.done", "completionReview"}
DIRECT_EVENTS = {"capture", "interview", "plan"}
COMMENT_EVENTS = {"resolvePr", "qa"}
CHART_EVENTS = {"chart"}
FAKE_FLOWCTL = ORACLE_PATH.parent / "fake_flowctl.py"

SKILLS = REPO_ROOT / "plugins" / "flow-next" / "skills"

# The fn-169 branch-disclosure wave split several caller gates: the
# always-loaded spine keeps a probe that prints a STOP sentinel naming a
# reference, and the reference carries the op resolution + facade call. The
# executable contract is unchanged, so the harness executes BOTH halves in one
# shell (variables flow across the split exactly as the host agent's session
# does) and asserts the same observations. `split_gate` names the spine slice;
# `fence` names the file + needles of the dispatch fence the wrapper is
# injected into.
#
# Spine slices are addressed by (start-token, sentinel-substring) so the slice
# is the gate itself, not the neighbouring gates that share the fence.
CURRENT_CALLER_GATES = {
    "capture": {
        "fence": (
            SKILLS / "flow-next-capture/references/tracker-integration.md",
            ("tracker.perEvent.capture", "tracker sync"),
        ),
    },
    "interview": {
        "split_gate": (
            SKILLS / "flow-next-refine/SKILL.md",
            "TRACKER_GATE=0",
            "TRACKER-SYNC GATE ACTIVE",
        ),
        "fence": (
            SKILLS / "flow-next-refine/references/post-write-back.md",
            ("tracker.perEvent.interview", "tracker sync"),
        ),
        "fired": '[ "$TRACKER_GATE" = "1" ]',
        "reference": "references/post-write-back.md",
    },
    "qa": {
        "split_gate": (
            SKILLS / "flow-next-qa/workflow.md",
            "ACTIVE=0",
            "TRACKER QA LEAF ACTIVE",
        ),
        "fence": (
            SKILLS / "flow-next-qa/references/autonomy.md",
            ("QA_OP", "tracker sync"),
        ),
        "fired": '[ "$ACTIVE" = "1" ]',
        "reference": "references/autonomy.md",
    },
    "chart": {
        "split_gate": (
            SKILLS / "flow-next-chart/workflow.md",
            "ACTIVE=0",
            "TRACKER PROJECTION GATE ACTIVE",
        ),
        "fence": (
            SKILLS / "flow-next-chart/references/tracker-projection.md",
            ("tracker sync",),
        ),
        "fired": '[ "$ACTIVE" = "1" ]',
        "reference": "references/tracker-projection.md",
    },
}

# Disclosure sentinels the split gates print. They are branch routing, not
# caller output: stripped from stdout before the byte-exact oracle comparison,
# and only after each stripped line is proven to name the reference that owns
# the rest of the caller gate.
_SENTINEL_RE = re.compile(r"STOP\. Read (references/[^\s]+)")

# `FLOWCTL=...` / `[ -x "$FLOWCTL" ] || FLOWCTL=...` bootstrap lines a reference
# repeats for standalone readability. The spine already resolved the binary, so
# the harness keeps its instrumented one.
_FLOWCTL_BOOTSTRAP = re.compile(
    r'^(?:FLOWCTL="\$\{DROID_PLUGIN_ROOT|\[ -x "\$FLOWCTL" \] \|\| FLOWCTL=)'
)

for _event in WORK_EVENTS:
    CURRENT_CALLER_GATES[_event] = {
        "fence": (SKILLS / "flow-next-work/references/tracker-touchpoints.md",
                  (f'.ops["{_event}"]', "tracker sync")),
    }

# Declared read deltas from the immutable pre-teardown oracle. Snapshot-backed
# callers consume their run preflight rather than repeating config reads. Other
# overrides account for short-circuiting gates and split-reference reads.
_INTERVIEW_LEAF = ["config", "get", "tracker.perEvent.interview", "--json"]
_QA_LEAF = ["config", "get", "tracker.perEvent.qa", "--json"]
_CHARTS_LEAF = ["config", "get", "tracker.charts", "--json"]
_SYNC_ACTIVE = ["sync", "active", "--json"]

CONFIG_READ_OVERRIDES = {
    **{(event, phase): [] for event in WORK_EVENTS for phase in ("active", "inactive")},
    # fn-259: these gates consume the already-captured preflight bundle.
    ("plan", "active"): [],
    ("plan", "inactive"): [],
    ("interview", "inactive"): [],
    # Interview now uses the preflight for its spine gate; the loaded reference
    # retains the operation lookup.
    ("interview", "active"): [_INTERVIEW_LEAF],
    ("interview", "active", "off"): [],
    # QA's spine gate probes only the leaf; the bridge check moved into the
    # reference the sentinel loads, so an `off` leaf never reaches it.
    ("qa", "active", "off"): [_QA_LEAF],
    # Chart's rewritten probe captures both raw payloads before parsing either
    # (fail-open probe shape), which swaps the order of the two reads.
    ("chart", "inactive"): [_SYNC_ACTIVE, _CHARTS_LEAF],
    ("chart", "active"): [_SYNC_ACTIVE, _CHARTS_LEAF],
}


def _bash_fences(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)\n```", text, flags=re.DOTALL)


def _single_fence(path: Path, *needles: str) -> str:
    matches = [
        fence
        for fence in _bash_fences(path.read_text(encoding="utf-8"))
        if all(needle in fence for needle in needles)
    ]
    if len(matches) != 1:
        raise AssertionError(f"{path}: expected one fence for {needles}, got {len(matches)}")
    return matches[0]


def _inject_before_last_fi(source: str, body: str) -> str:
    position = source.rfind("\nfi")
    if position < 0:
        raise AssertionError("caller fence has no terminal fi")
    return source[:position] + "\n" + textwrap.indent(body, "  ") + source[position:]


def _shell_if_block_around(
    path: Path, sentinel: str, start_token: str = "ACTIVE=0"
) -> str:
    """Slice a nested Markdown shell block without crossing its indented fence."""
    lines = path.read_text(encoding="utf-8").splitlines()
    sentinel_index = next(
        index for index, line in enumerate(lines) if sentinel in line
    )
    start = sentinel_index
    while start >= 0 and lines[start].strip() != start_token:
        start -= 1
    if start < 0:
        raise AssertionError(f"{path}: no {start_token} before {sentinel!r}")
    end = sentinel_index
    while end < len(lines) and not lines[end].strip().startswith("fi"):
        end += 1
    if end == len(lines):
        raise AssertionError(f"{path}: no fi after {sentinel!r}")
    return textwrap.dedent("\n".join(lines[start : end + 1]))


class TrackerCallerExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bash = shutil.which("bash")
        if cls.bash is None:
            raise unittest.SkipTest("tracker caller execution requires bash")
        oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        # R8 uses a repository-write-free API touchpoint, not the retired shell
        # facade gate. Its real helper contract lives in test_land_tracker_api.py.
        cls.callers = {row["id"]: row for row in oracle["callers"]
                       if row["id"] != "land.merged"}
        cls.values = tuple(oracle["per_event_enum"])
        cls.sources = {
            caller_id: (
                CURRENT_CALLER_GATES[caller_id]["fence"][0]
                if caller_id in CURRENT_CALLER_GATES
                else REPO_ROOT / row["file"]
            )
            for caller_id, row in cls.callers.items()
        }

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.call_log = self.root / "calls.jsonl"
        self.import_log = self.root / "imports.txt"
        self.fake_flowctl = self.root / "flowctl"
        self.fake_gh = self.root / "gh"
        shutil.copyfile(FAKE_FLOWCTL, self.fake_flowctl)
        self.fake_flowctl.chmod(0o755)
        self.fake_gh.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                if [ "$MERGED_STATE" = "true" ]; then
                  printf '%s\\n' '[{"state":"MERGED"}]'
                else
                  printf '%s\\n' '[]'
                fi
                """
            ),
            encoding="utf-8",
        )
        self.fake_gh.chmod(0o755)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _environment(self, value: str, active: bool, merged: bool = True) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "FLOWCTL": self.fake_flowctl.as_posix(),
                "CALL_LOG": self.call_log.as_posix(),
                "IMPORT_LOG": self.import_log.as_posix(),
                "TRACKER_LEAF": value,
                "BRIDGE_ACTIVE": str(active).lower(),
                "MERGED_STATE": str(merged).lower(),
                "SPEC_ID": "fn-141-harness",
                "PR_URL": "https://example.test/pull/141",
                "BRANCH_NAME": "fn-141-harness",
                "BODY_FILE": (self.root / "comment.md").as_posix(),
                "TMPDIR": self.root.as_posix(),
                "PATH": f"{self.root.as_posix()}{os.pathsep}{env['PATH']}",
            }
        )
        (self.root / "comment.md").write_text("caller-owned comment\n", encoding="utf-8")
        (self.root / "flow.md").write_text("# Flow body\n", encoding="utf-8")
        (self.root / "source.md").write_text("Tracker source\n", encoding="utf-8")
        (self.root / "comments.json").write_text("[]\n", encoding="utf-8")
        return env

    def _run_shell(
        self,
        source: str,
        *,
        value: str,
        active: bool,
        merged: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        forbidden = re.search(
            r"(?m)^\s*(?:git|curl|glab|rm|mv)\s|gh\s+pr\s+merge",
            source,
        )
        if forbidden is not None:
            raise AssertionError(
                f"caller harness refused side-effecting command: {forbidden.group(0)!r}"
            )
        return subprocess.run(
            [self.bash, "-c", source],
            cwd=REPO_ROOT,
            env=self._environment(value, active, merged),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def _calls(self) -> list[list[str]]:
        if not self.call_log.exists():
            return []
        return [
            json.loads(line)
            for line in self.call_log.read_text(encoding="utf-8").splitlines()
        ]

    def _imports(self) -> list[str]:
        if not self.import_log.exists():
            return []
        return self.import_log.read_text(encoding="utf-8").splitlines()

    def _reset_observations(self) -> None:
        self.call_log.unlink(missing_ok=True)
        self.import_log.unlink(missing_ok=True)

    def _expected_op(self, caller_id: str, value: str, merged: bool) -> str | None:
        if caller_id in CHART_EVENTS:
            # Chart uses tracker.charts off|on, not the perEvent enum. The
            # shared matrix still walks off|pull|push|reconcile|comment;
            # none of those literals are "on", so the chart gate stays silent.
            return None
        if caller_id == "makePr":
            return "reconcile"
        if value == "off":
            return None
        if caller_id in DIRECT_EVENTS:
            return value
        if caller_id == "work.firstClaim":
            return "push"
        return "comment"

    def _facade_argv(self, caller_id: str, op: str) -> list[str]:
        row = self.callers[caller_id]
        argv = [
            "tracker",
            "sync",
            "fn-141-harness",
            "--op",
            op,
            "--event",
            row["event"],
        ]
        argv.extend(self._input_argv(op))
        if caller_id == "makePr" and op == "reconcile":
            argv.extend(["--pr-url", "https://example.test/pull/141"])
        if caller_id == "work.firstClaim":
            argv.append("--status-only")
        return argv

    def _input_argv(self, op: str) -> list[str]:
        inputs = {
            "push": [("--flow-file", "flow.md"), ("--body-file", "comment.md")],
            "pull": [
                ("--flow-file", "flow.md"),
                ("--body-file", "comment.md"),
                ("--comments-file", "comments.json"),
            ],
            "reconcile": [
                ("--flow-file", "flow.md"),
                ("--body-file", "comment.md"),
                ("--comments-file", "comments.json"),
                ("--source-body-file", "source.md"),
            ],
            "comment": [("--body-file", "comment.md")],
        }[op]
        return [
            item
            for flag, name in inputs
            for item in (flag, (self.root / name).as_posix())
        ]

    def _wrapper_body(self, caller_id: str, op_expression: str) -> str:
        row = self.callers[caller_id]
        modifier = ' STATUS_ARGS=(--status-only)' if caller_id == "work.firstClaim" else ' STATUS_ARGS=()'
        pr_modifier = (
            ' [ "$HARNESS_OP" != "reconcile" ] || '
            'INPUT_ARGS+=(--pr-url "$PR_URL")'
            if caller_id == "makePr"
            else ""
        )
        imports = []
        if caller_id == "plan":
            imports.append("references/tracker-projection.md")
        imports.append("skill:flow-next-tracker-sync")
        return "\n".join(
            [
                *[
                    f"printf '%s\\n' '{item}' >> \"$IMPORT_LOG\""
                    for item in imports
                ],
                f"HARNESS_OP={op_expression}",
                "case \"$HARNESS_OP\" in",
                '  push) INPUT_ARGS=(--flow-file "$TMPDIR/flow.md" --body-file "$BODY_FILE") ;;',
                '  pull) INPUT_ARGS=(--flow-file "$TMPDIR/flow.md" --body-file "$BODY_FILE" --comments-file "$TMPDIR/comments.json") ;;',
                '  reconcile) INPUT_ARGS=(--flow-file "$TMPDIR/flow.md" --body-file "$BODY_FILE" --comments-file "$TMPDIR/comments.json" --source-body-file "$TMPDIR/source.md") ;;',
                '  comment) INPUT_ARGS=(--body-file "$BODY_FILE") ;;',
                "esac",
                modifier,
                pr_modifier,
                f'FACADE_RESULT=$("$FLOWCTL" tracker sync "$SPEC_ID" --op "$HARNESS_OP" '
                f'--event {row["event"]} "${{INPUT_ARGS[@]}}" "${{STATUS_ARGS[@]}}")',
                'printf "%s" "$FACADE_RESULT" >/dev/null',
            ]
        )

    def _instrumented_fence(self, caller_id: str, op_expression: str) -> str:
        row = self.callers[caller_id]
        gate = CURRENT_CALLER_GATES.get(caller_id)
        needles = (
            gate["fence"][1]
            if gate is not None
            else (row["config_key"], "tracker sync")
        )
        fence = _single_fence(self.sources[caller_id], *needles)
        # References that open with the flowctl bootstrap must not clobber the
        # harness-supplied instrumented binary (the spine resolved it already).
        fence = "\n".join(
            line
            for line in fence.splitlines()
            if not _FLOWCTL_BOOTSTRAP.match(line)
        )
        body = self._wrapper_body(caller_id, op_expression)
        fence = (
            _inject_before_last_fi(fence, body)
            if "\nfi" in fence
            else f"{fence}\n{body}"
        )
        if gate is not None and "split_gate" in gate:
            # The reference is read ONLY when the spine's gate fired — the
            # sentinel is the load instruction. Both halves run in one shell so
            # state flows across the split exactly as it does in a session.
            path, start_token, sentinel = gate["split_gate"]
            fence = "\n".join(
                (
                    _shell_if_block_around(path, sentinel, start_token),
                    f"if {gate['fired']}; then",
                    textwrap.indent(fence, "  "),
                    "fi",
                )
            )
        return fence

    def _expected_config_reads(
        self, caller_id: str, phase: str, value: str | None = None
    ) -> list[list[str]]:
        for key in ((caller_id, phase, value), (caller_id, phase)):
            if key in CONFIG_READ_OVERRIDES:
                return CONFIG_READ_OVERRIDES[key]
        return self.callers[caller_id]["config_reads"][phase]

    def _strip_disclosure(
        self, caller_id: str, result: subprocess.CompletedProcess[str]
    ) -> subprocess.CompletedProcess[str]:
        """Remove branch-disclosure STOP sentinels from a split gate's stdout.

        A sentinel is only stripped after it is proven to name the reference
        that owns the rest of that caller gate — routing, never caller output.
        """
        gate = CURRENT_CALLER_GATES.get(caller_id)
        if gate is None or "split_gate" not in gate:
            return result
        kept: list[str] = []
        for line in result.stdout.splitlines(keepends=True):
            match = _SENTINEL_RE.search(line)
            if match is None:
                kept.append(line)
                continue
            self.assertTrue(
                match.group(1).startswith(gate["reference"]),
                f"{caller_id}: gate sentinel names {match.group(1)!r}, "
                f"not the reference {gate['reference']!r} that owns the "
                "rest of the caller gate",
            )
        return subprocess.CompletedProcess(
            result.args, result.returncode, "".join(kept), result.stderr
        )

    def test_config_read_overrides_are_declared_deltas(self) -> None:
        """Snapshot-backed gates remove reads; no override introduces a new read."""
        for key, override in CONFIG_READ_OVERRIDES.items():
            caller_id, phase = key[0], key[1]
            with self.subTest(key=key):
                oracle = self.callers[caller_id]["config_reads"][phase]
                self.assertTrue(
                    {tuple(argv) for argv in override}
                    <= {tuple(argv) for argv in oracle},
                    "override introduced a config read the oracle never made",
                )
                self.assertLessEqual(len(override) - len(oracle), 1)

    def _run_standard(
        self,
        caller_id: str,
        *,
        value: str,
        active: bool,
    ) -> subprocess.CompletedProcess[str]:
        op_expression = '"$OP"'
        if caller_id == "qa":
            op_expression = '"$QA_OP"'
        source = self._instrumented_fence(caller_id, op_expression)
        if caller_id in ("plan", "interview"):
            stem = "flow-plan-config" if caller_id == "plan" else "flow-refine-preflight"
            source = source.replace(f"{stem}-<suffix>.json", f"{stem}-harness.json")
            (self.root / f"{stem}-harness.json").write_text(json.dumps({
                "value": {"tracker": {"perEvent": {"plan": value, "interview": value}}},
                "probes": {
                    "config": {"status": "ok"},
                    "tracker": {"status": "ok", "value": {"active": active}},
                },
            }), encoding="utf-8")
        return self._strip_disclosure(
            caller_id, self._run_shell(source, value=value, active=active)
        )

    def _work_outer_fence(self, caller_id: str) -> str:
        phases = REPO_ROOT / "plugins/flow-next/skills/flow-next-work/phases.md"
        heading = {
            "work.firstClaim": "read and execute references/tracker-touchpoints.md#first-claim",
            "work.done": "read and execute references/tracker-touchpoints.md#task-done",
            "completionReview": "read and execute references/tracker-touchpoints.md#completion-review",
        }[caller_id]
        return _shell_if_block_around(phases, heading)

    def _run_work(
        self,
        caller_id: str,
        *,
        value: str,
        active: bool,
    ) -> subprocess.CompletedProcess[str]:
        snapshot = self.root / "run-sync-active.json"
        ops = {event: ("off" if value == "off" else "push" if event == "work.firstClaim" else "comment")
               for event in WORK_EVENTS} if active else {}
        snapshot.write_text(json.dumps({"active": active, "ops": ops}), encoding="utf-8")
        outer_source = self._work_outer_fence(caller_id).replace("<run-sync-active.json>", str(snapshot))
        outer = self._run_shell(outer_source, value=value, active=active)
        self.assertEqual(outer.returncode, 0, outer.stderr)
        if "GATE ACTIVE" not in outer.stdout:
            return subprocess.CompletedProcess(outer.args, 0, "", "")

        with self.import_log.open("a", encoding="utf-8") as handle:
            handle.write("references/tracker-touchpoints.md\n")
        inner = self._instrumented_fence(caller_id, '"$OP"').replace("<run-sync-active.json>", str(snapshot))
        return self._run_shell(inner, value=value, active=active)

    def _run_make_pr(
        self,
        *,
        value: str,
        active: bool,
    ) -> subprocess.CompletedProcess[str]:
        fence = _single_fence(
            self.sources["makePr"],
            "PR_URL",
            "sync active --json",
            "tracker sync",
        )
        return self._run_shell(
            _inject_before_last_fi(
                fence,
                self._wrapper_body("makePr", '"reconcile"'),
            ),
            value=value,
            active=active,
        )


    def _run_caller(
        self,
        caller_id: str,
        *,
        value: str,
        active: bool,
        merged: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if caller_id in WORK_EVENTS:
            return self._run_work(caller_id, value=value, active=active)
        if caller_id == "makePr":
            return self._run_make_pr(value=value, active=active)
        return self._run_standard(caller_id, value=value, active=active)

    def _config_calls(self) -> list[list[str]]:
        return [
            argv
            for argv in self._calls()
            if argv[:2] in (["config", "get"], ["sync", "active"])
        ]

    def _facade_calls(self) -> list[list[str]]:
        return [argv for argv in self._calls() if argv[:2] == ["tracker", "sync"]]

    def test_inactive_routes_are_byte_exact_against_pre_teardown_oracle(self) -> None:
        for caller_id, row in self.callers.items():
            with self.subTest(caller=caller_id):
                self._reset_observations()
                result = self._run_caller(caller_id, value="push", active=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    self._config_calls(),
                    self._expected_config_reads(caller_id, "inactive"),
                )
                self.assertEqual(self._facade_calls(), row["argv"]["inactive"])
                self.assertEqual(self._imports(), row["imports"]["inactive"])
                self.assertEqual(result.stdout, row["stdout"]["inactive"])
                self.assertEqual(result.stderr, row["stderr"]["inactive"])

    def test_every_per_event_value_executes_the_real_caller_gate(self) -> None:
        self.assertEqual(self.values, VALUES)
        for caller_id, row in self.callers.items():
            for value in self.values:
                with self.subTest(caller=caller_id, value=value):
                    self._reset_observations()
                    result = self._run_caller(caller_id, value=value, active=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        self._config_calls(),
                        self._expected_config_reads(caller_id, "active", value),
                    )
                    expected_op = self._expected_op(caller_id, value, merged=True)
                    expected_facades = (
                        [] if expected_op is None else [self._facade_argv(caller_id, expected_op)]
                    )
                    self.assertEqual(self._facade_calls(), expected_facades)
                    expected_imports = []
                    if caller_id in WORK_EVENTS:
                        expected_imports.append("references/tracker-touchpoints.md")
                    if expected_op is not None:
                        if caller_id == "plan":
                            expected_imports.append("references/tracker-projection.md")
                        expected_imports.append("skill:flow-next-tracker-sync")
                    self.assertEqual(self._imports(), expected_imports)
                    self.assertEqual(result.stdout, row["stdout"]["active_success"])
                    self.assertEqual(result.stderr, row["stderr"]["active_success"])

    def test_qa_coerces_every_non_off_value_to_comment(self) -> None:
        for value in VALUES[1:]:
            with self.subTest(value=value):
                self._reset_observations()
                result = self._run_caller("qa", value=value, active=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    self._facade_calls(),
                    [self._facade_argv("qa", "comment")],
                )


    def test_current_active_argv_is_a_declared_delta_from_the_oracle(self) -> None:
        for caller_id, row in self.callers.items():
            with self.subTest(caller=caller_id):
                if caller_id in CHART_EVENTS:
                    # Chart is post-baseline: argv is facade-native
                    # tracker sync with chart subject, not the pre-teardown
                    # skill-dispatch grammar.
                    self.assertEqual(row["resolved_facade_op"], "push")
                    self.assertEqual(
                        row["argv"]["active"][:2],
                        ["tracker", "sync"],
                    )
                    self.assertIn("--event", row["argv"]["active"])
                    self.assertIn("chart", row["argv"]["active"])
                    continue
                expected_op = self._expected_op(caller_id, "push", merged=True)
                self.assertIsNotNone(expected_op)
                old_argv = row["argv"]["active"]
                self.assertIn("flow-next-tracker-sync", old_argv)
                self.assertIn("<spec-id>", old_argv)
                if row["resolved_facade_op"] == "configured_value":
                    oracle_operation = "operation:<configured-value>"
                else:
                    oracle_operation = f"operation:{expected_op}"
                self.assertIn(oracle_operation, old_argv)
                current = self._facade_argv(caller_id, expected_op or "")
                self.assertEqual(current[:3], ["tracker", "sync", "fn-141-harness"])
                self.assertEqual(current[3:5], ["--op", expected_op])
                self.assertEqual(current[5:7], ["--event", row["event"]])
                self.assertEqual(
                    "--status-only" in current,
                    caller_id == "work.firstClaim",
                )


if __name__ == "__main__":
    unittest.main()

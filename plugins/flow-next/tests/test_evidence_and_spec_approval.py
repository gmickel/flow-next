"""Opt-in development evidence, spec approval by PR, and `flowctl trace`.

Default config must leave every output unchanged (R1); `evidence.persist on`
writes and stages per-round evidence (R2-R4); `spec.approval pr` gates
implementation on an approved, merged spec PR and records it (R5-R7);
`trace` builds the per-criterion matrix and gap check (R8).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import flowctl  # noqa: E402

SPEC = "fn-1-demo"
SPEC_MD = "# Demo\n\n## Acceptance Criteria\n\n- **R1:** One.\n- **R2:** Two.\n"
APPROVED_PR = [{
    "number": 7, "url": "https://example.test/pr/7", "state": "MERGED",
    "mergedAt": "2026-10-01T00:00:00Z", "mergedBy": {"login": "lead"},
    "reviews": [{"author": {"login": "qa-lead"}, "state": "APPROVED",
                 "submittedAt": "2026-09-30T00:00:00Z"}],
}]
NO_SHIM = os.name == "nt"  # A PATH shim cannot intercept list-form spawns on Windows.


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self.root = self.tempdir()
        # A fake `gh` answering from a file the test controls.
        self.bin = self.tempdir()
        self.gh_out = self.bin / "gh.json"
        self.gh_out.write_text("[]", encoding="utf-8")
        gh = self.bin / "gh"
        gh.write_text('#!/bin/sh\ncat "$FAKE_GH_OUT"\nexit "${FAKE_GH_RC:-0}"\n', encoding="utf-8")
        gh.chmod(0o755)
        self.gh_rc = "0"
        for argv in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
                     ["git", "config", "user.name", "t"]):
            subprocess.check_call(argv, cwd=self.root)
        self.flow("init")
        self.flow("spec", "create", "--title", "Demo")
        (self.root / ".flow" / "specs" / f"{SPEC}.md").write_text(SPEC_MD, encoding="utf-8")
        self.flow("task", "create", "--spec", SPEC, "--title", "T", "--satisfies", "R1")
        subprocess.check_call(["git", "add", "-A"], cwd=self.root)
        subprocess.check_call(["git", "commit", "-qm", "init"], cwd=self.root)

    def tempdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name).resolve()  # macOS /var symlink, Windows 8.3 short names

    def flow(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "FAKE_GH_OUT": str(self.gh_out), "FAKE_GH_RC": self.gh_rc}
        proc = subprocess.run([*FLOWCTL_CMD, *args], cwd=self.root, env=env,
                              capture_output=True, text=True, timeout=120)
        if check and proc.returncode != 0:
            self.fail(f"flowctl {' '.join(args)} -> {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
        return proc

    def set_raw_config(self, key: str, value) -> None:
        path = self.root / ".flow" / "config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        node = config
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        path.write_text(json.dumps(config), encoding="utf-8")

    def complete_task(self, summary: str = "Done. Tier: x (model: opus-test)") -> dict:
        self.flow("start", f"{SPEC}.1")
        out = self.flow("done", f"{SPEC}.1", "--test", "pytest -k r1",
                        "--summary", summary, "--json").stdout
        return json.loads(out)

    def qa_receipt(self, outcome: str = "SHIP") -> None:
        payload = self.root / "qa.json"
        payload.write_text(json.dumps({
            "id": SPEC, "qa_outcome": outcome, "findings": [],
            "rid_coverage": {"rids": [{"id": "R2", "coverage": "live"}]},
        }), encoding="utf-8")
        self.flow("qa", "receipt", "--from-json", str(payload), "--json")

    def staged(self) -> list[str]:
        return subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=self.root,
                              capture_output=True, text=True, check=True).stdout.split()

    def evidence(self) -> Path:
        return self.root / ".flow" / "evidence" / SPEC


class DefaultPathTest(Repo):
    """R1/R5: absent, off or any non-"on" value changes nothing."""

    def test_default_and_non_on_values_write_nothing(self) -> None:
        for value in (None, "off", True, "yes", "ON"):
            with self.subTest(value=value):
                self.setUp()
                if value is not None:
                    self.set_raw_config("evidence.persist", value)
                self.gh_rc = "1"  # Any forge call would fail the local path.
                done = self.complete_task()
                self.qa_receipt()
                self.assertEqual(done["modified_paths"],
                                 [str(self.root / ".flow" / "tasks" / f"{SPEC}.1.md")])
                self.assertFalse((self.root / ".flow" / "evidence").exists())
                self.assertEqual(self.staged(), [])
                self.flow("spec", "ready", SPEC)

    def test_route_lifecycle_unchanged_without_approval_state(self) -> None:
        state = {"pr_exists": False, "status": "open", "tasks_total": 0, "tasks_done": 0,
                 "no_plan": True, "ready": False, "spec_body": ""}
        self.assertEqual(flowctl.judge_route_lifecycle(state)["value"], "work_no_plan_default")


class EvidencePersistTest(Repo):
    """R2-R4: committed, staged, per-round evidence and the run record."""

    def setUp(self) -> None:
        super().setUp()
        self.flow("config", "set", "evidence.persist", "on")

    def test_task_qa_and_captures_are_written_and_staged(self) -> None:
        done = self.complete_task()
        captures = self.root / ".flow" / "tmp" / f"qa-{SPEC}"
        captures.mkdir(parents=True)
        (captures / "shot.png").write_bytes(b"png")
        self.qa_receipt("NEEDS_WORK")
        self.qa_receipt("SHIP")
        task_record = self.evidence() / "tasks" / f"{SPEC}.1.json"
        self.assertIn(str(task_record), done["modified_paths"])
        self.assertEqual(json.loads(task_record.read_text())["evidence"]["tests"], ["pytest -k r1"])
        rounds = sorted(p.parent.name for p in self.evidence().glob("qa/*/receipt.json"))
        self.assertEqual(len(rounds), 2, rounds)  # A later round never overwrites an earlier one.
        outcomes = {json.loads((self.evidence() / "qa" / r / "receipt.json").read_text())["qa_outcome"]
                    for r in rounds}
        self.assertEqual(outcomes, {"NEEDS_WORK", "SHIP"})
        self.assertTrue((self.evidence() / "qa" / rounds[-1] / "captures" / "shot.png").is_file())
        staged = self.staged()
        self.assertIn(f".flow/evidence/{SPEC}/tasks/{SPEC}.1.json", staged)
        self.assertIn(f".flow/evidence/{SPEC}/qa/{rounds[0]}/receipt.json", staged)

    def test_review_receipt_rounds_and_run_record(self) -> None:
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        receipt_path = self.root / "impl-receipt.json"
        base = {"type": "impl_review", "id": f"{SPEC}.1", "mode": "codex", "verdict": "NEEDS_WORK"}
        flowctl.atomic_write_json(receipt_path, {**base, "model": "gpt-x",
                                                 "timestamp": "2026-10-01T10:00:00Z"})
        # A rewrite of the same round (a lease or findings update) keeps its file.
        flowctl.atomic_write_json(receipt_path, {**base, "model": "gpt-x", "phase_lease": {},
                                                 "timestamp": "2026-10-01T10:00:00Z"})
        flowctl.atomic_write_json(receipt_path, {**base, "verdict": "SHIP",
                                                 "timestamp": "2026-10-01T11:00:00Z"})
        files = sorted(p.name for p in (self.evidence() / "reviews").iterdir())
        self.assertEqual(len(files), 2, files)
        run = json.loads((self.evidence() / "run.json").read_text())
        reviews = {row["key"]: row for row in run["reviews"]}
        self.assertEqual(len(reviews), 2)
        models = sorted(row["model"] for row in reviews.values())
        self.assertEqual(models, ["gpt-x", "unknown"])  # Unknown is written, never guessed.
        for row in reviews.values():
            self.assertEqual(row["backend"], "codex")
            self.assertEqual(row["flow_next_version"], flowctl.evidence_flow_next_version())
            self.assertIn("host", row)

    def test_run_record_stage_model(self) -> None:
        self.complete_task(summary="Done. Tier: session (model: not reported)")
        run = json.loads((self.evidence() / "run.json").read_text())
        self.assertEqual(run["stages"][0]["implementing_model"], "unknown")

    def test_unsafe_evidence_dir_fails_the_stage(self) -> None:
        outside = self.tempdir()
        (self.root / "linked").symlink_to(outside, target_is_directory=True)
        cases = (("../escape", "outside the repository"),
                 ("linked/evidence", "through a symlink"),
                 (str(outside), "repo-relative"))
        for number, (value, message) in enumerate(cases, start=2):
            with self.subTest(value=value):
                self.flow("config", "set", "evidence.dir", value)
                self.flow("task", "create", "--spec", SPEC, "--title", "X")
                task = f"{SPEC}.{number}"
                self.flow("start", task)
                proc = self.flow("done", task, "--summary", "s", "--json", check=False)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(message, json.loads(proc.stdout)["error"])  # --json keeps its envelope
                # The failed evidence write leaves the task retryable, not done.
                shown = json.loads(self.flow("show", task, "--json").stdout)
                self.assertEqual(shown["status"], "in_progress")

    def test_failed_receipt_copy_leaves_the_receipt_unwritten(self) -> None:
        receipt = self.root / "receipt.json"
        content = json.dumps({"type": "impl_review", "id": f"{SPEC}.1", "verdict": "SHIP"})
        with mock.patch.object(flowctl, "evidence_record_receipt", side_effect=SystemExit(1)):
            with self.assertRaises(SystemExit):
                flowctl.atomic_write(receipt, content)
        self.assertFalse(receipt.exists())

    def test_symlink_inside_the_evidence_folder_is_refused(self) -> None:
        outside = self.tempdir()
        self.evidence().mkdir(parents=True)
        (self.evidence() / "tasks").symlink_to(outside, target_is_directory=True)
        self.flow("start", f"{SPEC}.1")
        proc = self.flow("done", f"{SPEC}.1", "--summary", "s", "--json", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("is a symlink", json.loads(proc.stdout)["error"])
        self.assertEqual(list(outside.iterdir()), [])


@unittest.skipIf(NO_SHIM, "PATH shim cannot intercept list-form gh spawns on Windows")
class SpecApprovalTest(Repo):
    """R6/R7: readiness comes from an approved, merged spec PR."""

    def setUp(self) -> None:
        super().setUp()
        self.flow("config", "set", "spec.approval", "pr")

    def test_unapproved_states_block_start_and_ready(self) -> None:
        cases = (
            ([], "no spec PR from branch spec/"),
            ([{"number": 3, "state": "OPEN", "reviews": []}], "is open"),
            ([{"number": 4, "state": "CLOSED", "reviews": []}], "closed without merge"),
            ([{"number": 5, "state": "MERGED", "mergedAt": "x", "reviews": [
                {"state": "COMMENTED", "author": {"login": "a"}}]}], "without an approving review"),
        )
        for rows, reason in cases:
            with self.subTest(reason=reason):
                self.gh_out.write_text(json.dumps(rows), encoding="utf-8")
                for args in (("start", f"{SPEC}.1"), ("spec", "ready", SPEC)):
                    proc = self.flow(*args, "--json", check=False)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn(reason, proc.stdout)
                    self.assertIn("spec-approval-pr.md", proc.stdout)

    def test_forge_unreachable_fails_closed(self) -> None:
        self.gh_rc = "1"
        proc = self.flow("start", f"{SPEC}.1", "--json", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("forge unreachable", proc.stdout)

    def test_approved_merge_records_and_unblocks(self) -> None:
        self.flow("config", "set", "evidence.persist", "on")
        self.gh_out.write_text(json.dumps(APPROVED_PR), encoding="utf-8")
        self.flow("start", f"{SPEC}.1")
        spec = json.loads((self.root / ".flow" / "specs" / f"{SPEC}.json").read_text())
        self.assertIs(spec["ready"], True)
        record = spec["spec_approval"]
        self.assertEqual(record["approvers"], [{"login": "qa-lead", "approved_at": "2026-09-30T00:00:00Z"}])
        self.assertEqual((record["merged_by"], record["merged_at"]), ("lead", "2026-10-01T00:00:00Z"))
        persisted = json.loads((self.evidence() / "approval.json").read_text())
        self.assertEqual(persisted["approvers"], record["approvers"])

    def test_concurrent_unready_is_never_overwritten(self) -> None:
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        old_path = os.environ["PATH"]
        os.environ.update(PATH=f"{self.bin}{os.pathsep}{old_path}", FAKE_GH_OUT=str(self.gh_out))
        self.addCleanup(os.environ.update, PATH=old_path)
        self.gh_out.write_text(json.dumps(APPROVED_PR), encoding="utf-8")
        spec_path = self.root / ".flow" / "specs" / f"{SPEC}.json"
        stale = json.loads(spec_path.read_text())  # Read before the unready below.
        withdrawn = {"approved": False, "invalidated_at": "2000-01-01T00:00:00Z"}
        spec_path.write_text(json.dumps({**stale, "spec_approval": withdrawn}), encoding="utf-8")
        status = flowctl.spec_approval_status(self.root / ".flow", stale)
        self.assertFalse(status["approved"])
        self.assertEqual(json.loads(spec_path.read_text())["spec_approval"], withdrawn)

    def test_route_holds_an_unapproved_spec(self) -> None:
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        old_path = os.environ["PATH"]
        os.environ.update(PATH=f"{self.bin}{os.pathsep}{old_path}", FAKE_GH_OUT=str(self.gh_out))
        self.addCleanup(os.environ.update, PATH=old_path)
        state = flowctl.judge_route_state({}, SPEC)
        decision = flowctl.judge_route_lifecycle(state)
        self.assertEqual(decision["value"], "host")
        self.assertIn("spec.approval is pr", decision["rule"])
        # Held ahead of make-pr and plan review, not only ahead of task work.
        for extra in ({"tasks_total": 1, "tasks_done": 1}, {"plan_review_status": "stale"}):
            held = flowctl.judge_route_lifecycle({**state, "pr_exists": False, **extra})
            self.assertEqual(held["value"], "host")

    def test_invalid_value_stops(self) -> None:
        self.assertNotEqual(self.flow("config", "set", "spec.approval", "maybe", check=False).returncode, 0)
        for value in ("maybe", None):
            with self.subTest(value=value):
                self.set_raw_config("spec.approval", value)
                proc = self.flow("start", f"{SPEC}.1", "--json", check=False)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(f"Invalid spec.approval value {value!r}", proc.stdout)

    def test_unready_withdraws_approval_until_a_later_merge(self) -> None:
        self.gh_out.write_text(json.dumps(APPROVED_PR), encoding="utf-8")
        self.flow("spec", "ready", SPEC)
        self.flow("spec", "unready", SPEC)  # A rewrite withdraws readiness.
        proc = self.flow("spec", "ready", SPEC, "--json", check=False)
        self.assertNotEqual(proc.returncode, 0)  # The old merge no longer approves.
        spec_path = self.root / ".flow" / "specs" / f"{SPEC}.json"
        withdrawn = json.loads(spec_path.read_text())["spec_approval"]["invalidated_at"]
        # A merge earlier in the same second as the withdrawal does not re-approve.
        same_second = [{**APPROVED_PR[0], "mergedAt": withdrawn[:19] + "Z"}]
        self.gh_out.write_text(json.dumps(same_second), encoding="utf-8")
        self.assertNotEqual(self.flow("start", f"{SPEC}.1", check=False).returncode, 0)
        later = [{**APPROVED_PR[0], "number": 9, "mergedAt": "2999-01-01T00:00:00Z"}]
        self.gh_out.write_text(json.dumps(APPROVED_PR + later), encoding="utf-8")
        self.flow("start", f"{SPEC}.1")
        spec = json.loads((self.root / ".flow" / "specs" / f"{SPEC}.json").read_text())
        self.assertEqual(spec["spec_approval"]["number"], 9)

    def test_authoring_writes_point_at_the_spec_pr(self) -> None:
        proc = self.flow("task", "create", "--spec", SPEC, "--title", "Next")
        self.assertIn("spec-approval-pr.md", proc.stderr)
        self.flow("config", "set", "spec.approval", "local")
        self.assertNotIn("spec.approval", self.flow("spec", "create", "--title", "Other").stderr)

    def test_trace_reads_spec_approval_from_the_forge(self) -> None:
        self.gh_out.write_text(json.dumps(APPROVED_PR), encoding="utf-8")
        result = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)
        self.assertIn("approved by qa-lead", result["rows"][0]["spec_approval"])
        spec = json.loads((self.root / ".flow" / "specs" / f"{SPEC}.json").read_text())
        self.assertNotIn("spec_approval", spec)  # trace never records.


class TraceTest(Repo):
    """R8: matrix, gap check and exit codes."""

    def test_gaps_formats_and_exit_codes(self) -> None:
        self.complete_task()
        proc = self.flow("trace", SPEC, "--json", check=False)
        self.assertEqual(proc.returncode, 1)
        result = json.loads(proc.stdout)
        self.assertEqual([row["criterion"] for row in result["rows"]], ["R1", "R2"])
        self.assertEqual(result["rows"][0]["tests"], [f"pytest -k r1 ({SPEC}.1)"])
        self.assertEqual(result["gaps"], ["R2: no evidence"])
        self.qa_receipt()  # Live QA coverage for R2 closes the gap.
        self.assertEqual(self.flow("trace", SPEC, check=False).returncode, 0)
        csv_out = self.flow("trace", SPEC, "--format", "csv").stdout.splitlines()
        self.assertTrue(csv_out[0].startswith("criterion,text,tests,test_result,qa"))
        self.assertEqual(len(csv_out), 3)

    def test_evidence_naming_no_criterion_is_a_gap(self) -> None:
        self.flow("task", "create", "--spec", SPEC, "--title", "Loose")
        self.flow("start", f"{SPEC}.2")
        self.flow("done", f"{SPEC}.2", "--test", "pytest", "--summary", "s")
        result = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)
        self.assertIn(f"{SPEC}.2: test evidence names no criterion", result["gaps"])

    def test_skipped_tests_and_unknown_finding_criteria_are_gaps(self) -> None:
        self.flow("config", "set", "evidence.persist", "on")
        self.flow("start", f"{SPEC}.1")
        self.flow("done", f"{SPEC}.1", "--test", "GATE_SKIPPED:unit:docs-only", "--summary", "s")
        review = self.evidence() / "reviews" / "r.json"
        review.parent.mkdir()
        review.write_text(json.dumps({"type": "impl_review", "id": f"{SPEC}.1", "findings": {
            "items": [{"title": "t", "severity": "P1", "status": "open", "rIds": ["R9"]}]}}),
            encoding="utf-8")
        gaps = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)["gaps"]
        self.assertIn("R1: no evidence", gaps)
        self.assertIn("review finding 't' names unknown criterion R9", gaps)

    def test_fresh_clone_reads_committed_task_evidence(self) -> None:
        self.flow("config", "set", "evidence.persist", "on")
        self.complete_task()
        subprocess.check_call(["git", "add", "-A"], cwd=self.root)
        subprocess.check_call(["git", "commit", "-qm", "done"], cwd=self.root)
        clone = self.tempdir() / "clone"
        subprocess.check_call(["git", "clone", "-q", str(self.root), str(clone)])
        self.root = clone
        result = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)
        self.assertEqual(result["rows"][0]["tests"], [f"pytest -k r1 ({SPEC}.1)"])

    def write_report(self, *cases: str) -> Path:
        report = self.evidence() / "tests" / f"{SPEC}.1" / "junit.xml"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text('<?xml version="1.0"?><testsuites><testsuite name="s">'
                          + "".join(cases) + "</testsuite></testsuites>", encoding="utf-8")
        return report

    def test_junit_report_gives_per_test_results_by_rid(self) -> None:
        self.flow("config", "set", "evidence.persist", "on")
        start = self.flow("start", f"{SPEC}.1")
        self.assertIn(f".flow/evidence/{SPEC}/tests/{SPEC}.1/", start.stderr)
        self.write_report('<testcase classname="ledger" name="R1: books with a cost centre"/>',
                          '<testcase name="test_r1_rejects_missing"><failure>boom</failure></testcase>',
                          '<testcase name="unrelated helper"/>')
        done = json.loads(self.flow("done", f"{SPEC}.1", "--test", "pytest", "--summary", "s",
                                    "--json").stdout)
        record = json.loads((self.evidence() / "tasks" / f"{SPEC}.1.json").read_text())
        self.assertEqual(record["test_reports"], [f"tests/{SPEC}.1/junit.xml"])
        self.assertIn(f".flow/evidence/{SPEC}/tests/{SPEC}.1/junit.xml", self.staged())
        self.assertIn(str(self.evidence() / "tasks" / f"{SPEC}.1.json"), done["modified_paths"])
        result = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)
        row = result["rows"][0]
        self.assertEqual(row["tests"], [f"ledger R1: books with a cost centre: passed ({SPEC}.1)",
                                        f"test_r1_rejects_missing: failed ({SPEC}.1)"])
        self.assertEqual(row["test_result"], "failed, passed")
        self.assertIn("R1: test 'test_r1_rejects_missing' failed", result["gaps"])
        self.assertFalse([g for g in result["gaps"] if "unrelated helper" in g])

    def test_failures_without_a_known_criterion_and_unreadable_reports_are_gaps(self) -> None:
        self.flow("config", "set", "evidence.persist", "on")
        self.flow("start", f"{SPEC}.1")
        report = self.write_report('<testcase name="test_r1_ok"/>',
                                   '<testcase name="helper"><error>x</error></testcase>',
                                   '<testcase name="test_r99_typo"/>')
        self.flow("done", f"{SPEC}.1", "--test", "pytest", "--summary", "s")
        gaps = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)["gaps"]
        self.assertIn(f"{SPEC}.1: test 'helper' error and names no criterion", gaps)
        self.assertIn(f"{SPEC}.1: test 'test_r99_typo' (passed) names unknown criterion R99", gaps)
        report.write_text('<?xml version="1.0"?><testsuites><testcase name="R1: x">',
                          encoding="utf-8")  # Truncated: never a fallback to "recorded at done".
        result = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)
        self.assertTrue(any(g.startswith(f"{SPEC}.1: test report junit.xml unreadable")
                            for g in result["gaps"]))
        self.assertEqual(result["rows"][0]["test_result"], "none")

    def test_report_without_a_test_for_a_satisfied_rid_is_a_gap(self) -> None:
        self.flow("config", "set", "evidence.persist", "on")
        self.flow("start", f"{SPEC}.1")
        self.write_report('<testcase name="unrelated"/>')
        self.flow("done", f"{SPEC}.1", "--test", "pytest", "--summary", "s")
        gaps = json.loads(self.flow("trace", SPEC, "--json", check=False).stdout)["gaps"]
        self.assertIn(f"R1: no test in {SPEC}.1's report names it", gaps)
        self.assertIn("R1: no evidence", gaps)

    def test_no_notice_by_default(self) -> None:
        self.assertNotIn("evidence.persist", self.flow("start", f"{SPEC}.1").stderr)

    def test_errors(self) -> None:
        self.assertEqual(self.flow("trace", "fn-99", check=False).returncode, 2)
        if NO_SHIM:
            return
        self.gh_rc = "1"  # Forge unreachable: approval unknown with a warning.
        proc = self.flow("trace", SPEC, "--json", check=False)
        self.assertEqual(json.loads(proc.stdout)["rows"][0]["implementation_approval"], "unknown")
        self.assertIn("implementation approval unknown", proc.stderr)


if __name__ == "__main__":
    unittest.main()

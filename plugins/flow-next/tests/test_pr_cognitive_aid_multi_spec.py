"""Range membership and additive multi-spec briefing contracts."""

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import flowctl
from test_pr_cognitive_aid import SPEC_ID, artifact, artifact_diff_files


SIBLING = "fn-250-sibling"
FIXTURE = Path(__file__).parent / "fixtures/pr-cognitive-aid/single-spec-export.json"


def multi_artifact():
    value = artifact()
    value["specIds"] = [SPEC_ID, SIBLING, "fn-251-no-requirements"]
    for source in value["sources"]:
        if source["kind"] == "rid":
            source["ref"] = "fn-136:" + source["ref"]
    groups = value["changeWalkthrough"]["groups"]
    for group in groups:
        for record in [group, *group["files"]]:
            record["rIds"] = ["fn-136:" + rid for rid in record["rIds"]]
    value["sources"].extend([
        {"id": "sibling", "kind": "spec", "ref": SIBLING},
        {"id": "sibling-task", "kind": "task", "ref": SIBLING + ".1"},
        {"id": "sibling-rid", "kind": "rid", "ref": "fn-250:R1"},
        {"id": "uncovered", "kind": "rid", "ref": "fn-250:R7"},
    ])
    row = groups[2]["files"][1]
    row.update(sourceRefs=["diff", "sibling-task", "sibling-rid"],
               taskIds=[SIBLING + ".1"], rIds=["fn-250:R1"])
    return value


class MultiSpecArtifactTests(unittest.TestCase):
    def test_single_member_and_old_artifact_preserve_bytes(self):
        old = artifact()
        single = copy.deepcopy(old)
        single["specIds"] = [SPEC_ID]
        self.assertEqual(flowctl.validate_pr_cognitive_aid(old), old)
        self.assertEqual(flowctl.render_pr_cognitive_aid_markdown(old),
                         flowctl.render_pr_cognitive_aid_markdown(single))

    def test_qualified_coverage_and_html(self):
        value = multi_artifact()
        self.assertEqual(flowctl.validate_pr_cognitive_aid(value, expected_spec_id=SPEC_ID), value)
        with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, "specId:"):
            flowctl.validate_pr_cognitive_aid(value, expected_spec_id=SIBLING)
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertEqual(text, flowctl.render_pr_cognitive_aid_markdown(value))
        self.assertIn("[fn-136:R6]", text)
        self.assertIn("[fn-250:R1]", text)
        self.assertIn("fn-136: R6 → 1", text)
        self.assertIn("fn-250: R1 → 1; R7 → uncovered", text)
        self.assertLess(text.index("fn-136: R6"), text.index("fn-250: R1"))
        self.assertIn("| fn-250:R7 | unevidenced |", text)
        self.assertNotIn("fn-251:", text)
        sparse = copy.deepcopy(value)
        for row in sparse["changeWalkthrough"]["groups"][2]["files"]:
            for field in ("changeType", "additions", "deletions"):
                del row[field]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aid.json"
            path.write_text(json.dumps(sparse), encoding="utf-8")
            output = StringIO()
            with mock.patch.object(flowctl, "_pr_aid_live_diff_files", return_value=artifact_diff_files(value)), \
                 mock.patch.object(flowctl, "_pr_aid_blob_prefix", return_value=None), redirect_stdout(output):
                flowctl.cmd_pr_cognitive_aid_html_input(argparse.Namespace(file=str(path)))
            embedded = output.getvalue().split(">", 1)[1].split("</script>", 1)[0]
            self.assertEqual(json.loads(embedded), value)

    def test_invalid_spec_sets(self):
        for ids in ([SIBLING], [SPEC_ID, SPEC_ID], [SPEC_ID, "bad"],
                    [SPEC_ID, SPEC_ID + ".1"], [], "fn-250", [SPEC_ID] * 33):
            with self.subTest(ids=ids):
                value = multi_artifact()
                value["specIds"] = ids
                with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, "specIds"):
                    flowctl.validate_pr_cognitive_aid(value)

    def test_rid_scope_and_task_membership_errors_name_path(self):
        for ref in ("R6", "fn-999:R6", "fn-136:R0"):
            value = multi_artifact()
            value["sources"][2]["ref"] = ref
            with self.subTest(ref=ref), self.assertRaisesRegex(
                    flowctl.PrCognitiveAidValidationError, r"sources\[2\].ref"):
                flowctl.validate_pr_cognitive_aid(value)
        value = multi_artifact()
        value["specIds"].append("fn-136-ambiguous")
        with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, r"sources\[2\].ref"):
            flowctl.validate_pr_cognitive_aid(value)
        value = multi_artifact()
        value["changeWalkthrough"]["groups"][2]["rIds"] = ["R6"]
        with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, r"groups\[2\].rIds\[0\]"):
            flowctl.validate_pr_cognitive_aid(value)
        for ids in (None, [SPEC_ID]):
            value = artifact()
            if ids:
                value["specIds"] = ids
            value["sources"][2]["ref"] = "fn-136:R6"
            value["changeWalkthrough"]["groups"][2]["rIds"] = ["fn-136:R6"]
            with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, r"groups\[2\].rIds\[0\]"):
                flowctl.validate_pr_cognitive_aid(value)
        value = multi_artifact()
        value["sources"][-3]["ref"] = "fn-999-other.1"
        value["changeWalkthrough"]["groups"][2]["files"][1]["taskIds"] = ["fn-999-other.1"]
        with self.assertRaises(flowctl.PrCognitiveAidValidationError) as exc:
            flowctl.validate_pr_cognitive_aid(value)
        self.assertIn("sources[6].ref", str(exc.exception))
        self.assertIn("files[1].taskIds[0]", str(exc.exception))


class ClosedRangeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.flow = self.repo / ".flow"
        (self.flow / "specs").mkdir(parents=True)
        (self.flow / "tasks").mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Range Test")
        self.git("config", "user.email", "range@example.test")
        self.git("config", "commit.gpgsign", "false")
        patch = mock.patch.object(flowctl, "get_repo_root", return_value=self.repo)
        patch.start()
        self.addCleanup(patch.stop)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True,
                              capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def spec(self, number, status):
        sid = f"fn-{number}-spec"
        (self.flow / "specs" / f"{sid}.json").write_text(json.dumps({
            "id": sid, "title": f"Spec {number}", "status": status,
        }), encoding="utf-8")
        (self.flow / "specs" / f"{sid}.md").write_text(
            f"# Spec {number}\n\n## Goal & Context\n\nGoal {number}.\n\n"
            f"## Acceptance Criteria\n\n- **R1:** Requirement {number}.\n", encoding="utf-8")
        return sid

    def commit(self):
        self.git("add", ".flow")
        self.git("commit", "-qm", "state")
        return self.git("rev-parse", "HEAD")

    def test_one_newly_closed_and_host_always_present(self):
        sid = self.spec(250, "open")
        base = self.commit()
        self.spec(250, "done")
        self.commit()
        self.assertEqual(flowctl.specs_closed_in_range(self.flow, base), [sid])
        self.assertEqual(flowctl.specs_closed_in_range(self.flow, base, "fn-2-host"), ["fn-2-host", sid])
        self.assertEqual(flowctl.specs_closed_in_range(self.flow, "HEAD", sid), [sid])
        self.assertEqual(flowctl.specs_closed_in_range(self.flow, "HEAD"), [])

    def test_three_closed_exclusions_order_and_committed_objects_only(self):
        already = self.spec(1, "done")
        self.spec(30, "open")
        self.spec(8, "open")
        base = self.commit()
        expected = [self.spec(8, "done"), self.spec(30, "done"), self.spec(250, "done")]
        self.spec(2, "open")
        self.commit()
        self.spec(2, "done")  # Dirt must not affect membership.
        self.spec(30, "open")
        self.assertEqual(flowctl.specs_closed_in_range(self.flow, base), expected)
        self.assertEqual(flowctl.specs_closed_in_range(self.flow, base, already), [already, *expected])

    def export(self, module=flowctl, *, multi=False):
        sid = self.spec(250, "open")
        task = sid + ".1"
        (self.flow / "tasks" / f"{task}.json").write_text("{}", encoding="utf-8")
        (self.flow / "tasks" / f"{task}.md").write_text(
            "---\nsatisfies: [R1]\n---\n\n## Done summary\n\nImplemented.\n", encoding="utf-8")
        base = self.commit()
        self.spec(250, "done")
        if multi:
            self.spec(251, "done")
        self.commit()
        with ExitStack() as stack:
            for name, result in {
                "get_repo_root": self.repo,
                "get_flow_dir": self.flow,
                "_export_resolve_merge_base": base,
                "load_task_with_state": {"id": task, "status": "done", "title": "Task", "evidence": {"tests": ["unit"]}},
                "_export_memory_during_epic": {},
                "_export_materialize_diff": SimpleNamespace(name_status=[], name_status_rc=0, events=[]),
                "_export_glossary_diff": {},
                "_export_diff_summary": {},
                "_export_removed_export_refs": [],
                "_export_deferred_findings": {},
            }.items():
                stack.enter_context(mock.patch.object(module, name, return_value=result))
            output = stack.enter_context(redirect_stdout(StringIO()))
            module.cmd_spec_export_cognitive_aid(argparse.Namespace(id=sid, base=base, json=True))
            return output.getvalue()

    def test_single_export_matches_pre_change_bytes(self):
        self.assertEqual(self.export().encode("utf-8"), FIXTURE.read_text(encoding="utf-8").encode("utf-8"))

    def test_multi_export_reuses_host_summary_and_carries_requirements(self):
        payload = json.loads(self.export(multi=True))
        self.assertEqual([s["short_id"] for s in payload["specs"]], ["fn-250", "fn-251"])
        for member in payload["specs"]:
            self.assertEqual(member["spec_sections"]["acceptance_criteria"][0]["id"], "R1")
            self.assertIn(member["short_id"][3:], member["spec_sections"]["acceptance_criteria"][0]["text"])
        host = payload["specs"][0]
        self.assertEqual(host["tasks"], payload["tasks"])
        self.assertEqual(host["tasks_summary"], payload["tasks_summary"])
        self.assertEqual(host["tasks"][0]["evidence"]["tests"], ["unit"])
        self.assertEqual(payload["specs"][1]["tasks_summary"]["undeclared_r_ids"], ["R1"])

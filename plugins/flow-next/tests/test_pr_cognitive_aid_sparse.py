"""Sparse aid input expands at validate/write boundaries; stored v1 stays strict."""

import argparse
import copy
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from test_pr_cognitive_aid import (
    BASE_SHA, HEAD_SHA, SPEC_ID, artifact, artifact_diff_files, flowctl,
)


class SparseInputTests(unittest.TestCase):
    def setUp(self):
        remote = mock.patch.object(
            flowctl, "_export_run_git", return_value=(0, "git@example.test:acme/repo.git", "")
        )
        remote.start()
        self.addCleanup(remote.stop)

    def complete(self):
        value = artifact(canonical_files=1)
        group = value["changeWalkthrough"]["groups"][2]
        group["sourceRefs"] = ["diff", "task", "rid"]
        for row in group["files"]:
            row["diffUrl"] = f"/acme/repo/blob/{HEAD_SHA}/{row['path']}"
        return value

    def validate_input(self, value, diff):
        output = StringIO()
        with mock.patch.object(flowctl, "_pr_aid_read_input", return_value=value), \
             mock.patch.object(flowctl, "get_repo_root", return_value=Path.cwd()), \
             mock.patch.object(flowctl, "_pr_aid_live_diff_files", return_value=diff), \
             redirect_stdout(output):
            flowctl.cmd_pr_cognitive_aid_validate(
                argparse.Namespace(file="unused.json", json=True)
            )
        return json.loads(output.getvalue())["artifact"]

    def write(self, root, value, diff):
        return flowctl.write_pr_cognitive_aid(
            root, value, spec_id=SPEC_ID, base_sha=BASE_SHA,
            head_sha=HEAD_SHA, expected_diff_files=diff,
        )

    def test_file_commands_share_expansion_and_complete_render_is_unchanged(self):
        complete = self.complete()
        sparse = copy.deepcopy(complete)
        rows = sparse["changeWalkthrough"]["groups"][2]["files"]
        described = rows[0]["path"]
        omitted = rows.pop()["path"]
        for row in rows:
            for field in ("changeType", "additions", "deletions", "diffUrl"):
                del row[field]
        diff = artifact_diff_files(complete)
        expanded = self.validate_input(sparse, diff)
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(flowctl, "_pr_aid_live_diff_files", return_value=diff):
            path = Path(tmp) / "input.json"
            for value, expected in ((sparse, expanded), (complete, complete)):
                path.write_text(json.dumps(value), encoding="utf-8")
                args = argparse.Namespace(file=str(path), json=True)
                output = StringIO()
                with redirect_stdout(output):
                    flowctl.cmd_pr_cognitive_aid_validate(args)
                self.assertEqual(json.loads(output.getvalue())["artifact"], expected)
                output = StringIO()
                with redirect_stdout(output):
                    flowctl.cmd_pr_cognitive_aid_render(args)
                self.assertEqual(output.getvalue().encode("utf-8"),
                                 flowctl.render_pr_cognitive_aid_markdown(expected).encode("utf-8"))
                if value is sparse:
                    self.assertIn(described, output.getvalue())
                    self.assertIn(omitted, output.getvalue())
                output = StringIO()
                with redirect_stdout(output):
                    flowctl.cmd_pr_cognitive_aid_html_input(args)
                payload = output.getvalue().split(">", 1)[1].split("</script>", 1)[0]
                self.assertEqual(json.loads(payload), expected)

    def test_file_commands_report_parse_errors_as_human_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            for command in (flowctl.cmd_pr_cognitive_aid_render,
                            flowctl.cmd_pr_cognitive_aid_html_input):
                with self.subTest(command=command.__name__):
                    out, err = StringIO(), StringIO()
                    with redirect_stdout(out), redirect_stderr(err), \
                         self.assertRaises(SystemExit) as raised:
                        command(argparse.Namespace(file=str(path)))
                    self.assertEqual(raised.exception.code, 2)
                    self.assertEqual(out.getvalue(), "")
                    self.assertIn("invalid JSON", err.getvalue())
                    self.assertFalse(err.getvalue().lstrip().startswith("{"))

    def test_optional_link_absent_without_identity_or_bound_diff(self):
        for remote, diff_available in (("", True), ("/local/repo", True),
                                       ("git@example.test:acme/repo.git", False)):
            with self.subTest(remote=remote, diff=diff_available):
                value = self.complete()
                row = value["changeWalkthrough"]["groups"][2]["files"][0]
                del row["diffUrl"]
                diff = artifact_diff_files(value) if diff_available else None
                with mock.patch.object(flowctl, "_export_run_git", return_value=(0, remote, "")):
                    expanded = self.validate_input(value, diff)
                self.assertNotIn("diffUrl", expanded["changeWalkthrough"]["groups"][2]["files"][0])
                self.assertEqual(expanded, value)

    def test_derived_link_encodes_path_and_binds_head_for_remote_forms(self):
        for remote in ("https://example.test/acme/repo.git",
                       "ssh://git@example.test/acme/repo.git",
                       "git@example.test:acme/repo.git"):
            with self.subTest(remote=remote):
                value = self.complete()
                row = value["changeWalkthrough"]["groups"][2]["files"][0]
                row["path"] = "src/a #()[].py"
                del row["diffUrl"]
                with mock.patch.object(flowctl, "_export_run_git", return_value=(0, remote, "")):
                    result = self.validate_input(value, artifact_diff_files(value))
                self.assertEqual(result["changeWalkthrough"]["groups"][2]["files"][0]["diffUrl"],
                                 f"/acme/repo/blob/{HEAD_SHA}/src/a%20%23%28%29%5B%5D.py")

    def test_empty_summary_round_trips_without_semantic_grounding(self):
        value = self.complete()
        row = value["changeWalkthrough"]["groups"][2]["files"][0]
        row.update(summary="", sourceRefs=["diff"], rIds=[], taskIds=[])
        diff = artifact_diff_files(value)
        self.assertEqual(self.validate_input(value, diff), value)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(Path(tmp), value, diff)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(self.validate_input(stored, diff), value)

    def test_r1_omitted_mechanics_validate_and_write_for_all_git_statuses(self):
        for status in ("added", "modified", "deleted", "copied", "renamed"):
            for field in ("additions", "deletions", "changeType", "diffUrl", "all"):
                with self.subTest(status=status, field=field):
                    complete = self.complete()
                    row = complete["changeWalkthrough"]["groups"][2]["files"][0]
                    row.update(changeType=status, additions=20, deletions=20)
                    sparse = copy.deepcopy(complete)
                    row = sparse["changeWalkthrough"]["groups"][2]["files"][0]
                    for key in (("additions", "deletions", "changeType", "diffUrl")
                                if field == "all" else (field,)):
                        del row[key]
                    before = copy.deepcopy(sparse)
                    diff = artifact_diff_files(complete)
                    self.assertEqual(self.validate_input(sparse, diff), complete)
                    with tempfile.TemporaryDirectory() as tmp:
                        path = self.write(Path(tmp), sparse, diff)
                        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), complete)
                    self.assertEqual(sparse, before)

    def test_r1_missing_metadata_names_row_and_underivable_field(self):
        for field in ("changeType", "additions", "deletions"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                value = self.complete()
                del value["changeWalkthrough"]["groups"][2]["files"][0][field]
                with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError,
                                            rf"groups\[2\].files\[0\].{field}"):
                    self.write(Path(tmp), value, None)
                self.assertEqual(list(Path(tmp).rglob("*.json")), [])

    def test_r1_supplied_mismatch_is_not_overwritten(self):
        for field, wrong in (("changeType", "copied"), ("additions", 99), ("deletions", 99)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                value = self.complete()
                diff = artifact_diff_files(value)
                value["changeWalkthrough"]["groups"][2]["files"][0][field] = wrong
                with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, "bound Git diff"):
                    self.write(Path(tmp), value, diff)

    def test_r2_complete_and_sparse_write_identical_v1_bytes_and_paths(self):
        complete = self.complete()
        # Authored safe links remain valid even when they differ from the default.
        complete["changeWalkthrough"]["groups"][2]["files"][0]["diffUrl"] = "https://example.test/diff"
        sparse = copy.deepcopy(complete)
        row = sparse["changeWalkthrough"]["groups"][2]["files"][0]
        for field in ("additions", "deletions", "changeType", "sourceRefs", "rIds", "taskIds"):
            del row[field]
        diff = artifact_diff_files(complete)
        self.assertEqual(self.validate_input(complete, diff), complete)
        with tempfile.TemporaryDirectory() as tmp:
            first_root, second_root = Path(tmp) / "complete", Path(tmp) / "sparse"
            first = self.write(first_root, complete, diff)
            second = self.write(second_root, sparse, diff)
            expected = Path("artifacts") / SPEC_ID / "pr-cognitive-aid/aid-001.json"
            self.assertEqual(first.relative_to(first_root), expected)
            self.assertEqual(second.relative_to(second_root), expected)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(second.read_text(encoding="utf-8"))["schemaVersion"], 1)

    def test_r4_unlisted_paths_expand_without_claims_and_store_like_complete(self):
        patterns = {
            ".flow/tasks/fn-1.1.json": "mechanical",
            ".flow/specs/fn-1.json": "mechanical",
            "packages/app/pnpm-lock.yaml": "mechanical",
            "plugins/flow-next/codex/skills/example.md": "generated",
            "src/forgotten.py": "canonical",
            ".flow/specs/fn-1.md": "canonical",
            ".flow/tasks/fn-1.1.md": "canonical",
            ".flow/memory/decision.md": "canonical",
            "src/generated/handwritten.py": "canonical",
            "dist/handwritten.py": "canonical",
            "custom.lock": "canonical",
        }
        sparse = self.complete()
        diff = artifact_diff_files(sparse)
        diff.update({path: ("added", 1, 0) for path in patterns})
        complete = copy.deepcopy(sparse)
        files = complete["changeWalkthrough"]["groups"][2]["files"]
        for path in sorted(patterns):
            files.append({
                "path": path, "summary": "", "attentionClass": patterns[path],
                "changeType": "added", "additions": 1, "deletions": 0,
                "diffUrl": f"/acme/repo/blob/{HEAD_SHA}/{path}",
                "sourceRefs": ["diff"], "rIds": [], "taskIds": [],
            })
        before = copy.deepcopy(sparse)
        self.assertEqual(self.validate_input(sparse, diff), complete)
        self.assertEqual(self.validate_input(sparse, dict(reversed(list(diff.items())))), complete)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.write(root / "sparse", sparse, diff)
            second = self.write(root / "complete", complete, diff)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            stored = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(flowctl.validate_pr_cognitive_aid(stored), complete)
        self.assertEqual(sparse, before)

    def test_r4_seven_steps_keep_group_identity_and_file_bounds(self):
        golden = Path(__file__).parent / "fixtures/pr-cognitive-aid/v1/golden.json"
        for fill_last_step in (False, True):
            with self.subTest(fill_last_step=fill_last_step):
                value = json.loads(golden.read_text(encoding="utf-8"))
                groups = value["changeWalkthrough"]["groups"]
                step_indexes = [i for i, g in enumerate(groups) if g["kind"] == "step"]
                self.assertEqual(len(step_indexes), 7)
                last_step = groups[step_indexes[-1]]
                if fill_last_step:
                    for group in groups[2:step_indexes[-1]]:
                        while group["files"] and len(last_step["files"]) < 200:
                            last_step["files"].append(group["files"].pop())
                    self.assertEqual(len(last_step["files"]), 200)
                # The fixture already has 500 paths. Omit a row, keeping its
                # diff entry, rather than exceeding the v1 file limit.
                diff = artifact_diff_files(value)
                donor = next(g for g in groups[2:step_indexes[-1]] if g["files"])
                omitted = donor["files"].pop(0)["path"]
                result = self.validate_input(value, diff)
                expanded = result["changeWalkthrough"]["groups"]
                self.assertEqual(len(expanded), len(groups))
                target = step_indexes[-2] if fill_last_step else step_indexes[-1]
                self.assertEqual(expanded[target]["files"][-1]["path"], omitted)
                for old, new in zip(groups, expanded, strict=True):
                    self.assertEqual({k: v for k, v in old.items() if k != "files"},
                                     {k: v for k, v in new.items() if k != "files"})
                    self.assertEqual(new["files"][:len(old["files"])], old["files"])
                    self.assertLessEqual(len(new["files"]), 200)

    def test_r4_authored_pattern_defaults_and_explicit_classes(self):
        for path, default in ((".flow/tasks/fn-1.1.json", "mechanical"),
                              ("yarn.lock", "mechanical"),
                              ("plugins/flow-next/codex/generated.md", "generated")):
            for explicit in (None, "canonical", "mechanical", "generated"):
                with self.subTest(path=path, explicit=explicit):
                    value = self.complete()
                    row = value["changeWalkthrough"]["groups"][2]["files"][0]
                    row["path"] = "nested/" + path if path == "yarn.lock" else path
                    # Avoid the other fixture row's generated path.
                    row["path"] = row["path"].replace("generated.md", "other.md")
                    if explicit is None:
                        del row["attentionClass"]
                    else:
                        row["attentionClass"] = explicit
                    result = self.validate_input(value, artifact_diff_files(value))
                    self.assertEqual(result["changeWalkthrough"]["groups"][2]["files"][0]
                                     ["attentionClass"], explicit or default)

    def test_r4_unknown_pattern_requires_authored_attention(self):
        value = self.complete()
        del value["changeWalkthrough"]["groups"][2]["files"][0]["attentionClass"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError,
                                        r"groups\[2\].files\[0\].*attentionClass"):
                self.write(Path(tmp), value, artifact_diff_files(value))

    def test_r4_authored_path_outside_diff_stays_rejected(self):
        value = self.complete()
        diff = artifact_diff_files(value)
        del diff[value["changeWalkthrough"]["groups"][2]["files"][0]["path"]]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError,
                                        r"groups\[2\].files\[0\].path:.*bound Git diff"):
                self.write(Path(tmp), value, diff)

    def test_r5_inherits_each_omitted_reference_field_and_preserves_overrides(self):
        for field in ("sourceRefs", "rIds", "taskIds", "all"):
            with self.subTest(field=field):
                complete = self.complete()
                sparse = copy.deepcopy(complete)
                row = sparse["changeWalkthrough"]["groups"][2]["files"][0]
                for key in (("sourceRefs", "rIds", "taskIds") if field == "all" else (field,)):
                    del row[key]
                # The other rows explicitly override with diff-only refs and empty IDs.
                self.assertEqual(self.validate_input(sparse, artifact_diff_files(complete)), complete)

    def test_r5_ungrounded_summary_and_unknown_references_remain_rejected(self):
        for field, wrong in (("sourceRefs", []), ("sourceRefs", ["unknown"]),
                             ("rIds", ["R999"]), ("taskIds", [f"{SPEC_ID}.999"])):
            with self.subTest(field=field, wrong=wrong), tempfile.TemporaryDirectory() as tmp:
                value = self.complete()
                value["changeWalkthrough"]["groups"][2]["files"][0][field] = wrong
                with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError,
                                            rf"groups\[2\].files\[0\].{field}"):
                    self.write(Path(tmp), value, artifact_diff_files(value))

    def test_r5_group_without_references_cannot_ground_a_row(self):
        value = self.complete()
        group = value["changeWalkthrough"]["groups"][2]
        group["sourceRefs"] = []
        del group["files"][0]["sourceRefs"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, "sourceRefs"):
                self.write(Path(tmp), value, artifact_diff_files(value))


if __name__ == "__main__":
    unittest.main()

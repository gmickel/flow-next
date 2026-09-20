"""Sparse aid input expands at validate/write boundaries; stored v1 stays strict."""

import argparse
import copy
import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from test_pr_cognitive_aid import (
    BASE_SHA, HEAD_SHA, SPEC_ID, artifact, artifact_diff_files, flowctl,
)


class SparseInputTests(unittest.TestCase):
    def complete(self):
        value = artifact(canonical_files=1)
        group = value["changeWalkthrough"]["groups"][2]
        group["sourceRefs"] = ["diff", "task", "rid"]
        for row in group["files"]:
            row["diffUrl"] = "#diff-" + hashlib.sha256(
                row["path"].encode("utf-8")
            ).hexdigest()
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

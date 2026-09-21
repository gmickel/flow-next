"""Additive v1 briefing fields survive every aid input boundary."""

import argparse
import copy
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import flowctl
from test_pr_cognitive_aid import BASE_SHA, HEAD_SHA, SPEC_ID, artifact, artifact_diff_files


FIELDS = {
    "userImpact": "Operators can inspect the change before opening a review.",
    "blastRadius": "Touches local review artifacts only.",
    "tradeoffs": "Keep authored context in one artifact for all consumers.",
    "openItems": "Live forge verification remains unfinished.",
}


class AuthoredFieldTests(unittest.TestCase):
    def test_optional_fields_round_trip_through_all_four_entry_points(self):
        variants = [{}, *({key: value} for key, value in FIELDS.items()), FIELDS,
                    {field: "" for field in FIELDS}]
        for fields, outcomes in ((fields, outcomes) for fields in variants
                                 for outcomes in (False, True)):
            for sparse in (False, True):
                with self.subTest(fields=fields, outcomes=outcomes, sparse=sparse), \
                     tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    value = artifact()
                    value["changeWalkthrough"].update(copy.deepcopy(fields))
                    original_cell = value["changeWalkthrough"]["proof"][0]
                    if outcomes:
                        value["changeWalkthrough"]["proof"].extend(
                            dict(original_cell, outcome=outcome)
                            for outcome in ("pass", "fail", "unverified")
                        )
                    expected = copy.deepcopy(value)
                    diff = artifact_diff_files(value)
                    if sparse:
                        for group in value["changeWalkthrough"]["groups"]:
                            for row in group["files"]:
                                for field in ("changeType", "additions", "deletions"):
                                    del row[field]
                    path = root / "input.json"
                    path.write_text(json.dumps(value), encoding="utf-8")
                    args = argparse.Namespace(file=str(path), json=True, id=SPEC_ID,
                                              base_sha=BASE_SHA, head_sha=HEAD_SHA)
                    with mock.patch.object(flowctl, "get_repo_root", return_value=root), \
                         mock.patch.object(flowctl, "get_flow_dir", return_value=root / ".flow"), \
                         mock.patch.object(flowctl, "resolve_spec_id_arg", return_value=SPEC_ID), \
                         mock.patch.object(flowctl, "_export_run_git", return_value=(1, "", "")), \
                         mock.patch.object(flowctl, "_pr_aid_live_diff_files", return_value=diff):
                        output = StringIO()
                        with redirect_stdout(output):
                            flowctl.cmd_pr_cognitive_aid_validate(args)
                        self.assertEqual(json.loads(output.getvalue())["artifact"], expected)

                        output = StringIO()
                        with redirect_stdout(output):
                            flowctl.cmd_pr_cognitive_aid_write(args)
                        stored_path = Path(json.loads(output.getvalue())["path"])
                        self.assertEqual(stored_path.relative_to(root), Path(
                            f".flow/artifacts/{SPEC_ID}/pr-cognitive-aid/aid-001.json"))
                        stored = json.loads(stored_path.read_text(encoding="utf-8"))
                        self.assertEqual(stored, expected)
                        self.assertEqual(stored["schemaVersion"], 1)

                        with mock.patch.object(flowctl, "render_pr_cognitive_aid_markdown",
                                               return_value="rendered\n") as render, \
                             redirect_stdout(StringIO()):
                            flowctl.cmd_pr_cognitive_aid_render(args)
                        render.assert_called_once_with(expected)

                        output = StringIO()
                        with redirect_stdout(output):
                            flowctl.cmd_pr_cognitive_aid_html_input(args)
                        carrier = output.getvalue().split(">", 1)[1].split("</script>", 1)[0]
                        self.assertEqual(json.loads(carrier), expected)

    def test_wrong_types_name_each_authored_field(self):
        for field in FIELDS:
            wrong_values = [None, False, 42, {}, [], ["text"]]
            for wrong in wrong_values:
                with self.subTest(field=field, wrong=wrong):
                    value = artifact()
                    value["changeWalkthrough"][field] = wrong
                    with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                        flowctl.validate_pr_cognitive_aid(value)
                    self.assertEqual(str(raised.exception),
                                     f"changeWalkthrough.{field}: must be a string")

    def test_invalid_outcome_names_the_proof_cell(self):
        for wrong in (None, False, 42, {}, [], "", "PASS", "failed", "unknown"):
            for index in (0, 1):
                with self.subTest(outcome=wrong, index=index):
                    value = artifact()
                    proof = value["changeWalkthrough"]["proof"]
                    proof[:] = [copy.deepcopy(proof[0]) for _ in range(2)]
                    proof[index]["outcome"] = wrong
                    with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                        flowctl.validate_pr_cognitive_aid(value)
                    message = (
                        "unsupported proof outcome"
                        if isinstance(wrong, str) and wrong
                        else "must not be empty" if wrong == ""
                        else "must be a string"
                    )
                    self.assertEqual(str(raised.exception),
                                     f"changeWalkthrough.proof[{index}].outcome: {message}")

    def test_unknown_fields_remain_rejected(self):
        for location, field, content in (
            ("root", "unknownAuthoredField", "text"),
            ("changeWalkthrough", "unknownAuthoredField", "text"),
            ("changeWalkthrough", "unverifiedSteps", ["Not run"]),
        ):
            with self.subTest(location=location, field=field):
                value = artifact()
                target = value if location == "root" else value[location]
                target[field] = content
                with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                    flowctl.validate_pr_cognitive_aid(value)
                prefix = "pr_cognitive_aid" if location == "root" else location
                self.assertEqual(str(raised.exception),
                                 f"{prefix}: unknown fields: {field}")


if __name__ == "__main__":
    unittest.main()

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
    "unverifiedSteps": ["Live forge smoke: no credentials available."],
}


class AuthoredFieldTests(unittest.TestCase):
    def test_optional_fields_round_trip_through_all_four_entry_points(self):
        variants = [{}, *({key: value} for key, value in FIELDS.items()), FIELDS,
                    {"userImpact": "", "blastRadius": "", "unverifiedSteps": []}]
        for fields in variants:
            for sparse in (False, True):
                with self.subTest(fields=fields, sparse=sparse), \
                     tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    value = artifact()
                    value["changeWalkthrough"].update(copy.deepcopy(fields))
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
            wrong_values = [None, False, 42, {}]
            wrong_values += [[], ["text"]] if field != "unverifiedSteps" else ["text"]
            for wrong in wrong_values:
                with self.subTest(field=field, wrong=wrong):
                    value = artifact()
                    value["changeWalkthrough"][field] = wrong
                    with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                        flowctl.validate_pr_cognitive_aid(value)
                    expected_type = "an array" if field == "unverifiedSteps" else "a string"
                    self.assertEqual(str(raised.exception),
                                     f"changeWalkthrough.{field}: must be {expected_type}")
        for wrong in (None, False, 42, {}, []):
            with self.subTest(item=wrong):
                value = artifact()
                value["changeWalkthrough"]["unverifiedSteps"] = [wrong]
                with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                    flowctl.validate_pr_cognitive_aid(value)
                self.assertEqual(str(raised.exception),
                                 "changeWalkthrough.unverifiedSteps[0]: must be a string")

    def test_unknown_fields_remain_rejected(self):
        for location in ("root", "changeWalkthrough"):
            with self.subTest(location=location):
                value = artifact()
                target = value if location == "root" else value[location]
                target["unknownAuthoredField"] = "text"
                with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                    flowctl.validate_pr_cognitive_aid(value)
                prefix = "pr_cognitive_aid" if location == "root" else location
                self.assertEqual(str(raised.exception),
                                 f"{prefix}: unknown fields: unknownAuthoredField")


if __name__ == "__main__":
    unittest.main()

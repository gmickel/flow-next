"""R3: one validation reports independent errors without dependent cascades."""

import argparse
import copy
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from test_pr_cognitive_aid import BASE_SHA, HEAD_SHA, SPEC_ID, artifact, artifact_diff_files, flowctl


class AllViolationsTests(unittest.TestCase):
    def cli_errors(self, value, diff, *, as_json, command="validate", raw=None):
        stdout, stderr = StringIO(), StringIO()
        args = argparse.Namespace(file="unused.json", json=as_json, id=SPEC_ID,
                                  base_sha=BASE_SHA, head_sha=HEAD_SHA)
        # Exercise the actual reader, including malformed JSON, without disk I/O.
        payload = raw if raw is not None else json.dumps(value).encode("utf-8")
        with mock.patch.object(Path, "open", mock.mock_open(read_data=payload)), \
             mock.patch.object(flowctl, "get_repo_root", return_value=Path.cwd()), \
             mock.patch.object(flowctl, "get_flow_dir", return_value=Path.cwd() / ".flow/tmp"), \
             mock.patch.object(flowctl, "resolve_spec_id_arg", return_value=SPEC_ID), \
             mock.patch.object(flowctl, "_pr_aid_live_diff_files", return_value=diff), \
             mock.patch.object(flowctl, "atomic_create") as publish, \
             redirect_stdout(stdout), redirect_stderr(stderr), \
             self.assertRaises(SystemExit) as raised:
            getattr(flowctl, f"cmd_pr_cognitive_aid_{command}")(args)
        self.assertEqual(raised.exception.code, 2)
        publish.assert_not_called()
        if as_json:
            self.assertEqual(stderr.getvalue(), "")
            result = json.loads(stdout.getvalue())
            self.assertFalse(result["success"])
            return result["error"].splitlines()
        self.assertEqual(stdout.getvalue(), "")
        self.assertTrue(stderr.getvalue().startswith("Error: "))
        return stderr.getvalue().removeprefix("Error: ").splitlines()

    def test_all_independent_schema_and_expansion_errors_are_stable(self):
        value = artifact()
        diff = artifact_diff_files(value)
        value["schemaVersion"] = 2
        value["generatedAt"] = "bad timestamp"
        value["sources"][0]["kind"] = "unknown"
        walk = value["changeWalkthrough"]
        walk["thesis"] = ""
        walk["proof"][0]["label"] = ""
        walk["proof"][0]["value"] = ""
        rows = walk["groups"][2]["files"]
        rows[0]["attentionClass"] = "unknown"
        rows[0]["sourceRefs"] = ["missing-1", "missing-2"]
        rows[1]["path"] = "outside.py"
        del rows[1]["changeType"]
        del rows[1]["additions"]
        rows[2]["summary"] = ""
        expected = {
            "schemaVersion", "generatedAt", "sources[0].kind", "changeWalkthrough.thesis",
            "changeWalkthrough.proof[0].label", "changeWalkthrough.proof[0].value",
            "changeWalkthrough.groups[2].files[0].attentionClass",
            "changeWalkthrough.groups[2].files[0].sourceRefs[0]",
            "changeWalkthrough.groups[2].files[0].sourceRefs[1]",
            "changeWalkthrough.groups[2].files[1].path",
            "changeWalkthrough.groups[2].files[2].summary",
        }
        baseline = None
        for command in ("validate", "write"):
            for as_json in (False, True):
                for _ in range(2):
                    with self.subTest(command=command, as_json=as_json):
                        errors = self.cli_errors(value, diff, as_json=as_json, command=command)
                        self.assertEqual({e.split(": ", 1)[0] for e in errors}, expected)
                        self.assertEqual(len(errors), len(expected))
                        if baseline is None:
                            baseline = errors
                        self.assertEqual(errors, baseline)

    def test_parse_error_is_the_only_error_in_both_formats(self):
        for command in ("validate", "write"):
            for as_json in (False, True):
                with self.subTest(command=command, as_json=as_json):
                    errors = self.cli_errors(None, {}, as_json=as_json, command=command, raw=b'{"broken":')
                    self.assertEqual(len(errors), 1)
                    self.assertIn("invalid JSON", errors[0])

    def test_pathless_row_is_reported_once_and_other_rows_still_checked(self):
        for path_value in (None, "", [], "../bad"):
            for command in ("validate", "write"):
                for as_json in (False, True):
                    with self.subTest(path=path_value, command=command, as_json=as_json):
                        value = artifact()
                        diff = artifact_diff_files(value)
                        rows = value["changeWalkthrough"]["groups"][2]["files"]
                        rows[0] = {} if path_value is None else {"path": path_value}
                        rows[1]["summary"] = ""
                        errors = self.cli_errors(value, diff, as_json=as_json, command=command)
                        self.assertEqual([e.split(": ", 1)[0] for e in errors], [
                            "changeWalkthrough.groups[2].files[0].path",
                            "changeWalkthrough.groups[2].files[1].summary",
                        ])

    def test_invalid_containers_and_bindings_do_not_hide_independent_errors(self):
        cases = (
            ({"baseSha": "bad", "headSha": "bad"}, {"baseSha", "headSha"}),
            ({"sources": None, "generatedAt": "bad"}, {"sources", "generatedAt"}),
            ({"changeWalkthrough": [], "artifactId": ""}, {"changeWalkthrough", "artifactId"}),
        )
        for updates, expected in cases:
            for as_json in (False, True):
                with self.subTest(updates=updates, as_json=as_json):
                    value = artifact()
                    diff = artifact_diff_files(value)
                    value.update(updates)
                    errors = self.cli_errors(value, diff, as_json=as_json)
                    self.assertEqual({e.split(": ", 1)[0] for e in errors}, expected)
                    self.assertEqual(len(errors), len(expected))

    def test_oversized_arrays_still_report_independent_child_errors(self):
        for container, count, field in (("proof", 17, "label"), ("files", 201, "summary")):
            with self.subTest(container=container):
                value = artifact()
                walk = value["changeWalkthrough"]
                owner = walk if container == "proof" else walk["groups"][2]
                rows = [copy.deepcopy(owner[container][0]) for _ in range(count)]
                if container == "files":
                    for index, row in enumerate(rows):
                        row["path"] = f"file-{index}.py"
                for row in rows[:2]:
                    row[field] = ""
                owner[container] = rows
                path = "changeWalkthrough.proof" if container == "proof" else "changeWalkthrough.groups[2].files"
                with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
                    flowctl.validate_pr_cognitive_aid(value)
                self.assertEqual([error.split(": ", 1)[0] for error in str(raised.exception).splitlines()], [
                    path, f"{path}[0].{field}", f"{path}[1].{field}",
                ])

    def test_underivable_fields_accumulate_with_schema_errors_without_mutation(self):
        value = artifact()
        rows = value["changeWalkthrough"]["groups"][2]["files"]
        for row in rows[:2]:
            for field in ("changeType", "additions", "deletions"):
                del row[field]
        value["changeWalkthrough"]["thesis"] = ""
        original = copy.deepcopy(value)
        with self.assertRaises(flowctl.PrCognitiveAidValidationError) as raised:
            flowctl.write_pr_cognitive_aid(Path.cwd() / ".flow/tmp", value,
                spec_id=SPEC_ID, base_sha=BASE_SHA, head_sha=HEAD_SHA)
        errors = str(raised.exception).splitlines()
        self.assertEqual(len(errors), 7)
        self.assertEqual(sum("cannot derive omitted field" in e for e in errors), 6)
        self.assertIn("changeWalkthrough.thesis", errors[-1])
        self.assertEqual(value, original)


if __name__ == "__main__":
    unittest.main()

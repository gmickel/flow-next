"""R7: make-pr resolves sparse-written generations before composing again.

Complete-input chain behavior stays in PersistenceAndCurrentnessTests:
 test_immutable_generations_form_a_materialized_supersedes_chain,
 test_newer_stale_chain_tip_invalidates_older_matching_generation, and
 test_invalid_or_unsupported_home_never_projects_current_data.
These cases exercise the CLI current seam specifically after sparse expansion.
"""

import argparse
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


class ReuseTests(unittest.TestCase):
    def test_current_resolves_sparse_written_generation(self) -> None:
        cases = (("unchanged", "current"), ("moved_head", "stale"),
                 ("missing", "absent"), ("invalid_diff", "invalid"))
        for case, status in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                flow_dir = Path(tmp) / ".flow"
                value = artifact()
                expected = artifact_diff_files(value)
                group = value["changeWalkthrough"]["groups"][2]
                group["sourceRefs"].append("diff")
                # Keep one authored row; flowctl supplies the other diff paths.
                group["files"] = group["files"][:1]
                row = group["files"][0]
                for field in ("changeType", "additions", "deletions", "diffUrl",
                              "sourceRefs", "rIds", "taskIds"):
                    del row[field]
                path = flowctl.write_pr_cognitive_aid(
                    flow_dir, value, spec_id=SPEC_ID, base_sha=BASE_SHA,
                    head_sha=HEAD_SHA, expected_diff_files=expected,
                )
                stored_text = path.read_text(encoding="utf-8")
                stored = json.loads(stored_text)
                rows = {item["path"]: item
                        for g in stored["changeWalkthrough"]["groups"]
                        for item in g["files"]}
                self.assertEqual(set(rows), set(expected))
                authored = rows[row["path"]]
                for field in ("sourceRefs", "rIds", "taskIds"):
                    self.assertEqual(authored[field], group[field])
                for name, item in rows.items():
                    self.assertEqual((item["changeType"], item["additions"],
                                      item["deletions"]), expected[name])
                    self.assertTrue(item["diffUrl"])
                    if name != row["path"]:
                        self.assertEqual(item["summary"], "")

                head = "c" * 40 if case == "moved_head" else HEAD_SHA
                if case == "invalid_diff":
                    change, additions, deletions = expected[row["path"]]
                    expected[row["path"]] = (change, additions + 1, deletions)
                args = argparse.Namespace(id=SPEC_ID, json=True,
                                          base_sha=BASE_SHA, head_sha=head)
                output = StringIO()
                # A separate empty artifact home models another clone.
                current_home = Path(tmp) / "empty" if case == "missing" else flow_dir
                with (
                    mock.patch.object(flowctl, "get_flow_dir", return_value=current_home),
                    mock.patch.object(flowctl, "get_repo_root", return_value=Path(tmp)),
                    mock.patch.object(flowctl, "resolve_spec_id_arg", return_value=SPEC_ID),
                    mock.patch.object(flowctl, "_pr_aid_live_diff_files", return_value=expected),
                    redirect_stdout(output),
                ):
                    flowctl.cmd_pr_cognitive_aid_current(args)
                selected = json.loads(output.getvalue())
                self.assertEqual(selected["status"], status)
                self.assertEqual(selected["artifact"], stored if status == "current" else None)
                self.assertEqual(path.read_text(encoding="utf-8"), stored_text)
                self.assertEqual(list(path.parent.glob("*.json")), [path])


if __name__ == "__main__":
    unittest.main()

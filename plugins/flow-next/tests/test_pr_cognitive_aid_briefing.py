"""Single artifact-only markdown briefing (fn-252 R1-R6, R8)."""

import copy
import json
import re
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import flowctl
from test_pr_cognitive_aid import GOLDEN, artifact


HEADINGS = ["Why", "What changes for a user or operator", "Scope", "Blast radius",
            "Verification", "Tradeoffs", "Open items"]


def full_artifact():
    value = artifact(canonical_files=2)
    value["changeWalkthrough"].update({
        "userImpact": "Reviewers can see what changed.",
        "blastRadius": "Only the markdown briefing changes.",
        "tradeoffs": "Keep full provenance in the stored artifact.",
        "openItems": "The live forge check remains unverified.",
        "proof": [{"label": "Focused tests", "value": "Passed locally", "outcome": "pass",
                   "sourceRefs": ["task"]}],
    })
    return value


class BriefingTests(unittest.TestCase):
    def test_one_deterministic_form_across_former_size_boundaries(self):
        for count, churn in ((2, 20), (2, 200), (6, 1)):
            value = artifact(canonical_files=count, churn=churn)
            before = copy.deepcopy(value)
            with self.subTest(count=count, churn=churn), \
                 mock.patch.object(flowctl, "get_flow_dir", side_effect=AssertionError("live state")):
                text = flowctl.render_pr_cognitive_aid_markdown(value)
                self.assertEqual(text, flowctl.render_pr_cognitive_aid_markdown(value))
                self.assertEqual(value, before)
                self.assertIn("## Scope\n", text)
                self.assertEqual(text.count("```diff"), 1)
                self.assertNotIn("<details", text)
                self.assertNotIn("Legend", text)

    def test_invalid_artifact_produces_no_partial_body(self):
        value = artifact()
        value["schemaVersion"] = 2
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(flowctl.PrCognitiveAidValidationError):
            flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertEqual(output.getvalue(), "")

    def test_seven_sections_in_order_and_legacy_omission(self):
        for value, headings in ((full_artifact(), HEADINGS),
                                (artifact(), ["Why", "Scope", "Verification"])):
            with self.subTest(headings=headings):
                text = flowctl.render_pr_cognitive_aid_markdown(value)
                self.assertEqual(re.findall(r"^## (.+)$", text, re.M), headings)
        value = full_artifact()
        for key in ("userImpact", "blastRadius", "tradeoffs", "openItems"):
            value["changeWalkthrough"][key] = " \n\t"
        self.assertEqual(re.findall(r"^## (.+)$", flowctl.render_pr_cognitive_aid_markdown(value), re.M),
                         ["Why", "Scope", "Verification"])

    def test_thesis_only_has_only_why(self):
        value = artifact()
        value["sources"] = [s for s in value["sources"] if s["kind"] != "rid"]
        group = value["changeWalkthrough"]["groups"][2]
        group.update(files=[], sourceRefs=["task"], rIds=[])
        value["changeWalkthrough"].update(groups=[group], proof=[])
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertEqual(re.findall(r"^## (.+)$", text, re.M), ["Why"])
        self.assertNotIn("Coverage:", text)

    def test_scope_trees_purpose_requirement_and_honest_remaining_counts(self):
        value = artifact()
        files = value["changeWalkthrough"]["groups"][2]["files"]
        files[1]["summary"] = ""
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn(" └── src/change_0.py — Implements bounded behavior 0. [R6]", text)
        self.assertIn("1 mechanical file; 1 generated file; 1 not described file", text)
        self.assertNotIn("src/change_1.py", text)
        self.assertIn("**1. Validate and render**", text)
        self.assertIn("Coverage: R6 → 1\n", text)
        self.assertNotIn("| Requirement |", text)
        files[0]["summary"] = ""
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("**1. Validate and render**\n\n", text)
        self.assertIn("2 not described files", text)
        self.assertNotIn("├──", text)

    def test_uncovered_and_undeclared_requirements_have_table(self):
        value = artifact()
        value["sources"].append({"id": "uncovered", "kind": "rid", "ref": "R9"})
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("R9 → uncovered", text)
        self.assertIn("| R9 | unevidenced |", text)
        value["sources"] = [s for s in value["sources"] if s["kind"] != "rid"]
        for group in value["changeWalkthrough"]["groups"]:
            for record in [group, *group["files"]]:
                record["rIds"] = []
                record["sourceRefs"] = [ref for ref in record["sourceRefs"] if ref != "rid"]
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("Coverage: requirements undeclared", text)
        self.assertIn("| Undeclared |", text)
        self.assertIn("[requirement undeclared]", text)

    def test_proof_outcomes_are_structural_and_old_cells_are_plain(self):
        value = artifact()
        proof = [{"label": f"Gate {i}", "value": f"Note {i}", "sourceRefs": ["task"],
                  **({"outcome": outcome} if outcome else {})}
                 for i, outcome in enumerate(("pass", "fail", "unverified", None))]
        value["changeWalkthrough"]["proof"] = proof
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("- [x] Gate 0: Note 0", text)
        self.assertIn("- [ ] fail: Gate 1: Note 1", text)
        self.assertIn("- [ ] unverified: Gate 2: Note 2", text)
        self.assertIn("\n- Gate 3: Note 3\n", text)
        self.assertEqual(text.count("[x]"), 1)
        value["changeWalkthrough"]["proof"] = []
        self.assertNotIn("## Verification", flowctl.render_pr_cognitive_aid_markdown(value))
        value["changeWalkthrough"]["proof"] = [dict(proof[0], outcome="maybe")]
        with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, r"proof\[0\].outcome"):
            flowctl.render_pr_cognitive_aid_markdown(value)

    def test_identity_is_one_comment_and_machine_rows_are_gone(self):
        value = artifact()
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        comments = re.findall(r"<!--.*?-->", text)
        self.assertEqual(comments, [f"<!-- artifact={value['artifactId']} base={value['baseSha']} head={value['headSha']} -->"])
        visible = re.sub(r"<!--.*?-->", "", text)
        for item in (value["artifactId"], value["baseSha"], value["headSha"],
                     "Human-review lines", "Canonical files", "Total files", "Evidence |",
                     "source:diff", "## Review plan", "Generated by", "flow-next:make-pr"):
            self.assertNotIn(item, visible)

    def test_budget_is_deterministic_and_counts_collapsed_files(self):
        for value in (artifact(canonical_files=150), json.loads(GOLDEN.read_text(encoding="utf-8")),
                      full_artifact()):
            with self.subTest(files=sum(len(g["files"]) for g in value["changeWalkthrough"]["groups"])):
                text = flowctl.render_pr_cognitive_aid_markdown(value)
                self.assertLessEqual(len(text.splitlines()), 40)
                self.assertEqual(text, flowctl.render_pr_cognitive_aid_markdown(value))
                self.assertIn("Coverage:", text)
                self.assertIn(value["changeWalkthrough"]["thesis"], text)
                shown = len(re.findall(r"^[ +-] [├└]── \S+ — ", text, re.M))
                counts = sum(int(n) for n in re.findall(r"(\d+) (?:mechanical|generated|not described|described) files?\b", text))
                self.assertEqual(shown + counts, sum(len(g["files"]) for g in value["changeWalkthrough"]["groups"]))
        text = flowctl.render_pr_cognitive_aid_markdown(artifact(canonical_files=150))
        self.assertIn("src/change_0.py", text)
        self.assertNotIn("src/change_149.py", text)

    def test_budget_reflows_short_thesis_without_removing_content(self):
        value = full_artifact()
        reasons = [f"Reason {i}." for i in range(35)]
        value["changeWalkthrough"]["thesis"] = "\n".join(reasons)
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertLessEqual(len(text.splitlines()), 40)
        why = text.split("## Why\n\n", 1)[1].split("\n\n## ", 1)[0]
        self.assertEqual(why, " ".join(reasons))
        self.assertIn("Coverage:", text)

    def test_over_budget_thesis_is_complete_and_other_content_is_counted(self):
        value = full_artifact()
        thesis = "\n".join(f"Reason {i}." for i in range(45))
        value["changeWalkthrough"]["thesis"] = thesis
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn(thesis, text)
        self.assertIn("Coverage:", text)
        self.assertIn("1 group collapsed: 1 mechanical file; 1 generated file; 2 described files", text)
        self.assertEqual(text.count("1 authored line collapsed"), 4)
        self.assertIn("Proof cells collapsed: 1 pass", text)
        self.assertNotIn("├──", text)

    def test_file_only_requirement_is_covered_without_table(self):
        value = artifact()
        value["sources"].append({"id": "file_rid", "kind": "rid", "ref": "R7"})
        record = value["changeWalkthrough"]["groups"][2]["files"][0]
        for citation in ({"rIds": ["R7", "R6"], "sourceRefs": ["file_rid", "rid", "diff", "task"]},
                         {"rIds": [], "sourceRefs": ["file_rid", "rid", "diff", "task"]}):
            record.update(citation)
            text = flowctl.render_pr_cognitive_aid_markdown(value)
            self.assertIn("R7 → 1", text)
            self.assertNotIn("| Requirement |", text)

    def test_setext_underlines_are_neutralized_in_each_authored_field(self):
        for key in ("thesis", "userImpact", "blastRadius", "tradeoffs", "openItems"):
            for underline in ("=", "-", "==  ", "--  "):
                with self.subTest(key=key, underline=underline):
                    value = artifact()
                    value["changeWalkthrough"][key] = "Forged heading\n" + underline
                    text = flowctl.render_pr_cognitive_aid_markdown(value)
                    self.assertNotIn("\n" + underline + "\n", text)
                    self.assertIn(f"&#{ord(underline[0])};", text)

    def test_tree_change_signs_and_last_row(self):
        value = artifact()
        group = value["changeWalkthrough"]["groups"][2]
        group["files"] = group["files"][:2]
        group["files"][0]["changeType"] = "added"
        group["files"][1]["changeType"] = "deleted"
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("+ ├── src/change_0.py", text)
        self.assertIn("- └── src/change_1.py", text)

    def test_undescribed_group_has_same_shape_in_each_position(self):
        value = artifact()
        group = value["changeWalkthrough"]["groups"][2]
        group["files"] = group["files"][-2:]
        other = copy.deepcopy(group)
        other["ordinal"] = group["ordinal"] + 1
        other["title"] = "Other"
        for record in other["files"]:
            record["path"] = "other/" + record["path"]
        value["changeWalkthrough"]["groups"] = [group, other]
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        for number, title in ((1, group["title"]), (2, "Other")):
            self.assertIn(f"**{number}. {title}**\n\n1 mechanical file; 1 generated file", text)
        self.assertNotIn("```", text)

    def test_table_escapes_pipe_in_group_title(self):
        value = artifact()
        group = value["changeWalkthrough"]["groups"][2]
        group.update(files=[], title="One | Two")
        value["changeWalkthrough"]["groups"] = [group]
        value["sources"].append({"id": "uncovered", "kind": "rid", "ref": "R9"})
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn(r"| R6 | One \| Two |", text)

    def test_reflow_precedes_collapse_and_preserves_warnings(self):
        value = artifact()
        walk = value["changeWalkthrough"]
        walk["thesis"] = "\n".join(f"Reason {i}." for i in range(26))
        walk["openItems"] = "Investigate the failure."
        walk["proof"] = [{"label": "Gate", "value": "Broken", "outcome": "fail",
                          "sourceRefs": ["task"]}]
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("- [ ] fail: Gate: Broken", text)
        self.assertIn(walk["openItems"], text)
        self.assertLessEqual(len(text.splitlines()), 40)

    def test_proof_collapse_order_and_minimum_needed(self):
        value = full_artifact()
        del value["changeWalkthrough"]["groups"][2]["files"][1]
        walk = value["changeWalkthrough"]
        walk["proof"] = [
            {"label": f"Gate {i}", "value": "Note", "sourceRefs": ["task"],
             **({"outcome": outcome} if outcome else {})}
            for i, outcome in enumerate(["fail", "unverified"] + ["pass"] * 5 + [None] * 5)
        ]
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("5 no outcome", text)
        self.assertIn("- [x] Gate 2", text)
        self.assertIn("- [ ] fail: Gate 0", text)
        self.assertIn("- [ ] unverified: Gate 1", text)
        self.assertIn("src/change_0.py", text)
        for key in ("userImpact", "blastRadius", "tradeoffs", "openItems"):
            self.assertIn(walk[key], text)
        self.assertLessEqual(len(text.splitlines()), 40)
        for index, line in enumerate(text.splitlines()):
            if line.startswith(("Proof cells collapsed:", "Coverage:")) or " files" in line:
                self.assertEqual(text.splitlines()[index - 1], "")

    def test_thesis_budget_threshold_includes_why_scaffolding(self):
        for length in range(25, 43):
            with self.subTest(length=length):
                value = full_artifact()
                thesis = "\n".join(f"Reason {i}." for i in range(length))
                value["changeWalkthrough"]["thesis"] = thesis
                text = flowctl.render_pr_cognitive_aid_markdown(value)
                self.assertEqual(text, flowctl.render_pr_cognitive_aid_markdown(value))
                if length + 4 <= 40:
                    self.assertLessEqual(len(text.splitlines()), 40)
                    self.assertIn(" ".join(thesis.splitlines()), text)
                else:
                    self.assertIn(thesis, text)
                    self.assertIn("1 group collapsed:", text)

    def test_partial_legacy_collapse_does_not_touch_pass_or_files(self):
        value = full_artifact()
        del value["changeWalkthrough"]["groups"][2]["files"][1]
        value["changeWalkthrough"]["proof"].extend(
            {"label": f"Legacy {i}", "value": "Note", "sourceRefs": ["task"]}
            for i in range(6)
        )
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("- [x] Focused tests", text)
        self.assertIn("- Legacy 0: Note", text)
        self.assertNotIn("- Legacy 5: Note", text)
        shown = len(re.findall(r"^- Legacy", text, re.M))
        self.assertIn(f"Proof cells collapsed: {6 - shown} no outcome", text)
        self.assertIn("src/change_0.py", text)
        self.assertEqual(len(text.splitlines()), 40)

    def test_file_rows_collapse_from_last_group_after_pass_cells(self):
        value = full_artifact()
        group = value["changeWalkthrough"]["groups"][2]
        other = copy.deepcopy(group)
        other["ordinal"] = group["ordinal"] + 1
        other["title"] = "Later group"
        for record in other["files"]:
            record["path"] = "later/" + record["path"]
        value["changeWalkthrough"]["groups"] = [group, other]
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("Proof cells collapsed: 1 pass", text)
        self.assertNotIn("later/src/change_1.py", text)
        self.assertIn("src/change_0.py", text)
        self.assertLessEqual(len(text.splitlines()), 40)

    def test_multiline_field_collapse_preserves_first_lines_and_counts(self):
        value = full_artifact()
        walk = value["changeWalkthrough"]
        for key in ("userImpact", "blastRadius", "tradeoffs", "openItems"):
            walk[key] = "\n".join(f"{key} {i}" for i in range(10))
        value["sources"].append({"id": "missing", "kind": "rid", "ref": "R9"})
        walk["proof"][0]["outcome"] = "fail"
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertLessEqual(len(text.splitlines()), 40)
        for key in ("userImpact", "blastRadius", "tradeoffs", "openItems"):
            self.assertIn(f"{key} 0", text)
            section = text.split(f"{key} 0", 1)[1].split("##", 1)[0]
            visible = 1 + len(re.findall(rf"^{key} \d+", section, re.M))
            self.assertIn(f"{10 - visible} authored lines collapsed", section)
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if "collapsed" in line or line.startswith("Coverage:"):
                self.assertEqual(lines[index - 1], "")

    def test_literal_quotes_and_neutralized_prose_injection(self):
        value = full_artifact()
        value["changeWalkthrough"]["thesis"] = '''It's a "briefing" <script> & [link](bad) _italic_\n## forged\n```\n> quoted'''
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn('It\'s a "briefing"', text)
        self.assertNotIn("&#x27;", text)
        self.assertNotIn("&quot;", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("\n## forged", text)
        self.assertNotIn("\n> quoted", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("\\[link\\]", text)
        self.assertIn("\\_italic\\_", text)
        self.assertIn("&#96;&#96;&#96;", text)
        value["changeWalkthrough"]["proof"] = [{
            "label": "## forged", "value": "part\u2028" * 20, "sourceRefs": ["task"]}]
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertNotIn("\n## forged", text)
        self.assertNotIn("\u2028", text)
        self.assertLessEqual(len(text.splitlines()), 40)



if __name__ == "__main__":
    unittest.main()

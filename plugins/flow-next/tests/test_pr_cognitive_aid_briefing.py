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


def seven_section_artifact():
    value = full_artifact()
    walk = value["changeWalkthrough"]
    template = artifact(canonical_files=4)["changeWalkthrough"]["groups"][2]
    walk["groups"] = []
    for index in range(5):
        group = copy.deepcopy(template)
        group.update(ordinal=index + 1, title=f"Review step {index}")
        for record in group["files"]:
            record["path"] = f"group{index}/" + record["path"]
        walk["groups"].append(group)
    for key in ("userImpact", "blastRadius", "tradeoffs", "openItems"):
        walk[key] = "\n".join(f"{key} detail {i}" for i in range(3))
    walk["proof"] = [
        {"label": f"Gate {i}", "value": f"Note {i}", "sourceRefs": ["task"],
         **({"outcome": outcome} if outcome else {})}
        for i, outcome in enumerate(("pass", "fail", "unverified", None) * 2)
    ]
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

    def test_uncovered_requirements_have_table_but_undeclared_are_omitted(self):
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
        self.assertNotIn("Coverage:", text)
        self.assertNotIn("| Requirement |", text)
        self.assertNotIn("| Undeclared |", text)
        self.assertNotIn("[requirement undeclared]", text)

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

    def test_seven_section_fixture_keeps_all_authored_content(self):
        value = seven_section_artifact()
        value["sources"].append({"id": "missing", "kind": "rid", "ref": "R9"})
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertEqual(text, flowctl.render_pr_cognitive_aid_markdown(value))
        self.assertEqual(re.findall(r"^## (.+)$", text, re.M), HEADINGS)
        walk = value["changeWalkthrough"]
        for key in ("thesis", "userImpact", "blastRadius", "tradeoffs", "openItems"):
            self.assertIn(walk[key], text)
        titles = []
        for group in walk["groups"]:
            titles.append(text.index(group["title"]))
            for record in group["files"]:
                if record["attentionClass"] == "canonical":
                    self.assertIn(record["path"], text)
                    self.assertIn(record["summary"], text)
        self.assertEqual(titles, sorted(titles))
        self.assertEqual(len(re.findall(r"^[ +-] [├└]──", text, re.M)), 20)
        for cell in walk["proof"]:
            outcome = cell.get("outcome")
            prefix = "- [x] " if outcome == "pass" else "- [ ] " if outcome else "- "
            status = f"{outcome}: " if outcome in ("fail", "unverified") else ""
            self.assertIn(f"{prefix}{status}{cell['label']}: {cell['value']}", text)
        self.assertEqual(text.count("[x]"), 2)
        self.assertIn("R9 → uncovered", text)
        self.assertIn("| R9 | unevidenced |", text)

    def test_eleventh_described_row_is_counted_in_author_order(self):
        value = artifact(canonical_files=11)
        records = value["changeWalkthrough"]["groups"][2]["files"]
        records[:11] = reversed(records[:11])
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        positions = [text.index(record["path"]) for record in records[:10]]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn(records[10]["path"], text)
        self.assertIn("1 more described file", text)
        self.assertNotIn("not described", text)

    def test_golden_renders_and_accounts_for_every_file(self):
        value = json.loads(GOLDEN.read_text(encoding="utf-8"))
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertEqual(text, flowctl.render_pr_cognitive_aid_markdown(value))
        shown = len(re.findall(r"^[ +-] [├└]──", text, re.M))
        counted = sum(int(n) for n in re.findall(
            r"(\d+) (?:mechanical|generated|not described|more described) files?\b", text))
        self.assertEqual(shown + counted, 500)

    def test_multiline_thesis_keeps_authored_line_breaks(self):
        value = seven_section_artifact()
        thesis = "\n".join(f"Reason {i}." for i in range(45))
        value["changeWalkthrough"]["thesis"] = thesis
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn(f"## Why\n\n{thesis}\n\n## ", text)
        self.assertIn(value["changeWalkthrough"]["openItems"], text)

    def test_counted_lines_are_separated_from_next_title_and_coverage(self):
        text = flowctl.render_pr_cognitive_aid_markdown(seven_section_artifact())
        self.assertEqual(text.count("1 generated file\n\n**"), 4)
        self.assertIn("1 generated file\n\nCoverage:", text)
        self.assertEqual(text.count("```\n\n1 mechanical file"), 5)

    def test_group_summary_is_a_neutralized_paragraph_before_fence(self):
        value = artifact()
        group = value["changeWalkthrough"]["groups"][2]
        group["summary"] = "## Check <input>\n[links](bad) and `code`."
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        expected = flowctl._pr_aid_prose(" ".join(group["summary"].splitlines()))
        self.assertIn(f"**1. {group['title']}**\n\n{expected}\n\n```diff", text)
        self.assertNotIn("<input>", text)
        self.assertNotIn("\n## Check", text)

    def test_row_ids_override_inherited_sources_without_changing_coverage(self):
        value = artifact()
        value["sources"].append({"id": "second", "kind": "rid", "ref": "R2"})
        group = value["changeWalkthrough"]["groups"][2]
        group["sourceRefs"].append("second")
        group["rIds"].append("R2")
        row = group["files"][0]
        row.update(rIds=["R2"], sourceRefs=["diff", "task", "rid", "second"])
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        line = next(line for line in text.splitlines() if row["path"] in line)
        self.assertTrue(line.endswith("[R2]"))
        coverage = next(line for line in text.splitlines() if line.startswith("Coverage:"))
        row["rIds"] = []
        inherited = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertTrue(next(line for line in inherited.splitlines() if row["path"] in line).endswith("[R6, R2]"))
        self.assertIn(coverage, inherited)

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
            self.assertIn(f"**{number}. {title}**\n\n{group['summary']}\n\n1 mechanical file; 1 generated file", text)
        self.assertNotIn("```", text)

    def test_table_escapes_pipe_in_group_title(self):
        value = artifact()
        group = value["changeWalkthrough"]["groups"][2]
        group.update(files=[], title="One | Two")
        value["changeWalkthrough"]["groups"] = [group]
        value["sources"].append({"id": "uncovered", "kind": "rid", "ref": "R9"})
        text = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn(r"| R6 | One \| Two |", text)

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



if __name__ == "__main__":
    unittest.main()

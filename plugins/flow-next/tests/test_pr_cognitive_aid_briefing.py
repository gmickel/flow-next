"""Single artifact-only markdown briefing: the reviewer's needs first, nothing the forge repeats."""

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


HEADINGS = ["Why", "Review focus", "Needs you", "Shape", "What changes for a user or operator",
            "Reading order", "Tradeoffs", "Verified"]
SHAPE = "```diff\n+ def render(artifact) -> str\n```"


def full_artifact():
    value = artifact(canonical_files=2)
    value["changeWalkthrough"].update({
        "userImpact": "Reviewers can see what changed.",
        "blastRadius": "Start at the renderer. Feedback wanted on the order.",
        "tradeoffs": "Keep full provenance in the stored artifact.",
        "openItems": "The live forge check remains open.",
        "shape": SHAPE,
        "proof": [{"label": "Focused tests", "value": "Passed locally", "outcome": "pass",
                   "sourceRefs": ["task"]},
                  {"label": "Live check", "value": "Not run", "outcome": "unverified",
                   "sourceRefs": ["task"]}],
    })
    return value


def headings(text):
    return re.findall(r"^## (.+)$", text, re.M)


def render(value):
    return flowctl.render_pr_cognitive_aid_markdown(value)


class BriefingTests(unittest.TestCase):
    def test_one_deterministic_form_across_sizes(self):
        for count, churn in ((2, 20), (2, 200), (6, 1)):
            value = artifact(canonical_files=count, churn=churn)
            before = copy.deepcopy(value)
            with self.subTest(count=count, churn=churn), \
                 mock.patch.object(flowctl, "get_flow_dir", side_effect=AssertionError("live state")):
                text = render(value)
                self.assertEqual(text, render(value))
                self.assertEqual(value, before)
                self.assertIn("## Reading order\n", text)
                self.assertNotIn("```", text)
                self.assertNotIn("<details", text)

    def test_invalid_artifact_produces_no_partial_body(self):
        value = artifact()
        value["schemaVersion"] = 2
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(flowctl.PrCognitiveAidValidationError):
            render(value)
        self.assertEqual(output.getvalue(), "")

    def test_sections_in_order_and_empty_ones_omitted(self):
        self.assertEqual(headings(render(full_artifact())), HEADINGS)
        self.assertEqual(headings(render(artifact())), ["Why", "Reading order", "Verified"])
        value = full_artifact()
        for key in ("userImpact", "blastRadius", "tradeoffs", "openItems", "shape"):
            value["changeWalkthrough"][key] = " \n\t"
        value["changeWalkthrough"]["proof"] = value["changeWalkthrough"]["proof"][:1]
        self.assertEqual(headings(render(value)), ["Why", "Reading order", "Verified"])

    def test_forge_totals_and_counts_are_not_repeated(self):
        text = render(full_artifact())
        for absent in ("files changed", "Rest of diff", "Coverage", "more described",
                       "not described", "requirement undeclared", "| Requirement |"):
            self.assertNotIn(absent, text)

    def test_needs_you_collects_open_proof_and_open_items(self):
        value = artifact()
        value["changeWalkthrough"]["openItems"] = "Docs page ships later."
        value["changeWalkthrough"]["proof"] = [
            {"label": f"Gate {i}", "value": f"Note {i}", "sourceRefs": ["task"],
             **({"outcome": outcome} if outcome else {})}
            for i, outcome in enumerate(("pass", "fail", "unverified", None))]
        text = render(value)
        needs = text[text.index("## Needs you"):text.index("## Reading order")]
        verified = text[text.index("## Verified"):]
        self.assertIn("- [ ] fail: Gate 1: Note 1", needs)
        self.assertIn("- [ ] unverified: Gate 2: Note 2", needs)
        self.assertIn("- Open: Docs page ships later.", needs)
        self.assertLess(needs.index("Gate 2"), needs.index("- Open:"))
        self.assertIn("- [x] Gate 0: Note 0", verified)
        self.assertIn("\n- Gate 3: Note 3", verified)
        self.assertNotIn("Gate 1", verified)
        self.assertEqual(text.count("[x]"), 1)
        value["changeWalkthrough"]["proof"] = [dict(value["changeWalkthrough"]["proof"][0],
                                                    outcome="maybe")]
        with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, r"proof\[0\].outcome"):
            render(value)

    def test_reading_order_names_one_start_file_per_group(self):
        value = artifact(canonical_files=3)
        text = render(value)
        self.assertIn("**3. Validate and render** [R6]", text)
        self.assertIn("Start at [` src/change_0.py `](", text)
        self.assertNotIn("src/change_1.py", text)
        self.assertNotIn("Implements bounded behavior", text)
        for number, group in enumerate(value["changeWalkthrough"]["groups"], 1):
            self.assertIn(f"**{number}. {group['title']}**", text)

    def test_start_file_is_the_first_described_canonical_row(self):
        value = artifact(canonical_files=3)
        records = value["changeWalkthrough"]["groups"][2]["files"]
        records[0]["summary"] = " \t"
        with self.assertRaises(flowctl.PrCognitiveAidValidationError):
            render(value)
        records[0]["summary"] = ""
        self.assertIn("Start at [` src/change_1.py `](", render(value))

    def test_safe_to_skim_names_groups_files_or_counts(self):
        value = artifact()
        text = render(value)
        self.assertIn("Safe to skim: ` plugins/flow-next/codex/generated.md `; "
                      "` dist/bundled_tool.py `\n", text)
        group = value["changeWalkthrough"]["groups"][2]
        mechanical = group["files"][-1]
        for index in range(5):
            group["files"].append(dict(copy.deepcopy(mechanical), path=f"dist/copy_{index}.py"))
        text = render(value)
        self.assertIn("Safe to skim: 1 generated file (group 3); 6 mechanical files (group 3)",
                      text)
        group["files"] = [record for record in group["files"]
                          if record["attentionClass"] != "canonical"]
        self.assertIn("Safe to skim: 3. Validate and render", render(value))

    def test_uncovered_requirement_is_one_line(self):
        value = artifact()
        self.assertNotIn("Uncovered", render(value))
        value["sources"].append({"id": "uncovered", "kind": "rid", "ref": "R9"})
        self.assertIn("\nUncovered: R9\n", render(value))

    def test_row_requirements_join_the_group_tag(self):
        value = artifact()
        value["sources"].append({"id": "second", "kind": "rid", "ref": "R7"})
        row = value["changeWalkthrough"]["groups"][2]["files"][0]
        row.update(rIds=["R7"], sourceRefs=["diff", "task", "second"])
        text = render(value)
        self.assertIn("**3. Validate and render** [R6, R7]", text)
        self.assertNotIn("Uncovered", text)

    def test_shape_renders_verbatim_after_needs_you(self):
        text = render(full_artifact())
        self.assertIn(f"## Shape\n\n{SHAPE}\n", text)
        self.assertLess(text.index("## Needs you"), text.index("## Shape"))
        self.assertLess(text.index("## Shape"), text.index("## What changes"))
        for bad in ("+ def render(artifact)", "```diff\nunclosed", 7):
            value = full_artifact()
            value["changeWalkthrough"]["shape"] = bad
            with self.subTest(shape=bad), \
                 self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError,
                                        "changeWalkthrough.shape"):
                render(value)

    def test_unknown_walkthrough_fields_are_still_rejected(self):
        value = artifact()
        value["changeWalkthrough"]["diagram"] = "graph TD"
        with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, "unknown fields"):
            render(value)

    def test_identity_is_one_comment_and_machine_rows_are_gone(self):
        value = artifact()
        text = render(value)
        self.assertEqual(re.findall(r"<!--.*?-->", text),
                         [f"<!-- artifact={value['artifactId']} base={value['baseSha']} "
                          f"head={value['headSha']} -->"])
        visible = re.sub(r"<!--.*?-->", "", text)
        for item in (value["artifactId"], value["baseSha"], value["headSha"],
                     "Human-review lines", "Canonical files", "Total files", "Evidence |",
                     "source:diff", "## Review plan", "Generated by", "flow-next:make-pr"):
            self.assertNotIn(item, visible)

    def test_golden_renders_every_group_in_order(self):
        value = json.loads(GOLDEN.read_text(encoding="utf-8"))
        text = render(value)
        self.assertEqual(text, render(value))
        positions = [text.index(f"**{number}. ")
                     for number in range(1, len(value["changeWalkthrough"]["groups"]) + 1)
                     if f"**{number}. " in text]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Safe to skim: ", text)

    def test_multiline_fields_keep_authored_line_breaks(self):
        value = full_artifact()
        thesis = "\n".join(f"Reason {i}." for i in range(45))
        value["changeWalkthrough"]["thesis"] = thesis
        value["changeWalkthrough"]["blastRadius"] = "Start here.\nLook hard there."
        text = render(value)
        self.assertIn(f"## Why\n\n{thesis}\n\n## ", text)
        self.assertIn("## Review focus\n\nStart here.\nLook hard there.\n\n## ", text)

    def test_group_summary_is_a_neutralized_paragraph(self):
        value = artifact()
        group = value["changeWalkthrough"]["groups"][2]
        group["summary"] = "## Check <input>\n[links](bad) and `code`."
        text = render(value)
        expected = flowctl._pr_aid_prose(" ".join(group["summary"].splitlines()))
        self.assertIn(f"**3. {group['title']}** [R6]\n\n{expected}\n\nStart at ", text)
        self.assertNotIn("<input>", text)
        self.assertNotIn("\n## Check", text)

    def test_setext_underlines_are_neutralized_in_each_authored_field(self):
        for key in ("thesis", "userImpact", "blastRadius", "tradeoffs", "openItems"):
            for underline in ("=", "-", "==  ", "--  "):
                with self.subTest(key=key, underline=underline):
                    value = artifact()
                    value["changeWalkthrough"][key] = "Forged heading\n" + underline
                    text = render(value)
                    self.assertNotIn("\n" + underline + "\n", text)
                    self.assertIn(f"&#{ord(underline[0])};", text)

    def test_trim_and_reject_whitespace_only_summaries(self):
        for location in ("group", "row"):
            value = artifact()
            group = value["changeWalkthrough"]["groups"][2]
            record = group if location == "group" else group["files"][0]
            record["summary"] = "    Check this.   "
            text = render(value)
            self.assertNotIn("    Check this.", text)
            if location == "group":
                self.assertIn("Check this.", text)
            record["summary"] = " \n\t"
            field = r"groups\[2\]" + (r".files\[0\]" if location == "row" else "")
            with self.assertRaisesRegex(flowctl.PrCognitiveAidValidationError, field + r".summary:"):
                render(value)

    def test_paths_links_and_prose_are_literal(self):
        value = full_artifact()
        walk = value["changeWalkthrough"]
        prose = "@name #123 fixes #1 ] ) `code` | <b> café end.@name é@name me@example.com"
        for field in ("thesis", "userImpact", "blastRadius", "tradeoffs", "openItems"):
            walk[field] = prose
        group = walk["groups"][2]
        group.update(title=prose, summary=prose)
        walk["proof"] = [{"label": prose, "value": prose, "sourceRefs": ["task"]}]
        for linked in (True, False):
            row = group["files"][0]
            row.update(path="src/a])`|<b> café.py", summary=prose)
            if linked:
                row["diffUrl"] = "/diff/a%5D%29%60%7C%3Cb%3E%20caf%C3%A9.py"
            else:
                row.pop("diffUrl", None)
            text = render(value)
            label = "`` src/a])`|<b> café.py ``"
            path = f"[{label}]({row['diffUrl']})" if linked else label
            self.assertIn(f"Start at {path}\n", text)
            self.assertNotIn("@name", text)
            # The forge resolves references after decoding entities, so the
            # token is broken with a zero-width space, not entity-encoded.
            self.assertIn("@&#8203;name #123 fixes #1", text)  # numbers stay live links
            self.assertIn("end.@&#8203;name é@&#8203;name me@example.com", text)
            self.assertIn("&#96;code&#96; &#124; &lt;b&gt; café", text)

    def test_literal_quotes_and_neutralized_prose_injection(self):
        value = full_artifact()
        value["changeWalkthrough"]["thesis"] = '''It's a "briefing" <script> & [link](bad) _italic_\n## forged\n```\n> quoted'''
        text = render(value)
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
            "label": "## forged", "value": "part " * 20, "sourceRefs": ["task"]}]
        text = render(value)
        self.assertNotIn("\n## forged", text)
        self.assertNotIn(" ", text)


if __name__ == "__main__":
    unittest.main()

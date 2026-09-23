"""Jira bodies render as written: Markdown <-> wiki markup on v2 (fn-253).

A stateful fake Jira stores exactly what flowctl sends, so every assertion
is about the stored wire form or the decoded read, never a byte round trip.
"""

from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import syncbody as SB  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.lifecycle import verbs as LV  # noqa: E402
from flowctl_tracker.providers import jira_markup as JM  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402

JR_ID = "10042"
LOC = {"durable": JR_ID, "display": "SCRUM-1"}
MUTATING = {"wire-update", "wire-comment-add", "wire-comment-update",
            "lifecycle-create"}

ISSUE_465_MD = (
    "# Branch deployment build-time optimizations\n"
    "\n"
    "## Goal & Context\n"
    "\n"
    "There is one saving: **a unit the change did not touch takes a "
    "published artifact.**\n"
)
ISSUE_465_WIKI = (
    "h1. Branch deployment build-time optimizations\n"
    "\n"
    "h2. Goal & Context\n"
    "\n"
    "There is one saving: *a unit the change did not touch takes a "
    "published artifact.*\n"
)

SPEC_MD = (
    "## Goal\n"
    "\n"
    "Ship **it** with `flowctl --json`.\n"
    "\n"
    "- [ ] first\n"
    "  - nested\n"
)


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None
                    else b"", 0.01)


class FakeJira:
    """One issue plus comments; stores request bodies verbatim."""

    def __init__(self, description: str = "") -> None:
        self.description = description
        self.comments: list[dict] = []
        self.calls: list = []

    def issue(self) -> dict:
        return {"id": JR_ID, "key": "SCRUM-1",
                "fields": {"summary": "Demo", "description": self.description,
                           "labels": []}}

    def __call__(self, request):
        self.calls.append(request)
        op = request.op
        payload = json.loads(request.body) if request.body else None
        if op in ("sync-body-parent-read", "wire-parent-read", "wire-read",
                  "wire-pr-link-parent-read"):
            return ok(self.issue())
        if op == "lifecycle-create-meta":
            return ok({})
        if op == "lifecycle-create":
            self.description = payload["fields"].get("description", "")
            return ok({"id": JR_ID, "key": "SCRUM-1"})
        if op == "wire-update":
            if "description" in payload["fields"]:
                self.description = payload["fields"]["description"]
            return Response(204, {}, b"", 0.01)
        if op == "wire-comment-add":
            comment = {"id": str(len(self.comments) + 1),
                       "body": payload["body"], "created": "2026-01-01"}
            self.comments.append(comment)
            return ok(comment)
        if op == "wire-comment-update":
            cid = str(request.url_or_argv).rsplit("/", 1)[-1]
            comment = next(c for c in self.comments if c["id"] == cid)
            comment["body"] = payload["body"]
            return ok(comment)
        if op == "wire-comment-list":
            return ok({"comments": self.comments, "total": len(self.comments)})
        if op == "wire-pr-link":
            return TrackerError(ErrorClass.CAPABILITY, "remote links off")
        raise AssertionError(f"unexpected op {op!r}")

    def ops(self) -> list[str]:
        return [c.op for c in self.calls]


def jr_cfg() -> dict:
    return {"tracker": {"type": "jira",
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2}}}}


def write_flow(flow: Path, *, base_flow=None, base_tracker=None,
               linked: bool = True) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(jr_cfg()), encoding="utf-8")
    tracker = {"id": None, "identifier": None, "url": None,
               "lastSyncedAt": None, "depRelations": []}
    if linked:
        tracker = {
            "id": JR_ID, "identifier": "SCRUM-1", "url": "https://x",
            "lastSyncedAt": "2020-01-01T00:00:00Z", "depRelations": [],
            "linkState": "linked",
            "mergeBaseFlow": base_flow, "mergeBaseTracker": base_tracker,
            "baseHashFlow": None, "baseHashTracker": None,
        }
    spec = {"id": "fn-1-demo", "title": "Demo", "status": "open",
            "branch_name": "fn-1-demo", "tracker": tracker}
    path = flow / "specs" / "fn-1-demo.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return path


def saved_tracker(flow: Path) -> dict:
    return json.loads(
        (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))["tracker"]


# ---------------------------------------------------------------------------
# R1 / R2 - the transforms
# ---------------------------------------------------------------------------

#: (construct, markdown, stored wiki, decoded canonical Markdown)
CONSTRUCTS = [
    ("headings", "# One\n### Three", "h1. One\nh3. Three", "# One\n### Three"),
    ("bold", "a **b** c __d__", "a *b* c *d*", "a **b** c **d**"),
    ("italic", "a *b* c _d_", "a _b_ c _d_", "a *b* c *d*"),
    ("inline code", "run `a_b --x`", "run {{a\\_b \\-\\-x}}", "run `a_b --x`"),
    ("link", "[the docs](https://x.y/a_b)", "[the docs|https://x.y/a_b]",
     "[the docs](https://x.y/a_b)"),
    ("autolink", "<https://x.y>", "[https://x.y]", "<https://x.y>"),
    ("fenced code", "```python\nx = {'a': 1}  # **no**\n```",
     "{code:python}\nx = {'a': 1}  # **no**\n{code}",
     "```python\nx = {'a': 1}  # **no**\n```"),
    ("plain fence", "```text\n# not a heading\n```",
     "{noformat}\n# not a heading\n{noformat}", "```\n# not a heading\n```"),
    ("table", "| A | B |\n|---|:-:|\n| **x** | y \\| z |",
     "||A||B||\n|*x*|y \\| z|", "| A | B |\n| --- | --- |\n| **x** | y \\| z |"),
    ("blockquote", "> quoted **b**\n>\n> more",
     "bq. quoted *b*\nbq.\nbq. more", "> quoted **b**\n>\n> more"),
    ("nested lists", "- a\n  - b\n    1. c\n    2. d\n1. e\n   - f",
     "* a\n** b\n**# c\n**# d\n# e\n#* f",
     "- a\n  - b\n    1. c\n    2. d\n1. e\n   - f"),
    ("checklist", "- [ ] open\n- [x] done", "* \\[ \\] open\n* \\[x\\] done",
     "- [ ] open\n- [x] done"),
    ("non-ascii", "Grüße, Äpfel — naïve 日本", "Grüße, Äpfel — naïve 日本",
     "Grüße, Äpfel — naïve 日本"),
    ("wiki-special prose", "snake_case C++ (x) a -- b {v} ~s~ ^s^ !img! #tag",
     "snake\\_case C\\+\\+ \\(x) a \\-\\- b \\{v\\} \\~s\\~ \\^s\\^ \\!img\\! #tag",
     "snake_case C++ (x) a -- b {v} ~s~ ^s^ !img! #tag"),
    ("outside the subset", "#nothead\n---\n~~gone~~",
     "\\#nothead\n\\-\\-\\-\n\\~\\~gone\\~\\~", "#nothead\n---\n~~gone~~"),
    ("sync marker",
     "<!-- flow-next:sync issue=SCRUM-1 spec=fn-1 event=e evidence=a_b -->\n\nx_y",
     "<!-- flow-next:sync issue=SCRUM-1 spec=fn-1 event=e evidence=a_b -->\n\nx\\_y",
     "<!-- flow-next:sync issue=SCRUM-1 spec=fn-1 event=e evidence=a_b -->\n\nx_y"),
    ("chart rollup marker",
     "<!-- flow-next:chart-rollup -->\n- **D1** _open_\n<!-- /flow-next:chart-rollup -->",
     "<!-- flow-next:chart-rollup -->\n* *D1* _open_\n<!-- /flow-next:chart-rollup -->",
     "<!-- flow-next:chart-rollup -->\n- **D1** *open*\n<!-- /flow-next:chart-rollup -->"),
]


class Transforms(unittest.TestCase):
    def test_issue_465_fixture_stores_wiki_markup(self) -> None:
        self.assertEqual(JM.markdown_to_wiki(ISSUE_465_MD), ISSUE_465_WIKI)

    def test_each_construct_encodes_then_decodes_to_stable_markdown(self) -> None:
        for name, md, wiki, canonical in CONSTRUCTS:
            with self.subTest(construct=name):
                self.assertEqual(JM.markdown_to_wiki(md), wiki)
                self.assertEqual(JM.wiki_to_markdown(wiki), canonical)
                self.assertEqual(JM.markdown_to_wiki(canonical), wiki)

    def test_unknown_wiki_fragments_decode_unchanged(self) -> None:
        for fragment in ("{color:red}alert{color}", "[~accountid:5b10ac8d]",
                         "-struck- and +under+", "!screen.png|thumbnail!",
                         "{panel:title=Note}", "??cite??", "\\q stays"):
            with self.subTest(fragment=fragment):
                self.assertEqual(JM.wiki_to_markdown(fragment), fragment)

    def test_transforms_use_only_the_standard_library(self) -> None:
        tree = ast.parse(Path(JM.__file__).read_text(encoding="utf-8"))
        imported = {alias.name for node in ast.walk(tree)
                    if isinstance(node, ast.Import) for alias in node.names}
        imported |= {node.module for node in ast.walk(tree)
                     if isinstance(node, ast.ImportFrom)}
        self.assertEqual(imported, {"__future__", "re"})


# ---------------------------------------------------------------------------
# R1 - every body write converts; a converter failure sends nothing
# ---------------------------------------------------------------------------

def _write_cases(flow: Path):
    """(verb, call, stored-body getter) for every Jira body write."""
    return [
        ("issue update",
         lambda ex: W.dispatch("update", jr_cfg(), locator=LOC,
                               body=ISSUE_465_MD, execute=ex),
         lambda fake: fake.description),
        ("comment add",
         lambda ex: W.dispatch("comment-add", jr_cfg(), locator=LOC,
                               body=ISSUE_465_MD, execute=ex),
         lambda fake: fake.comments[-1]["body"]),
        ("comment update",
         lambda ex: W.dispatch("comment-update", jr_cfg(), locator=LOC,
                               comment_id="1", body=ISSUE_465_MD, execute=ex),
         lambda fake: fake.comments[0]["body"]),
        ("issue create",
         lambda ex: LV.create(flow, "fn-1-demo", title="Demo",
                              body=ISSUE_465_MD, execute=ex),
         lambda fake: fake.description),
    ]


class WriteBoundary(unittest.TestCase):
    def _fake(self) -> FakeJira:
        fake = FakeJira()
        fake.comments.append({"id": "1", "body": "old", "created": "x"})
        return fake

    def test_every_body_write_stores_wiki_markup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            write_flow(flow, linked=False)
            for verb, call, stored in _write_cases(flow):
                with self.subTest(verb=verb):
                    fake = self._fake()
                    out = call(fake)
                    self.assertNotIsInstance(out, TrackerError, out)
                    self.assertEqual(stored(fake), ISSUE_465_WIKI)

    def test_converter_failure_is_structured_and_sends_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            write_flow(flow, linked=False)
            for verb, call, _stored in _write_cases(flow):
                with self.subTest(verb=verb), mock.patch(
                        "flowctl_tracker.wire.jira.markdown_to_wiki",
                        side_effect=RuntimeError("boom")):
                    fake = self._fake()
                    out = call(fake)
                    self.assertIsInstance(out, TrackerError)
                    self.assertEqual(out.subtype, "wiki_conversion")
                    self.assertFalse(MUTATING & set(fake.ops()), fake.ops())


# ---------------------------------------------------------------------------
# R2 / R3 / R5 - decode once; no false divergence; edits still detected
# ---------------------------------------------------------------------------

class SyncRoundTrip(unittest.TestCase):
    def test_create_base_matches_next_read_without_a_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            write_flow(flow, linked=False)
            fake = FakeJira()
            created = LV.create(flow, "fn-1-demo", title="Demo", body=SPEC_MD,
                                execute=fake)
            self.assertNotIsInstance(created, TrackerError, created)
            self.assertEqual(fake.description, JM.markdown_to_wiki(SPEC_MD))
            saved = saved_tracker(flow)
            self.assertEqual(saved["mergeBaseFlow"], SPEC_MD)
            self.assertEqual(saved["mergeBaseTracker"],
                             SB.trackerBodyForMerge(
                                 JM.wiki_to_markdown(fake.description)))
            again = SB.sync_body(flow, "fn-1-demo", flow_file_body=SPEC_MD,
                                 direction="push", execute=fake)
            self.assertEqual(again["kind"], "noop")
            self.assertNotIn("wire-update", fake.ops())

    def test_push_then_reconcile_reports_no_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            write_flow(flow)
            fake = FakeJira("old")
            pushed = SB.sync_body(flow, "fn-1-demo", flow_file_body=SPEC_MD,
                                  tracker_body=SPEC_MD, direction="push",
                                  execute=fake)
            self.assertEqual(pushed["kind"], "pushed")
            self.assertEqual(fake.description, JM.markdown_to_wiki(SPEC_MD))

            read = W.dispatch("read", jr_cfg(), locator=LOC, execute=fake)
            self.assertEqual(SB.trackerBodyForMerge(read["body"]),
                             saved_tracker(flow)["mergeBaseTracker"])
            writes = fake.ops().count("wire-update")
            again = SB.sync_body(flow, "fn-1-demo", flow_file_body=SPEC_MD,
                                 tracker_body=read["body"],
                                 expected_tracker_body=read["body"],
                                 direction="push", execute=fake)
            self.assertEqual(again["kind"], "noop")
            self.assertEqual(fake.ops().count("wire-update"), writes)

    def test_genuine_jira_edit_is_still_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            write_flow(flow)
            fake = FakeJira("old")
            SB.sync_body(flow, "fn-1-demo", flow_file_body=SPEC_MD,
                         direction="push", execute=fake)
            fake.description += "\nh3. Added in Jira"
            read = W.dispatch("read", jr_cfg(), locator=LOC, execute=fake)
            self.assertNotEqual(SB.trackerBodyForMerge(read["body"]),
                                saved_tracker(flow)["mergeBaseTracker"])
            self.assertTrue(read["body"].endswith("\n### Added in Jira"))

    def test_marker_comments_dedup_including_pr_link_fallback(self) -> None:
        fake = FakeJira()
        marker = "<!-- flow-next:sync issue=SCRUM-1 spec=fn-1 event=e evidence=a_b -->"
        added = W.dispatch("comment-add", jr_cfg(), locator=LOC,
                           body=f"{marker}\n\n**done**", execute=fake)
        self.assertTrue(fake.comments[0]["body"].startswith(marker + "\n"))
        self.assertEqual(added["body"], f"{marker}\n\n**done**")

        url = "https://github.com/o/r/pull/7"
        first = W.link_pr("jira", jr_cfg(), LOC, fake, url=url)
        second = W.link_pr("jira", jr_cfg(), LOC, fake, url=url)
        self.assertEqual(first["kind"], "comment-fallback")
        self.assertTrue(second["deduped"])
        self.assertEqual(fake.ops().count("wire-comment-add"), 2)


# ---------------------------------------------------------------------------
# R4 - issues linked before fn-253 still hold raw Markdown
# ---------------------------------------------------------------------------

LEGACY_MD = "## Goal\n\nShip **it**.\n"


class LegacyBody(unittest.TestCase):
    def _legacy(self, tmp: str):
        flow = Path(tmp)
        base = SB.trackerBodyForMerge(LEGACY_MD)
        write_flow(flow, base_flow=LEGACY_MD, base_tracker=base)
        return flow, FakeJira(LEGACY_MD), base

    def test_pull_refuses_before_conversion_then_push_converts(self) -> None:
        reads = {
            "parent read": None,
            "wire read": lambda fake: (
                lambda loc: W.dispatch("read", jr_cfg(), locator=loc,
                                       execute=fake)),
        }
        for mode, reader in reads.items():
            with self.subTest(read=mode), tempfile.TemporaryDirectory() as tmp:
                flow, fake, base = self._legacy(tmp)
                pulled = SB.sync_body(
                    flow, "fn-1-demo", flow_file_body=LEGACY_MD,
                    direction="pull", execute=fake,
                    tracker_read=reader(fake) if reader else None)
                self.assertIsInstance(pulled, TrackerError)
                self.assertEqual(pulled.subtype, "jira_body_unconverted")
                self.assertEqual(saved_tracker(flow)["mergeBaseTracker"], base)
                self.assertEqual(saved_tracker(flow)["mergeBaseFlow"], LEGACY_MD)
                self.assertFalse(MUTATING & set(fake.ops()))

                pushed = SB.sync_body(flow, "fn-1-demo",
                                      flow_file_body=LEGACY_MD,
                                      direction="push", execute=fake)
                self.assertEqual(pushed["kind"], "pushed")
                self.assertEqual(fake.description,
                                 JM.markdown_to_wiki(LEGACY_MD))
                self.assertEqual(saved_tracker(flow)["mergeBaseTracker"],
                                 SB.trackerBodyForMerge(LEGACY_MD))

                again = SB.sync_body(flow, "fn-1-demo",
                                     flow_file_body=LEGACY_MD,
                                     direction="pull", execute=fake)
                self.assertNotIsInstance(again, TrackerError, again)

    def test_reconcile_converts_an_unchanged_legacy_body(self) -> None:
        for source in ("recorded base", "decoded read"):
            with self.subTest(source=source), \
                    tempfile.TemporaryDirectory() as tmp:
                flow, fake, base = self._legacy(tmp)
                seen = (base if source == "recorded base"
                        else JM.wiki_to_markdown(LEGACY_MD))
                out = SB.sync_body(flow, "fn-1-demo",
                                   flow_file_body=LEGACY_MD,
                                   tracker_body=LEGACY_MD,
                                   expected_tracker_body=seen,
                                   direction="push", execute=fake)
                self.assertEqual(out["kind"], "pushed")
                self.assertEqual(fake.description,
                                 JM.markdown_to_wiki(LEGACY_MD))

    def test_edited_legacy_body_takes_the_normal_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow, fake, _base = self._legacy(tmp)
            fake.description = LEGACY_MD + "\nEdited in Jira."
            pulled = SB.sync_body(flow, "fn-1-demo", flow_file_body=LEGACY_MD,
                                  direction="pull", execute=fake)
            self.assertNotIsInstance(pulled, TrackerError, pulled)
            self.assertEqual(pulled["mergeBaseTracker"],
                             SB.trackerBodyForMerge(
                                 JM.wiki_to_markdown(fake.description)))


if __name__ == "__main__":
    unittest.main()

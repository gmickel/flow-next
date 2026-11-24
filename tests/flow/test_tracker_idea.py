"""Start from an upstream idea: Jira Product Discovery (fn-330).

The idea source is `tracker.perTracker.ideaProjectKeys`. With it set, the wire
read of an idea points at the idea-intake reference, and three operations read
the idea, settle its delivery parent and write the delivery link. Without it,
every request and every read is what it was before.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "flow"
sys.path.insert(0, str(ROOT / "skills" / "flow" / "scripts"))

from flowctl_tracker import classify  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402

FLOWCTL = ROOT / "skills" / "flow" / "scripts" / "edge.py"
BASE = "https://ex.atlassian.net"
IDEA_ID = "20007"
LINK_TYPES = {"issueLinkTypes": [
    {"id": "10000", "name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
    {"id": "10039", "name": "Polaris merge work item link",
     "inward": "merged into", "outward": "merged from"},
    {"id": "10038", "name": "Polaris work item link",
     "inward": "is implemented by", "outward": "implements"},
]}
DELIVERY_TYPE = LINK_TYPES["issueLinkTypes"][2]
PROJECT = {"id": "10000", "key": "PROJ", "issueTypes": [
    {"id": "10001", "name": "Story", "hierarchyLevel": 0, "subtask": False},
    {"id": "10002", "name": "Task", "hierarchyLevel": 0, "subtask": False},
    {"id": "10003", "name": "Epic", "hierarchyLevel": 1, "subtask": False},
    {"id": "10004", "name": "Subtask", "hierarchyLevel": -1, "subtask": True},
]}


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def created() -> Response:
    return Response(201, {}, b"", 0.01)


def rejected(status: int, body: dict) -> TrackerError:
    err = classify.classify(
        "jira", Response(status, {}, json.dumps(body).encode(), 0.01))
    assert isinstance(err, TrackerError)
    return err


def fake_execute(responses: dict):
    calls = []

    def execute(request):
        calls.append(request)
        if request.op == "lifecycle-create-meta" and request.op not in responses:
            return ok({})
        if request.op == "idea-marker-search" and request.op not in responses:
            return ok({"issues": [], "isLast": True})
        if request.op not in responses:
            raise AssertionError(
                f"unexpected op {request.op!r}; have {sorted(responses)}")
        out = responses[request.op]
        if isinstance(out, list):
            out = out.pop(0)
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def jr_cfg(*, idea_keys=None, tracker_type: str = "jira",
           auth_scheme: str | None = None) -> dict:
    per: dict = {"blocksLinkType": "Blocks"}
    if idea_keys is not None:
        per["ideaProjectKeys"] = idea_keys
    if auth_scheme is not None:
        per["authScheme"] = auth_scheme
    return {"tracker": {"type": tracker_type, "perTracker": per,
                        "resolved": {"destination": {
                            "baseUrl": BASE, "projectKey": "PROJ",
                            "projectId": "10000", "issueTypeId": "10001",
                            "apiVersion": 2,
                            "statusIds": {"todo": "1", "in_progress": "2",
                                          "done": "4"}}}}}


def linked(key: str, *, link_id: str = "30001", level: int = 1,
           type_name: str = "Epic", link_type: dict = DELIVERY_TYPE,
           side: str = "inwardIssue") -> dict:
    return {"id": link_id, "type": link_type, side: {
        "id": str(40000 + int(key.rsplit("-", 1)[1])), "key": key,
        "fields": {"summary": f"{key} summary",
                   "status": {"name": "To Do"},
                   "issuetype": {"name": type_name, "hierarchyLevel": level}}}}


def idea(*, links=None, description="h2. Problem\n\nShoppers abandon carts.") -> dict:
    return {"id": IDEA_ID, "key": "IDEAS-7", "fields": {
        "summary": "Express checkout", "description": description,
        "status": {"name": "Ready for delivery"},
        "project": {"key": "IDEAS"},
        "issuelinks": links or []}}


def comments(*bodies: str) -> dict:
    return {"total": len(bodies), "comments": [
        {"id": str(i), "body": b, "created": "2026-11-16T10:00:00.000+0000"}
        for i, b in enumerate(bodies, 1)]}


def _idea_mod():
    from flowctl_tracker import idea  # noqa: PLC0415 - the module under test
    return idea


def _posts(ex, op: str) -> list:
    return [json.loads(c.body.decode()) for c in ex.calls if c.op == op]


def _body_file(tmp: str, text: str = "Delivery parent for IDEAS-7.") -> str:
    path = Path(tmp) / "parent.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


class WireReadPointsAtTheReference(unittest.TestCase):
    """R1/R7: the routing pointer rides the existing read; requests unchanged."""

    def _read(self, config: dict, display: str):
        issue = idea() if display == "IDEAS-7" else {
            "id": "10012", "key": display, "fields": {"summary": "S"}}
        ex = fake_execute({"wire-read": ok(issue)})
        durable = IDEA_ID if display == "IDEAS-7" else "10012"
        out = W.dispatch("read", config,
                         locator={"durable": durable, "display": display},
                         execute=ex)
        return out, ex

    def test_idea_read_carries_the_reference(self) -> None:
        out, _ = self._read(jr_cfg(idea_keys=["IDEAS", "RESEARCH"]), "IDEAS-7")
        self.assertIsInstance(out, dict)
        reference = Path(out["idea"]["reference"])
        self.assertEqual(reference.name, "tracker.md")
        self.assertTrue(reference.is_file(), reference)

    def test_missing_reference_is_named_under_the_plugin_root(self) -> None:
        from flowctl_tracker.wire import jira as JW  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
                JW, "IDEA_REFERENCE", Path(tmp) / "missing.md"):
            out, _ = self._read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7")
        self.assertEqual(out["idea"]["reference"], "playbooks/tracker.md")

    def test_request_is_byte_identical_with_and_without_the_key(self) -> None:
        _, plain = self._read(jr_cfg(), "IDEAS-7")
        _, configured = self._read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7")
        self.assertEqual(
            [(c.method, c.url_or_argv, c.body) for c in plain.calls],
            [(c.method, c.url_or_argv, c.body) for c in configured.calls])

    def test_no_pointer_without_the_key_or_outside_an_idea_project(self) -> None:
        for config, display in ((jr_cfg(), "IDEAS-7"),
                                (jr_cfg(idea_keys=[]), "IDEAS-7"),
                                (jr_cfg(idea_keys=["IDEAS"]), "PROJ-12"),
                                # The delivery project is never an idea project.
                                (jr_cfg(idea_keys=["PROJ"]), "PROJ-12")):
            out, _ = self._read(config, display)
            self.assertNotIn("idea", out, (config, display))


class IdeasAreReadOnly(unittest.TestCase):
    """R6: no write reaches an idea, even through a link made before opt-in."""

    LOCATOR = {"durable": IDEA_ID, "display": "IDEAS-7"}

    def test_writes_to_an_idea_are_refused_before_any_request(self) -> None:
        for verb, kwargs in (("update", {"body": "spec body"}),
                             ("comment-add", {"body": "note"}),
                             ("label", {"add": ["x"]})):
            ex = fake_execute({})
            out = W.dispatch(verb, jr_cfg(idea_keys=["IDEAS"]),
                             locator=self.LOCATOR, execute=ex, **kwargs)
            self.assertIsInstance(out, TrackerError, verb)
            self.assertIs(out.cls, ErrorClass.CAPABILITY, verb)
            self.assertTrue(Path(out.details["reference"]).is_file(), verb)
            self.assertEqual(ex.calls, [], verb)

    def test_without_the_key_the_write_goes_ahead(self) -> None:
        ex = fake_execute({"wire-parent-read": ok(idea()),
                           "wire-update": created()})
        out = W.dispatch("update", jr_cfg(), locator=self.LOCATOR,
                         body="spec body", execute=ex)
        self.assertIsInstance(out, dict, out)

    def test_a_configured_delivery_read_loads_no_idea_code(self) -> None:
        probe = (
            "import json, sys\n"
            f"sys.path.insert(0, {str(ROOT / 'skills' / 'flow' / 'scripts')!r})\n"
            "from flowctl_tracker import wire\n"
            "from flowctl_tracker.types import Response\n"
            "body = json.dumps({'id': '10012', 'key': 'PROJ-12', 'fields': {}}).encode()\n"
            "cfg = json.loads(sys.argv[1])\n"
            "out = wire.dispatch('read', cfg, locator={'durable': '10012', "
            "'display': 'PROJ-12'}, execute=lambda r: Response(200, {}, body, 0.0))\n"
            "print(json.dumps(['idea' in out, 'flowctl_tracker.idea' in sys.modules]))\n")
        run = subprocess.run([sys.executable, "-c", probe,
                              json.dumps(jr_cfg(idea_keys=["IDEAS"]))],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), [False, False])


def _linked_spec(flow: Path, spec_id: str, durable: str, display: str) -> None:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"id: {spec_id}",
        "title: Demo",
        "tracker:",
        f"  id: {json.dumps(durable)}",
        f"  identifier: {json.dumps(display)}",
        "---",
        "",
    ]
    (flow / "specs" / f"{spec_id}.md").write_text("\n".join(lines), encoding="utf-8")


class IdeaStatusAndRelationsAreReadOnly(unittest.TestCase):
    """R6 siblings: dependency links and status transitions skip the
    pre-write parent read, so each refuses an idea itself."""

    def _relate(self, a: str, b: str):
        from flowctl_tracker import relate as R  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _linked_spec(flow, "fn-1-a", *a)
            _linked_spec(flow, "fn-2-b", *b)
            (flow / "config.json").write_text(
                json.dumps(jr_cfg(idea_keys=["IDEAS"])), encoding="utf-8")
            ex = fake_execute({})
            out = R.relate(flow, "fn-1-a", blocked_by="fn-2-b", execute=ex)
        return out, ex

    def test_relation_with_an_idea_at_either_end_makes_no_request(self) -> None:
        idea_end, delivery = (IDEA_ID, "IDEAS-7"), ("10012", "PROJ-12")
        for a, b in ((idea_end, delivery), (delivery, idea_end)):
            out, ex = self._relate(a, b)
            self.assertIsInstance(out, TrackerError, a)
            self.assertIs(out.cls, ErrorClass.CAPABILITY, a)
            self.assertEqual(out.subtype, "idea_read_only", a)
            self.assertEqual(ex.calls, [], a)

    def test_status_transition_on_an_idea_makes_no_request(self) -> None:
        from flowctl_tracker.status.providers import apply_status  # noqa: PLC0415
        ex = fake_execute({})
        out = apply_status("jira", jr_cfg(idea_keys=["IDEAS"]),
                           {"durable": IDEA_ID, "display": "IDEAS-7"}, {}, ex,
                           target_slot="done")
        self.assertIs(out.cls, ErrorClass.CAPABILITY)
        self.assertEqual(out.subtype, "idea_read_only")
        self.assertEqual(ex.calls, [])

    def test_unready_reads_the_idea_and_moves_nothing(self) -> None:
        config = jr_cfg(idea_keys=["IDEAS"])
        config["tracker"]["readyState"] = "Ready for delivery"
        ex = fake_execute({"wire-read": ok(idea())})
        out = W.dispatch("unready", config,
                         locator={"durable": IDEA_ID, "display": "IDEAS-7"},
                         execute=ex)
        self.assertIs(out.cls, ErrorClass.CAPABILITY)
        self.assertEqual([c.op for c in ex.calls], [])


class IdeaRead(unittest.TestCase):
    def test_reads_text_comments_and_delivery_links(self) -> None:
        ex = fake_execute({
            "idea-read": ok(idea(links=[
                linked("PROJ-12"),
                linked("PROJ-30", link_id="30002",
                       link_type=LINK_TYPES["issueLinkTypes"][0]),
            ])),
            "wire-comment-list": ok(comments("Decision: ship in Q1",
                                             "Requirement: one-tap pay")),
        })
        out = _idea_mod().read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7", ex)
        self.assertIsInstance(out, dict, out)
        self.assertEqual(out["idea"]["identifier"], "IDEAS-7")
        self.assertEqual(out["idea"]["title"], "Express checkout")
        self.assertIn("Shoppers abandon carts.", out["idea"]["body"])
        self.assertEqual([c["body"] for c in out["comments"]],
                         ["Decision: ship in Q1", "Requirement: one-tap pay"])
        self.assertEqual([d["key"] for d in out["deliveryLinks"]], ["PROJ-12"])
        self.assertTrue(Path(out["reference"]).is_file())
        self.assertIn("issuelinks", ex.calls[0].url_or_argv)
        self.assertTrue(all(c.method == "GET" for c in ex.calls))

    def test_colour_tags_are_removed_and_their_text_kept(self) -> None:
        # fn-331: the discovery template wraps its prompts in colour tags.
        ex = fake_execute({
            "idea-read": ok(idea(description=(
                "h2. Problem\n\n{color:#97a0af}Who has the problem?{color}\n\n"
                "* {color:#97A0AF}first{color} and {color}stray close\n"
                "* {color:red}open without a close"))),
            "wire-comment-list": ok(comments(
                "{color:#97a0af}Decision: ship in Q1{color}", "plain")),
        })
        out = _idea_mod().read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7", ex)
        self.assertIsInstance(out, dict, out)
        self.assertEqual(out["idea"]["body"],
                         "## Problem\n\nWho has the problem?\n\n"
                         "- first and stray close\n- open without a close")
        self.assertEqual([c["body"] for c in out["comments"]],
                         ["Decision: ship in Q1", "plain"])

    def test_ordinary_issue_read_keeps_colour_tags(self) -> None:
        body = "{color:#97a0af}Who has the problem?{color}"
        ex = fake_execute({"wire-read": ok(idea(description=body)),
                           "wire-comment-list": ok(comments(body))})
        locator = {"durable": IDEA_ID, "display": "IDEAS-7"}
        out = W.dispatch("read", jr_cfg(idea_keys=["IDEAS"]),
                         locator=locator, execute=ex)
        self.assertEqual(out["body"], body)
        listed = W.dispatch("comment-list", jr_cfg(idea_keys=["IDEAS"]),
                            locator=locator, execute=ex)
        self.assertEqual([c["body"] for c in listed["comments"]], [body])

    def test_url_with_selected_issue_resolves_to_the_key(self) -> None:
        ex = fake_execute({"idea-read": ok(idea()),
                           "wire-comment-list": ok(comments())})
        url = f"{BASE}/jira/polaris/projects/IDEAS/ideas/view/9?selectedIssue=IDEAS-7"
        out = _idea_mod().read(jr_cfg(idea_keys=["IDEAS"]), url, ex)
        self.assertEqual(out["idea"]["identifier"], "IDEAS-7")
        self.assertIn("/issue/IDEAS-7?", ex.calls[0].url_or_argv)

    def test_refusals_make_no_request(self) -> None:
        cases = [
            (jr_cfg(), "IDEAS-7", ErrorClass.UNRESOLVED),
            (jr_cfg(idea_keys=["IDEAS"]), "PROJ-12", ErrorClass.INVALID_INPUT),
            (jr_cfg(idea_keys=["IDEAS"]), "https://other.atlassian.net/browse/IDEAS-7",
             ErrorClass.INVALID_INPUT),
            (jr_cfg(idea_keys="IDEAS"), "IDEAS-7", ErrorClass.INVALID_INPUT),
            # R8: another tracker, or Jira Data Center.
            (jr_cfg(idea_keys=["IDEAS"], tracker_type="linear"), "IDEAS-7",
             ErrorClass.CAPABILITY),
            (jr_cfg(idea_keys=["IDEAS"], auth_scheme="bearer-pat"), "IDEAS-7",
             ErrorClass.CAPABILITY),
        ]
        for config, ref, cls in cases:
            ex = fake_execute({})
            out = _idea_mod().read(config, ref, ex)
            self.assertIsInstance(out, TrackerError, (config, ref))
            self.assertIs(out.cls, cls, (ref, out))
            self.assertEqual(ex.calls, [])

    def test_unreadable_idea_stops_with_the_transport_error(self) -> None:
        ex = fake_execute({"idea-read": rejected(
            404, {"errorMessages": ["Issue does not exist or you do not "
                                    "have permission to see it."]})})
        out = _idea_mod().read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7", ex)
        self.assertIsInstance(out, TrackerError)
        self.assertTrue(all(c.method == "GET" for c in ex.calls))


class SettleParent(unittest.TestCase):
    """R3/R4: reuse or create one parent; link it; a repeat creates nothing."""

    def _settle(self, links, *, use=None, extra=None, tmp=None):
        responses = {"idea-link-types": ok(LINK_TYPES),
                     "idea-read": ok(idea(links=links)),
                     "idea-project": ok(PROJECT)}
        responses.update(extra or {})
        ex = fake_execute(responses)
        with tempfile.TemporaryDirectory() as own:
            body = _body_file(tmp or own)
            out = _idea_mod().settle_parent(
                jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7", ex,
                body=Path(body).read_text(encoding="utf-8"), use=use)
        return out, ex

    def test_creates_an_epic_and_links_it_to_the_idea(self) -> None:
        out, ex = self._settle([], extra={
            "lifecycle-create": ok({"id": "40099", "key": "PROJ-99"}),
            "idea-link": created()})
        self.assertIsInstance(out, dict, out)
        self.assertTrue(out["parent"]["created"])
        self.assertEqual(out["parent"]["key"], "PROJ-99")
        self.assertTrue(out["link"]["created"])
        fields = _posts(ex, "lifecycle-create")[0]["fields"]
        self.assertEqual(fields["issuetype"], {"id": "10003"})
        self.assertEqual(fields["project"], {"id": "10000"})
        self.assertEqual(fields["summary"], "Express checkout")
        self.assertNotIn("parent", fields)
        self.assertEqual(_posts(ex, "idea-link"), [{
            "type": {"id": "10038"},
            "inwardIssue": {"key": "PROJ-99"},
            "outwardIssue": {"key": "IDEAS-7"}}])

    def test_reuses_the_delivery_linked_epic_and_writes_nothing(self) -> None:
        out, ex = self._settle([linked("PROJ-12")])
        self.assertFalse(out["parent"]["created"])
        self.assertEqual(out["parent"]["key"], "PROJ-12")
        self.assertTrue(out["link"]["existing"])
        self.assertFalse(out["link"]["created"])
        self.assertTrue(all(c.method == "GET" for c in ex.calls))

    def test_second_run_finds_the_first_runs_parent(self) -> None:
        first, _ = self._settle([], extra={
            "lifecycle-create": ok({"id": "40099", "key": "PROJ-99"}),
            "idea-link": created()})
        second, ex = self._settle([linked(first["parent"]["key"])])
        self.assertEqual(second["parent"]["key"], "PROJ-99")
        self.assertFalse(second["parent"]["created"])
        self.assertEqual([c for c in ex.calls if c.method != "GET"], [])

    def test_issues_that_cannot_serve_are_named_not_reused(self) -> None:
        out, ex = self._settle(
            [linked("OTHER-4"), linked("PROJ-31", level=0, type_name="Story"),
             linked("PROJ-40", link_type=LINK_TYPES["issueLinkTypes"][0])],
            extra={"lifecycle-create": ok({"id": "40099", "key": "PROJ-99"}),
                   "idea-link": created()})
        self.assertTrue(out["parent"]["created"])
        self.assertEqual(sorted(n["key"] for n in out["notReused"]),
                         ["OTHER-4", "PROJ-31"])
        self.assertEqual(len(_posts(ex, "lifecycle-create")), 1)

    def test_several_candidates_ask_and_use_picks_one(self) -> None:
        links = [linked("PROJ-12"), linked("PROJ-13", link_id="30002")]
        out, ex = self._settle(links)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "several_parents")
        self.assertEqual(sorted(c["key"] for c in out.details["candidates"]),
                         ["PROJ-12", "PROJ-13"])
        self.assertTrue(all(c.method == "GET" for c in ex.calls))
        picked, ex = self._settle(links, use="PROJ-13")
        self.assertEqual(picked["parent"]["key"], "PROJ-13")
        self.assertTrue(all(c.method == "GET" for c in ex.calls))
        wrong, _ = self._settle(links, use="PROJ-99")
        self.assertIs(wrong.cls, ErrorClass.INVALID_INPUT)

    def test_missing_or_ambiguous_link_type_stops_before_any_write(self) -> None:
        polaris = LINK_TYPES["issueLinkTypes"][2]
        for types in ([LINK_TYPES["issueLinkTypes"][0]],
                      [polaris, {**polaris, "id": "10099",
                                 "name": "Polaris work item link (old)"}]):
            ex = fake_execute({"idea-link-types": ok({"issueLinkTypes": types})})
            out = _idea_mod().settle_parent(
                jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7", ex, body="B")
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.UNRESOLVED)
            self.assertEqual(out.subtype, "delivery_link_type")
            self.assertIn("found", out.details)
            self.assertEqual([c.op for c in ex.calls], ["idea-link-types"])

    def test_several_parent_level_types_block_only_a_create(self) -> None:
        project = {**PROJECT, "issueTypes": PROJECT["issueTypes"] + [
            {"id": "10005", "name": "Feature", "hierarchyLevel": 1, "subtask": False}]}
        out, _ = self._settle([linked("PROJ-12")], extra={"idea-project": ok(project)})
        self.assertEqual(out["parent"]["key"], "PROJ-12")
        out, ex = self._settle([], extra={"idea-project": ok(project)})
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "parent_type")
        self.assertTrue(all(c.method == "GET" for c in ex.calls))

    def test_failed_link_reports_the_parent_and_the_retry(self) -> None:
        out, _ = self._settle([], extra={
            "lifecycle-create": ok({"id": "40099", "key": "PROJ-99"}),
            "idea-link": rejected(403, {"errorMessages": ["No link permission"]})})
        self.assertIsInstance(out, dict, out)
        self.assertEqual(out["parent"]["key"], "PROJ-99")
        self.assertFalse(out["link"]["created"])
        self.assertIn("error", out["link"])
        self.assertIn("tracker idea link IDEAS-7 PROJ-99", out["link"]["retry"])


class DeliveryLink(unittest.TestCase):
    def _link(self, links, extra=None):
        responses = {"idea-link-types": ok(LINK_TYPES),
                     "idea-read": ok(idea(links=links))}
        responses.update(extra or {})
        ex = fake_execute(responses)
        return _idea_mod().link(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7",
                                "PROJ-99", ex), ex

    def test_writes_the_link_once(self) -> None:
        out, ex = self._link([], {"idea-link": created()})
        self.assertTrue(out["created"])
        self.assertEqual(len(_posts(ex, "idea-link")), 1)
        again, ex = self._link([linked("PROJ-99")])
        self.assertFalse(again["created"])
        self.assertTrue(again["existing"])
        self.assertTrue(all(c.method == "GET" for c in ex.calls))

    def test_refuses_to_link_an_idea_to_itself_or_another_idea(self) -> None:
        ex = fake_execute({})
        out = _idea_mod().link(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7",
                               "IDEAS-8", ex)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(ex.calls, [])


class Cli(unittest.TestCase):
    """The verbs through the real parser; R6's link refusal; R8 by exit code."""

    def _run(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(FLOWCTL), *args],
                              cwd=cwd, capture_output=True, text=True,
                              encoding="utf-8")

    def _repo(self, tmp: str, config: dict) -> Path:
        cwd = Path(tmp)
        (cwd / ".flow").mkdir(parents=True, exist_ok=True)
        (cwd / ".flow" / "config.json").write_text(json.dumps(config),
                                                   encoding="utf-8")
        return cwd

    def test_other_tracker_is_a_capability_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._repo(tmp, jr_cfg(idea_keys=["IDEAS"],
                                         tracker_type="linear"))
            out = self._run(cwd, "tracker", "idea", "read", "IDEAS-7")
            self.assertEqual(out.returncode, 9, out.stdout + out.stderr)
            self.assertEqual(json.loads(out.stdout)["class"], "capability")


def _search_jql(request) -> str:
    from urllib.parse import parse_qs, urlparse  # noqa: PLC0415
    return parse_qs(urlparse(request.url_or_argv).query)["jql"][0]


def _marked(key: str, *, level: int = 1) -> dict:
    return {"id": str(40000 + int(key.rsplit("-", 1)[1])), "key": key,
            "fields": {"summary": f"{key} summary", "status": {"name": "To Do"},
                       "issuetype": {"name": "Epic" if level else "Story",
                                     "hierarchyLevel": level}}}


class RerunFindsTheUnlinkedParent(unittest.TestCase):
    """fn-334 R1: a parent whose delivery link failed is found by its marker."""

    def _settle(self, extra: dict, *, use=None):
        responses = {"idea-link-types": ok(LINK_TYPES),
                     "idea-read": ok(idea()), "idea-project": ok(PROJECT)}
        responses.update(extra)
        ex = fake_execute(responses)
        out = _idea_mod().settle_parent(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7",
                                        ex, body="B", use=use)
        return out, ex

    def test_rerun_after_a_failed_link_links_the_first_parent(self) -> None:
        first, ex = self._settle({
            "lifecycle-create": ok({"id": "40099", "key": "PROJ-99"}),
            "idea-link": rejected(500, {})})
        self.assertFalse(first["link"]["created"])
        labels = _posts(ex, "lifecycle-create")[0]["fields"].get("labels", [])
        self.assertEqual(len(labels), 1)
        marker = labels[0]
        self.assertIn("IDEAS-7", marker)

        def search(request):
            self.assertIn(marker, _search_jql(request))
            self.assertIn("PROJ", _search_jql(request))
            return ok({"issues": [_marked("PROJ-99"), _marked("PROJ-98", level=0)],
                       "isLast": True})

        second, ex = self._settle({"idea-marker-search": search,
                                   "lifecycle-create": ok({"id": "1", "key": "PROJ-1"}),
                                   "idea-link": created()})
        self.assertEqual(_posts(ex, "lifecycle-create"), [])
        self.assertEqual(second["parent"]["key"], "PROJ-99")
        self.assertFalse(second["parent"]["created"])
        self.assertTrue(second["link"]["created"])
        self.assertEqual(_posts(ex, "idea-link")[0]["inwardIssue"], {"key": "PROJ-99"})

    def test_several_marked_parents_are_a_conflict_and_use_picks(self) -> None:
        found = ok({"issues": [_marked("PROJ-98"), _marked("PROJ-99")], "isLast": True})
        out, ex = self._settle({"idea-marker-search": found})
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "several_parents")
        self.assertEqual(sorted(c["key"] for c in out.details["candidates"]),
                         ["PROJ-98", "PROJ-99"])
        self.assertTrue(all(c.method == "GET" for c in ex.calls))
        picked, ex = self._settle({"idea-marker-search": ok(
            {"issues": [_marked("PROJ-98"), _marked("PROJ-99")], "isLast": True}),
            "idea-link": created()}, use="PROJ-98")
        self.assertEqual(picked["parent"]["key"], "PROJ-98")
        self.assertEqual(_posts(ex, "lifecycle-create"), [])

    def test_no_labels_field_refuses_before_creating(self) -> None:
        meta = ok({"projects": [{"issuetypes": [{"id": "10003", "fields": {
            "summary": {}, "description": {}}}]}]})
        out, ex = self._settle({"lifecycle-create-meta": meta,
                                "lifecycle-create": ok({"id": "40099", "key": "PROJ-99"}),
                                "idea-link": created()})
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CAPABILITY)
        self.assertIn("tracker idea link", out.message)
        self.assertEqual(_posts(ex, "lifecycle-create"), [])

    def test_unreadable_marker_search_creates_nothing(self) -> None:
        # PR #625 review: a search response it cannot read completely is an
        # error, never "no marked parent".
        for body in ([], {"issues": []}, {"issues": {}, "isLast": True},
                     {"issues": [], "isLast": "yes"}):
            with self.subTest(body=body):
                out, ex = self._settle({"idea-marker-search": ok(body),
                                        "lifecycle-create": ok({"id": "1", "key": "PROJ-1"}),
                                        "idea-link": created()})
                self.assertIsInstance(out, TrackerError)
                self.assertEqual(out.subtype, "malformed_body")
                self.assertEqual(_posts(ex, "lifecycle-create"), [])

    def test_marker_search_reads_every_page(self) -> None:
        from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

        def search(request):
            query = parse_qs(urlparse(request.url_or_argv).query)
            if "nextPageToken" not in query:
                return ok({"issues": [_marked("PROJ-98", level=0), _marked("PROJ-97")],
                           "isLast": False, "nextPageToken": "p2"})
            self.assertEqual(query["nextPageToken"], ["p2"])
            return ok({"issues": [_marked("PROJ-99")], "isLast": True})

        out, ex = self._settle({"idea-marker-search": search,
                                "lifecycle-create": ok({"id": "1", "key": "PROJ-1"}),
                                "idea-link": created()})
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "several_parents")
        self.assertEqual(sorted(c["key"] for c in out.details["candidates"]),
                         ["PROJ-97", "PROJ-99"])
        self.assertTrue(all(c.method == "GET" for c in ex.calls))


class MovedOutIdeaIsRefused(unittest.TestCase):
    """fn-334 R17: an idea key Jira now files outside the discovery projects."""

    def test_read_parent_and_link_refuse_before_any_write(self) -> None:
        moved = {**idea(), "key": "PROJ-77"}
        config = jr_cfg(idea_keys=["IDEAS"])
        for verb in ("read", "parent", "link"):
            with self.subTest(verb=verb):
                ex = fake_execute({
                    "idea-link-types": ok(LINK_TYPES), "idea-read": ok(moved),
                    "idea-project": ok(PROJECT), "wire-comment-list": ok(comments()),
                    "lifecycle-create": ok({"id": "1", "key": "PROJ-1"}),
                    "idea-link": created()})
                if verb == "read":
                    out = _idea_mod().read(config, "IDEAS-7", ex)
                elif verb == "parent":
                    out = _idea_mod().settle_parent(config, "IDEAS-7", ex, body="B")
                else:
                    out = _idea_mod().link(config, "IDEAS-7", "PROJ-12", ex)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.CAPABILITY)
                self.assertIn("PROJ-77", out.message)
                self.assertTrue(all(c.method == "GET" for c in ex.calls))


def _flow_dir(tmp: str, config: dict) -> Path:
    flow = Path(tmp) / ".flow"
    flow.mkdir()
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return flow


class KeyOnlyRead(unittest.TestCase):
    """fn-334 R2: a Jira read by key or URL alone fills in the durable id."""

    def _read(self, display: str, responses: dict, config=None):
        ex = fake_execute(responses)
        with tempfile.TemporaryDirectory() as tmp:
            flow = _flow_dir(tmp, config or jr_cfg(idea_keys=["IDEAS"]))
            payload, code = W.run(flow, "read",
                                  locator=json.dumps({"display": display}),
                                  execute=ex)
        return json.loads(payload), code, ex

    def test_idea_key_alone_returns_the_id_and_the_idea_block(self) -> None:
        out, code, ex = self._read("IDEAS-7", {"wire-read": ok(idea())})
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["id"], IDEA_ID)
        self.assertEqual(out["data"]["identifier"], "IDEAS-7")
        self.assertTrue(Path(out["data"]["idea"]["reference"]).is_file())
        self.assertIn("/issue/IDEAS-7", ex.calls[0].url_or_argv)

    def test_ordinary_key_and_url_alone(self) -> None:
        issue = {"id": "10012", "key": "PROJ-12", "fields": {"summary": "S"}}
        for display in ("PROJ-12", f"{BASE}/browse/PROJ-12"):
            with self.subTest(display=display):
                out, code, ex = self._read(display, {"wire-read": ok(issue)})
                self.assertEqual(code, 0, out)
                self.assertEqual(out["data"]["id"], "10012")
                self.assertNotIn("idea", out["data"])
                self.assertIn("/issue/PROJ-12", ex.calls[0].url_or_argv)

    def test_unknown_key_and_another_site_keep_the_reads_errors(self) -> None:
        out, code, _ex = self._read("PROJ-404", {"wire-read": rejected(404, {})})
        self.assertEqual(out["class"], "not_found", out)
        out, code, ex = self._read("https://other.atlassian.net/browse/PROJ-12", {})
        self.assertEqual(out["class"], "invalid_input", out)
        self.assertEqual(ex.calls, [])


class MovedIssueIsRefused(unittest.TestCase):
    """fn-334 R3: the key Jira returns decides, and every write path refuses
    an idea before it writes; a display key that is an idea, before any request."""

    LOCATOR = {"durable": IDEA_ID, "display": "PROJ-7"}

    def _jira(self, *, moved_key: str = "IDEAS-7", ready: bool = False):
        calls = []

        def execute(request):
            calls.append(request)
            if request.method != "GET":
                return created()
            if "/transitions" in request.url_or_argv:
                return ok({"transitions": [{"id": "31", "to": {"id": "4"}}]})
            if "issueLinkType" in request.url_or_argv:
                return ok({"issueLinkTypes": [LINK_TYPES["issueLinkTypes"][0]]})
            if "/comment" in request.url_or_argv:
                return ok(comments())
            durable = request.url_or_argv.split("/issue/", 1)[1].split("?", 1)[0]
            key = moved_key if durable in (IDEA_ID, "PROJ-7") else f"PROJ-{durable[-2:]}"
            status = "Ready for delivery" if ready else "To Do"
            return ok({"id": IDEA_ID if key == moved_key else durable, "key": key,
                       "fields": {"summary": "S", "description": "d", "labels": [],
                                  "status": {"id": "1", "name": status,
                                             "statusCategory": {"key": "new"}},
                                  "issuelinks": []}})

        execute.calls = calls
        return execute

    def _writes(self, ex) -> list:
        return [(c.op, c.method) for c in ex.calls if c.method != "GET"]

    def assert_refused(self, out, ex, label) -> None:
        self.assertIsInstance(out, TrackerError, label)
        self.assertIs(out.cls, ErrorClass.CAPABILITY, label)
        self.assertEqual(out.subtype, "idea_read_only", label)
        self.assertEqual(self._writes(ex), [], label)

    def test_wire_writes_refuse_a_moved_issue_and_name_both_keys(self) -> None:
        for verb, kwargs in (("update", {"body": "spec body"}),
                             ("comment-add", {"body": "note"}),
                             ("label", {"add": ["x"]})):
            ex = self._jira()
            out = W.dispatch(verb, jr_cfg(idea_keys=["IDEAS"]),
                             locator=self.LOCATOR, execute=ex, **kwargs)
            self.assert_refused(out, ex, verb)
            self.assertIn("PROJ-7", out.message, verb)
            self.assertIn("IDEAS-7", out.message, verb)

    def test_pr_link_and_status_refuse_a_moved_issue(self) -> None:
        from flowctl_tracker.status.providers import apply_status  # noqa: PLC0415
        ex = self._jira()
        out = W.link_pr("jira", jr_cfg(idea_keys=["IDEAS"]), self.LOCATOR, ex,
                        url="https://github.com/o/r/pull/1")
        self.assert_refused(out, ex, "pr link")
        ex = self._jira()
        out = apply_status("jira", jr_cfg(idea_keys=["IDEAS"]), self.LOCATOR, {},
                           ex, target_slot="done")
        self.assert_refused(out, ex, "status")

    def test_relation_with_a_moved_end_writes_nothing(self) -> None:
        from flowctl_tracker import relate as R  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _linked_spec(flow, "fn-1-a", "10011", "PROJ-11")
            _linked_spec(flow, "fn-2-b", IDEA_ID, "PROJ-7")
            (flow / "config.json").write_text(
                json.dumps(jr_cfg(idea_keys=["IDEAS"])), encoding="utf-8")
            ex = self._jira()
            out = R.relate(flow, "fn-1-a", blocked_by="fn-2-b", execute=ex)
        self.assert_refused(out, ex, "relate")

    def test_unready_refuses_a_moved_issue_after_its_read(self) -> None:
        config = jr_cfg(idea_keys=["IDEAS"])
        config["tracker"]["readyState"] = "Ready for delivery"
        ex = self._jira(ready=True)
        out = W.dispatch("unready", config, locator=self.LOCATOR, execute=ex)
        self.assert_refused(out, ex, "unready")

    def test_question_to_an_idea_makes_no_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ex = self._jira()
            out = W.dispatch(
                "question", jr_cfg(idea_keys=["IDEAS"]),
                locator={"durable": IDEA_ID, "display": "IDEAS-7"}, body="Q?",
                subject_id="fn-1", blocked_stage="plan", reason_code="r",
                question_slug="q", flow_dir=Path(tmp), execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "idea_read_only")
        self.assertEqual(ex.calls, [])


class ColourTagsLeaveCodeAlone(unittest.TestCase):
    """fn-334 R7: code and {noformat} blocks are byte-for-byte unchanged."""

    def test_colour_is_removed_only_outside_code(self) -> None:
        description = (
            "Plain {color:#97a0af}grey{color} text.\n"
            "{code:python}\nx = \"{color:red}\"\n{code}\n"
            "{noformat}\n{color}raw{color}\n{noformat}\n"
            "Inline {noformat}{color:blue}{noformat} stays.")
        ex = fake_execute({"idea-read": ok(idea(description=description)),
                           "wire-comment-list": ok(comments())})
        out = _idea_mod().read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7", ex)
        body = out["idea"]["body"]
        self.assertIn("Plain grey text.", body)
        self.assertIn('```python\nx = "{color:red}"\n```', body)
        self.assertIn("```\n{color}raw{color}\n```", body)
        self.assertIn("{noformat}{color:blue}{noformat}", body)


if __name__ == "__main__":
    unittest.main()

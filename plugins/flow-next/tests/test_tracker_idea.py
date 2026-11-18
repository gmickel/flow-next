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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import classify  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402

FLOWCTL = ROOT / "scripts" / "flowctl.py"
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
        self.assertEqual(reference.name, "idea-intake.md")
        self.assertTrue(reference.is_file(), reference)

    def test_missing_reference_is_named_under_the_plugin_root(self) -> None:
        from flowctl_tracker.wire import jira as JW  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
                JW, "IDEA_REFERENCE", Path(tmp) / "missing.md"):
            out, _ = self._read(jr_cfg(idea_keys=["IDEAS"]), "IDEAS-7")
        self.assertEqual(out["idea"]["reference"], "references/idea-intake.md")

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
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
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
    (flow / "specs" / f"{spec_id}.json").write_text(json.dumps({
        "id": spec_id, "title": "Demo", "status": "open", "branch_name": spec_id,
        "tracker": {"id": durable, "identifier": display, "url": None,
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked"}}), encoding="utf-8")


class IdeaStatusAndRelationsAreReadOnly(unittest.TestCase):
    """R6 siblings: dependency links and status transitions skip the
    pre-write parent read, so each refuses an idea itself."""

    def _relate(self, a: str, b: str, *, many: bool = False):
        from flowctl_tracker import relate as R  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _linked_spec(flow, "fn-1-a", *a)
            _linked_spec(flow, "fn-2-b", *b)
            (flow / "config.json").write_text(
                json.dumps(jr_cfg(idea_keys=["IDEAS"])), encoding="utf-8")
            ex = fake_execute({})
            if many:
                out = R.relate_many(flow, "fn-1-a", ["fn-2-b"], event="plan",
                                    execute=ex)[0]
            else:
                out = R.relate(flow, "fn-1-a", blocked_by="fn-2-b", execute=ex)
        return out, ex

    def test_relation_with_an_idea_at_either_end_makes_no_request(self) -> None:
        idea_end, delivery = (IDEA_ID, "IDEAS-7"), ("10012", "PROJ-12")
        for many in (False, True):
            for a, b in ((idea_end, delivery), (delivery, idea_end)):
                out, ex = self._relate(a, b, many=many)
                self.assertIsInstance(out, TrackerError, (many, a))
                self.assertIs(out.cls, ErrorClass.CAPABILITY, (many, a))
                self.assertEqual(out.subtype, "idea_read_only", (many, a))
                self.assertEqual(ex.calls, [], (many, a))

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
        self.assertEqual([c.op for c in ex.calls], ["wire-read"])


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
        init = self._run(cwd, "init", "--json")
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
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

    def test_spec_is_never_linked_to_an_idea(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self._repo(tmp, jr_cfg(idea_keys=["IDEAS"]))
            made = self._run(cwd, "spec", "create", "--title", "Child", "--json")
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            spec_id = json.loads(made.stdout)["id"]
            linked_out = self._run(cwd, "sync", "set-tracker-id", spec_id,
                                   IDEA_ID, "--identifier", "IDEAS-7", "--json")
            self.assertNotEqual(linked_out.returncode, 0)
            self.assertIn("idea", linked_out.stdout.lower())
            self.assertIn("idea-intake.md", linked_out.stdout)
            tracker = json.loads((cwd / ".flow" / "specs" / f"{spec_id}.json")
                                 .read_text(encoding="utf-8"))["tracker"]
            self.assertIsNone(tracker.get("id"))
            minted = self._run(cwd, "spec", "create", "--title", "Minted",
                               "--tracker-first", "--tracker-identifier",
                               "IDEAS-7", "--json")
            self.assertNotEqual(minted.returncode, 0)
            # A stored idea identifier cannot be completed into a link either.
            (cwd / ".flow" / "config.json").write_text(json.dumps(jr_cfg()),
                                                       encoding="utf-8")
            stored = self._run(cwd, "spec", "create", "--title", "Old",
                               "--tracker-first", "--tracker-identifier",
                               "IDEAS-7", "--json")
            self.assertEqual(stored.returncode, 0, stored.stdout + stored.stderr)
            (cwd / ".flow" / "config.json").write_text(
                json.dumps(jr_cfg(idea_keys=["IDEAS"])), encoding="utf-8")
            completed = self._run(cwd, "sync", "set-tracker-id",
                                  json.loads(stored.stdout)["id"], IDEA_ID,
                                  "--json")
            self.assertNotEqual(completed.returncode, 0,
                                completed.stdout + completed.stderr)
            # A delivery issue still links as before.
            ok_link = self._run(cwd, "sync", "set-tracker-id", spec_id,
                                "10012", "--identifier", "PROJ-12", "--json")
            self.assertEqual(ok_link.returncode, 0, ok_link.stdout + ok_link.stderr)


if __name__ == "__main__":
    unittest.main()

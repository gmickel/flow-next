"""Lifecycle verbs: create / create-first / persist-external (fn-140.2).

Fake transport = the injected executor seam from fn-139.2 / test_tracker_wire.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import lifecycle as L  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def fake_execute(responses: dict):
    calls = []

    def execute(request):
        calls.append(request)
        if request.op not in responses:
            raise AssertionError(f"unexpected op {request.op!r}; have {sorted(responses)}")
        out = responses[request.op]
        if isinstance(out, list):
            if not out:
                raise AssertionError(f"no more responses for op {request.op!r}")
            out = out.pop(0)
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


GH_NODE = "I_kwDOTestNode1"
GL_ID = 84817009
LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
JR_ID = "10042"


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab",
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p"}}}}


def ln_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR"}}}}


def jr_cfg() -> dict:
    return {"tracker": {"type": "jira",
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2}}}}


def _write_flow(flow: Path, config: dict, *, spec_id: str = "fn-1-demo",
                tracker: dict | None = None) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    spec = {"id": spec_id, "title": "Demo",
            "tracker": tracker if tracker is not None else {
                "id": None, "identifier": None, "url": None,
                "lastSyncedAt": None, "depRelations": [],
            }}
    path = flow / "specs" / f"{spec_id}.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return path


def _receipts(flow: Path) -> list[dict]:
    runs = flow / "sync-runs"
    if not runs.is_dir():
        return []
    out = []
    for p in sorted(runs.glob("sync-*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


class LinkStateMigration(unittest.TestCase):
    def test_derive_all_four_legacy_shapes(self) -> None:
        self.assertEqual(L.derive_link_state({"linkState": "identifier_only",
                                              "id": "x"}), "identifier_only")
        self.assertEqual(L.derive_link_state({"id": "uuid-1",
                                              "identifier": "WOR-1"}), "linked")
        self.assertEqual(L.derive_link_state({"id": None,
                                              "identifier": "WOR-1"}), "identifier_only")
        self.assertEqual(L.derive_link_state({"id": None,
                                              "identifier": None}), "unlinked")

    def test_require_durable_distinct_messages(self) -> None:
        only = L.require_durable({"id": None, "identifier": "WOR-1"})
        self.assertIsInstance(only, TrackerError)
        self.assertIs(only.cls, ErrorClass.UNRESOLVED)
        self.assertIn("identifier_only", only.message)

        bare = L.require_durable({"id": None, "identifier": None})
        self.assertIsInstance(bare, TrackerError)
        self.assertIs(bare.cls, ErrorClass.UNRESOLVED)
        self.assertIn("unlinked", bare.message)
        self.assertNotEqual(only.message, bare.message)

        got = L.require_durable({"id": "uuid-1", "identifier": "WOR-1"})
        self.assertEqual(got, "uuid-1")


class CreateReceiptSemantics(unittest.TestCase):
    def test_create_writes_receipt_create_first_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg())
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42",
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           event="work.firstClaim", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["type"], "sync")
            self.assertEqual(receipts[0]["status"], "pushed")
            self.assertEqual(receipts[0]["event"], "work.firstClaim")
            self.assertEqual(receipts[0]["tracker_id"], GH_NODE)
            self.assertNotIn("receipts", str(flow / "sync-runs"))

            # create-first: fresh flow, no receipt
            flow2 = Path(tmp) / "cf" / ".flow"
            flow2.mkdir(parents=True)
            (flow2 / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            key = L.compute_create_first_key("github", "T2", "B2")
            ex2 = fake_execute({"lifecycle-create": ok({
                "id": 2, "node_id": "I_other", "number": 7,
                "html_url": "https://github.com/o/r/issues/7",
            })})
            out2 = L.create_first(flow2, title="T2", body="B2",
                                  retry_key=key, execute=ex2)
            self.assertNotIsInstance(out2, TrackerError)
            self.assertEqual(_receipts(flow2), [])
            self.assertTrue((flow2 / "create-first" / f"{key}.json").is_file())


class CreateFirstRetry(unittest.TestCase):
    def test_retry_returns_recorded_issue_with_no_second_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            key = L.compute_create_first_key("github", "T", "B")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42",
            })})
            first = L.create_first(flow, title="T", body="B",
                                   retry_key=key, execute=ex)
            self.assertEqual(first["id"], GH_NODE)
            self.assertFalse(first["retried"])
            self.assertEqual(len(ex.calls), 1)

            ex2 = fake_execute({})  # any create would AssertionError
            second = L.create_first(flow, title="T", body="B",
                                    retry_key=key, execute=ex2)
            self.assertEqual(second["id"], GH_NODE)
            self.assertTrue(second["retried"])
            self.assertEqual(len(ex2.calls), 0)


class PersistExternal(unittest.TestCase):
    def test_happy_path_resolves_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg())
            ex = fake_execute({"lifecycle-resolve-uuid": ok({
                "data": {"issue": {"id": LN_UUID, "identifier": "WOR-17",
                                   "url": "https://linear.app/x/issue/WOR-17"}},
            })})
            out = L.persist_external(
                flow, "fn-1-demo", identifier="WOR-17", source="mcp", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["id"], LN_UUID)
            self.assertEqual(out["linkState"], "linked")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], LN_UUID)
            self.assertEqual(saved["linkState"], "linked")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["tracker_id"], LN_UUID)

    def test_graphql_down_persists_identifier_only_plus_warning_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg())
            ex = fake_execute({
                "lifecycle-resolve-uuid": TrackerError(
                    ErrorClass.TRANSPORT, "unreachable", subtype="timeout"),
            })
            out = L.persist_external(
                flow, "fn-1-demo", identifier="WOR-17",
                url="https://linear.app/x/issue/WOR-17", source="mcp", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertIsNone(out["id"])
            self.assertEqual(out["linkState"], "identifier_only")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertIsNone(saved["id"])
            self.assertEqual(saved["identifier"], "WOR-17")
            self.assertEqual(saved["linkState"], "identifier_only")
            # Must NOT migrate as unlinked
            self.assertEqual(L.derive_link_state(saved), "identifier_only")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            note = receipts[0]["note"] or ""
            # Round-1 finding 5: degradation is the STRUCTURED field; the note
            # stays informational.
            self.assertIn("identifier_only", note)
            self.assertIn("WOR-17", note)
            self.assertIn("https://linear.app/x/issue/WOR-17", note)
            self.assertEqual((receipts[0].get("degraded") or {}).get("kind"),
                             "identifier_only")

    def test_non_mcp_source_is_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            out = L.persist_external(
                flow, "fn-1-demo", identifier="WOR-17", source="cli", execute=fake_execute({}))
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)


class CompleteIdentifierOnly(unittest.TestCase):
    def test_atomic_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg(), tracker={
                "id": None, "identifier": "WOR-17",
                "url": "https://linear.app/x/issue/WOR-17",
                "linkState": "identifier_only", "depRelations": [],
            })
            ex = fake_execute({"lifecycle-resolve-uuid": ok({
                "data": {"issue": {"id": LN_UUID, "identifier": "WOR-17",
                                   "url": "https://linear.app/x/issue/WOR-17"}},
            })})
            out = L.complete_identifier_only(flow, "fn-1-demo", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertTrue(out["completed"])
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], LN_UUID)
            self.assertEqual(saved["linkState"], "linked")
            # Single atomic write: both fields present together
            self.assertIsNotNone(saved["id"])
            self.assertEqual(saved["linkState"], "linked")


class CreateGuards(unittest.TestCase):
    def test_already_linked_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(), tracker={
                "id": GH_NODE, "identifier": "#42", "url": "u",
                "linkState": "linked", "depRelations": [],
            })
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           execute=fake_execute({}))
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "already_linked")

    def test_durable_collision_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(), spec_id="fn-1-demo")
            _write_flow(flow, gh_cfg(), spec_id="fn-2-other", tracker={
                "id": GH_NODE, "identifier": "#99", "url": "u",
                "linkState": "linked", "depRelations": [],
            })
            # Overwrite config once (second write_flow rewrote config; fine)
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42",
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "durable_collision")
            # Spec must remain unlinked
            saved = json.loads((flow / "specs" / "fn-1-demo.json").read_text())["tracker"]
            self.assertIsNone(saved.get("id"))


class ProviderCreateShapes(unittest.TestCase):
    def test_github_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg())
            ex = fake_execute({"lifecycle-create": ok({
                "id": 999, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42",
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out, {"id": GH_NODE, "identifier": "#42",
                                   "url": "https://github.com/o/r/issues/42",
                                   "linkState": "linked"})
            req = ex.calls[0]
            self.assertIn("repos/o/r/issues", str(req.url_or_argv))
            self.assertEqual(req.method, "POST")

    def test_gitlab_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gl_cfg())
            ex = fake_execute({"lifecycle-create": ok({
                "id": GL_ID, "iid": 12,
                "web_url": "https://gitlab.com/g/p/-/issues/12",
                "references": {"full": "g/p#12"},
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out["id"], str(GL_ID))
            self.assertEqual(out["identifier"], "g/p#12")
            self.assertIn("projects/1/issues", str(ex.calls[0].url_or_argv))

    def test_gitlab_falls_back_to_project_iid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gl_cfg())
            ex = fake_execute({"lifecycle-create": ok({
                "id": GL_ID, "iid": 12,
                "web_url": "https://gitlab.com/g/p/-/issues/12",
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out["identifier"], "g/p#12")

    def test_linear_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute({"lifecycle-create": ok({
                "data": {"issueCreate": {
                    "success": True,
                    "issue": {"id": LN_UUID, "identifier": "WOR-17",
                              "url": "https://linear.app/x/issue/WOR-17"},
                }},
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out["id"], LN_UUID)
            self.assertEqual(out["identifier"], "WOR-17")
            body = json.loads(ex.calls[0].body.decode())
            self.assertIn("issueCreate", body["query"])
            self.assertEqual(body["variables"]["input"]["teamId"], "team-1")

    def test_jira_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, jr_cfg())
            ex = fake_execute({"lifecycle-create": ok({
                "id": JR_ID, "key": "SCRUM-1",
                "self": "https://ex.atlassian.net/rest/api/2/issue/10042",
            })})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out["id"], JR_ID)
            self.assertEqual(out["identifier"], "SCRUM-1")
            self.assertEqual(out["url"], "https://ex.atlassian.net/browse/SCRUM-1")
            url = str(ex.calls[0].url_or_argv)
            self.assertIn("/rest/api/2/issue", url)
            payload = json.loads(ex.calls[0].body.decode())
            self.assertEqual(payload["fields"]["project"]["id"], "10000")
            self.assertEqual(payload["fields"]["issuetype"]["id"], "10001")


class NoReconcileCli(unittest.TestCase):
    def test_package_has_no_reconcile_verb(self) -> None:
        self.assertFalse(hasattr(L, "reconcile"))
        src = (ROOT / "scripts" / "flowctl.py").read_text(encoding="utf-8")
        # CLI must not register a `tracker reconcile` command.
        self.assertNotRegex(src, r'add_parser\(\s*"reconcile"')


class CreateFirstKeyParity(unittest.TestCase):
    def test_matches_flowctl_compute(self) -> None:
        import flowctl  # noqa: PLC0415
        for typ, title, body in (
            ("github", "T", "B"),
            (" GitHub ", "x", ""),
            ("linear", "中文", "body\n"),
        ):
            self.assertEqual(
                L.compute_create_first_key(typ, title, body),
                flowctl.compute_create_first_key(typ, title, body),
            )


if __name__ == "__main__":
    unittest.main()


SPEC_ID = "fn-1-demo"


def gql_issue(issue) -> Response:
    return ok({"data": {"issue": issue}})


class HostRoundFixes(unittest.TestCase):
    """persist-external --id verification + create receipt-failure honesty."""

    def test_supplied_durable_is_verified_and_mismatch_conflicts(self) -> None:
        flow = self._flow()
        ex = fake_execute({"lifecycle-resolve-uuid": gql_issue(
            {"id": "real-uuid", "identifier": "WOR-9", "url": None})})
        out = L.persist_external(flow, SPEC_ID, identifier="WOR-9",
                                 durable_id="typo-uuid", source="mcp", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "durable_mismatch")

    def test_supplied_durable_matching_graphql_links(self) -> None:
        flow = self._flow()
        ex = fake_execute({"lifecycle-resolve-uuid": gql_issue(
            {"id": "real-uuid", "identifier": "WOR-9", "url": "https://l/9"})})
        out = L.persist_external(flow, SPEC_ID, identifier="WOR-9",
                                 durable_id="real-uuid", source="mcp", execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(out["linkState"], "linked")

    def test_supplied_durable_with_graphql_down_is_trusted(self) -> None:
        flow = self._flow()
        ex = fake_execute({"lifecycle-resolve-uuid": TrackerError(
            ErrorClass.TRANSPORT, "down")})
        out = L.persist_external(flow, SPEC_ID, identifier="WOR-9",
                                 durable_id="asserted-uuid", source="mcp", execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(out["id"], "asserted-uuid")
        self.assertEqual(out["linkState"], "linked")

    def _flow(self):
        import tempfile as _t
        td = _t.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        flow = Path(td.name)
        _write_flow(flow, ln_cfg(), spec_id=SPEC_ID)
        return flow


class Round1Fixes(unittest.TestCase):
    """Path containment, symlink safety, link-state guard, degrade classes."""

    def test_spec_id_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            victim = Path(tmp) / "victim.json"
            victim.write_text('{"precious": true}', encoding="utf-8")
            out = L.create(flow, "../../victim", title="t", body="b",
                           execute=fake_execute({}))
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(json.loads(victim.read_text(encoding="utf-8")),
                             {"precious": True}, "no byte may change")

    def test_symlinked_create_first_dir_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            outside = Path(tmp) / "outside"
            outside.mkdir()
            try:
                (flow / "create-first").symlink_to(outside,
                                                   target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            out = L.create_first(flow, title="t", body="b",
                                 retry_key="a" * 16, execute=fake_execute({}))
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(list(outside.iterdir()), [],
                             "nothing written through the symlink")

    def test_persist_external_never_repoints_a_linked_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(), tracker={
                "id": "old-uuid", "identifier": "WOR-1",
                "url": None, "linkState": "linked"})
            out = L.persist_external(flow, "fn-1-demo", identifier="NEW-2",
                                     source="mcp", execute=fake_execute({}))
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            saved = json.loads((flow / "specs" / "fn-1-demo.json")
                               .read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], "old-uuid", "durable never erased")

    def test_persist_external_same_identifier_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(), tracker={
                "id": "old-uuid", "identifier": "WOR-1",
                "url": None, "linkState": "linked"})
            out = L.persist_external(flow, "fn-1-demo", identifier="WOR-1",
                                     source="mcp", execute=fake_execute({}))
            self.assertNotIsInstance(out, TrackerError)
            self.assertTrue(out.get("idempotent"))

    def test_semantic_resolution_errors_propagate_not_degrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            # issue: null over a healthy 200 is NOT unreachable - it is a real
            # not-found verdict about this identifier.
            ex = fake_execute({"lifecycle-resolve-uuid": gql_issue(None)})
            out = L.persist_external(flow, "fn-1-demo", identifier="GHOST-9",
                                     source="mcp", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.NOT_FOUND)
            saved = json.loads((flow / "specs" / "fn-1-demo.json")
                               .read_text(encoding="utf-8")).get("tracker")
            self.assertNotEqual((saved or {}).get("linkState"), "identifier_only",
                                "a semantic failure must not fake a degraded link")

    def test_degraded_is_structured_on_result_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute({"lifecycle-resolve-uuid": TrackerError(
                ErrorClass.TRANSPORT, "down")})
            out = L.persist_external(flow, "fn-1-demo", identifier="WOR-3",
                                     source="mcp", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["degraded"]["kind"], "identifier_only")
            self.assertEqual(out["degraded"]["reason"], "transport")


class CreateFirstStorageIsSecuredBeforeRemoteMutation(unittest.TestCase):
    def test_missing_gitignore_pattern_is_added_before_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            (flow / ".gitignore").write_text("receipts/\n", encoding="utf-8")
            key = L.compute_create_first_key("github", "T", "B")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42"})})
            out = L.create_first(flow, title="T", body="B",
                                 retry_key=key, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            gi = (flow / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("create-first/", gi)
            self.assertIn("receipts/", gi, "existing patterns preserved")

    def test_existing_pattern_is_not_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            (flow / ".gitignore").write_text("create-first/\n", encoding="utf-8")
            key = L.compute_create_first_key("github", "T", "B")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42"})})
            L.create_first(flow, title="T", body="B", retry_key=key, execute=ex)
            gi = (flow / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(gi.count("create-first/"), 1)

    def test_symlinked_gitignore_aborts_before_any_remote_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            victim = Path(tmp) / "victim.txt"
            victim.write_text("precious", encoding="utf-8")
            try:
                (flow / ".gitignore").symlink_to(victim)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            ex = fake_execute({})  # any remote call would AssertionError
            out = L.create_first(flow, title="T", body="B",
                                 retry_key="a" * 16, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(len(ex.calls), 0, "abort BEFORE remote mutation")
            self.assertEqual(victim.read_text(encoding="utf-8"), "precious")

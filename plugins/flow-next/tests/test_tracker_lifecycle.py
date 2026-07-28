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
            # Epic contract: degradation is EXCLUSIVELY the structured field -
            # the note never carries a degradation sentence.
            note = receipts[0]["note"] or ""
            self.assertNotIn("identifier_only", note)
            self.assertNotIn("degraded", note.lower())
            degraded = receipts[0].get("degraded") or {}
            self.assertEqual(degraded.get("kind"), "identifier_only")
            self.assertEqual(degraded.get("identifier"), "WOR-17")
            self.assertEqual(degraded.get("url"),
                             "https://linear.app/x/issue/WOR-17")

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


class GitignoreRuleSemanticsNotSubstrings(unittest.TestCase):
    def _run_create_first(self, gitignore_text: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            (flow / ".gitignore").write_text(gitignore_text, encoding="utf-8")
            key = L.compute_create_first_key("github", "T", "B")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42"})})
            out = L.create_first(flow, title="T", body="B",
                                 retry_key=key, execute=ex)
            assert not isinstance(out, TrackerError), out
            return (flow / ".gitignore").read_text(encoding="utf-8")

    def test_commented_rule_is_not_an_active_rule(self) -> None:
        gi = self._run_create_first("# create-first/\n")
        self.assertTrue(L.verbs._create_first_rule_active(gi),
                        "an ACTIVE rule must exist after the call")
        self.assertIn("\ncreate-first/", "\n" + gi.replace("# create-first/", ""))

    def test_negated_rule_is_re_secured_by_appending_last(self) -> None:
        gi = self._run_create_first("create-first/\n!create-first/\n")
        self.assertTrue(L.verbs._create_first_rule_active(gi),
                        "last-match-wins: the appended rule beats the negation")

    def test_active_rule_variants_are_recognized(self) -> None:
        for text in ("create-first/\n", "/create-first/\n", "create-first\n"):
            self.assertTrue(L.verbs._create_first_rule_active(text), repr(text))
        for text in ("# create-first/\n", "!create-first/\n",
                     "create-first/\n!create-first/\n", ""):
            self.assertFalse(L.verbs._create_first_rule_active(text), repr(text))


class LegacyBlockDefaultsDoNotClobberMigration(unittest.TestCase):
    """PR #246 review: merging {"linkState": "unlinked"} defaults over a
    legacy block that predates the field defeated derive_link_state's
    migration read - create duplicated the issue, status/relate/sync-body
    rejected the existing link as unresolved."""

    def test_merged_tracker_derives_link_state_from_raw_block(self) -> None:
        from flowctl_tracker.lifecycle.helpers import merged_tracker
        legacy = {"tracker": {"id": "I_legacy", "identifier": "#7"}}
        self.assertEqual(merged_tracker(legacy)["linkState"], "linked")
        self.assertEqual(
            merged_tracker({"tracker": {"id": None, "identifier": "WOR-9"}})
            ["linkState"], "identifier_only")
        self.assertEqual(merged_tracker({"tracker": {}})["linkState"],
                         "unlinked")
        # An explicit stored linkState still wins over derivation.
        self.assertEqual(
            merged_tracker({"tracker": {"id": "x",
                                        "linkState": "identifier_only"}})
            ["linkState"], "identifier_only")
        # Defaults are still filled in for the rest of the schema.
        self.assertEqual(merged_tracker(legacy)["depRelations"], [])

    def test_legacy_linked_spec_refuses_bare_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(),
                        tracker={"id": "I_legacy", "identifier": "#7"})
            ex = fake_execute({})  # any provider call would AssertionError
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "already_linked")
            self.assertEqual(len(ex.calls), 0,
                             "refusal must happen before any remote call")

    def test_legacy_linked_block_passes_require_durable_after_merge(self) -> None:
        from flowctl_tracker.lifecycle.helpers import merged_tracker
        got = L.require_durable(
            merged_tracker({"tracker": {"id": "uuid-1", "identifier": "WOR-1"}}))
        self.assertEqual(got, "uuid-1")


class CreateLinkWriteFailureCarriesCreatedIdentity(unittest.TestCase):
    """PR #246 review: provider create succeeded but the tracker-block write
    failed -> a bare error read as "nothing happened" and a retry duplicated
    the issue. The error must carry the created durable identity so the
    caller can link the existing issue instead of re-creating."""

    def test_write_failure_error_carries_id_and_completed_steps(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            spec_path = _write_flow(flow, gh_cfg())
            before = spec_path.read_text(encoding="utf-8")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42"})})
            boom = TrackerError(ErrorClass.TRANSPORT,
                                "atomic write failed: disk full",
                                subtype="write")
            # The persist path runs through helpers.locked_tracker_write,
            # which resolves write_tracker_block in the helpers namespace.
            with mock.patch.object(L.helpers, "write_tracker_block",
                                   return_value=boom):
                out = L.create(flow, "fn-1-demo", title="T", body="B",
                               execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.TRANSPORT)
            details = out.details or {}
            self.assertEqual(details.get("completed_steps"), ["create"])
            self.assertEqual(details.get("id"), GH_NODE)
            self.assertEqual(details.get("identifier"), "#42")
            self.assertEqual(details.get("url"),
                             "https://github.com/o/r/issues/42")
            # The spec really is still unlinked, and no receipt was written.
            self.assertEqual(spec_path.read_text(encoding="utf-8"), before)
            self.assertEqual(_receipts(flow), [])


class PersistExternalReceiptFailureCarriesLinkedIdentity(unittest.TestCase):
    """PR #246 review: the tracker block was persisted but the receipt write
    failed -> a bare error read as "nothing happened" even though the spec is
    already linked, and a retry took the idempotent linked return without ever
    reporting the partial success. The error must carry the completed link
    step plus the linked identity (mirrors create's receipt-failure branch)."""

    def test_receipt_failure_error_carries_link_and_identity(self) -> None:
        from unittest import mock

        from flowctl_tracker.lifecycle import verbs
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            spec_path = _write_flow(flow, ln_cfg())
            ex = fake_execute({"lifecycle-resolve-uuid": ok({
                "data": {"issue": {"id": LN_UUID, "identifier": "WOR-17",
                                   "url": "https://linear.app/x/issue/WOR-17"}},
            })})
            boom = TrackerError(ErrorClass.TRANSPORT,
                                "receipt write failed: disk full",
                                subtype="write")
            with mock.patch.object(verbs, "write_sync_receipt",
                                   return_value=boom):
                out = L.persist_external(flow, "fn-1-demo", identifier="WOR-17",
                                         source="mcp", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.TRANSPORT)
            details = out.details or {}
            self.assertEqual(details.get("completed_steps"), ["link"])
            self.assertEqual(details.get("id"), LN_UUID)
            self.assertEqual(details.get("identifier"), "WOR-17")
            self.assertEqual(details.get("linkState"), "linked")
            # The persisted link is NOT rolled back.
            saved = json.loads(spec_path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], LN_UUID)
            self.assertEqual(saved["linkState"], "linked")


class Round5PersistIntegrity(unittest.TestCase):
    """PR #246 review: reload-under-lock persistence for create and
    persist-external. The pre-request spec snapshot must never be replayed
    wholesale - a concurrent flowctl update to the same spec landing while
    the provider request is in flight would be silently erased."""

    def test_create_link_write_does_not_erase_concurrent_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, gh_cfg())

            def concurrent_create(req):
                # Another command updates the same spec while create() is
                # mid-flight (after its snapshot load, before its persist).
                data = json.loads(path.read_text(encoding="utf-8"))
                data["title"] = "CONCURRENT"
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok({"id": 1, "node_id": GH_NODE, "number": 42,
                           "html_url": "https://github.com/o/r/issues/42"})

            ex = fake_execute({"lifecycle-create": concurrent_create})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "CONCURRENT",
                             "persist must reload, never replay the stale snapshot")
            self.assertEqual(saved["tracker"]["id"], GH_NODE)
            self.assertEqual(saved["tracker"]["linkState"], "linked")

    def test_persist_external_does_not_erase_concurrent_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg())

            def concurrent_resolve(req):
                data = json.loads(path.read_text(encoding="utf-8"))
                data["title"] = "CONCURRENT"
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok({"data": {"issue": {
                    "id": LN_UUID, "identifier": "WOR-17",
                    "url": "https://linear.app/x/issue/WOR-17"}}})

            ex = fake_execute({"lifecycle-resolve-uuid": concurrent_resolve})
            out = L.persist_external(flow, "fn-1-demo", identifier="WOR-17",
                                     source="mcp", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "CONCURRENT",
                             "persist must reload, never replay the stale snapshot")
            self.assertEqual(saved["tracker"]["id"], LN_UUID)
            self.assertEqual(saved["tracker"]["linkState"], "linked")

    def test_complete_identifier_only_does_not_erase_concurrent_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg(),
                               tracker={"id": None, "identifier": "WOR-17",
                                        "url": None, "lastSyncedAt": None,
                                        "linkState": "identifier_only",
                                        "depRelations": []})

            def concurrent_resolve(req):
                # Another command updates the same spec while the GraphQL
                # UUID resolve is in flight (after the snapshot load,
                # before the persist).
                data = json.loads(path.read_text(encoding="utf-8"))
                data["title"] = "CONCURRENT"
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok({"data": {"issue": {
                    "id": LN_UUID, "identifier": "WOR-17",
                    "url": "https://linear.app/x/issue/WOR-17"}}})

            ex = fake_execute({"lifecycle-resolve-uuid": concurrent_resolve})
            out = L.complete_identifier_only(flow, "fn-1-demo", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["linkState"], "linked")
            self.assertTrue(out["completed"])
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "CONCURRENT",
                             "persist must reload, never replay the stale snapshot")
            self.assertEqual(saved["tracker"]["id"], LN_UUID)
            self.assertEqual(saved["tracker"]["linkState"], "linked")
            self.assertEqual(saved["tracker"]["identifier"], "WOR-17")
            self.assertEqual(saved["tracker"]["url"],
                             "https://linear.app/x/issue/WOR-17")

    def test_complete_identifier_only_refuses_concurrent_relink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg(),
                               tracker={"id": None, "identifier": "WOR-17",
                                        "url": None, "lastSyncedAt": None,
                                        "linkState": "identifier_only",
                                        "depRelations": []})

            def concurrent_set_tracker_id(req):
                # A concurrent `sync set-tracker-id` links the spec to a
                # DIFFERENT durable identity while the GraphQL UUID resolve
                # is in flight. The locked merge must re-check the reloaded
                # block and refuse - an unconditional merge would silently
                # repoint the spec to the resolution result for the OLD
                # identifier.
                data = json.loads(path.read_text(encoding="utf-8"))
                data["tracker"] = {"id": "lin_OTHER_uuid", "identifier": "WOR-99",
                                   "url": "https://linear.app/x/issue/WOR-99",
                                   "linkState": "linked", "depRelations": []}
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok({"data": {"issue": {
                    "id": LN_UUID, "identifier": "WOR-17",
                    "url": "https://linear.app/x/issue/WOR-17"}}})

            ex = fake_execute({"lifecycle-resolve-uuid": concurrent_set_tracker_id})
            out = L.complete_identifier_only(flow, "fn-1-demo", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "already_linked")
            details = out.details or {}
            self.assertEqual(details.get("linkState"), "linked")
            self.assertEqual(details.get("identifier"), "WOR-99")
            self.assertEqual(details.get("id"), "lin_OTHER_uuid")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], "lin_OTHER_uuid",
                             "concurrent identity must survive untouched")
            self.assertEqual(saved["identifier"], "WOR-99")
            self.assertEqual(saved["linkState"], "linked")

    def test_persist_external_degraded_write_preserves_concurrent_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg())

            def concurrent_then_down(req):
                data = json.loads(path.read_text(encoding="utf-8"))
                data["title"] = "CONCURRENT"
                path.write_text(json.dumps(data), encoding="utf-8")
                return TrackerError(ErrorClass.TRANSPORT, "unreachable")

            ex = fake_execute({"lifecycle-resolve-uuid": concurrent_then_down})
            out = L.persist_external(flow, "fn-1-demo", identifier="WOR-17",
                                     url="https://linear.app/x/issue/WOR-17",
                                     source="mcp", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["linkState"], "identifier_only")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "CONCURRENT")
            self.assertEqual(saved["tracker"]["identifier"], "WOR-17")
            self.assertEqual(saved["tracker"]["linkState"], "identifier_only")


class CreateFirstClaimSerialization(unittest.TestCase):
    """PR #246 review: two concurrent create-first calls with the same retry
    key could both observe the record absent and both run provider_create -
    two remote issues, the last record write hiding the first. The retry key
    is claimed under the shared writer lock before the remote create."""

    def _flow(self, tmp: str) -> Path:
        flow = Path(tmp) / ".flow"
        flow.mkdir()
        (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
        return flow

    def test_concurrent_same_key_refused_single_remote_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp)
            key = L.compute_create_first_key("github", "T", "B")
            rec_path = flow / "create-first" / f"{key}.json"
            inner: dict = {}

            def racing_create(req):
                # The claim must be durable BEFORE the remote create...
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                # ...so a second worker racing in while the create is in
                # flight refuses instead of creating a duplicate.
                inner["out"] = L.create_first(
                    flow, title="T", body="B", retry_key=key,
                    execute=fake_execute({}))  # any create would AssertionError
                return ok({"id": 1, "node_id": GH_NODE, "number": 42,
                           "html_url": "https://github.com/o/r/issues/42"})

            ex = fake_execute({"lifecycle-create": racing_create})
            out = L.create_first(flow, title="T", body="B",
                                 retry_key=key, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertFalse(out["retried"])
            self.assertEqual(len(ex.calls), 1, "exactly ONE remote create")

            raced = inner["out"]
            self.assertIsInstance(raced, TrackerError)
            self.assertIs(raced.cls, ErrorClass.CONFLICT)
            self.assertEqual(raced.subtype, "create_in_flight")
            self.assertTrue(raced.auto_retryable)
            self.assertEqual((raced.details or {}).get("retryKey"), key)

            # After the winner finalizes, a retry reuses its recorded issue.
            third = L.create_first(flow, title="T", body="B",
                                   retry_key=key, execute=fake_execute({}))
            self.assertEqual(third["id"], GH_NODE)
            self.assertTrue(third["retried"])

    def test_stale_claim_from_dead_pid_is_reclaimed(self) -> None:
        import socket
        import time
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp)
            key = L.compute_create_first_key("github", "T", "B")
            rec_path = flow / "create-first" / f"{key}.json"
            rec_path.parent.mkdir(parents=True)
            # pid 0 is never alive; claimedAt is past the stale window.
            rec_path.write_text(json.dumps({
                "retryKey": key, "status": "pending", "pid": 0,
                "host": socket.gethostname(),
                "claimedAt": time.time() - 999,
                "title": "T", "transport": "github"}), encoding="utf-8")
            ex = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42"})})
            out = L.create_first(flow, title="T", body="B",
                                 retry_key=key, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertFalse(out["retried"])
            saved = json.loads(rec_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["id"], GH_NODE, "record finalized")
            self.assertNotIn("status", saved)

    def test_observed_create_failure_releases_the_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp)
            key = L.compute_create_first_key("github", "T", "B")
            rec_path = flow / "create-first" / f"{key}.json"
            ex = fake_execute({"lifecycle-create": TrackerError(
                ErrorClass.TRANSPORT, "boom")})
            out = L.create_first(flow, title="T", body="B",
                                 retry_key=key, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.TRANSPORT)
            self.assertFalse(rec_path.exists(),
                             "claim released on OBSERVED failure so a retry "
                             "may create again")
            ex2 = fake_execute({"lifecycle-create": ok({
                "id": 1, "node_id": GH_NODE, "number": 42,
                "html_url": "https://github.com/o/r/issues/42"})})
            retry = L.create_first(flow, title="T", body="B",
                                   retry_key=key, execute=ex2)
            self.assertNotIsInstance(retry, TrackerError)
            self.assertFalse(retry["retried"])


class Round6CreateSpecClaimSerialization(unittest.TestCase):
    """PR #246 review: two concurrent create/facade-push calls against the
    same UNLINKED spec could both pass the in-memory linkState check and both
    reach the provider mutation - two remote issues, the later link write
    replacing the first identity and orphaning it. The spec is reserved under
    the shared writer lock (create-first's claim pattern, keyed on the spec
    id) BEFORE the remote create."""

    def test_concurrent_creates_single_remote_create_loser_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, gh_cfg())
            rec_path = flow / "create-first" / "spec-fn-1-demo.json"
            inner: dict = {}

            def racing_create(req):
                # The claim must be durable BEFORE the remote create...
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                self.assertEqual(claim.get("specId"), "fn-1-demo")
                # ...so a second worker racing in while the create is in
                # flight refuses instead of creating a duplicate (any create
                # attempt on the empty executor would AssertionError).
                inner["out"] = L.create(flow, "fn-1-demo", title="T", body="B",
                                        execute=fake_execute({}))
                return ok({"id": 1, "node_id": GH_NODE, "number": 42,
                           "html_url": "https://github.com/o/r/issues/42"})

            ex = fake_execute({"lifecycle-create": racing_create})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(len(ex.calls), 1, "exactly ONE remote create")

            raced = inner["out"]
            self.assertIsInstance(raced, TrackerError)
            self.assertIs(raced.cls, ErrorClass.CONFLICT)
            self.assertEqual(raced.subtype, "create_in_flight")
            self.assertTrue(raced.auto_retryable)
            self.assertEqual((raced.details or {}).get("specId"), "fn-1-demo")

            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], GH_NODE)
            self.assertEqual(saved["linkState"], "linked")
            self.assertFalse(rec_path.exists(),
                             "claim released after the link persisted")

    def test_concurrent_identity_is_never_clobbered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, gh_cfg())
            rec_path = flow / "create-first" / "spec-fn-1-demo.json"

            def link_appears_mid_flight(req):
                # An identity lands on the spec while the provider create is
                # in flight (e.g. a path that takes no create claim). The
                # locked link write must refuse to replace it - replacing it
                # is exactly the orphan-duplicate the review cites.
                data = json.loads(path.read_text(encoding="utf-8"))
                data["tracker"] = {"id": "I_kwDOOtherNode", "identifier": "#7",
                                   "url": "u7", "linkState": "linked",
                                   "depRelations": []}
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok({"id": 1, "node_id": GH_NODE, "number": 42,
                           "html_url": "https://github.com/o/r/issues/42"})

            ex = fake_execute({"lifecycle-create": link_appears_mid_flight})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "already_linked")
            details = out.details or {}
            # Partial-success decoration: the created identity is in hand so
            # the caller can clean up / link it, never a bare failure.
            self.assertEqual(details.get("completed_steps"), ["create"])
            self.assertEqual(details.get("id"), GH_NODE)
            self.assertEqual(details.get("identifier"), "#42")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], "I_kwDOOtherNode",
                             "existing link must survive")
            self.assertEqual(saved["identifier"], "#7")
            self.assertFalse(rec_path.exists(), "claim released")

    def test_relinked_spec_refused_under_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, gh_cfg())
            # A stale-but-reclaimable claim plus a spec that got LINKED after
            # the caller's unlocked check: the locked re-check must refuse
            # before any remote mutation.
            data = json.loads(path.read_text(encoding="utf-8"))

            real_load = L.create.__globals__["load_spec"]
            calls = {"n": 0}

            def linking_load(fd, sid):
                calls["n"] += 1
                if calls["n"] == 2:
                    # Between the unlocked check (first load) and the locked
                    # re-check (second load) another worker links the spec.
                    data["tracker"] = {"id": GH_NODE, "identifier": "#42",
                                       "url": "u", "linkState": "linked",
                                       "depRelations": []}
                    path.write_text(json.dumps(data), encoding="utf-8")
                return real_load(fd, sid)

            L.create.__globals__["load_spec"] = linking_load
            try:
                out = L.create(flow, "fn-1-demo", title="T", body="B",
                               execute=fake_execute({}))
            finally:
                L.create.__globals__["load_spec"] = real_load
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "already_linked")


class Round6LockedCollisionScan(unittest.TestCase):
    """PR #246 review: the durable-collision scan ran OUTSIDE the writer
    lock - two specs concurrently persisting the same durable id could both
    pass the scan, then both serialized writes succeed, violating the
    one-spec-per-durable-id invariant. The scan now runs INSIDE the same
    critical section as the link write."""

    def _two_specs(self, tmp: str) -> tuple[Path, Path, Path]:
        flow = Path(tmp) / ".flow"
        a = _write_flow(flow, ln_cfg(), spec_id="fn-2-other")
        b = _write_flow(flow, ln_cfg(), spec_id="fn-1-demo")
        return flow, a, b

    @staticmethod
    def _link_other(other: Path) -> None:
        data = json.loads(other.read_text(encoding="utf-8"))
        data["tracker"] = {"id": LN_UUID, "identifier": "WOR-17",
                           "url": "u", "linkState": "linked",
                           "depRelations": []}
        other.write_text(json.dumps(data), encoding="utf-8")

    def test_persist_external_collision_caught_inside_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow, other, mine = self._two_specs(tmp)
            # The other spec links the SAME durable id in the exact window
            # the review cites: after any unlocked collision scan could have
            # run, immediately before OUR critical section is entered. Only
            # a scan INSIDE the locked section catches this.
            gl = L.persist_external.__globals__
            real_lw = gl["_locked_tracker_write"]

            def losing_lw(fd, sid, mutate, **kw):
                self._link_other(other)
                return real_lw(fd, sid, mutate, **kw)

            ex = fake_execute({"lifecycle-resolve-uuid": ok({
                "data": {"issue": {
                    "id": LN_UUID, "identifier": "WOR-17",
                    "url": "https://linear.app/x/issue/WOR-17"}}})})
            gl["_locked_tracker_write"] = losing_lw
            try:
                out = L.persist_external(flow, "fn-1-demo", identifier="WOR-17",
                                         source="mcp", execute=ex)
            finally:
                gl["_locked_tracker_write"] = real_lw
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "durable_collision")
            self.assertEqual((out.details or {}).get("owner"), "fn-2-other")
            saved = json.loads(mine.read_text(encoding="utf-8"))["tracker"]
            self.assertIsNone(saved.get("id"), "loser spec stays unlinked")

    def test_complete_identifier_only_collision_caught_inside_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            other = _write_flow(flow, ln_cfg(), spec_id="fn-2-other")
            mine = _write_flow(flow, ln_cfg(), tracker={
                "id": None, "identifier": "WOR-17", "url": None,
                "linkState": "identifier_only", "depRelations": []})

            gl = L.complete_identifier_only.__globals__
            real_lw = gl["locked_tracker_write"]

            def losing_lw(fd, sid, mutate, **kw):
                # Same window as the persist-external case: the other spec
                # wins the durable id just before OUR critical section.
                Round6LockedCollisionScan._link_other(other)
                return real_lw(fd, sid, mutate, **kw)

            ex = fake_execute({"lifecycle-resolve-uuid": ok({
                "data": {"issue": {
                    "id": LN_UUID, "identifier": "WOR-17",
                    "url": "https://linear.app/x/issue/WOR-17"}}})})
            gl["locked_tracker_write"] = losing_lw
            try:
                out = L.complete_identifier_only(flow, "fn-1-demo", execute=ex)
            finally:
                gl["locked_tracker_write"] = real_lw
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "durable_collision")
            self.assertEqual((out.details or {}).get("owner"), "fn-2-other")
            saved = json.loads(mine.read_text(encoding="utf-8"))["tracker"]
            self.assertIsNone(saved.get("id"))
            self.assertEqual(saved["linkState"], "identifier_only",
                             "loser record is not upgraded")

    def test_create_collision_caught_inside_the_lock_with_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            other = _write_flow(flow, gh_cfg(), spec_id="fn-2-other")
            mine = _write_flow(flow, gh_cfg(), spec_id="fn-1-demo")

            def create_then_lose_race(req):
                data = json.loads(other.read_text(encoding="utf-8"))
                data["tracker"] = {"id": GH_NODE, "identifier": "#42",
                                   "url": "u", "linkState": "linked",
                                   "depRelations": []}
                other.write_text(json.dumps(data), encoding="utf-8")
                return ok({"id": 1, "node_id": GH_NODE, "number": 42,
                           "html_url": "https://github.com/o/r/issues/42"})

            ex = fake_execute({"lifecycle-create": create_then_lose_race})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "durable_collision")
            details = out.details or {}
            # The remote issue exists: the collision verdict carries the
            # created identity (completed-steps decoration), never a bare
            # failure that invites a duplicating retry.
            self.assertEqual(details.get("completed_steps"), ["create"])
            self.assertEqual(details.get("id"), GH_NODE)
            saved = json.loads(mine.read_text(encoding="utf-8"))["tracker"]
            self.assertIsNone(saved.get("id"), "loser spec stays unlinked")

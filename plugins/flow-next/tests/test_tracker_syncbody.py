"""sync-body: readback canonical + paired merge base (fn-140.5).

Fake transport = injected executor seam (same harness as test_tracker_status).
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import syncbody as SB  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.relate.ledger import FLOW_DEPS_CLOSE, FLOW_DEPS_OPEN  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def empty_ok() -> Response:
    return Response(204, {}, b"", 0.01)


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

FLOW_BODY = "## Goal\nShip it.\n"
DEPS_BLOCK = (
    f"{FLOW_DEPS_OPEN}\n"
    "**Blocked by:** #12, #15\n"
    f"{FLOW_DEPS_CLOSE}"
)


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


def gql_issue(issue) -> Response:
    return ok({"data": {"issue": issue}})


def gql_update(issue) -> Response:
    return ok({"data": {"issueUpdate": {"success": True, "issue": issue}}})


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_flow(flow: Path, config: dict, *, spec_id: str = "fn-1-demo",
                tracker: dict | None = None) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    base_tracker = {
        "id": GH_NODE, "identifier": "#42", "url": "https://x/42",
        "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
        "baseHashFlow": None, "baseHashTracker": None,
        "mergeBaseFlow": None, "mergeBaseTracker": None,
    }
    if tracker:
        base_tracker.update(tracker)
    spec = {
        "id": spec_id, "title": "Demo", "status": "open",
        "branch_name": spec_id, "tracker": base_tracker,
    }
    path = flow / "specs" / f"{spec_id}.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return path


def _saved(flow: Path, spec_id: str = "fn-1-demo") -> dict:
    return json.loads((flow / "specs" / f"{spec_id}.json").read_text(encoding="utf-8"))


def _receipts(flow: Path) -> list[dict]:
    runs = flow / "sync-runs"
    if not runs.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(runs.glob("sync-*.json"))]


# ---------------------------------------------------------------------------
# trackerBodyForMerge
# ---------------------------------------------------------------------------

class TrackerBodyForMerge(unittest.TestCase):
    def test_strips_flow_deps_region_markers_included(self) -> None:
        raw = f"{FLOW_BODY}\n{DEPS_BLOCK}\n"
        out = SB.trackerBodyForMerge(raw)
        self.assertNotIn(FLOW_DEPS_OPEN, out)
        self.assertNotIn(FLOW_DEPS_CLOSE, out)
        self.assertNotIn("Blocked by", out)
        self.assertEqual(out, FLOW_BODY.rstrip("\n"))

    def test_trailing_newline_only_no_linear_prediction(self) -> None:
        # Fixture carries Linear-rewritable constructs; client must NOT rewrite.
        raw = ("_italic_ [l](https://ex.com) - bullet\n"
               "| a | b |\n|---|---|\n- [x] done\n")
        out = SB.trackerBodyForMerge(raw)
        self.assertIn("_italic_", out)
        self.assertIn("[l](https://ex.com)", out)
        self.assertIn("- bullet", out)
        self.assertIn("|---|---|", out)
        self.assertIn("[x]", out)
        self.assertFalse(out.endswith("\n"))


# ---------------------------------------------------------------------------
# Per-provider parent + issue helpers
# ---------------------------------------------------------------------------

def _gh_issue(body: str) -> dict:
    return {"id": 999001, "node_id": GH_NODE, "number": 42, "title": "T",
            "body": body, "html_url": "https://github.com/o/r/issues/42",
            "labels": [], "state": "open"}


def _gl_issue(body: str) -> dict:
    return {"id": GL_ID, "iid": 12, "title": "T", "description": body,
            "web_url": "https://gitlab.com/g/p/-/issues/12",
            "labels": [], "state": "opened"}


def _ln_issue(body: str) -> dict:
    return {"id": LN_UUID, "identifier": "WOR-17", "title": "T",
            "description": body, "url": "https://linear.app/x/issue/WOR-17"}


def _jr_issue(body: str) -> dict:
    return {"id": JR_ID, "key": "SCRUM-1",
            "fields": {"summary": "T", "description": body, "labels": []}}


PROVIDERS = [
    ("github", gh_cfg, GH_NODE, "#42", _gh_issue,
     lambda body: ok(_gh_issue(body))),
    ("gitlab", gl_cfg, str(GL_ID), "g/p#12", _gl_issue,
     lambda body: ok(_gl_issue(body))),
    ("linear", ln_cfg, LN_UUID, "WOR-17", _ln_issue,
     lambda body: gql_issue(_ln_issue(body))),
    ("jira", jr_cfg, JR_ID, "SCRUM-1", _jr_issue,
     lambda body: ok(_jr_issue(body))),
]


def _seeded_tracker(durable, display, *, body_for_base: str = FLOW_BODY):
    merged = SB.trackerBodyForMerge(body_for_base)
    return {
        "id": durable, "identifier": display, "url": "https://x",
        "lastSyncedAt": "2020-01-01T00:00:00Z", "depRelations": [],
        "linkState": "linked",
        "mergeBaseFlow": FLOW_BODY,
        "mergeBaseTracker": merged,
        "baseHashFlow": sha(FLOW_BODY),
        "baseHashTracker": sha(merged),
    }


# ---------------------------------------------------------------------------
# No-op reconcile: NO write on all four
# ---------------------------------------------------------------------------

class NoOpReconcile(unittest.TestCase):
    def test_noop_produces_no_write_on_all_four(self) -> None:
        for provider, cfg_fn, durable, display, _mk, parent_resp in PROVIDERS:
            with self.subTest(provider=provider):
                with tempfile.TemporaryDirectory() as tmp:
                    flow = Path(tmp)
                    _write_flow(
                        flow, cfg_fn(),
                        tracker=_seeded_tracker(durable, display,
                                                body_for_base=FLOW_BODY))
                    # Parent body matches outgoing after trackerBodyForMerge.
                    ex = fake_execute({
                        "sync-body-parent-read": parent_resp(FLOW_BODY),
                    })
                    out = SB.sync_body(
                        flow, "fn-1-demo", flow_file_body=FLOW_BODY,
                        direction="push", execute=ex)
                    self.assertEqual(out["kind"], "noop")
                    self.assertEqual(out["side_written"], "none")
                    write_ops = [c for c in ex.calls if c.op == "wire-update"]
                    self.assertEqual(write_ops, [],
                                     f"{provider}: no-op must not issue wire-update")
                    saved = _saved(flow)["tracker"]
                    self.assertEqual(saved["lastSyncedAt"], "2020-01-01T00:00:00Z")
                    self.assertEqual(saved["mergeBaseFlow"], FLOW_BODY)


# ---------------------------------------------------------------------------
# Linear rewrite: halves differ; second reconcile is no-op
# ---------------------------------------------------------------------------

def _linear_rewrite(sent: str) -> str:
    """Apply the six measured Linear description rewrites."""
    text = sent
    text = text.replace("_italic_", "*italic*")
    text = text.replace("[l](https://ex.com)", "[l](<https://ex.com>)")
    # bullet marker: leading "- " -> "* " (line-start only)
    lines = []
    for line in text.split("\n"):
        if line.startswith("- ") and not line.startswith("- ["):
            line = "* " + line[2:]
        lines.append(line)
    text = "\n".join(lines)
    text = text.replace("|---|---|", "| -- | -- |")
    text = text.replace("[x]", "[X]")
    return text.rstrip("\n")


class LinearReadbackCanonical(unittest.TestCase):
    def test_merge_base_halves_differ_then_second_is_noop(self) -> None:
        sent = ("_italic_ and [l](https://ex.com)\n"
                "- bullet\n"
                "| a | b |\n|---|---|\n"
                "- [x] done\n")
        rewritten = _linear_rewrite(sent)
        self.assertNotEqual(sent.rstrip("\n"), rewritten)

        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, ln_cfg(),
                tracker={
                    "id": LN_UUID, "identifier": "WOR-17", "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
            # Parent (pre) has different body so push is not a no-op.
            parent_before = _ln_issue("old body")
            after_write = _ln_issue(rewritten)
            ex = fake_execute({
                "sync-body-parent-read": gql_issue(parent_before),
                "wire-parent-read": gql_issue(parent_before),
                "wire-update": gql_update(after_write),
                "wire-read": gql_issue(after_write),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=sent,
                direction="push", event="reconcile", execute=ex)
            self.assertEqual(out["kind"], "pushed")
            self.assertEqual(out["mergeBaseFlow"], sent)
            self.assertEqual(out["mergeBaseTracker"],
                             SB.trackerBodyForMerge(rewritten))
            self.assertNotEqual(out["mergeBaseFlow"], out["mergeBaseTracker"])
            saved = _saved(flow)["tracker"]
            self.assertEqual(saved["mergeBaseFlow"], sent)
            self.assertEqual(saved["mergeBaseTracker"],
                             SB.trackerBodyForMerge(rewritten))
            self.assertEqual(saved["baseHashFlow"], sha(sent))
            self.assertEqual(saved["baseHashTracker"],
                             sha(SB.trackerBodyForMerge(rewritten)))
            self.assertIsNotNone(saved["lastSyncedAt"])
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "pushed")
            self.assertEqual(receipts[0]["event"], "reconcile")
            self.assertIn("degraded", receipts[0])

            # Second reconcile against the rewritten store is a no-op
            # (no false divergence from Linear rewriting).
            ex2 = fake_execute({
                "sync-body-parent-read": gql_issue(_ln_issue(rewritten)),
            })
            out2 = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=sent,
                direction="push", execute=ex2)
            self.assertEqual(out2["kind"], "noop")
            self.assertEqual(
                [c.op for c in ex2.calls if c.op == "wire-update"], [])


# ---------------------------------------------------------------------------
# Pull seeds without writes
# ---------------------------------------------------------------------------

class PullSeedsBase(unittest.TestCase):
    def test_pull_seeds_paired_base_with_zero_writes(self) -> None:
        remote = "tracker-side body\n"
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, gh_cfg(),
                tracker={
                    "id": GH_NODE, "identifier": "#42", "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
            ex = fake_execute({
                "sync-body-parent-read": ok(_gh_issue(remote)),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=FLOW_BODY,
                direction="pull", event="pull", execute=ex)
            self.assertEqual(out["kind"], "pulled")
            self.assertEqual(out["side_written"], "none")
            self.assertEqual(
                [c.op for c in ex.calls if c.op == "wire-update"], [])
            saved = _saved(flow)["tracker"]
            self.assertEqual(saved["mergeBaseFlow"], FLOW_BODY)
            self.assertEqual(saved["mergeBaseTracker"],
                             SB.trackerBodyForMerge(remote))
            self.assertEqual(saved["baseHashFlow"], sha(FLOW_BODY))
            self.assertEqual(saved["baseHashTracker"],
                             sha(SB.trackerBodyForMerge(remote)))
            self.assertIsNotNone(saved["lastSyncedAt"])
            self.assertEqual(_receipts(flow)[0]["status"], "pulled")


# ---------------------------------------------------------------------------
# Partial failure leaves prior base untouched
# ---------------------------------------------------------------------------

class PartialFailure(unittest.TestCase):
    def test_readback_failure_leaves_prior_base_bytes(self) -> None:
        prior_flow = "PRIOR FLOW\n"
        prior_tracker = "PRIOR TRACKER"
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, gh_cfg(),
                tracker={
                    "id": GH_NODE, "identifier": "#42", "url": "https://x",
                    "lastSyncedAt": "OLD", "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": prior_flow,
                    "mergeBaseTracker": prior_tracker,
                    "baseHashFlow": sha(prior_flow),
                    "baseHashTracker": sha(prior_tracker),
                })
            ex = fake_execute({
                "sync-body-parent-read": ok(_gh_issue("old remote")),
                "wire-parent-read": ok(_gh_issue("old remote")),
                "wire-update": ok(_gh_issue("written")),
                "wire-read": TrackerError(ErrorClass.TRANSPORT, "readback boom",
                                          subtype="readback"),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body="NEW FLOW\n",
                direction="push", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.details.get("completed_steps"), ["wire-update"])
            saved = _saved(flow)["tracker"]
            self.assertEqual(saved["mergeBaseFlow"], prior_flow)
            self.assertEqual(saved["mergeBaseTracker"], prior_tracker)
            self.assertEqual(saved["baseHashFlow"], sha(prior_flow))
            self.assertEqual(saved["baseHashTracker"], sha(prior_tracker))
            self.assertEqual(saved["lastSyncedAt"], "OLD")


# ---------------------------------------------------------------------------
# Paired snapshot invariant
# ---------------------------------------------------------------------------

class PairedSnapshot(unittest.TestCase):
    def test_both_halves_always_written_together(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, gh_cfg(),
                tracker={
                    "id": GH_NODE, "identifier": "#42", "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
            remote = "remote body after write"
            ex = fake_execute({
                "sync-body-parent-read": ok(_gh_issue("before")),
                "wire-parent-read": ok(_gh_issue("before")),
                "wire-update": ok(_gh_issue(remote)),
                "wire-read": ok(_gh_issue(remote)),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=FLOW_BODY,
                direction="push", execute=ex)
            self.assertEqual(out["kind"], "pushed")
            saved = _saved(flow)["tracker"]
            # All four fields present together; never one half alone.
            for key in ("mergeBaseFlow", "mergeBaseTracker",
                        "baseHashFlow", "baseHashTracker"):
                self.assertIsNotNone(saved[key], key)
            self.assertEqual(saved["baseHashFlow"],
                             sha(saved["mergeBaseFlow"]))
            self.assertEqual(saved["baseHashTracker"],
                             sha(saved["mergeBaseTracker"]))


# ---------------------------------------------------------------------------
# Jira v2 plain-string body
# ---------------------------------------------------------------------------

class JiraV2PlainString(unittest.TestCase):
    def test_jira_write_uses_api2_and_plain_string_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, jr_cfg(),
                tracker={
                    "id": JR_ID, "identifier": "SCRUM-1", "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
            body = "jira plain body\n"
            ex = fake_execute({
                "sync-body-parent-read": ok(_jr_issue("before")),
                "wire-parent-read": ok(_jr_issue("before")),
                "wire-update": empty_ok(),
                "wire-read": ok(_jr_issue(body)),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=body,
                direction="push", execute=ex)
            self.assertEqual(out["kind"], "pushed")
            updates = [c for c in ex.calls if c.op == "wire-update"]
            self.assertEqual(len(updates), 1)
            req = updates[0]
            self.assertIn("/rest/api/2/", str(req.url_or_argv))
            payload = json.loads(req.body.decode())
            desc = payload["fields"]["description"]
            self.assertIsInstance(desc, str)
            self.assertEqual(desc, body)
            # Not ADF (dict with type/version/content)
            self.assertNotIsInstance(desc, dict)


# ---------------------------------------------------------------------------
# flow:deps carry-forward + strip at hash boundary
# ---------------------------------------------------------------------------

class FlowDepsCarryAndStrip(unittest.TestCase):
    def test_push_carries_deps_and_strip_keeps_hashes_stable(self) -> None:
        current = f"{FLOW_BODY}\n{DEPS_BLOCK}\n"
        # Outgoing differs so this is not a no-op, but lacks the deps block.
        outgoing = "## Goal\nShip it. (edited)\n"
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, gl_cfg(),
                tracker={
                    "id": str(GL_ID), "identifier": "g/p#12", "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
            written_holder = {}

            def capture_update(request):
                payload = json.loads(request.body.decode())
                written_holder["description"] = payload.get("description")
                # Server stores what was written (incl. carried deps).
                return ok(_gl_issue(payload["description"]))

            ex = fake_execute({
                "sync-body-parent-read": ok(_gl_issue(current)),
                "wire-parent-read": ok(_gl_issue(current)),
                "wire-update": capture_update,
                "wire-read": lambda req: ok(_gl_issue(written_holder["description"])),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=outgoing,
                direction="push", execute=ex)
            self.assertEqual(out["kind"], "pushed")
            written = written_holder["description"]
            self.assertIn(FLOW_DEPS_OPEN, written)
            self.assertIn(FLOW_DEPS_CLOSE, written)
            self.assertIn("Blocked by", written)
            # Hash boundary strips the block: mergeBaseTracker has no deps.
            self.assertNotIn(FLOW_DEPS_OPEN, out["mergeBaseTracker"])
            self.assertNotIn("Blocked by", out["mergeBaseTracker"])
            # mergeBaseFlow is the exact --flow-file body (no deps invent).
            self.assertEqual(out["mergeBaseFlow"], outgoing)


# ---------------------------------------------------------------------------
# No-op seed when no base yet
# ---------------------------------------------------------------------------

class NoOpSeedsWhenNoBase(unittest.TestCase):
    def test_noop_with_no_base_seeds_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, gh_cfg(),
                tracker={
                    "id": GH_NODE, "identifier": "#42", "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
            ex = fake_execute({
                "sync-body-parent-read": ok(_gh_issue(FLOW_BODY)),
            })
            out = SB.sync_body(
                flow, "fn-1-demo", flow_file_body=FLOW_BODY,
                direction="push", execute=ex)
            self.assertEqual(out["kind"], "seeded")
            self.assertEqual(
                [c.op for c in ex.calls if c.op == "wire-update"], [])
            saved = _saved(flow)["tracker"]
            self.assertEqual(saved["mergeBaseFlow"], FLOW_BODY)
            self.assertEqual(saved["mergeBaseTracker"],
                             SB.trackerBodyForMerge(FLOW_BODY))
            self.assertIsNotNone(saved["lastSyncedAt"])


# ---------------------------------------------------------------------------
# R14: GitLab system notes filtered (wire-owned; regression pin)
# ---------------------------------------------------------------------------

class GitlabSystemNotesFiltered(unittest.TestCase):
    def test_wire_comment_list_filters_system_true(self) -> None:
        # sync-body owns no comment machinery; R14 lives in wire comment-list.
        ex = fake_execute({
            "wire-comment-list": ok([
                {"id": 1, "body": "human", "noteable_id": GL_ID, "system": False},
                {"id": 2, "body": "changed title", "noteable_id": GL_ID,
                 "system": True},
            ]),
        })
        out = W.dispatch(
            "comment-list", gl_cfg(),
            locator={"durable": str(GL_ID), "display": "g/p#12"},
            execute=ex)
        self.assertEqual(len(out["comments"]), 1)
        self.assertEqual(out["comments"][0]["body"], "human")


# ---------------------------------------------------------------------------
# Envelope / CLI-shaped run()
# ---------------------------------------------------------------------------

class RunEnvelope(unittest.TestCase):
    def test_run_reads_flow_file_and_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_flow(
                flow, gh_cfg(),
                tracker=_seeded_tracker(GH_NODE, "#42"))
            body_path = flow / "body.md"
            body_path.write_text(FLOW_BODY, encoding="utf-8")
            ex = fake_execute({
                "sync-body-parent-read": ok(_gh_issue(FLOW_BODY)),
            })
            payload, code = SB.run(
                flow, spec_id="fn-1-demo", flow_file=str(body_path),
                direction="push", execute=ex)
            self.assertEqual(code, 0)
            data = json.loads(payload)
            self.assertTrue(data["success"])
            self.assertEqual(data["data"]["kind"], "noop")


if __name__ == "__main__":
    unittest.main()

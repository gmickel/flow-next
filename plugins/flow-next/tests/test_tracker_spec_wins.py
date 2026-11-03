"""tracker.specWins: first claim and make-pr reconcile write the rendered spec (fn-313).

Fake transport = the facade's injected executor seam, shared with
test_tracker_facade (imported as a module so its test classes are not
collected twice).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tracker_facade as TF  # noqa: E402

from flowctl_tracker import facade as F  # noqa: E402
from flowctl_tracker import syncbody as SB  # noqa: E402
from flowctl_tracker.facade.preparation import render_body  # noqa: E402
from flowctl_tracker.types import ErrorClass, TrackerError  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SPEC_MD = "## Goal\nShip it.\n\n## Acceptance Criteria\n\n- **R1:** Works.\n"
RENDERED = render_body(SPEC_MD)
EDITED = "Someone rewrote this on the tracker.\n"
SPEC_ID = TF.SPEC_ID


def _cfg(provider: str, spec_wins) -> dict:
    cfg = TF.gh_cfg() if provider == "github" else TF.ln_cfg(preferred="graphql")
    if spec_wins is not None:
        cfg["tracker"]["specWins"] = spec_wins
    return cfg


def _issue(provider: str, body: str, *, in_progress: bool = False) -> dict:
    if provider == "github":
        label = "status:in-progress" if in_progress else "status:backlog"
        return TF._gh_issue(body, labels=[{"name": label}])
    issue = TF._ln_issue(body)
    if in_progress:
        issue["state"] = {"id": "s-i", "name": "In Progress",
                          "type": "started"}
    return issue


def _linked(provider: str, **kw) -> dict:
    tracker = TF._linked(**kw)
    if provider == "linear":
        tracker.update(id=TF.LN_UUID, identifier="WOR-17")
    return tracker


def _write(flow: Path, provider: str, spec_wins, *, base_tracker: str) -> None:
    TF._write_flow(
        flow, _cfg(provider, spec_wins), spec_md=SPEC_MD,
        tracker=_linked(provider, mergeBaseFlow=SPEC_MD,
                        mergeBaseTracker=base_tracker),
        tasks=[{"status": "in_progress"}])


def _body_sent(provider: str, req) -> dict:
    payload = json.loads(req.body)
    if provider == "linear":
        return payload["variables"]["input"]
    return payload


def _status_responses(provider: str, parent: dict) -> dict:
    """Status move backlog -> in progress, plus every read it may need."""
    if provider == "github":
        moved = {**parent, "labels": [{"name": "status:in-progress"}]}
        return {
            "status-parent-read": TF.ok(parent),
            "status-set": TF.ok(moved),
            "status-label-rm": TF.empty_ok(),
            "status-label-add": TF.ok([{"name": "status:in-progress"}]),
            "status-label-readback": TF.ok([{"name": "status:in-progress"}]),
            "merge-evidence": TF.ok([]),
        }
    return {
        "status-parent-read": TF.gql_issue(parent),
        "status-state-read": TF.gql_issue(parent),
        "status-set": TF.ok({"data": {"issueUpdate": {
            "success": True, "issue": {"id": TF.LN_UUID}}}}),
        "merge-evidence": TF.ok([]),
    }


def _update(provider: str, sent: list):
    def capture(req):
        fields = _body_sent(provider, req)
        sent.append(fields)
        body = fields.get("body", fields.get("description"))
        return TF._update_resp(provider, _issue(provider, body))
    return capture


def _saved_tracker(flow: Path) -> dict:
    spec = json.loads((flow / "specs" / f"{SPEC_ID}.json")
                      .read_text(encoding="utf-8"))
    return spec["tracker"]


def _first_claim(flow: Path, ex):
    with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "lin_test"}):
        return F.sync(flow, SPEC_ID, op="push", event="work.firstClaim",
                      status_only=True, execute=ex)


def _ops(ex) -> list[str]:
    return [c.op for c in ex.calls]


class FirstClaim(unittest.TestCase):
    def test_edited_body_is_replaced_by_rendered_spec_and_status_moves(
            self) -> None:
        for provider in ("github", "linear"):
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write(flow, provider, True, base_tracker=EDITED)
                parent = _issue(provider, EDITED)
                sent: list = []
                responses = _status_responses(provider, parent)
                responses.update({
                    "sync-body-parent-read": TF._parent_resp(provider, parent),
                    "wire-update": _update(provider, sent),
                    "wire-read": TF._parent_resp(
                        provider, _issue(provider, RENDERED)),
                })
                ex = TF.fake_execute(responses)

                out = _first_claim(flow, ex)

                self.assertNotIsInstance(out, TrackerError, out)
                # Body only: no title, no relation step.
                self.assertEqual(len(sent), 1)
                self.assertEqual(set(sent[0]) & {"title"}, set())
                self.assertEqual(
                    sent[0].get("body", sent[0].get("description")), RENDERED)
                self.assertFalse(any(op.startswith("relation-")
                                     for op in _ops(ex)))
                self.assertIn("status-set", _ops(ex))
                self.assertEqual(out["steps"]["spec_wins_body"]["kind"],
                                 "pushed")
                saved = _saved_tracker(flow)
                self.assertEqual(saved["mergeBaseFlow"], SPEC_MD)
                self.assertEqual(saved["mergeBaseTracker"],
                                 SB.trackerBodyForMerge(RENDERED))
                receipt = TF._receipts(flow)[-1]
                self.assertEqual(receipt["event"], "work.firstClaim")
                self.assertEqual(receipt["details"],
                                 {"specWinsBody": "written"})

    def test_equal_live_body_sends_no_update_even_when_pair_differs(
            self) -> None:
        for provider in ("github", "linear"):
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                # The recorded pair is stale; the live body already matches.
                _write(flow, provider, True, base_tracker="OLD PAIR")
                parent = _issue(provider, RENDERED)
                responses = _status_responses(provider, parent)
                responses["sync-body-parent-read"] = TF._parent_resp(
                    provider, parent)
                ex = TF.fake_execute(responses)

                out = _first_claim(flow, ex)

                self.assertNotIsInstance(out, TrackerError, out)
                self.assertNotIn("wire-update", _ops(ex))
                self.assertIn("status-set", _ops(ex))
                self.assertEqual(TF._receipts(flow)[-1]["details"],
                                 {"specWinsBody": "unchanged"})
                self.assertEqual(_saved_tracker(flow)["mergeBaseTracker"],
                                 SB.trackerBodyForMerge(RENDERED))

    def test_failed_body_write_still_moves_status_and_is_reported(
            self) -> None:
        for provider in ("github", "linear"):
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write(flow, provider, True, base_tracker=EDITED)
                parent = _issue(provider, EDITED)
                responses = _status_responses(provider, parent)
                responses.update({
                    "sync-body-parent-read": TF._parent_resp(provider, parent),
                    "wire-update": TrackerError(
                        ErrorClass.AUTH, "forbidden", subtype="http_403"),
                })
                ex = TF.fake_execute(responses)

                out = _first_claim(flow, ex)

                self.assertNotIsInstance(out, TrackerError, out)
                self.assertIn("status-set", _ops(ex))
                failed = out["steps"]["spec_wins_body"]
                self.assertEqual(failed["kind"], "failed")
                self.assertEqual(failed["class"], "auth")
                self.assertEqual(out["receipt_status"], "errored")
                receipt = TF._receipts(flow)[-1]
                self.assertEqual(receipt["status"], "errored")
                self.assertEqual(receipt["details"],
                                 {"specWinsBody": "failed"})
                # The pair is untouched by a failed write.
                self.assertEqual(_saved_tracker(flow)["mergeBaseTracker"],
                                 EDITED)

    def test_body_failure_survives_a_later_status_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write(flow, "github", True, base_tracker=EDITED)
            parent = _issue("github", EDITED)
            responses = _status_responses("github", parent)
            responses.update({
                "sync-body-parent-read": TF.ok(parent),
                "wire-update": TrackerError(
                    ErrorClass.AUTH, "forbidden", subtype="http_403"),
                "status-set": TrackerError(
                    ErrorClass.TRANSPORT, "bad gateway", subtype="http_502"),
            })
            ex = TF.fake_execute(responses)

            out = _first_claim(flow, ex)

            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.TRANSPORT)
            self.assertEqual(out.details["specWinsBody"], "failed")
            self.assertEqual(out.details["specWinsBodyStep"]["class"], "auth")
            receipt = TF._receipts(flow)[-1]
            self.assertEqual(receipt["status"], "errored")
            self.assertEqual(receipt["details"]["specWinsBody"], "failed")

    def test_first_claim_leaves_linear_project_membership_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            TF._write_flow(
                flow, _cfg("linear", True), spec_md=SPEC_MD,
                tracker=_linked("linear", mergeBaseFlow=SPEC_MD,
                                mergeBaseTracker=RENDERED,
                                projectId="proj-1",
                                projectMilestoneId="ms-1"),
                tasks=[{"status": "in_progress"}])
            parent = _issue("linear", RENDERED)
            responses = _status_responses("linear", parent)
            responses["sync-body-parent-read"] = TF.gql_issue(parent)
            ex = TF.fake_execute(responses)

            out = _first_claim(flow, ex)

            self.assertNotIsInstance(out, TrackerError, out)
            self.assertNotIn("wire-project-set", _ops(ex))
            self.assertNotIn("wire-update", _ops(ex))
            self.assertIn("status-set", _ops(ex))

    def test_setting_off_or_not_true_stays_status_only(self) -> None:
        for provider in ("github", "linear"):
            for value in (None, False, "true", 1):
                with self.subTest(provider=provider, value=value), \
                        tempfile.TemporaryDirectory() as tmp:
                    flow = Path(tmp) / ".flow"
                    _write(flow, provider, value, base_tracker="OLD PAIR")
                    ex = TF.fake_execute(_status_responses(
                        provider, _issue(provider, EDITED)))

                    out = _first_claim(flow, ex)

                    self.assertNotIsInstance(out, TrackerError, out)
                    self.assertEqual(set(out["steps"]), {"create", "status"})
                    self.assertFalse(any(op.startswith("sync-body")
                                         or op == "wire-update"
                                         for op in _ops(ex)))
                    self.assertIn("status-set", _ops(ex))
                    receipt = TF._receipts(flow)[-1]
                    self.assertNotIn("details", receipt)
                    self.assertEqual(_saved_tracker(flow)["mergeBaseTracker"],
                                     "OLD PAIR")


class MakePrReconcile(unittest.TestCase):
    def _reconcile(self, root: Path, flow: Path, provider: str, ex):
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "lin_test"}):
            return F.sync(
                flow, SPEC_ID, op="reconcile", event="makePr",
                flow_file=TF._flow_file(root, SPEC_MD),
                # The tracker snapshot the fold kept: the old issue text.
                body_file=TF._body_file(root, EDITED),
                comments_file=TF._comments_file(root),
                source_body_file=TF._source_body_file(root, EDITED),
                execute=ex)

    def test_final_body_is_rendered_spec_and_next_push_writes_nothing(
            self) -> None:
        for provider in ("github", "linear"):
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                flow = root / ".flow"
                # The spec changed during the work; the issue holds old text.
                _write(flow, provider, True, base_tracker=EDITED)
                old = _issue(provider, EDITED, in_progress=True)
                new = _issue(provider, RENDERED, in_progress=True)
                sent: list = []
                ex = TF.fake_execute({
                    "wire-read": [TF._parent_resp(provider, old),
                                  TF._parent_resp(provider, new)],
                    "sync-body-parent-read": TF._parent_resp(provider, old),
                    "wire-update": _update(provider, sent),
                    "status-parent-read": TF._parent_resp(provider, new),
                    "status-state-read": TF._parent_resp(provider, new),
                    "merge-evidence": TF.ok([]),
                })

                out = self._reconcile(root, flow, provider, ex)

                self.assertNotIsInstance(out, TrackerError, out)
                self.assertEqual(len(sent), 1)
                self.assertEqual(
                    sent[0].get("body", sent[0].get("description")), RENDERED)
                saved = _saved_tracker(flow)
                self.assertEqual(saved["mergeBaseFlow"], SPEC_MD)
                self.assertEqual(saved["mergeBaseTracker"],
                                 SB.trackerBodyForMerge(RENDERED))

                # A later `sync-body --direction push` with no spec change.
                ex2 = TF.fake_execute({
                    "sync-body-parent-read": TF._parent_resp(provider, new)})
                with mock.patch.dict(os.environ,
                                     {"LINEAR_API_KEY": "lin_test"}):
                    after = SB.sync_body(flow, SPEC_ID, flow_file_body=SPEC_MD,
                                         direction="push", execute=ex2)
                self.assertNotIsInstance(after, TrackerError, after)
                self.assertEqual(after["side_written"], "none")
                self.assertNotIn("wire-update", _ops(ex2))

    def test_setting_off_keeps_the_folded_tracker_body(self) -> None:
        for provider in ("github", "linear"):
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                flow = root / ".flow"
                _write(flow, provider, None, base_tracker=EDITED)
                old = _issue(provider, EDITED, in_progress=True)
                ex = TF.fake_execute({
                    "wire-read": TF._parent_resp(provider, old),
                    "sync-body-parent-read": TF._parent_resp(provider, old),
                    "status-parent-read": TF._parent_resp(provider, old),
                    "status-state-read": TF._parent_resp(provider, old),
                    "merge-evidence": TF.ok([]),
                })

                out = self._reconcile(root, flow, provider, ex)

                self.assertNotIsInstance(out, TrackerError, out)
                self.assertNotIn("wire-update", _ops(ex))
                # Today's pair: the new spec with the old live body.
                saved = _saved_tracker(flow)
                self.assertEqual(saved["mergeBaseFlow"], SPEC_MD)
                self.assertEqual(saved["mergeBaseTracker"],
                                 SB.trackerBodyForMerge(EDITED))

    def test_failed_write_is_a_reconcile_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write(flow, "github", True, base_tracker=EDITED)
            old = _issue("github", EDITED, in_progress=True)
            ex = TF.fake_execute({
                "wire-read": TF.ok(old),
                "sync-body-parent-read": TF.ok(old),
                "wire-update": TrackerError(
                    ErrorClass.TRANSPORT, "boom", subtype="http_502"),
            })

            out = self._reconcile(root, flow, "github", ex)

            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.TRANSPORT)
            self.assertEqual(_saved_tracker(flow)["mergeBaseTracker"], EDITED)


class Schema(unittest.TestCase):
    def test_schema_declares_spec_wins_boolean(self) -> None:
        schema = json.loads((ROOT / "schema" / "flow-config.schema.json")
                            .read_text(encoding="utf-8"))
        node = schema["properties"]["tracker"]["properties"]["specWins"]
        self.assertEqual(node["type"], "boolean")


if __name__ == "__main__":
    unittest.main()

"""R8: bind land to the existing receipt-free tracker API, not sync/status.

Exercise real policy/provider helpers; this is not a land runner or a claim
that Python executes the skill's prose or prints its verdict.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker.resolve_verb import bound_executor  # noqa: E402
from flowctl_tracker.status.policy import decide, flow_to_normalized  # noqa: E402
from flowctl_tracker.status.providers import (  # noqa: E402
    apply_status, tracker_norm_from_parent,
)
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402
from flowctl_tracker.wire import parent_read  # noqa: E402


class LandTrackerApiTests(unittest.TestCase):
    def test_r8_existing_api_preserves_mapping_without_local_writes(self):
        prose = "\n".join(
            path.read_text(encoding="utf-8") for path in
            (ROOT / "skills/flow-next-land").rglob("*.md")
        )
        self.assertTrue("apply_status" in prose, "land must use receipt-free apply_status")
        config = {"tracker": {"type": "linear", "resolved": {
            "destination": {"stateIds": {
                "in_review": "review-state", "done": "configured-done",
            }},
        }}}
        locator = {"display": "ENG-42", "durable": "issue-uuid"}
        spec = {"status": "done", "completion_review_status": "ship"}
        calls = []

        def execute(request):
            calls.append(request)
            if request.op == "wire-parent-read":
                payload = {"issue": {
                    "id": "issue-uuid", "identifier": "ENG-42",
                    "state": {"id": "review-state"},
                }}
            else:
                self.assertEqual(request.op, "status-set")
                self.assertEqual(json.loads(request.body)["variables"], {
                    "id": "issue-uuid", "stateId": "configured-done",
                })
                payload = {"issueUpdate": {"success": True}}
            return Response(200, {}, json.dumps({"data": payload}).encode(), 0)

        # All fixture/config/spec values already reside in memory. Deny file
        # opens, including low-level lock creation, during the actual API path.
        with mock.patch("builtins.open", side_effect=AssertionError("file open")), \
                mock.patch("os.open", side_effect=AssertionError("file open")), \
                mock.patch("io.open", side_effect=AssertionError("file open")):
            ex = bound_executor(config, execute)
            parent = parent_read("linear", config, locator, ex)
            flow = flow_to_normalized(spec, "merged", True)
            tracker = tracker_norm_from_parent(
                "linear", parent, config["tracker"]["resolved"]["destination"])
            decision = decide("done", None, flow, tracker, "merged")
            self.assertEqual(decision.kind, "apply")
            result = apply_status("linear", config, locator, parent, ex,
                                  target_slot=decision.target_slot)
        self.assertEqual(result["stateId"], "configured-done")
        self.assertEqual(len(calls), 2)

    def test_r8_provider_failure_is_available_to_verdict_reason(self):
        prose = "\n".join(
            path.read_text(encoding="utf-8") for path in
            (ROOT / "skills/flow-next-land").rglob("*.md")
        )
        self.assertTrue("apply_status" in prose, "land must bind the tested provider API")
        error = TrackerError(ErrorClass.AUTH, "tracker authentication failed")
        config = {"tracker": {"resolved": {"destination": {
            "stateIds": {"done": "configured-done"},
        }}}}
        with mock.patch("builtins.open", side_effect=AssertionError("file open")), \
                mock.patch("os.open", side_effect=AssertionError("file open")), \
                mock.patch("io.open", side_effect=AssertionError("file open")):
            result = apply_status(
                "linear", config, {"durable": "issue-uuid"}, {},
                lambda request: error, target_slot="done")
        self.assertIs(result, error)
        self.assertEqual(result.message, "tracker authentication failed")


if __name__ == "__main__":
    unittest.main()

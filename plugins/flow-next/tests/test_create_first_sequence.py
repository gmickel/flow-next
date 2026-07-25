"""create-first end-to-end state sequence with a counted transport (fn-134 R19/R20).

WHAT THIS TESTS, AND WHAT IT DELIBERATELY DOES NOT.

`create-first` is skill prose executed by a host agent. Its steps split into
two halves with very different testability:

  1. State transitions driven by REAL flowctl commands - compute the retry key,
     record the created issue, mint the spec, attach the tracker id, seed the
     merge base, clear the recovery record. These are executable and are
     exercised here for real, in the order the prose specifies.

  2. Agent behaviours - which of the five mint sites routes, explicit override
     precedence, silent flow-first degradation when no transport is reachable.
     These have no executable entry point. Modelling them in Python would mean
     re-implementing the prose and asserting the model against itself: a
     parallel construction that can pass while the prose it mirrors is wrong.
     This repo has been bitten by exactly that, so those stay pinned by the
     prose-contract tests in `test_spec_id_routing_prose.py` instead.

Only the network boundary is faked. `_CountedTransport` stands in for the
adapter's `writeIssue` / `postComment` and counts both, so the load-bearing
promise - a retry after a partial failure LINKS, and a later lifecycle
touchpoint comments rather than creating a second issue - is asserted against
real counts rather than a prose reading. The touchpoint takes its
create-vs-comment branch from real flowctl state, and a companion test drives
the same touchpoint on an unlinked spec to prove the create branch is live.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"


def _fc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke the REAL flowctl CLI - no mock patching of the routing table."""
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


class _CountedTransport:
    """Stands in for the adapter at the ONE boundary that cannot be executed.

    Counts `write_issue` calls. Everything else in the sequence runs through
    real flowctl state so the test is not a model of itself.
    """

    def __init__(self) -> None:
        self.creates = 0
        self.comments = 0
        self.issues: dict[str, dict[str, str]] = {}

    def write_issue(self, title: str) -> dict[str, str]:
        self.creates += 1
        n = 700 + self.creates
        rec = {"id": f"I_{n}", "identifier": f"#{n}", "url": f"https://example/{n}", "title": title}
        self.issues[rec["identifier"]] = rec
        return rec

    def post_comment(self, identifier: str, body: str) -> None:
        self.comments += 1


class CreateFirstSequence(unittest.TestCase):
    TITLE = "Graduate the recurring lesson"
    TTYPE = "github"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _fc(self.repo, "init")
        _fc(self.repo, "config", "set", "tracker.type", self.TTYPE)
        _fc(self.repo, "config", "set", "tracker.enabled", "true")
        self.tp = _CountedTransport()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _key(self) -> str:
        r = _fc(self.repo, "sync", "create-first-key", "--type", self.TTYPE, "--title", self.TITLE)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def _create_first(self) -> dict[str, str]:
        """The prose's create-first step: check recovery FIRST, only then create."""
        key = self._key()
        found = _fc(self.repo, "sync", "create-first-get", "--key", key, "--json")
        if found.returncode == 0:
            return json.loads(found.stdout)          # resume: LINK, do not create
        rec = self.tp.write_issue(self.TITLE)         # the one faked boundary
        put = _fc(
            self.repo, "sync", "create-first-put", "--key", key,
            "--id", rec["id"], "--identifier", rec["identifier"],
            "--url", rec["url"], "--title", rec["title"], "--transport", "gh",
        )
        self.assertEqual(put.returncode, 0, put.stderr)
        return rec

    def _lifecycle_comment(self, spec_id: str) -> str | None:
        """A later lifecycle touchpoint, routed on REAL flowctl state.

        steps.md:11 - a `comment` op on an UNLINKED spec runs create-if-unlinked
        first (create + attach), then comments; on a LINKED spec it only
        comments. The branch is taken from `sync get-state`, so if the earlier
        attach had failed to persist, this fires the create branch and the
        create count moves. That is what keeps the final assertion honest.
        """
        state = _fc(self.repo, "sync", "get-state", spec_id, "--json")
        linked = (
            json.loads(state.stdout)["tracker"].get("identifier")
            if state.returncode == 0
            else None
        )
        if not linked:                                    # create-if-unlinked branch
            rec = self.tp.write_issue(self.TITLE)
            _fc(self.repo, "sync", "set-tracker-id", spec_id, rec["id"],
                "--identifier", rec["identifier"], "--url", rec["url"], "--json")
            linked = rec["identifier"]
        self.tp.post_comment(linked, "work.done")
        return linked

    def test_full_sequence_creates_exactly_one_issue_across_a_failed_mint_and_retry(self) -> None:
        key = self._key()

        # Attempt 1: issue created and recorded, then minting dies before it runs.
        first = self._create_first()
        self.assertEqual(self.tp.creates, 1)

        # Attempt 2 (the retry): same intent, so create-first must LINK.
        second = self._create_first()
        self.assertEqual(
            self.tp.creates, 1, "retry must link to the recorded issue, never create a second"
        )
        self.assertEqual(second["identifier"], first["identifier"])

        # Mint for real against the recovered identifier, then attach and seed.
        mint = _fc(
            self.repo, "spec", "create", "--title", self.TITLE,
            "--tracker-first", "--tracker-identifier", second["identifier"], "--json",
        )
        self.assertEqual(mint.returncode, 0, mint.stderr)
        spec_id = json.loads(mint.stdout)["id"]
        self.assertTrue(
            spec_id.startswith("gh-701-"),
            f"github issue must mint a synthetic gh- id, got {spec_id}",
        )

        attach = _fc(
            self.repo, "sync", "set-tracker-id", spec_id, second["id"],
            "--identifier", second["identifier"], "--url", second["url"], "--json",
        )
        self.assertEqual(attach.returncode, 0, attach.stderr)

        base = _fc(self.repo, "sync", "set-merge-base", spec_id, "--flow", "seed", "--tracker", "seed", "--json")
        self.assertEqual(base.returncode, 0, base.stderr)

        # Mint + attach succeeded, so the recovery record is cleared.
        self.assertEqual(_fc(self.repo, "sync", "create-first-clear", "--key", key).returncode, 0)
        self.assertEqual(
            list((self.repo / ".flow" / "create-first").glob("*.json")), [],
            "recovery record must not outlive a completed sequence",
        )

        # A LATER lifecycle touchpoint fires through the transport. Because the
        # spec is now linked it must take the comment-only branch.
        self.assertEqual(self._lifecycle_comment(spec_id), second["identifier"])
        self.assertEqual(self.tp.comments, 1, "the touchpoint must actually have fired")
        self.assertEqual(
            self.tp.creates, 1,
            "exactly one remote creation across create + retry + mint + attach + later touchpoint",
        )

    def test_the_later_touchpoint_would_create_on_an_unlinked_spec(self) -> None:
        """Proves the touchpoint's create branch is live, so the linked-spec
        assertion above is a real routing result and not a tautology."""
        mint = _fc(self.repo, "spec", "create", "--title", "Never linked", "--json")
        spec_id = json.loads(mint.stdout)["id"]
        self.assertEqual(self.tp.creates, 0)
        self._lifecycle_comment(spec_id)
        self.assertEqual(self.tp.creates, 1, "an unlinked spec must hit create-if-unlinked")
        self.assertEqual(self.tp.comments, 1)

    def test_a_genuinely_different_intent_does_create_a_second_issue(self) -> None:
        """The guard must not over-link: a different title is a different issue."""
        self._create_first()
        self.TITLE = "A different lesson entirely"
        self._create_first()
        self.assertEqual(self.tp.creates, 2)

    def test_recovery_record_survives_an_interrupted_mint(self) -> None:
        """If minting fails, the record must remain so the next run can resume."""
        key = self._key()
        self._create_first()
        # No mint, no clear - simulating a crash between create and mint.
        found = _fc(self.repo, "sync", "create-first-get", "--key", key, "--json")
        self.assertEqual(found.returncode, 0, "record must survive for the resume path")
        self.assertEqual(json.loads(found.stdout)["identifier"], "#701")


if __name__ == "__main__":
    unittest.main()

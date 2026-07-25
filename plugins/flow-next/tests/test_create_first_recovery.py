"""Pre-spec create-first recovery records (fn-134 R19/R20).

`create-first` makes a tracker issue BEFORE any local spec exists, so
`sync receipt` (which resolves a local spec id) cannot be used. These tests
pin the mechanical half of the safety promise: a retry after a partial
failure LINKS to the already-created issue and never creates a second one.

Exercises the real argparse routing (the two-token `sync create-first-*`
forms), not a mock-patched helper.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"

spec = importlib.util.spec_from_file_location("flowctl", FLOWCTL_PY)
flowctl = importlib.util.module_from_spec(spec)
sys.modules["flowctl"] = flowctl
spec.loader.exec_module(flowctl)


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


class CreateFirstKeyDeterminism(unittest.TestCase):
    def test_same_inputs_same_key(self) -> None:
        a = flowctl.compute_create_first_key("github", "Fix login", "body")
        b = flowctl.compute_create_first_key("github", "Fix login", "body")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_each_input_changes_the_key(self) -> None:
        base = flowctl.compute_create_first_key("github", "Fix login", "body")
        self.assertNotEqual(base, flowctl.compute_create_first_key("gitlab", "Fix login", "body"))
        self.assertNotEqual(base, flowctl.compute_create_first_key("github", "Fix logout", "body"))
        self.assertNotEqual(base, flowctl.compute_create_first_key("github", "Fix login", "other"))

    def test_field_boundaries_are_not_ambiguous(self) -> None:
        """Concatenation must not let a shifted boundary collide."""
        self.assertNotEqual(
            flowctl.compute_create_first_key("gh", "ab", "c"),
            flowctl.compute_create_first_key("gh", "a", "bc"),
        )

    def test_prose_definition_matches_code(self) -> None:
        """steps.md Phase 2d documents this key; the two must not drift."""
        steps = (
            ROOT / "skills" / "flow-next-tracker-sync" / "steps.md"
        ).read_text(encoding="utf-8")
        self.assertIn("sha256", steps)
        self.assertIn("16", steps)
        self.assertIn("create-first-key", steps)
        self.assertIn("create-first-get", steps)


class CreateFirstRecoveryRoundTrip(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _run(self.repo, "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _put(self, key: str, **over: str) -> subprocess.CompletedProcess:
        fields = {
            "--id": "I_abc",
            "--identifier": "#123",
            "--url": "https://example/123",
            "--title": "Fix login",
            "--transport": "gh",
        }
        fields.update(over)
        flat: list[str] = []
        for k, v in fields.items():
            flat += [k, v]
        return _run(self.repo, "sync", "create-first-put", "--key", key, *flat)

    def test_key_action_via_real_cli(self) -> None:
        r = _run(self.repo, "sync", "create-first-key",
                 "--type", "github", "--title", "Fix login")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), flowctl.compute_create_first_key("github", "Fix login", ""))

    def test_get_absent_exits_nonzero_without_traceback(self) -> None:
        r = _run(self.repo, "sync", "create-first-get", "--key", "deadbeefdeadbeef")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)

    def test_put_then_get_round_trips_every_field(self) -> None:
        key = "0123456789abcdef"
        self.assertEqual(self._put(key).returncode, 0)
        r = _run(self.repo, "sync", "create-first-get", "--key", key, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertEqual(rec["retryKey"], key)
        self.assertEqual(rec["id"], "I_abc")
        self.assertEqual(rec["identifier"], "#123")
        self.assertEqual(rec["url"], "https://example/123")
        self.assertEqual(rec["title"], "Fix login")
        self.assertEqual(rec["transport"], "gh")
        self.assertTrue(rec["createdAt"])

    def test_second_put_is_idempotent_and_keeps_original_createdAt(self) -> None:
        key = "1111222233334444"
        self._put(key)
        first = json.loads(
            _run(self.repo, "sync", "create-first-get", "--key", key, "--json").stdout
        )
        self._put(key, **{"--url": "https://example/123?x=1"})
        second = json.loads(
            _run(self.repo, "sync", "create-first-get", "--key", key, "--json").stdout
        )
        self.assertEqual(first["createdAt"], second["createdAt"], "createdAt must describe the remote create")
        self.assertEqual(second["url"], "https://example/123?x=1", "second write wins on mutable fields")
        files = list((self.repo / ".flow" / "create-first").glob("*.json"))
        self.assertEqual(len(files), 1, "a second put must not create a second record")

    def test_clear_removes_and_get_is_then_absent(self) -> None:
        key = "5555666677778888"
        self._put(key)
        self.assertEqual(
            _run(self.repo, "sync", "create-first-clear", "--key", key).returncode, 0
        )
        self.assertNotEqual(
            _run(self.repo, "sync", "create-first-get", "--key", key).returncode, 0
        )

    def test_resume_after_partial_failure_links_and_creates_exactly_one(self) -> None:
        """THE contract: remote create succeeded, mint died, retry must LINK.

        Simulates the whole sequence the way the skill drives it, and asserts
        exactly one record exists for the key across the entire run.
        """
        title, body, ttype = "Harden the gate", "why it matters", "github"
        key = _run(self.repo, "sync", "create-first-key",
                   "--type", ttype, "--title", title).stdout.strip()

        # attempt 1: remote create succeeded, record written, then mint dies
        self._put(key, **{"--id": "I_777", "--identifier": "#777",
                          "--url": "https://example/777", "--title": title})

        # attempt 2 (the retry): recompute the SAME key from the same intent
        key2 = _run(self.repo, "sync", "create-first-key",
                    "--type", ttype, "--title", title).stdout.strip()
        self.assertEqual(key, key2, "retry must recompute the same key")

        found = _run(self.repo, "sync", "create-first-get", "--key", key2, "--json")
        self.assertEqual(found.returncode, 0, "retry must FIND the prior create and link")
        self.assertEqual(json.loads(found.stdout)["identifier"], "#777")

        files = list((self.repo / ".flow" / "create-first").glob("*.json"))
        self.assertEqual(len(files), 1, "exactly one issue recorded across create + retry")

        # mint+attach finally succeed -> the record is cleared
        _run(self.repo, "sync", "create-first-clear", "--key", key)
        self.assertEqual(
            list((self.repo / ".flow" / "create-first").glob("*.json")), []
        )

    def test_records_are_gitignored(self) -> None:
        ignore = (self.repo / ".flow" / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("create-first/", ignore)


class CreateFirstProseUsesTheHelperExclusively(unittest.TestCase):
    """The recovery record must only ever be touched through the helper.

    steps.md once carried BOTH the helper invocation and a hand-rolled block
    that recomputed the hash with `shasum`, wrote the JSON with a shell
    redirect, and deleted it with `rm`. An agent following the second block
    bypassed the atomic helper the retry guarantee rests on, so the two could
    silently drift. These assertions keep the duplicate from coming back.
    """

    STEPS = ROOT / "skills" / "flow-next-tracker-sync" / "steps.md"

    def setUp(self) -> None:
        self.text = self.STEPS.read_text(encoding="utf-8")
        start = self.text.find("#### Receipt / retry contract")
        end = self.text.find("**Back-reference:**", start)
        self.section = self.text[start:end]
        self.assertTrue(start != -1 and end > start, "create-first section not found")

    def test_no_hand_rolled_hash(self) -> None:
        for tool in ("shasum -a 256", "sha256sum", "openssl dgst"):
            self.assertNotIn(
                tool, self.section,
                f"create-first prose recomputes the retry key with {tool!r}; "
                "use `sync create-first-key` so prose and code cannot drift",
            )

    def test_no_raw_recovery_write(self) -> None:
        self.assertNotIn(
            '> "$RECOVERY_PATH"', self.section,
            "recovery record written by shell redirect; use `sync create-first-put`",
        )
        self.assertNotIn(
            "mkdir -p \"$RECOVERY_DIR\"", self.section,
            "prose creates the recovery dir by hand; the helper owns that",
        )

    def test_no_raw_recovery_delete(self) -> None:
        self.assertNotIn(
            "rm -f \".flow/create-first", self.section,
            "recovery record deleted with rm; use `sync create-first-clear`",
        )

    def test_all_four_helper_leaves_are_referenced(self) -> None:
        for leaf in ("create-first-key", "create-first-get",
                     "create-first-put", "create-first-clear"):
            self.assertIn(leaf, self.section, f"prose never invokes `sync {leaf}`")


if __name__ == "__main__":
    unittest.main()

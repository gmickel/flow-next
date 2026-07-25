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


class CreateFirstKeyIsValidatedBeforePathUse(unittest.TestCase):
    """The --key argument is interpolated into a path, so it must be validated.

    Found by PR review on #241, missed by every test here: `--key ../config`
    resolved to `.flow/config.json`, so `put` overwrote the repo's flow config
    and `clear` would have deleted it. Callers normally pass
    `create-first-key` output, but "normally" is not a guarantee.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _run(self.repo, "init")
        self.config = self.repo / ".flow" / "config.json"
        self.baseline = self.config.read_bytes()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    HOSTILE = ("../config", "../../etc/passwd", "a/b", "..", ".", "", "/abs")

    def test_put_rejects_traversal_and_leaves_config_untouched(self) -> None:
        for key in self.HOSTILE:
            r = _run(self.repo, "sync", "create-first-put", "--key", key,
                     "--id", "X", "--identifier", "#1", "--url", "u",
                     "--title", "t", "--transport", "gh")
            self.assertNotEqual(r.returncode, 0, f"{key!r} must be rejected")
            self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(
            self.config.read_bytes(), self.baseline,
            "a rejected key must never have touched .flow/config.json",
        )

    def test_clear_rejects_traversal_and_deletes_nothing(self) -> None:
        for key in self.HOSTILE:
            r = _run(self.repo, "sync", "create-first-clear", "--key", key)
            self.assertNotEqual(r.returncode, 0, f"{key!r} must be rejected")
        self.assertTrue(self.config.exists(), "config.json must still exist")

    def test_get_rejects_traversal(self) -> None:
        for key in self.HOSTILE:
            r = _run(self.repo, "sync", "create-first-get", "--key", key)
            self.assertNotEqual(r.returncode, 0, f"{key!r} must be rejected")

    def test_wrong_shape_hex_is_rejected(self) -> None:
        for key in ("ABCDEF0123456789", "0123456789abcde", "0123456789abcdef0", "zzzzzzzzzzzzzzzz"):
            r = _run(self.repo, "sync", "create-first-put", "--key", key,
                     "--id", "X", "--identifier", "#1", "--url", "u",
                     "--title", "t", "--transport", "gh")
            self.assertNotEqual(r.returncode, 0, f"{key!r} is not 16 lowercase hex")

    def test_a_real_key_still_works(self) -> None:
        key = flowctl.compute_create_first_key("github", "Fix login", "")
        r = _run(self.repo, "sync", "create-first-put", "--key", key,
                 "--id", "X", "--identifier", "#1", "--url", "u",
                 "--title", "t", "--transport", "gh")
        self.assertEqual(r.returncode, 0, r.stderr)


class RecoveryWriteReconcilesGitignore(unittest.TestCase):
    """Writing a record must ensure the ignore entry (PR #241 wave 4).

    A project whose auto-managed .flow/.gitignore predates this release would
    otherwise get an unignored recovery record, and `git add -A` would commit
    it - letting another checkout with the same retry key resume onto the first
    developer's issue. That is the correctness failure the gitignore exists to
    prevent, so it cannot wait for a future `init`.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _run(self.repo, "init")
        self.gi = self.repo / ".flow" / ".gitignore"
        # Simulate a pre-release ignore block with the pattern absent.
        self.gi.write_text(
            self.gi.read_text(encoding="utf-8").replace("create-first/\n", ""),
            encoding="utf-8",
        )
        self.assertNotIn("create-first/", self.gi.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_put_reconciles_the_ignore_block(self) -> None:
        key = flowctl.compute_create_first_key("github", "Fix login", "")
        r = _run(self.repo, "sync", "create-first-put", "--key", key,
                 "--id", "X", "--identifier", "#1", "--url", "u",
                 "--title", "t", "--transport", "gh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(
            "create-first/", self.gi.read_text(encoding="utf-8"),
            "writing a record must ensure it is ignored, not rely on a later init",
        )


class RecoveryRecordCarriesTheMintedSpecId(unittest.TestCase):
    """The record stores specId so resume never reconstructs the id (PR #241 wave 10).

    Rebuilding `<key>-<number>-<slug>` is impossible when the title slugifies to
    empty - a CJK- or emoji-only issue title gets a random suffix from
    `spec create` - so the id has to be recorded, not derived.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _run(self.repo, "init")
        self.key = flowctl.compute_create_first_key("github", "T", "")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _put(self, *extra: str) -> subprocess.CompletedProcess:
        return _run(self.repo, "sync", "create-first-put", "--key", self.key,
                    "--id", "I_1", "--identifier", "#1", "--url", "u",
                    "--title", "T", "--transport", "gh", *extra)

    def test_spec_id_is_optional_and_absent_before_mint(self) -> None:
        self.assertEqual(self._put().returncode, 0)
        rec = json.loads(
            _run(self.repo, "sync", "create-first-get", "--key", self.key, "--json").stdout
        )
        self.assertNotIn("specId", rec, "no specId until the mint succeeds")

    def test_post_mint_put_records_the_spec_id(self) -> None:
        self._put()
        self.assertEqual(self._put("--spec-id", "gh-1-t").returncode, 0)
        rec = json.loads(
            _run(self.repo, "sync", "create-first-get", "--key", self.key, "--json").stdout
        )
        self.assertEqual(rec["specId"], "gh-1-t")

    def test_a_later_put_does_not_drop_an_established_spec_id(self) -> None:
        self._put("--spec-id", "gh-1-t")
        self.assertEqual(self._put().returncode, 0)   # e.g. re-recording transport
        rec = json.loads(
            _run(self.repo, "sync", "create-first-get", "--key", self.key, "--json").stdout
        )
        self.assertEqual(
            rec.get("specId"), "gh-1-t",
            "losing specId would make the mint-to-attach window unresumable again",
        )

    def test_a_slugless_title_still_yields_a_recorded_id(self) -> None:
        """The case that makes reconstruction impossible."""
        r = _run(self.repo, "spec", "create", "--title", "日本語のみ", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        spec_id = json.loads(r.stdout)["id"]
        self._put("--spec-id", spec_id)
        rec = json.loads(
            _run(self.repo, "sync", "create-first-get", "--key", self.key, "--json").stdout
        )
        self.assertEqual(rec["specId"], spec_id)


class RetryKeyNormalizesTrackerType(unittest.TestCase):
    """Accepted spellings must yield the same key (PR #241 wave 11).

    An interrupted run that started from `GitHub` or ` github ` has to recompute
    the identical key after the config is normalized, or `create-first-get`
    misses the record and the workflow creates a second remote issue.
    """

    def test_casing_and_whitespace_collapse_to_one_key(self) -> None:
        base = flowctl.compute_create_first_key("github", "T", "b")
        for spelling in ("GitHub", " github ", "GITHUB", "\tgithub\n"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    flowctl.compute_create_first_key(spelling, "T", "b"), base
                )

    def test_distinct_providers_still_differ(self) -> None:
        self.assertNotEqual(
            flowctl.compute_create_first_key("github", "T", "b"),
            flowctl.compute_create_first_key("gitlab", "T", "b"),
        )


class RecoveryWritesAreContainedInFlow(unittest.TestCase):
    """A repository is untrusted input (PR #241, Cursor security review, HIGH).

    A checkout can ship `.flow/create-first` or `.flow/.gitignore` as a symlink
    pointing outside the workspace; the following mkdir + write then performs an
    arbitrary same-user file write outside the repo. Both vectors were
    reproduced before the guard existed - the record landed outside the repo,
    and an unrelated user file was overwritten with gitignore content.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._out = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.outside = Path(self._out.name)
        _run(self.repo, "init")
        self.key = flowctl.compute_create_first_key("github", "X", "")

    def tearDown(self) -> None:
        self._tmp.cleanup(); self._out.cleanup()

    def _put(self) -> subprocess.CompletedProcess:
        return _run(self.repo, "sync", "create-first-put", "--key", self.key,
                    "--id", "I", "--identifier", "#1", "--url", "u",
                    "--title", "X", "--transport", "gh")

    def test_symlinked_record_dir_is_refused(self) -> None:
        (self.repo / ".flow" / "create-first").symlink_to(self.outside)
        r = self._put()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(list(self.outside.iterdir()), [], "write escaped the workspace")
        self.assertNotIn("Traceback", r.stderr)

    def test_symlinked_gitignore_is_not_written_through(self) -> None:
        victim = self.outside / "victim.txt"
        victim.write_text("IMPORTANT-USER-FILE\n", encoding="utf-8")
        gi = self.repo / ".flow" / ".gitignore"
        gi.unlink()
        gi.symlink_to(victim)
        self._put()
        self.assertEqual(
            victim.read_text(encoding="utf-8"), "IMPORTANT-USER-FILE\n",
            "an out-of-tree file was overwritten through a symlinked .gitignore",
        )

    def test_a_legitimately_symlinked_flow_dir_still_works(self) -> None:
        """`.flow` itself being a symlink is supported and common."""
        with tempfile.TemporaryDirectory() as host, tempfile.TemporaryDirectory() as data:
            repo = Path(host)
            real = Path(data) / "flowdata"
            real.mkdir()
            (repo / ".flow").symlink_to(real)
            _run(repo, "init")
            r = _run(repo, "sync", "create-first-put", "--key", self.key,
                     "--id", "I", "--identifier", "#1", "--url", "u",
                     "--title", "X", "--transport", "gh")
            self.assertEqual(r.returncode, 0, r.stderr)
            got = _run(repo, "sync", "create-first-get", "--key", self.key, "--json")
            self.assertEqual(got.returncode, 0, got.stderr)


if __name__ == "__main__":
    unittest.main()

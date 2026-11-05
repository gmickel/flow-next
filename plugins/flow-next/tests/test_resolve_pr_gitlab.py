"""resolve-pr on a GitLab origin: the merge-request discussion scripts and the forge pick.

glab answers replay the live recordings in fixtures/gitlab/ (merge request !13 of the
self-managed test project, reviewed by a second user, with one thread fixed, replied to and
resolved, one diff thread made outdated by a later push, and a top-level note answered).
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

from test_make_pr_gitlab import GitLabShellCase, answers, recorded

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent / "skills" / "flow-next-resolve-pr"
SCRIPTS = SKILL / "scripts"
FIXED = "8ec02af31f716aa23cf68c2adb7ea5c3c1e251e0"   # the f-string thread, fixed in 900c162


class MrDiscussionCase(GitLabShellCase):
    def setUp(self):
        super().setUp()
        (self.bin / "cat").symlink_to(subprocess.run(["sh", "-c", "command -v cat"], capture_output=True,
                                                     text=True, check=True).stdout.strip())

    def listing(self, **changes):
        """The recorded --paginate listing (two discussions a page) under the script's argv."""
        fx = json.loads(recorded("mr-discussions-paged").read_text(encoding="utf-8"))
        fx = {**fx, "argv": ["glab", "api", "--paginate", "projects/:id/merge_requests/13/discussions?per_page=100"],
              **changes}
        path = self.tmp / f"listing-{len(list(self.tmp.glob('listing-*.json')))}.json"
        path.write_text(json.dumps(fx), encoding="utf-8")
        return path

    def fetch(self, *fixtures):
        return self.run_sh(["bash", str(SCRIPTS / "get-mr-discussions"), "13"], GLAB_ANSWERS=answers(*fixtures))


class FetchTests(MrDiscussionCase):
    def test_every_unresolved_discussion_and_note_on_every_page(self):
        pages = recorded("mr-discussions-paged").read_text(encoding="utf-8")
        self.assertEqual(json.loads(pages)["stdout"].count("]["), 3, "the recording spans four pages")
        result = self.fetch(recorded("mr-review-read"), self.listing())
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["pr_number"], 13)
        threads = {t["id"][:8]: t for t in out["review_threads"]}
        # The fixed thread is resolved; the plain notes and the push's system note are not threads.
        self.assertEqual(list(threads), ["84d90c49", "6685c71b", "d45185d6", "4bf51d3f"])
        outdated = threads["4bf51d3f"]
        self.assertEqual((outdated["isOutdated"], outdated["path"], outdated["line"]), (True, "app.py", 6))
        self.assertEqual([c["author"]["login"] for c in outdated["comments"]], ["fx-reviewer"],
                         "GitLab's 'changed this line' system note is not a comment")
        general = threads["84d90c49"]
        self.assertEqual((general["isOutdated"], general["path"], general["line"]), (False, None, None))
        self.assertEqual(set(general["comments"][0]), {"id", "author", "body", "createdAt"})
        # The author's last word on a thread stays visible for triage.
        self.assertEqual([c["author"]["login"] for c in threads["6685c71b"]["comments"]], ["fx-reviewer", "root"])
        # Only the reviewer's plain note; the author's own note and the push note are left out.
        self.assertEqual([(c["id"], c["author"]) for c in out["pr_comments"]], [(20, "fx-reviewer")])
        self.assertEqual(out["review_bodies"], [])
        self.assertEqual(out["cross_invocation"],
                         {"signal": True, "resolved_threads": [{"id": FIXED, "path": "app.py", "line": 2}]})

    def test_failed_or_malformed_reads_exit_nonzero(self):
        cases = [
            ("missing merge request", (recorded("mr-missing-read"),)),
            ("listing fails", (recorded("mr-review-read"),
                               self.listing(returncode=1, stdout="", stderr="glab: 500 Internal Server Error\n"))),
            ("listing not JSON", (recorded("mr-review-read"), self.listing(stdout="<html>busy</html>\n"))),
        ]
        for name, fixtures in cases:
            with self.subTest(name):
                result = self.fetch(*fixtures)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


class ReplyAndResolveTests(MrDiscussionCase):
    def reply(self, text, discussion=FIXED):
        return subprocess.run(["bash", str(SCRIPTS / "reply-to-mr-discussion"), "13", discussion], input=text,
                              env={"PATH": str(self.bin), "STUB_CALLS": str(self.calls),
                                   "GLAB_ANSWERS": answers(recorded("mr-discussion-reply"))},
                              capture_output=True, text=True, timeout=60)

    def recorded_body(self, name):
        argv = json.loads(recorded(name).read_text(encoding="utf-8"))["argv"]
        return argv[argv.index("-f") + 1].removeprefix("body=")

    def test_fixed_thread_gets_a_reply_then_resolves(self):
        result = self.reply(self.recorded_body("mr-discussion-reply") + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["author"]["username"], "root")
        resolved = self.run_sh(["bash", str(SCRIPTS / "resolve-mr-discussion"), "13", FIXED],
                               GLAB_ANSWERS=answers(recorded("mr-discussion-resolve")))
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertTrue(all(n["resolved"] for n in json.loads(resolved.stdout)["notes"] if n["resolvable"]))

    def test_declined_thread_gets_a_reply_and_no_resolve(self):
        """Replying never resolves: a declined thread stays open until resolve-mr-discussion runs."""
        self.reply(self.recorded_body("mr-discussion-reply"))
        self.assertNotIn("PUT", self.calls.read_text(encoding="utf-8"))

    def test_empty_reply_never_reaches_glab(self):
        result = self.reply("")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "")

    def test_failed_reply_or_resolve_exits_nonzero(self):
        self.assertNotEqual(self.reply("a reply nobody recorded").returncode, 0)
        resolve = self.run_sh(["bash", str(SCRIPTS / "resolve-mr-discussion"), "13", "0" * 40],
                              GLAB_ANSWERS=answers(recorded("mr-discussion-resolve")))
        self.assertNotEqual(resolve.returncode, 0)

    def test_top_level_comment_reply_is_a_new_note(self):
        """forge-gitlab.md's PR-comment command is the one recorded; a reply inside the note's own
        discussion would turn it into an unresolved thread (measured)."""
        line = next(l for l in (SKILL / "forge-gitlab.md").read_text(encoding="utf-8").splitlines()
                    if "/notes" in l and "glab api" in l)
        command = re.search(r"`(glab api [^`]+)`", line).group(1)
        result = self.run_sh(["bash", "-c", command], PR_NUMBER="13", REPLY=self.recorded_body("mr-note-create"),
                             GLAB_ANSWERS=answers(recorded("mr-note-create")))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["resolvable"], False)


class ForgePickTests(MrDiscussionCase):
    """workflow.md's Preamble reads the forge from flowctl and stays on GitHub when it cannot."""

    LINES = "\n".join(l for l in (SKILL / "workflow.md").read_text(encoding="utf-8").splitlines()
                      if l.startswith("FORGE="))

    def pick(self, flowctl_body):
        flowctl = self.tmp / "flowctl"
        flowctl.write_text(f"#!/bin/sh\n{flowctl_body}\n", encoding="utf-8")
        flowctl.chmod(0o755)
        result = self.run_sh(["bash", "-c", f'set -e\nFLOWCTL={flowctl}\n{self.LINES}\nprintf %s "$FORGE"'])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_forge_pick(self):
        self.assertEqual(self.LINES.count("FORGE="), 2, "the Preamble's two forge lines")
        for name, body, forge in (
            ("gitlab origin", "echo '{\"forge\": \"gitlab\"}'", "gitlab"),
            ("github origin", "echo '{\"forge\": \"github\"}'", "github"),
            ("unknown host", "echo '{\"forge\": null}'", "github"),
            ("snapshot fails", "echo 'no .flow' >&2; exit 1", "github"),
            ("snapshot not JSON", "echo 'not json'", "github"),
        ):
            with self.subTest(name):
                self.assertEqual(self.pick(body), forge)


if __name__ == "__main__":
    unittest.main()

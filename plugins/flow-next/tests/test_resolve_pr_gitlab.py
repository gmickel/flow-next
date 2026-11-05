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

    def test_a_listing_past_the_argument_limit(self):
        """Linux caps one argument at 128 KiB, so the listing reaches jq on stdin."""
        stdout, pages, at = json.loads(recorded("mr-discussions-paged").read_text(encoding="utf-8"))["stdout"], [], 0
        while stdout[at:].strip():
            page, at = json.JSONDecoder().raw_decode(stdout, at)
            pages.append(page)
        copies = [{**d, "id": f"{n:02d}{d['id'][2:]}"} for n in range(14) for page in pages for d in page]
        listing = json.dumps(copies)
        self.assertGreater(len(listing), 140_000)
        result = self.fetch(recorded("mr-review-read"), self.listing(stdout=listing))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["review_threads"]), 14 * 4)

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


class ReferenceCommandTests(MrDiscussionCase):
    """Every glab command forge-gitlab.md gives the agent replays a live recording."""

    REFERENCE = re.sub(r"\s*\n\s*", " ", (SKILL / "forge-gitlab.md").read_text(encoding="utf-8"))
    RECORDINGS = ("mr-view-branch", "project-read", "mr-review-read", "fork-project-read", "mr-note-create")

    def run_command(self, command):
        body = json.loads(recorded("mr-note-create").read_text(encoding="utf-8"))["argv"][-1].removeprefix("body=")
        return self.run_sh(["bash", "-c", f"set -o pipefail; {command}"], PR_NUMBER="13", SOURCE_PROJECT_ID="2",
                           REPLY=body, GLAB_ANSWERS=answers(*map(recorded, self.RECORDINGS)))

    def test_every_glab_command_is_recorded(self):
        commands = re.findall(r"`(glab (?:api|mr) [^`]+)`", self.REFERENCE)
        self.assertEqual(len(commands), 5, commands)
        for command in commands:
            with self.subTest(command):
                result = self.run_command(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.strip())

    def test_the_answers_the_reference_reads(self):
        reads = {c: self.run_command(c).stdout.strip() for c in re.findall(r"`(glab (?:api|mr) [^`]+)`", self.REFERENCE)}
        self.assertEqual(reads['glab mr view --output json | jq -r .iid'], "13")
        self.assertEqual(reads['glab api "projects/$SOURCE_PROJECT_ID" | jq -r .http_url_to_repo'],
                         "http://localhost:8929/root/flownext-fork.git")
        # The merge request URL check: this project's own URL matches, another project's does not.
        web_url = reads['glab api "projects/:id" | jq -r .web_url']
        mr_url = json.loads(json.loads(recorded("mr-review-read").read_text(encoding="utf-8"))["stdout"])["web_url"]
        self.assertEqual(mr_url.split("/-/merge_requests/")[0].lower(), web_url.lower())
        self.assertNotEqual("http://localhost:8929/root/flownext-fork", web_url.lower())
        # A top-level reply is a new note, never a reply inside the note's discussion, which
        # turns the note into an unresolved thread (measured).
        note = reads['glab api -X POST "projects/:id/merge_requests/$PR_NUMBER/notes" -f "body=$REPLY"']
        self.assertIs(json.loads(note)["resolvable"], False)


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

    def test_crlf_jq_output(self):
        """Windows jq.exe ends its output with CRLF; the CR never reaches FORGE."""
        jq = subprocess.run(["sh", "-c", "command -v jq"], capture_output=True, text=True, check=True).stdout.strip()
        (self.bin / "jq").unlink()
        self.stub("jq", f"#!/bin/sh\n{jq} \"$@\" | sed 's/$/\\r/'\n")
        self.assertEqual(self.pick("echo '{\"forge\": \"gitlab\"}'"), "gitlab")


if __name__ == "__main__":
    unittest.main()

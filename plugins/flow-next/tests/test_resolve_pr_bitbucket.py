"""resolve-pr on a Bitbucket Cloud origin: the pull request comment scripts and the forge pick.

bkt answers replay the live recordings in fixtures/bitbucket/ (pull request 9 of the
flownextnew/flownext test repository: a general and an inline comment, a reply and a reply to
it, a comment resolved and one deleted, and a later push that changed the inline comment's line).
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

from test_forge_bitbucket import ORIGIN
from test_make_pr_bitbucket import BitbucketShellCase, answers, recorded

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent / "skills" / "flow-next-resolve-pr"
SCRIPTS = SKILL / "scripts"
PULLS = "/repositories/flownextnew/flownext/pullrequests"
OPEN_THREAD, GENERAL, SETTLED = 901784115, 901784108, 901784139   # the recorded comment ids


def api(path):
    return ["bkt", "--context", "flownextnew", "api", path]


class BitbucketCommentCase(BitbucketShellCase):
    def setUp(self):
        super().setUp()
        (self.bin / "cat").symlink_to(subprocess.run(["sh", "-c", "command -v cat"], capture_output=True,
                                                     text=True, check=True).stdout.strip())
        self.repo = self.repo_on("fx-review", ORIGIN)

    def script(self, name, *args, stdin=None, **env):
        return self.run_sh(["bash", str(SCRIPTS / name), *args], cwd=self.repo, **env) if stdin is None else \
            subprocess.run(["bash", str(SCRIPTS / name), *args], cwd=self.repo, input=stdin, capture_output=True, text=True,
                           timeout=60, env={"PATH": str(self.bin), "HOME": str(self.tmp), "STUB_CALLS": str(self.calls), **env})

    def fetch(self, *fixtures, **env):
        return self.script("get-bb-comments", "9", BKT_ANSWERS=answers(*fixtures), **env)

    def threads(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return {t["id"]: t for t in json.loads(result.stdout)["review_threads"]}


class FetchTests(BitbucketCommentCase):
    def test_every_unresolved_top_level_comment_with_its_replies(self):
        result = self.fetch(recorded("pr-view-review"), recorded("comments-list"))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["pr_number"], 9)
        # The general and the line-4 comments are resolved; the deleted one is left out.
        self.assertEqual(list(self.threads(result)), [OPEN_THREAD])
        thread = out["review_threads"][0]
        self.assertEqual((thread["path"], thread["line"]), ("review.txt", 2))
        # The reply and the reply to that reply sit under their top-level comment, oldest first.
        self.assertEqual([c["id"] for c in thread["comments"]], [OPEN_THREAD, 901784129, 901785214])
        self.assertEqual(set(thread["comments"][0]), {"id", "author", "body", "createdAt"})
        self.assertEqual(thread["comments"][0]["body"], "Inline: line two should say 2.")
        self.assertEqual((out["pr_comments"], out["review_bodies"]), ([], []))
        self.assertEqual(out["cross_invocation"], {"signal": True, "resolved_threads": [
            {"id": GENERAL, "path": None, "line": None}, {"id": SETTLED, "path": "review.txt", "line": 4}]})

    def test_an_inline_comment_on_a_changed_line_is_outdated(self):
        # The push changed line 2, so Bitbucket kept that comment on the earlier head; the
        # comment on unchanged line 4 moved to the current head. Unresolved here to compare both.
        def reopen(page):
            for comment in page["values"]:
                comment.pop("resolution", None)
        threads = self.threads(self.fetch(recorded("pr-view-review"), self.derived("comments-list", reopen)))
        self.assertEqual({i: t["isOutdated"] for i, t in threads.items()}, {GENERAL: False, OPEN_THREAD: True, SETTLED: False})
        self.assertEqual((threads[GENERAL]["path"], threads[GENERAL]["line"]), (None, None))   # a general comment

    def test_every_page(self):
        first = self.derived("comments-page-1", argv=api(f"{PULLS}/9/comments?pagelen=100"))
        paged = self.fetch(recorded("pr-view-review"), first, recorded("comments-page-2"), recorded("comments-page-3"))
        whole = self.fetch(recorded("pr-view-review"), recorded("comments-list"))
        # The paged recording predates the reply to the reply; otherwise the answers agree.
        self.assertEqual([c["id"] for c in self.threads(paged)[OPEN_THREAD]["comments"]], [OPEN_THREAD, 901784129])
        self.assertEqual(json.loads(paged.stdout)["cross_invocation"], json.loads(whole.stdout)["cross_invocation"])

    def test_a_listing_past_the_argument_limit(self):
        """Linux caps one argument at 128 KiB, so the listing reaches jq on stdin."""
        def many(page):
            top = next(c for c in page["values"] if c["id"] == OPEN_THREAD)
            page["values"] = [{**top, "id": n, "content": {**top["content"], "raw": "x" * 400}} for n in range(1, 400)]
            page["size"] = len(page["values"])
        listing = self.derived("comments-list", many)
        self.assertGreater(len(listing.read_text(encoding="utf-8")), 140_000)
        self.assertEqual(len(self.threads(self.fetch(recorded("pr-view-review"), listing))), 399)

    def test_failed_partial_or_malformed_reads_exit_nonzero(self):
        def orphan(page):
            next(c for c in page["values"] if c["id"] == 901785214)["parent"]["id"] = 1
        listing = api(f"{PULLS}/9/comments?pagelen=100")
        cases = [
            ("missing pull request", (self.derived("comments-missing-pr", argv=api(f"{PULLS}/9")),), {}),
            ("listing fails", (recorded("pr-view-review"), self.derived("comments-missing-pr", argv=listing)), {}),
            ("listing not JSON", (recorded("pr-view-review"), self.derived("comments-list", stdout="<html>busy</html>\n")), {}),
            ("listing changed while read", (recorded("pr-view-review"), self.derived("comments-list", lambda p: p.update(size=9))), {}),
            ("next page elsewhere", (recorded("pr-view-review"), self.derived("comments-list", lambda p: p.update(next="https://example.test/2"))), {}),
            ("reply without its parent", (recorded("pr-view-review"), self.derived("comments-list", orphan)), {}),
            ("comment without content", (recorded("pr-view-review"), self.derived("comments-list", lambda p: [p["values"][1].pop("content"), None][1])), {}),
            ("unreadable parent", (recorded("pr-view-review"), self.derived("comments-list", lambda p: p["values"][2].update(parent={}))), {}),
            ("no Cloud context", (recorded("pr-view-review"), recorded("comments-list")), {"BKT_CONTEXTS": "context-list-none"}),
        ]
        for name, fixtures, env in cases:
            with self.subTest(name):
                result = self.fetch(*fixtures, **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
        self.assertIn("bkt context create", self.fetch(recorded("pr-view-review"), BKT_CONTEXTS="context-list-none").stderr)


class CurrentPullRequestTests(BitbucketCommentCase):
    def test_the_branch_open_pull_request(self):
        found = self.script("get-bb-current-pr", BKT_ANSWERS=answers(recorded("pr-branch-review")))
        self.assertEqual((found.returncode, found.stdout.strip()), (0, "9"), found.stderr)
        none = self.derived("pr-branch-review", lambda page: page.update(values=[], size=0))
        self.assertEqual(self.script("get-bb-current-pr", BKT_ANSWERS=answers(none)).stdout, "")
        fork = self.derived("pr-branch-review", lambda page: page["values"][0]["source"]["repository"].update(full_name="flownextnew/flownext-fork"))
        self.assertEqual(self.script("get-bb-current-pr", BKT_ANSWERS=answers(fork)).stdout, "")
        deleted_fork = self.derived("pr-branch-review", lambda page: page["values"][0]["source"].update(repository=None))
        self.assertEqual(self.script("get-bb-current-pr", BKT_ANSWERS=answers(deleted_fork)).stdout, "")
        for name, change in (("no source", lambda page: [page["values"][0].pop("source"), None][1]),
                             ("no source repository", lambda page: [page["values"][0]["source"].pop("repository"), None][1]),
                             ("unreadable source repository", lambda page: page["values"][0]["source"].update(repository={}))):
            with self.subTest(name):
                result = self.script("get-bb-current-pr", BKT_ANSWERS=answers(self.derived("pr-branch-review", change)))
                self.assertEqual((result.returncode, result.stdout), (1, ""))
        failed = self.derived("comments-missing-pr", argv=json.loads(recorded("pr-branch-review").read_text(encoding="utf-8"))["argv"])
        result = self.script("get-bb-current-pr", BKT_ANSWERS=answers(failed))
        self.assertEqual((result.returncode, result.stdout), (1, ""))

    def test_the_pull_request_push_target(self):
        result = self.script("get-bb-pr", "9", BKT_ANSWERS=answers(recorded("pr-view-review")))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "id": 9, "state": "OPEN", "source_branch": "fx-review", "destination_branch": "main",
            "source_repository": "flownextnew/flownext", "destination_repository": "flownextnew/flownext",
            "html_url": "https://bitbucket.org/flownextnew/flownext/pull-requests/9"})


class ReplyAndResolveTests(BitbucketCommentCase):
    def reply(self, text, comment=OPEN_THREAD):
        return self.script("reply-to-bb-comment", "9", str(comment), stdin=text, BKT_ANSWERS=answers(recorded("comment-reply")))

    def test_a_reply_goes_under_the_thread_then_it_resolves(self):
        result = self.reply('> quoted "x" $HOME\n\nFixed in abc123.\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["parent"]["id"], OPEN_THREAD)
        self.assertEqual(self.bodies(), [{"content": {"raw": '> quoted "x" $HOME\n\nFixed in abc123.'}, "parent": {"id": OPEN_THREAD}}])
        resolved = self.script("resolve-bb-comment", "9", str(SETTLED), BKT_ANSWERS=answers(recorded("comment-resolve-inline")))
        self.assertEqual((resolved.returncode, json.loads(resolved.stdout)["type"]), (0, "comment_resolution"), resolved.stderr)

    def test_replying_never_resolves(self):
        self.reply("declined, with evidence")
        self.assertNotIn("/resolve", self.calls.read_text(encoding="utf-8"))

    def test_resolving_a_resolved_comment_is_done(self):
        # Bitbucket answers 409 "Comment has already been resolved." (recorded).
        again = self.script("resolve-bb-comment", "9", str(GENERAL), BKT_ANSWERS=answers(recorded("comment-resolve-again")))
        self.assertEqual((again.returncode, again.stdout), (0, ""), again.stderr)

    def test_empty_reply_never_reaches_bkt(self):
        result = self.reply("")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "")

    def test_failed_reply_or_resolve_exits_nonzero(self):
        refused = self.derived("comments-missing-pr", argv=[*api(f"{PULLS}/9/comments"), "-X", "POST"])
        reply = self.script("reply-to-bb-comment", "9", "1", stdin="x", BKT_ANSWERS=answers(refused))
        self.assertEqual(reply.returncode, 1)
        self.assertIn("404 Not Found", reply.stderr)
        missing = self.derived("comments-missing-pr", argv=[*api(f"{PULLS}/9/comments/1/resolve"), "-X", "POST"])
        resolve = self.script("resolve-bb-comment", "9", "1", BKT_ANSWERS=answers(missing))
        self.assertEqual(resolve.returncode, 1)
        self.assertIn("404 Not Found", resolve.stderr)


class ReferenceTests(BitbucketCommentCase):
    REFERENCE = (SKILL / "forge-bitbucket.md").read_text(encoding="utf-8")

    def test_every_script_the_reference_names_exists(self):
        named = set(re.findall(r'"\$SCRIPTS/([a-z-]+)"', self.REFERENCE))
        self.assertEqual(named, {"get-bb-current-pr", "get-bb-comments", "get-bb-pr", "reply-to-bb-comment", "resolve-bb-comment"})
        for name in named:
            self.assertTrue((SCRIPTS / name).is_file(), name)

    def test_the_workflow_picks_bitbucket_from_the_snapshot(self):
        lines = "\n".join(l for l in (SKILL / "workflow.md").read_text(encoding="utf-8").splitlines() if l.startswith("FORGE="))
        flowctl = self.tmp / "flowctl"
        flowctl.write_text("#!/bin/sh\necho '{\"forge\": \"bitbucket\"}'\n", encoding="utf-8")
        flowctl.chmod(0o755)
        result = self.run_sh(["bash", "-c", f'set -e\nFLOWCTL={flowctl}\n{lines}\nprintf %s "$FORGE"'])
        self.assertEqual((result.returncode, result.stdout), (0, "bitbucket"), result.stderr)
        self.assertTrue((SKILL / "forge-bitbucket.md").is_file())


if __name__ == "__main__":
    unittest.main()

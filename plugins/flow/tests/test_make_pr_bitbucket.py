"""make-pr on a Bitbucket Cloud origin: the shell forge rule, the pull-request helper,
and the preflight reads and create path it serves.

bkt answers replay the live recordings in fixtures/bitbucket/ (argv, exit code, raw
stdout and stderr from the flownextnew/flownext Bitbucket Cloud test repository).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flowctl_test_support import git
from test_forge import f
from test_forge_bitbucket import ORIGIN, BktCli, branch_argv

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
PREFLIGHT = SCRIPTS / "make-pr-preflight.sh"
HELPER = SCRIPTS / "make-pr-bitbucket.sh"
CREATE = SCRIPTS / "make-pr-create.sh"
FIXTURES = TESTS / "fixtures" / "bitbucket"
PROJECT = "flownextnew/flownext"   # the recorded repository
BODY = '## Review focus\n\nQuotes "x", `ticks`, $HOME, back\\slash, ümlaut.\n'   # the recorded create body
PR_URL = "https://bitbucket.org/flownextnew/flownext/pull-requests/"

# Matches a call to its recording with the `-d` request body left out, and logs that body.
BKT_STUB = f'''#!{sys.executable}
import json, os, sys
def key(argv):
    argv = list(argv)
    if "-d" in argv:
        del argv[argv.index("-d"):argv.index("-d") + 2]
    return argv
argv = ["bkt", *sys.argv[1:]]
with open(os.environ["STUB_CALLS"], "a") as log:
    log.write(" ".join(key(argv)) + "\\n")
if "-d" in argv:
    with open(os.environ["STUB_CALLS"] + ".bodies", "a") as log:
        log.write(json.dumps(json.loads(argv[argv.index("-d") + 1])) + "\\n")
def replay(path):
    fx = json.load(open(path, encoding="utf-8"))
    sys.stdout.write(fx["stdout"]); sys.stderr.write(fx["stderr"]); sys.exit(fx["returncode"])
if argv[1:] == ["context", "list", "--json"]:
    replay(os.path.join({str(FIXTURES)!r}, (os.environ.get("BKT_CONTEXTS") or "context-list") + ".json"))
# Answers for the same call replay in order; the last one repeats.
matching = [p for p in os.environ.get("BKT_ANSWERS", "").split(os.pathsep)
            if p and key(json.load(open(p, encoding="utf-8"))["argv"]) == key(argv)]
if matching:
    used_log = os.environ["STUB_CALLS"] + ".used"
    used = open(used_log, encoding="utf-8").read().splitlines() if os.path.exists(used_log) else []
    path = next((p for p in matching if p not in used), matching[-1])
    with open(used_log, "a", encoding="utf-8") as log:
        log.write(path + "\\n")
    replay(path)
sys.exit("stub: no recorded bkt answer for " + repr(argv))
'''
GH_STUB = '''#!/usr/bin/env bash
printf 'gh %s\\n' "$*" >> "$STUB_CALLS"
case "$1 $2" in
  "auth token") [[ " $GH_HOSTS " == *" $4 "* ]] ;;
  "auth status") exit 0 ;;
  *) exit 1 ;;
esac
'''
GLAB_STUB = '''#!/usr/bin/env bash
printf 'glab %s\\n' "$*" >> "$STUB_CALLS"
exit 1
'''
SSH_STUB = '''#!/usr/bin/env bash
host=$2
for pair in $SSH_ALIASES; do [[ "${pair%%=*}" == "$2" ]] && host=${pair#*=}; done
printf 'user git\\nhostname %s\\nport 22\\n' "$host"
'''


def recorded(name: str) -> Path:
    return FIXTURES / f"{name}.json"


def answers(*paths: Path) -> str:
    return os.pathsep.join(str(p) for p in paths)


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"), "POSIX stubs and jq")
class BitbucketShellCase(unittest.TestCase):
    """A PATH holding only the stubs and the tools the scripts use, so no real gh, glab or bkt runs."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for tool in ("bash", "git", "sed", "awk", "tr", "jq", "dirname"):
            (self.bin / tool).symlink_to(shutil.which(tool))
        self.stub("gh", GH_STUB)
        self.stub("glab", GLAB_STUB)
        self.stub("bkt", BKT_STUB)
        self.stub("ssh", SSH_STUB)
        self.calls = self.tmp / "calls"
        self.calls.touch()

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def derived(self, name, change=None, *, argv=None, **fields):
        """A recorded answer with its body or fields changed, for shapes the test repository cannot produce."""
        fx = json.loads(recorded(name).read_text(encoding="utf-8"))
        if change:
            body = json.loads(fx["stdout"])
            fx["stdout"] = json.dumps(change(body) or body)
        fx.update(fields)
        if argv:
            fx["argv"] = argv
        path = self.tmp / f"{name}-{len(list(self.tmp.glob('*.json')))}.json"
        path.write_text(json.dumps(fx), encoding="utf-8")
        return path

    def bodies(self):
        """The JSON request bodies bkt received, in order."""
        path = Path(f"{self.calls}.bodies")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def calls_of(self, prefix):
        return [line for line in self.calls.read_text(encoding="utf-8").splitlines() if line.startswith(prefix)]

    def body_file(self, text=BODY):
        path = self.tmp / "body.md"
        path.write_text(text, encoding="utf-8")
        return path

    def run_sh(self, argv, cwd=None, **env):
        base = {"PATH": str(self.bin), "HOME": str(self.tmp), "STUB_CALLS": str(self.calls), "ORIGIN_PROJECT": PROJECT}
        return subprocess.run(argv, cwd=cwd or self.tmp, env={**base, **env}, capture_output=True, text=True, timeout=60)

    def repo_on(self, branch, origin=None):
        repo = self.tmp / "repo"
        shutil.rmtree(repo, ignore_errors=True)
        git(self.tmp, "init", "-q", "-b", branch, str(repo))
        git(repo, "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
        if origin:
            git(repo, "remote", "add", "origin", origin)
        return repo


class HelperReadTests(BitbucketShellCase):
    LIST = [str(HELPER), "pr", "list", "--state", "all", "--json", "number,state,baseRefName", "--head"]

    def test_listing_answers_in_gh_keys_without_fork_pull_requests(self):
        listed = self.run_sh([*self.LIST, "fx-reused"], BKT_ANSWERS=answers(recorded("pr-branch-reused")))
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout), [
            {"number": 4, "state": "OPEN", "baseRefName": "main"},
            {"number": 3, "state": "CLOSED", "baseRefName": "main"}])
        # PR #7 shares the branch name from flownextnew/flownext-fork.
        fork = self.run_sh([*self.LIST, "fx-open"], BKT_ANSWERS=answers(recorded("pr-branch-fork")))
        self.assertEqual([r["number"] for r in json.loads(fork.stdout)], [1])
        merged = self.run_sh([*self.LIST, "fx-merged"], BKT_ANSWERS=answers(recorded("pr-branch-merged")))
        self.assertEqual([(r["number"], r["state"]) for r in json.loads(merged.stdout)], [(5, "MERGED")])
        none = self.run_sh([*self.LIST, "fx-nothing"], BKT_ANSWERS=answers(recorded("pr-branch-none")))
        self.assertEqual((none.returncode, json.loads(none.stdout)), (0, []))
        count = self.run_sh([*self.LIST, "fx-reused", "--jq", '[.[] | select(.state=="OPEN" or .state=="MERGED")] | length'],
                            BKT_ANSWERS=answers(recorded("pr-branch-reused")))
        self.assertEqual(count.stdout.strip(), "1")
        # The context named on the call is the Cloud one bkt lists.
        self.assertEqual({c.split()[1:3] == ["--context", "flownextnew"] for c in self.calls_of("bkt --")}, {True})

    def test_reads_answer_exactly_the_requested_keys(self):
        repo = self.repo_on("fx-reused")
        view = self.run_sh([str(HELPER), "pr", "view", "--json", "number,state,isDraft,body,url"], cwd=repo,
                           BKT_ANSWERS=answers(recorded("pr-branch-reused")))
        self.assertEqual(view.returncode, 0, view.stderr)
        self.assertEqual(json.loads(view.stdout),
                         {"number": 4, "state": "OPEN", "isDraft": False, "body": "second", "url": f"{PR_URL}4"})
        drafted = self.derived("pr-branch-reused", lambda page: [row.update(draft=True, description=None)
                                                                 for row in page["values"]] and None)
        listed = self.run_sh([*self.LIST[:6], "isDraft,body,number", "--head", "fx-reused"],
                             BKT_ANSWERS=answers(drafted))
        self.assertEqual(json.loads(listed.stdout), [{"isDraft": True, "body": "", "number": 4},
                                                     {"isDraft": True, "body": "", "number": 3}])

    def test_a_key_the_helper_cannot_answer_exits_nonzero_naming_it(self):
        repo = self.repo_on("fx-reused")
        view = self.run_sh([str(HELPER), "pr", "view", "--json", "number,mergeable"], cwd=repo,
                           BKT_ANSWERS=answers(recorded("pr-branch-reused")))
        self.assertNotEqual(view.returncode, 0)
        self.assertIn("mergeable", view.stderr)
        self.assertEqual(view.stdout, "")

    def test_listing_follows_the_next_page(self):
        first = self.derived("pr-branch-reused", lambda page: page.update(
            values=page["values"][:1], pagelen=1,
            next=f"https://api.bitbucket.org/2.0{branch_argv('fx-reused')[4].replace('&page=1', '&page=2')}"))
        second = self.derived("pr-branch-reused", lambda page: page.update(values=page["values"][1:], page=2, pagelen=1),
                              argv=[*branch_argv("fx-reused")[:4], branch_argv("fx-reused")[4].replace("&page=1", "&page=2")])
        listed = self.run_sh([*self.LIST, "fx-reused"], BKT_ANSWERS=answers(first, second))
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual([r["number"] for r in json.loads(listed.stdout)], [4, 3])

    def test_view_answers_the_branch_open_pull_request(self):
        repo = self.repo_on("fx-reused")
        view = self.run_sh([str(HELPER), "pr", "view", "--json", "url,state,number"], cwd=repo,
                           BKT_ANSWERS=answers(recorded("pr-branch-reused")))
        self.assertEqual(view.returncode, 0, view.stderr)
        self.assertEqual((json.loads(view.stdout)["number"], json.loads(view.stdout)["state"]), (4, "OPEN"))
        created = self.run_sh([str(HELPER), "pr", "view", "--json", "createdAt", "--jq", ".createdAt"], cwd=repo,
                              BKT_ANSWERS=answers(recorded("pr-branch-reused")))
        self.assertEqual(created.stdout.strip(), "2026-11-13T10:37:47.056362+00:00")
        git(repo, "checkout", "-q", "-b", "fx-merged")   # merged only: no open pull request
        merged = self.run_sh([str(HELPER), "pr", "view", "--json", "url,state,number"], cwd=repo,
                             BKT_ANSWERS=answers(recorded("pr-branch-merged")))
        self.assertEqual((merged.returncode, merged.stdout), (0, ""))

    def test_failed_or_malformed_reads_exit_nonzero(self):
        reused = branch_argv("fx-reused")
        def drop(key):
            def edit(page):
                page["values"][1].pop(key)   # edits the row in place; the page stays the body
            return edit
        cases = [
            ("bkt fails", self.derived("pr-branch-missing-repo", argv=reused), {}),
            ("no credentials", self.derived("api-no-credentials", argv=reused), {}),
            ("no Cloud context", recorded("pr-branch-reused"), {"BKT_CONTEXTS": "context-list-none"}),
            ("row without id", self.derived("pr-branch-reused", drop("id")), {}),
            ("unknown state", self.derived("pr-branch-reused", lambda page: page["values"][0].update(state="WITHDRAWN")), {}),
            ("empty link", self.derived("pr-branch-reused", lambda page: page["values"][0]["links"]["html"].update(href="")), {}),
            ("not a listing", self.derived("pr-branch-reused", lambda page: page["values"]), {}),
            ("empty output", self.derived("pr-branch-reused", stdout=""), {}),
            ("non-JSON output", self.derived("pr-branch-reused", stdout="<html>unreadable</html>\n"), {}),
            ("size disagrees", self.derived("pr-branch-reused", lambda page: page.update(size=3)), {}),
            ("next page elsewhere", self.derived("pr-branch-reused", lambda page: page.update(next="https://example.test/2")), {}),
            ("unreadable source repository", self.derived("pr-branch-reused", lambda page: page["values"][0]["source"].update(repository={})), {}),
        ]
        for name, fixture, env in cases:
            with self.subTest(name):
                result = self.run_sh([*self.LIST, "fx-reused"], BKT_ANSWERS=answers(fixture), **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
        bad = self.run_sh([*self.LIST, "fx-reused"], ORIGIN_PROJECT="flownextnew")
        self.assertIn("no origin repository", bad.stderr)

    def test_login(self):
        repo = ["bkt", "--context", "flownextnew", "api", "/repositories/flownextnew/flownext"]
        cases = [("reads the repository", answers(recorded("repo-read")), {}, 0),
                 ("no credentials", answers(self.derived("api-no-credentials", argv=repo)), {}, 1),
                 ("no Cloud context", answers(recorded("repo-read")), {"BKT_CONTEXTS": "context-list-none"}, 1)]
        for name, fixtures, env, rc in cases:
            with self.subTest(name):
                self.assertEqual(self.run_sh([str(HELPER), "login"], BKT_ANSWERS=fixtures, **env).returncode, rc)


class HelperWriteTests(BitbucketShellCase):
    """`pr create` and `pr edit`: the request body bkt sends, and the URL printed."""

    def none_on(self, branch):
        """The recorded empty listing, answering `branch`'s read."""
        return self.derived("pr-branch-none", argv=branch_argv(branch))

    def test_create_sends_the_body_and_prints_the_url(self):
        body = self.body_file()
        for draft, name, branch, number in ((True, "pr-create-draft", "fx-draft", 2), (False, "pr-create-ready", "fx-open", 1)):
            with self.subTest(name):
                result = self.run_sh([str(HELPER), "pr", "create", "--title", "t", "--body-file", str(body),
                                      *(["--draft"] if draft else []), "--base", "main", "--head", branch],
                                     BKT_ANSWERS=answers(self.none_on(branch), recorded(name)))
                self.assertEqual((result.returncode, result.stdout), (0, f"{PR_URL}{number}\n"), result.stderr)
                self.assertEqual(self.bodies()[-1], {"title": "t", "description": BODY, **({"draft": True} if draft else {}),
                                                     "source": {"branch": {"name": branch}}, "destination": {"branch": {"name": "main"}}})

    def test_edit_replaces_the_description_and_keeps_the_draft_state_unless_ready(self):
        body = self.body_file()
        plain = self.run_sh([str(HELPER), "pr", "edit", "6", "--body-file", str(body)], BKT_ANSWERS=answers(recorded("pr-edit-description")))
        self.assertEqual((plain.returncode, plain.stdout), (0, f"{PR_URL}6\n"), plain.stderr)
        self.assertEqual(self.bodies(), [{"description": BODY}])
        ready = self.run_sh([str(HELPER), "pr", "edit", "6", "--body-file", str(body), "--ready"], BKT_ANSWERS=answers(recorded("pr-edit-ready")))
        self.assertEqual((ready.returncode, ready.stdout), (0, f"{PR_URL}6\n"), ready.stderr)
        self.assertEqual(self.bodies()[-1], {"description": BODY, "draft": False})

    def test_create_refuses_a_branch_with_an_open_pull_request(self):
        # Bitbucket would answer this create with PR #1, its title and description overwritten.
        argv = [str(HELPER), "pr", "create", "--title", "t", "--body-file", str(self.body_file()), "--base", "main", "--head", "fx-open"]
        for name, listing, message in (("open PR", recorded("pr-branch-fork"), f"already has an OPEN pull request: {PR_URL}1"),
                                       ("unreadable", self.derived("pr-branch-missing-repo", argv=branch_argv("fx-open")),
                                        "cannot read the pull requests of fx-open")):
            with self.subTest(name):
                self.calls.write_text("", encoding="utf-8")
                result = self.run_sh(argv, BKT_ANSWERS=answers(listing, recorded("pr-create-existing")))
                self.assertEqual((result.returncode, result.stdout), (1, ""))
                self.assertIn(message, result.stderr)
                self.assertEqual([c for c in self.calls_of("bkt") if "-X POST" in c], [])

    def test_refused_create_prints_bitbuckets_answer(self):
        result = self.run_sh([str(HELPER), "pr", "create", "--title", "t", "--body-file", str(self.body_file()),
                              "--base", "main", "--head", "fx-not-pushed"],
                             BKT_ANSWERS=answers(self.none_on("fx-not-pushed"), recorded("pr-create-no-branch")))
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertIn("source: branch not found: fx-not-pushed", result.stderr)


if __name__ == "__main__":
    unittest.main()

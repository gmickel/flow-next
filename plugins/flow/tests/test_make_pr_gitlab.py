"""make-pr on a GitLab origin: the shell forge rule, the merge-request read helper,
and the preflight reads it serves.

glab answers replay the live recordings in fixtures/gitlab/ (argv, environment,
exit code, raw stdout and stderr from a self-managed GitLab test project).
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
from test_forge import GITLAB_ORIGIN, FakeCli, f

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
PREFLIGHT = SCRIPTS / "make-pr-preflight.sh"
HELPER = SCRIPTS / "make-pr-gitlab.sh"
CREATE = SCRIPTS / "make-pr-create.sh"
FIXTURES = TESTS / "fixtures" / "gitlab"
HOST, PROJECT = "localhost:8929", "flownext/flownext"   # the recorded project
BODY = '## Review focus\n\nQuotes "x", `ticks`, $HOME, back\\slash, \u00fcmlaut.\n'   # the recorded create body
MR_URL = "http://localhost:8929/flownext/flownext/-/merge_requests/"

GLAB_STUB = f'''#!{sys.executable}
import json, os, sys
argv = ["glab", *sys.argv[1:]]
with open(os.environ["STUB_CALLS"], "a") as log:
    log.write(" ".join(argv) + "\\n")
if "--input" in argv:   # the request body, one JSON document per write
    with open(os.environ["STUB_CALLS"] + ".bodies", "a") as log:
        log.write(json.dumps(json.load(sys.stdin)) + "\\n")
def replay(path):
    fx = json.load(open(path, encoding="utf-8"))
    if "GITLAB_HOST" in fx["env"] and os.environ.get("GITLAB_HOST") != fx["env"]["GITLAB_HOST"]:
        sys.exit("stub: GITLAB_HOST is " + repr(os.environ.get("GITLAB_HOST")))
    sys.stdout.write(fx["stdout"]); sys.stderr.write(fx["stderr"]); sys.exit(fx["returncode"])
if argv[1:3] == ["auth", "status"]:
    name = ("auth-status-logged-in" if argv[4] in os.environ.get("GLAB_HOSTS", "").split()
            else os.environ.get("GLAB_AUTH") or "auth-status-unknown-host")
    replay(os.path.join({str(FIXTURES)!r}, name + ".json"))
# Answers for the same argv replay in order; the last one repeats.
matching = [p for p in os.environ.get("GLAB_ANSWERS", "").split(os.pathsep)
            if p and json.load(open(p, encoding="utf-8"))["argv"] == argv]
if matching:
    used_log = os.environ["STUB_CALLS"] + ".used"
    used = open(used_log, encoding="utf-8").read().splitlines() if os.path.exists(used_log) else []
    path = next((p for p in matching if p not in used), matching[-1])
    with open(used_log, "a", encoding="utf-8") as log:
        log.write(path + "\\n")
    replay(path)
sys.exit("stub: no recorded glab answer for " + repr(argv))
'''
GH_STUB = '''#!/usr/bin/env bash
printf 'gh %s\\n' "$*" >> "$STUB_CALLS"
case "$1 $2" in
  "auth token") [[ " $GH_HOSTS " == *" $4 "* ]] ;;
  "auth status") exit 0 ;;
  *) exit 1 ;;
esac
'''
SSH_STUB = '''#!/usr/bin/env bash
host=$2
for pair in $SSH_ALIASES; do [[ "${pair%%=*}" == "$2" ]] && host=${pair#*=}; done
printf 'user git\\nhostname %s\\nport 22\\n' "$host"
'''


def answers(*paths: Path) -> str:
    return os.pathsep.join(str(p) for p in paths)


def recorded(name: str) -> Path:
    return FIXTURES / f"{name}.json"


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"), "POSIX stubs and jq")
class GitLabShellCase(unittest.TestCase):
    """A PATH holding only the stubs and the tools the scripts use, so no real gh or glab runs."""

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
        self.stub("ssh", SSH_STUB)
        self.calls = self.tmp / "calls"
        self.calls.touch()

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def derived(self, name, change):
        """A recorded answer with one row changed, for shapes the live project cannot produce."""
        fx = json.loads(recorded(name).read_text(encoding="utf-8"))
        fx["stdout"] = json.dumps(change(json.loads(fx["stdout"])))
        path = self.tmp / f"{name}-{len(list(self.tmp.glob('*.json')))}.json"
        path.write_text(json.dumps(fx), encoding="utf-8")
        return path

    def blank(self, name, stdout):
        """A recorded success whose stdout is replaced: glab exits 0 without a listing."""
        path = self.derived(name, lambda rows: rows)
        fx = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**fx, "stdout": stdout}), encoding="utf-8")
        return path

    def bodies(self):
        """The JSON request bodies glab received, in order."""
        path = Path(f"{self.calls}.bodies")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def body_file(self, text=BODY):
        path = self.tmp / "body.md"
        path.write_text(text, encoding="utf-8")
        return path

    def run_sh(self, argv, cwd=None, **env):
        base = {"PATH": str(self.bin), "HOME": str(self.tmp), "STUB_CALLS": str(self.calls),
                "GITLAB_HOST": HOST, "ORIGIN_PROJECT": PROJECT}
        return subprocess.run(argv, cwd=cwd or self.tmp, env={**base, **env}, capture_output=True, text=True, timeout=60)

    def repo_on(self, branch, origin=None):
        repo = self.tmp / "repo"
        shutil.rmtree(repo, ignore_errors=True)
        git(self.tmp, "init", "-q", "-b", branch, str(repo))
        git(repo, "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
        if origin:
            git(repo, "remote", "add", "origin", origin)
        return repo


class HelperReadTests(GitLabShellCase):
    LIST = [str(HELPER), "pr", "list", "--state", "all", "--json", "number,state,baseRefName", "--head"]

    def test_listing_answers_in_gh_keys_without_fork_merge_requests(self):
        listed = self.run_sh([*self.LIST, "fn73-fx-reused"], GLAB_ANSWERS=answers(recorded("mr-branch-all")))
        self.assertEqual(listed.returncode, 0, listed.stderr)
        # The fork's MR !7 shares the branch name and is not the origin project's.
        self.assertEqual(json.loads(listed.stdout), [
            {"number": 2, "baseRefName": "main", "state": "OPEN"},
            {"number": 1, "baseRefName": "main", "state": "CLOSED"}])
        merged = self.run_sh([*self.LIST, "fn73-fx-merged"], GLAB_ANSWERS=answers(recorded("mr-branch-merged")))
        self.assertEqual([(r["number"], r["state"], r["baseRefName"]) for r in json.loads(merged.stdout)], [(3, "MERGED", "main")])
        none = self.run_sh([*self.LIST, "fn73-fx-absent"], GLAB_ANSWERS=answers(recorded("mr-branch-none")))
        self.assertEqual((none.returncode, json.loads(none.stdout)), (0, []))
        count = self.run_sh([*self.LIST, "fn73-fx-reused", "--jq", '[.[] | select(.state=="OPEN" or .state=="MERGED")] | length'],
                            GLAB_ANSWERS=answers(recorded("mr-branch-all")))
        self.assertEqual(count.stdout.strip(), "1")

    def test_reads_answer_exactly_the_requested_keys(self):
        repo = self.repo_on("fn73-fx-reused")
        view = self.run_sh([str(HELPER), "pr", "view", "--json", "number,isDraft,body"], cwd=repo,
                           GLAB_ANSWERS=answers(recorded("mr-branch-all")))
        self.assertEqual(view.returncode, 0, view.stderr)
        self.assertEqual(json.loads(view.stdout), {"number": 2, "isDraft": True, "body": ""})
        described = self.derived("mr-branch-all", lambda rows: [r.update(description="why") or r for r in rows])
        listed = self.run_sh([*self.LIST[:6], "body,number", "--head", "fn73-fx-reused"],
                             GLAB_ANSWERS=answers(described))
        self.assertEqual(json.loads(listed.stdout), [{"body": "why", "number": 2}, {"body": "why", "number": 1}])

    def test_a_key_the_helper_cannot_answer_exits_nonzero_naming_it(self):
        repo = self.repo_on("fn73-fx-reused")
        view = self.run_sh([str(HELPER), "pr", "view", "--json", "number,mergeable"], cwd=repo,
                           GLAB_ANSWERS=answers(recorded("mr-branch-all")))
        self.assertNotEqual(view.returncode, 0)
        self.assertIn("mergeable", view.stderr)
        self.assertEqual(view.stdout, "")

    def test_view_answers_the_branch_open_or_locked_merge_request(self):
        def lock(rows):
            next(r for r in rows if r["iid"] == 2)["state"] = "locked"   # mid-merge, still open
            return rows
        repo = self.repo_on("fn73-fx-reused")
        for fixture in (recorded("mr-branch-all"), self.derived("mr-branch-all", lock)):
            with self.subTest(fixture.name):
                view = self.run_sh([str(HELPER), "pr", "view", "--json", "url,state,number"], cwd=repo, GLAB_ANSWERS=answers(fixture))
                self.assertEqual(view.returncode, 0, view.stderr)
                self.assertEqual((json.loads(view.stdout)["number"], json.loads(view.stdout)["state"]), (2, "OPEN"))
        git(repo, "checkout", "-q", "-b", "fn73-fx-absent")
        none = self.run_sh([str(HELPER), "pr", "view", "--json", "url,state,number"], cwd=repo, GLAB_ANSWERS=answers(recorded("mr-branch-none")))
        self.assertEqual((none.returncode, none.stdout), (0, ""))

    def test_failed_or_malformed_reads_exit_nonzero(self):
        def drop_iid(rows):
            rows[1].pop("iid")
            return rows
        cases = [
            ("glab fails", recorded("mr-missing-project"), "flownext/missing"),
            ("row without iid", self.derived("mr-branch-all", drop_iid), PROJECT),
            ("list-valued state", self.derived("mr-branch-all", lambda rows: [{**rows[0], "state": ["opened"]}]), PROJECT),
            ("not a listing", self.derived("mr-branch-all", lambda rows: rows[0]), PROJECT),
            ("empty output", self.blank("mr-branch-all", ""), PROJECT),
            ("non-JSON output", self.blank("mr-branch-all", "<html>unreadable</html>\n"), PROJECT),
            ("empty web_url", self.derived("mr-branch-all", lambda rows: [{**rows[0], "web_url": ""}]), PROJECT),
        ]
        for name, fixture, project in cases:
            with self.subTest(name):
                result = self.run_sh([*self.LIST, "fn73-fx-reused"], GLAB_ANSWERS=answers(fixture), ORIGIN_PROJECT=project)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_api_scope(self):
        for name, rc in (("token-self-api", 0), ("token-self-read-api", 1), ("token-self-revoked", 1)):
            with self.subTest(name):
                self.assertEqual(self.run_sh([str(HELPER), "api-scope"], GLAB_ANSWERS=answers(recorded(name))).returncode, rc)
        # An OAuth login is refused by the token self-read and reads its scopes from token info.
        oauth = answers(recorded("token-self-oauth"), recorded("config-api-protocol"), recorded("token-info-oauth"))
        self.assertEqual(self.run_sh([str(HELPER), "api-scope"], GLAB_ANSWERS=oauth).returncode, 0)
        # glab may print a config warning before the value.
        warning = self.tmp / "config-api-protocol-warned.json"
        warning.write_text(json.dumps({**json.loads(recorded("config-api-protocol").read_text(encoding="utf-8")),
                                       "stdout": "a glab config warning\nhttp\n"}), encoding="utf-8")
        warned = answers(recorded("token-self-oauth"), warning, recorded("token-info-oauth"))
        self.assertEqual(self.run_sh([str(HELPER), "api-scope"], GLAB_ANSWERS=warned).returncode, 0)
        # A login keyed by the bare hostname reads token info on the web port its api_host names.
        def bare(name, argv, stdout=None):
            fx = json.loads(recorded(name).read_text(encoding="utf-8"))
            path = self.tmp / f"bare-{len(list(self.tmp.glob('bare-*')))}.json"
            path.write_text(json.dumps({**fx, "argv": argv, "env": {**fx["env"], "GITLAB_HOST": "localhost"},
                                        "stdout": fx["stdout"] if stdout is None else stdout}), encoding="utf-8")
            return path
        bare_host = answers(bare("token-self-oauth", ["glab", "api", "personal_access_tokens/self"]),
                            bare("config-api-protocol", ["glab", "config", "get", "api_protocol", "--host", "localhost"]),
                            bare("config-api-protocol", ["glab", "config", "get", "api_host", "--host", "localhost"], f"{HOST}\n"),
                            bare("token-info-oauth", ["glab", "api", f"http://{HOST}/oauth/token/info"]))
        self.assertEqual(self.run_sh([str(HELPER), "api-scope"], GLAB_ANSWERS=bare_host, GITLAB_HOST="localhost").returncode, 0)
        no_api = self.derived("token-info-oauth", lambda info: {**info, "scopes": ["read_api"], "scope": ["read_api"]})
        oauth_read_api = answers(recorded("token-self-oauth"), recorded("config-api-protocol"), no_api)
        self.assertEqual(self.run_sh([str(HELPER), "api-scope"], GLAB_ANSWERS=oauth_read_api).returncode, 1)
        # Scopes as a string are malformed: "read_api" must not read as api scope.
        string_scopes = self.derived("token-self-read-api", lambda tok: {**tok, "scopes": "read_api"})
        self.assertEqual(self.run_sh([str(HELPER), "api-scope"], GLAB_ANSWERS=answers(string_scopes)).returncode, 1)


class HelperWriteTests(GitLabShellCase):
    """`pr create` and `pr edit`: the request body glab receives on stdin, and the URL printed."""

    def test_create_sends_the_body_as_json_and_prints_the_url(self):
        body = self.body_file()
        for draft, name, branch, title, iid in ((True, "mr-create-draft", "fn73-fx-create", "Draft: fn73 create probe", 9),
                                                (False, "mr-create-ready", "fn73-fx-create-ready", "fn73 ready create probe", 10)):
            with self.subTest(name):
                result = self.run_sh([str(HELPER), "pr", "create", "--title", title.removeprefix("Draft: "), "--body-file", str(body),
                                      *(["--draft"] if draft else []), "--base", "main", "--head", branch],
                                     GLAB_ANSWERS=answers(recorded(name)))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"{MR_URL}{iid}\n")
                self.assertEqual(self.bodies()[-1], {"source_branch": branch, "target_branch": "main", "title": title, "description": BODY})

    def test_edit_replaces_the_description_and_keeps_the_draft_state_unless_ready(self):
        body = self.body_file()
        plain = self.run_sh([str(HELPER), "pr", "edit", "9", "--body-file", str(body)], GLAB_ANSWERS=answers(recorded("mr-edit")))
        self.assertEqual((plain.returncode, plain.stdout), (0, f"{MR_URL}9\n"), plain.stderr)
        self.assertEqual(self.bodies(), [{"description": BODY}])   # no title written: the draft state stays
        for title in ("Draft: fn73 create probe", "[Draft] fn73 create probe", "(draft) Draft: fn73 create probe"):
            with self.subTest(title):
                view = self.derived("mr-view-draft", lambda mr, title=title: {**mr, "title": title})
                ready = self.run_sh([str(HELPER), "pr", "edit", "9", "--body-file", str(body), "--ready"],
                                    GLAB_ANSWERS=answers(view, recorded("mr-edit-ready")))
                self.assertEqual((ready.returncode, ready.stdout), (0, f"{MR_URL}9\n"), ready.stderr)
                self.assertEqual(self.bodies()[-1], {"description": BODY, "title": "fn73 create probe"})

    def test_refused_create_prints_gitlabs_answer(self):
        result = self.run_sh([str(HELPER), "pr", "create", "--title", "t", "--body-file", str(self.body_file()),
                              "--base", "main", "--head", "fn73-fx-not-pushed"], GLAB_ANSWERS=answers(recorded("mr-create-no-branch")))
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertIn('{"message":{"source_branch":["does not exist"]}}', result.stderr)


if __name__ == "__main__":
    unittest.main()

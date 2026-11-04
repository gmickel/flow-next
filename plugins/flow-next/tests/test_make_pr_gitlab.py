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

from chain_fixture_support import git
from test_chain_consumer_fixtures import DETECT_OUT, MAKE_PR, ConsumerWorld, fence
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
            {"number": 2, "url": "http://localhost:8929/flownext/flownext/-/merge_requests/2", "baseRefName": "main", "state": "OPEN"},
            {"number": 1, "url": "http://localhost:8929/flownext/flownext/-/merge_requests/1", "baseRefName": "main", "state": "CLOSED"}])
        merged = self.run_sh([*self.LIST, "fn73-fx-merged"], GLAB_ANSWERS=answers(recorded("mr-branch-merged")))
        self.assertEqual([(r["number"], r["state"], r["baseRefName"]) for r in json.loads(merged.stdout)], [(3, "MERGED", "main")])
        none = self.run_sh([*self.LIST, "fn73-fx-absent"], GLAB_ANSWERS=answers(recorded("mr-branch-none")))
        self.assertEqual((none.returncode, json.loads(none.stdout)), (0, []))
        count = self.run_sh([*self.LIST, "fn73-fx-reused", "--jq", '[.[] | select(.state=="OPEN" or .state=="MERGED")] | length'],
                            GLAB_ANSWERS=answers(recorded("mr-branch-all")))
        self.assertEqual(count.stdout.strip(), "1")

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


class OriginBlockTests(GitLabShellCase):
    """The origin block runs before any close or push (the `# end:block` seam, without flowctl)."""

    BLOCK = PREFLIGHT.read_text(encoding="utf-8").split("# end:block", 1)[0]
    REPORT = '\nprintf "FORGE=%s PR_READ=%s PR_HEAD_REFS=%s GITLAB_HOST=%s ORIGIN_PROJECT=%s" "$FORGE" "$PR_READ" "$PR_HEAD_REFS" "$GITLAB_HOST" "$ORIGIN_PROJECT"\n'

    def block(self, origin, *, report=True, **env):
        repo = self.repo_on("main", origin)
        script = self.BLOCK + (self.REPORT if report else "")
        return self.run_sh(["bash", "-c", script], cwd=repo, REPO_ROOT=str(repo), DRY_RUN="0",
                           FLOWCTL=str(SCRIPTS / "flowctl"), GITLAB_HOST="", ORIGIN_PROJECT="", **env)

    def test_gitlab_origin_with_glab_login_and_api_scope_passes(self):
        result = self.block(GITLAB_ORIGIN, GLAB_HOSTS=HOST, GLAB_ANSWERS=answers(recorded("token-self-api")))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"FORGE=gitlab PR_READ={HELPER} PR_HEAD_REFS=refs/merge-requests GITLAB_HOST={HOST} ORIGIN_PROJECT={PROJECT}")

    def test_missing_or_logged_out_glab_stops_naming_glab_login(self):
        for name in ("missing", "logged out"):
            with self.subTest(name):
                if name == "missing":
                    (self.bin / "glab").rename(self.tmp / "glab-away")
                result = self.block("https://gitlab.com/g/p.git", report=False)
                if name == "missing":
                    (self.tmp / "glab-away").rename(self.bin / "glab")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("glab auth login --hostname gitlab.com", result.stderr)

    def test_token_without_api_scope_stops_needs_human(self):
        for name in ("token-self-read-api", "token-self-revoked"):
            with self.subTest(name):
                result = self.block(GITLAB_ORIGIN, report=False, GLAB_HOSTS=HOST, GLAB_ANSWERS=answers(recorded(name)))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(f"NEEDS_HUMAN: make-pr needs a glab token with api scope on {HOST}", result.stderr)

    def test_host_neither_cli_claims_names_both_login_commands(self):
        result = self.block("https://gitlab.unknown.example/g/p.git", report=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("NEEDS_HUMAN: make-pr opens GitHub pull requests only", result.stderr)
        for login in ("gh auth login --hostname gitlab.unknown.example", "glab auth login --hostname gitlab.unknown.example"):
            self.assertIn(login, result.stderr)

    def test_shell_and_python_forge_rules_agree(self):
        # (name, origin, env, gh hosts, glab hosts, ssh aliases, glab auth answer)
        cases = [
            ("github https", "https://github.com/o/r.git", {}, (), (), {}, None),
            ("github scp", "git@github.com:o/r.git", {}, (), (), {}, None),
            ("ssh alias", "git@gh-work:o/r.git", {}, (), (), {"gh-work": "ssh.github.com"}, None),
            ("gitlab.com", "https://gitlab.com/g/sub/p.git", {}, (), (), {}, None),
            ("CI_SERVER_HOST", "https://git.corp.test/g/p.git", {"CI_SERVER_HOST": "git.corp.test"}, (), (), {}, None),
            ("self-managed with port", GITLAB_ORIGIN, {}, (), (HOST,), {}, None),
            ("gh-known host", "https://ghe.corp.test/o/r.git", {}, ("ghe.corp.test",), (), {}, None),
            ("logged-out host", "https://gitlab.unknown.example/g/p.git", {}, (), (), {}, None),
            # gh with an enterprise token claims every host, so glab answers first.
            ("enterprise token", GITLAB_ORIGIN, {"GH_ENTERPRISE_TOKEN": "x"}, (HOST,), (HOST,), {}, None),
            ("enterprise token, offline glab", GITLAB_ORIGIN, {"GH_ENTERPRISE_TOKEN": "x"}, (HOST,), (), {}, "auth-status-offline"),
            ("enterprise token, logged-out glab", "https://ghe.corp.test/o/r.git", {"GITHUB_ENTERPRISE_TOKEN": "x"}, ("ghe.corp.test",), (), {}, None),
            ("no origin", None, {}, (), (), {}, None),
        ]
        clean = {key: "" for key in ("CI_SERVER_HOST", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")}
        trap = "trap 'printf \"FORGE=%s HOST=%s\" \"$FORGE\" \"$ORIGIN_HOST\" > \"$OUT\"' EXIT\n"
        for name, origin, env, gh_hosts, glab_hosts, ssh, glab_auth in cases:
            with self.subTest(name):
                f.repo_forge.cache_clear()
                fake = FakeCli(origin, gh_hosts=gh_hosts, glab_hosts=glab_hosts, ssh=ssh, glab_auth=glab_auth)
                with patch.object(f.subprocess, "run", side_effect=fake), patch.dict(os.environ, {**clean, **env}):
                    python = f.repo_forge(str(self.tmp))
                repo = self.repo_on("main", origin)
                out = self.tmp / "out"
                self.run_sh(["bash", "-c", trap + self.BLOCK], cwd=repo, REPO_ROOT=str(repo), DRY_RUN="0", OUT=str(out),
                            FLOWCTL=str(SCRIPTS / "flowctl"), GH_HOSTS=" ".join(gh_hosts), GLAB_HOSTS=" ".join(glab_hosts),
                            GLAB_AUTH=glab_auth or "", SSH_ALIASES=" ".join(f"{k}={v}" for k, v in ssh.items()),
                            GLAB_ANSWERS=answers(recorded("token-self-api")), **{**clean, **env})
                shell = dict(part.split("=", 1) for part in out.read_text(encoding="utf-8").split(" "))
                self.assertEqual((shell["FORGE"] or None, shell["HOST"] or None), (python.forge, python.host))
        f.repo_forge.cache_clear()


class GitLabChainDetectTests(GitLabShellCase):
    """R13: a dependent spec's base on GitLab, through the shared chain-detect fence."""

    def setUp(self):
        super().setUp()
        (self.tmp / "world").mkdir()
        self.w = ConsumerWorld(self.tmp / "world")
        shutil.copy(self.bin / "glab", self.w.bin / "glab")

    def detect(self, child, fixture, project=PROJECT):
        env = {"REPO_ROOT": str(self.w.work), "FLOWCTL": str(self.w.bin / "flowctl"), "SPEC_ID": child, "BASE_REF": "",
               "DRY_RUN": "0", "AUTONOMOUS": "0", "FORGE": "gitlab", "PR_READ": str(HELPER), "PR_HEAD_REFS": "refs/merge-requests",
               "STUB_CALLS": str(self.calls), "GITLAB_HOST": HOST, "ORIGIN_PROJECT": project, "GLAB_ANSWERS": answers(fixture)}
        script = "export STUB_CALLS GITLAB_HOST ORIGIN_PROJECT GLAB_ANSWERS\n" + fence(MAKE_PR / "workflow.md", "chain-detect")
        return self.w.run_rc(script, env, DETECT_OUT, cwd=self.w.work)

    def chain(self, parent_branch):
        a_tip = self.w.branch(parent_branch, "main", [("a.txt", "a\n")])
        self.w.branch("B", parent_branch, [("b.txt", "b\n")])
        parent = self.w.spec("parent", parent_branch)
        return parent, self.w.spec("child", "B", deps=[parent]), a_tip

    def test_open_parent_merge_request_targets_the_parent_branch(self):
        parent, child, a_tip = self.chain("fn73-fx-reused")
        rc, got = self.detect(child, recorded("mr-branch-all"))
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["CHAIN_PARENT"], got["CHAIN_BOUNDARY"], got["PARENT_PR"], got["PARENT_PR_STATE"]),
                         ("origin/fn73-fx-reused", parent, a_tip, "2", "OPEN"))

    def test_merged_parent_targets_the_default_branch_from_the_merge_request_ref(self):
        parent, child, a_tip = self.chain("fn73-fx-merged")
        self.w.squash_merge("fn73-fx-merged")
        origin = str(self.w.origin)
        git(self.w.tmp, "--git-dir", origin, "update-ref", "refs/merge-requests/3/head", a_tip)
        git(self.w.tmp, "--git-dir", origin, "update-ref", "-d", "refs/heads/fn73-fx-merged")
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.detect(child, recorded("mr-branch-merged"))
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["CHAIN_BOUNDARY"], got["CHAIN_REWRITE"], got["PARENT_PR"], got["PARENT_PR_STATE"]),
                         ("origin/main", a_tip, "1", "3", "MERGED"))

    def test_unreadable_parent_merge_request_stops_needs_human(self):
        parent, child, _ = self.chain("fn73-fx-reused")
        malformed = self.derived("mr-branch-all", lambda rows: [{k: v for k, v in r.items() if k != "web_url"} for r in rows])
        for name, fixture, project in (("glab fails", recorded("mr-missing-project"), "flownext/missing"),
                                       ("malformed", malformed, PROJECT), ("empty output", self.blank("mr-branch-all", ""), PROJECT)):
            with self.subTest(name):
                rc, got = self.detect(child, fixture, project)
                self.assertEqual(rc, 2, got["_stderr"])
                self.assertIn(f"NEEDS_HUMAN: cannot read the PR state of parent {parent} (fn73-fx-reused)", got["_stderr"])


class ExistingMergeRequestTests(GitLabShellCase):
    """The existing-MR check on GitLab, run from §0.5 to the end so a wrong "no MR" would close the spec."""

    TAIL = "set -e\n# --- §0.5:" + PREFLIGHT.read_text(encoding="utf-8").split("# --- §0.5:", 1)[1]
    FLOWCTL = '''#!/usr/bin/env bash
printf 'flowctl %s\\n' "$*" >> "$STUB_CALLS"
[[ "$1" == show ]] && printf '{"id":"fn-1","status":"%s","tasks":[{"id":"fn-1.1","status":"done"}]}\\n' "$SPEC_STATUS"
'''

    def tail(self, fixture, *, update="0", status="open", project=PROJECT):
        self.stub("flowctl", self.FLOWCTL)
        repo = self.repo_on("fn73-fx-reused")
        return self.run_sh(["bash", "-c", self.TAIL + '\nprintf "UPDATE=%s" "$UPDATE_PR_NUMBER"'], cwd=repo,
                           REPO_ROOT=str(repo), FLOWCTL=str(self.bin / "flowctl"), SPEC_ID="fn-1", SPEC_STATUS=status,
                           DRY_RUN="0", UPDATE_MODE=update, AUTONOMOUS="0", HEAD_SHA="x", COMMITS_AHEAD="1",
                           PR_READ=str(HELPER), ORIGIN_PROJECT=project, GLAB_ANSWERS=answers(fixture))

    def flowctl_calls(self):
        return [line for line in self.calls.read_text(encoding="utf-8").splitlines() if line.startswith("flowctl")]

    def test_open_merge_request_without_update_stops_as_on_github(self):
        result = self.tail(recorded("mr-branch-all"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("branch already has an OPEN PR: http://localhost:8929/flownext/flownext/-/merge_requests/2", result.stderr)
        updated = self.tail(recorded("mr-branch-all"), update="1", status="done")
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.assertEqual(updated.stdout, "UPDATE=2")

    def test_failed_or_malformed_read_stops_before_close(self):
        malformed = self.derived("mr-branch-all", lambda rows: [{k: v for k, v in r.items() if k != "project_id"} for r in rows])
        for name, fixture, project in (("glab fails", recorded("mr-missing-project"), "flownext/missing"),
                                       ("malformed", malformed, PROJECT), ("empty output", self.blank("mr-branch-all", ""), PROJECT)):
            with self.subTest(name):
                self.calls.write_text("", encoding="utf-8")
                result = self.tail(fixture, project=project)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("NEEDS_HUMAN: cannot read the merge requests of this branch", result.stderr)
                self.assertEqual(self.flowctl_calls(), ["flowctl show fn-1 --json"])


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


class CreateScriptTests(GitLabShellCase):
    """make-pr-create.sh on GitLab: push, then create or update through the helper, never gh."""

    GIT = """#!/usr/bin/env bash
case "$1" in
  branch) echo "$BRANCH" ;;
  rev-parse) echo abc ;;
  push) echo "git push" >> "$STUB_CALLS" ;;
  *) exit 1 ;;
esac
"""
    FLOWCTL = """#!/usr/bin/env bash
case "$1 $2" in
  "sync active") printf '{"active": %s}\\n' "${TRK_ACTIVE:-false}" ;;
  "config get") printf '{"value": "%s"}\\n' "$TRK_TYPE" ;;
  "sync get-state") printf '{"tracker": {"identifier": "#5", "url": "%s"}}\\n' "$TRK_URL" ;;
esac
"""

    def setUp(self):
        super().setUp()
        for tool in ("sh", "grep", "tail"):
            (self.bin / tool).symlink_to(shutil.which(tool))
        (self.bin / "git").unlink()   # a symlink to the real git; never write through it
        self.stub("git", self.GIT)
        self.stub("flowctl", self.FLOWCTL)
        self.stub("sleep", "#!/usr/bin/env bash\n")

    def create(self, fixtures, branch="fn73-fx-create", **env):
        base = {"BRANCH": branch, "FLOWCTL": str(self.bin / "flowctl"), "PR_READ": str(HELPER), "FORGE": "gitlab",
                "OPEN_ITEMS_COUNT": "0", "DRAFT_FORCE": "auto", "UPDATE_MODE": "0", "BODY_FILE": str(self.body_file()),
                "BASE_REF": "origin/main", "PR_TITLE": "fn73 create probe", "REPO_ROOT": str(self.tmp),
                "PHASE0_CONTEXT": "{}", "SPEC_ID": "fn-1", "SCRIPT": str(CREATE), "GLAB_ANSWERS": answers(*fixtures)}
        return self.run_sh(["bash", "-c", 'set -e; source "$SCRIPT"; printf "RESULT=%s" "$PR_URL"'], **{**base, **env})

    def calls_of(self, prefix):
        return [line for line in self.calls.read_text(encoding="utf-8").splitlines() if line.startswith(prefix)]

    def test_create_pushes_then_opens_the_merge_request(self):
        for name, open_items, title, iid, branch in (("draft", "1", "Draft: fn73 create probe", 9, "fn73-fx-create"),
                                                     ("ready", "0", "fn73 create probe", 10, "fn73-fx-create-ready")):
            with self.subTest(name):
                self.calls.write_text("", encoding="utf-8")
                result = self.create([recorded(f"mr-create-{name}")], branch=branch, OPEN_ITEMS_COUNT=open_items)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"RESULT={MR_URL}{iid}")
                self.assertEqual(self.bodies()[-1]["title"], title)
                calls = self.calls.read_text(encoding="utf-8").splitlines()
                self.assertEqual([c.split()[0] for c in calls], ["git", "glab"])   # push first; no gh
                self.assertIn("--method POST", calls[1])

    def test_create_retries_only_gitlabs_missing_branch_answer(self):
        retried = self.create([recorded("mr-create-no-branch"), recorded("mr-create-ready")])
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(retried.stdout, f"RESULT={MR_URL}10")
        self.assertEqual(len(self.calls_of("glab api --method POST")), 2)
        self.calls.write_text("", encoding="utf-8")
        refused = self.blank("mr-create-no-branch", '{"message":{"target_branch":["does not exist"]}}')
        stopped = self.create([refused, recorded("mr-create-ready")])
        self.assertEqual(stopped.returncode, 1)
        self.assertIn("Error: PR create failed", stopped.stderr)
        self.assertEqual(len(self.calls_of("glab api --method POST")), 1)

    def test_update_replaces_the_description_and_ready_drops_the_draft(self):
        fixtures = [recorded("mr-branch-create"), recorded("mr-edit"), recorded("mr-view-draft"), recorded("mr-edit-ready")]
        for force, written in (("auto", {"description": BODY}), ("draft", {"description": BODY}),
                               ("ready", {"description": BODY, "title": "fn73 create probe"})):
            with self.subTest(force):
                self.calls.write_text("", encoding="utf-8")
                result = self.create(fixtures, UPDATE_MODE="1", DRAFT_FORCE=force, OPEN_ITEMS_COUNT="1")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"RESULT={MR_URL}9")
                self.assertEqual(self.bodies()[-1], written)
                self.assertEqual(self.calls_of("gh"), [])
                self.assertEqual(self.calls_of("glab api --method POST"), [])

    def test_tracker_reference_is_the_issue_url_on_the_other_forge(self):
        cases = [("github", "gitlab", "https://github.com/o/r/issues/5", "Ref https://github.com/o/r/issues/5"),
                 ("gitlab", "github", "http://localhost:8929/flownext/flownext/-/issues/5", "Ref http://localhost:8929/flownext/flownext/-/issues/5"),
                 ("github", "github", "https://github.com/o/r/issues/5", "Refs #5"),
                 ("gitlab", "gitlab", "http://localhost:8929/flownext/flownext/-/issues/5", "Ref `#5`")]
        for tracker, forge, url, ref in cases:
            with self.subTest(tracker=tracker, forge=forge):
                result = self.create([], FORGE=forge, PR_READ=str(HELPER) if forge == "gitlab" else "",
                                     FLOW_PR_CREATE_CMD="echo https://example.test/o/r/pull/7; :",
                                     TRK_ACTIVE="true", TRK_TYPE=tracker, TRK_URL=url)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.tmp / "body.md").read_text(encoding="utf-8").splitlines()[-1], ref)


if __name__ == "__main__":
    unittest.main()

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

from chain_fixture_support import git
from test_chain_consumer_fixtures import DETECT_OUT, MAKE_PR, ConsumerWorld, fence
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
            {"number": 4, "url": f"{PR_URL}4", "baseRefName": "main", "createdAt": "2026-11-13T10:37:47.056362+00:00", "state": "OPEN"},
            {"number": 3, "url": f"{PR_URL}3", "baseRefName": "main", "createdAt": "2026-11-13T10:37:44.899774+00:00", "state": "CLOSED"}])
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
            return lambda page: page["values"][1].pop(key)
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


class OriginBlockTests(BitbucketShellCase):
    """The origin block runs before any close or push (the `# end:block` seam, without flowctl)."""

    BLOCK = PREFLIGHT.read_text(encoding="utf-8").split("# end:block", 1)[0]
    REPORT = '\nprintf "FORGE=%s PR_READ=%s ORIGIN_PROJECT=%s" "$FORGE" "$PR_READ" "$ORIGIN_PROJECT"\n'

    def block(self, origin, *, report=True, dry_run="0", **env):
        repo = self.repo_on("main", origin)
        script = self.BLOCK + (self.REPORT if report else "")
        return self.run_sh(["bash", "-c", script], cwd=repo, REPO_ROOT=str(repo), DRY_RUN=dry_run,
                           FLOWCTL=str(SCRIPTS / "flowctl"), GITLAB_HOST="", ORIGIN_PROJECT="", **env)

    def test_bitbucket_origin_with_a_bkt_login_passes(self):
        for origin in (ORIGIN, "https://bitbucket.org/flownextnew/flownext.git",
                       "ssh://git@altssh.bitbucket.org:443/flownextnew/flownext.git"):
            with self.subTest(origin):
                result = self.block(origin, BKT_ANSWERS=answers(recorded("repo-read")))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"FORGE=bitbucket PR_READ={HELPER} ORIGIN_PROJECT={PROJECT}")
                self.assertEqual(self.calls_of("gh") + self.calls_of("glab"), [])

    def test_missing_or_logged_out_bkt_stops_naming_bkt_login(self):
        repo = ["bkt", "--context", "flownextnew", "api", "/repositories/flownextnew/flownext"]
        for name, env in (("missing", {}), ("logged out", {"BKT_ANSWERS": answers(self.derived("api-no-credentials", argv=repo))}),
                          ("no Cloud context", {"BKT_CONTEXTS": "context-list-none"})):
            with self.subTest(name):
                if name == "missing":
                    (self.bin / "bkt").rename(self.tmp / "bkt-away")
                result = self.block(ORIGIN, report=False, **env)
                if name == "missing":
                    (self.tmp / "bkt-away").rename(self.bin / "bkt")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("bkt auth login https://bitbucket.org --kind cloud", result.stderr)

    def test_dry_run_names_the_forge_without_stops_or_checks(self):
        result = self.block(ORIGIN, dry_run="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"FORGE=bitbucket PR_READ={HELPER} ORIGIN_PROJECT={PROJECT}")
        self.assertEqual(self.calls_of("bkt"), [])   # no login read on a preview
        (self.bin / "bkt").unlink()
        missing = self.block(ORIGIN, dry_run="1")
        self.assertEqual((missing.returncode, missing.stdout), (0, "FORGE=bitbucket PR_READ= ORIGIN_PROJECT="))

    def test_shell_and_python_forge_rules_agree(self):
        # (name, origin, ssh aliases)
        cases = [
            ("https", "https://bitbucket.org/flownextnew/flownext.git", {}),
            ("https with user", "https://flownextnew-admin@bitbucket.org/flownextnew/flownext.git", {}),
            ("scp clone link", ORIGIN, {}),
            ("scp on bitbucket.org", "git@bitbucket.org:flownextnew/flownext.git", {}),
            ("ssh over 443", "ssh://git@altssh.bitbucket.org:443/flownextnew/flownext.git", {}),
            ("ssh alias", "git@bb-work:flownextnew/flownext.git", {"bb-work": "ssh.bitbucket.org"}),
            ("self-hosted Bitbucket", "https://bitbucket.corp.test/scm/proj/repo.git", {}),
            ("github", "https://github.com/o/r.git", {}),
        ]
        clean = {key: "" for key in ("CI_SERVER_HOST", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GITLAB_HOST")}
        trap = "trap 'printf \"FORGE=%s HOST=%s\" \"$FORGE\" \"$ORIGIN_HOST\" > \"$OUT\"' EXIT\n"
        for name, origin, ssh in cases:
            with self.subTest(name):
                f.repo_forge.cache_clear()
                fake = BktCli(origin, ssh=ssh, glab_hosts=())
                with patch.object(f.subprocess, "run", side_effect=fake), patch.dict(os.environ, clean):
                    python = f.repo_forge(str(self.tmp))
                repo = self.repo_on("main", origin)
                out = self.tmp / "out"
                self.run_sh(["bash", "-c", trap + self.BLOCK], cwd=repo, REPO_ROOT=str(repo), DRY_RUN="0", OUT=str(out),
                            FLOWCTL=str(SCRIPTS / "flowctl"), SSH_ALIASES=" ".join(f"{k}={v}" for k, v in ssh.items()),
                            BKT_ANSWERS=answers(recorded("repo-read")), **clean)
                shell = dict(part.split("=", 1) for part in out.read_text(encoding="utf-8").split(" "))
                self.assertEqual((shell["FORGE"] or None, shell["HOST"] or None), (python.forge, python.host))
        f.repo_forge.cache_clear()


class BitbucketChainDetectTests(BitbucketShellCase):
    """R4: a dependent spec's base on Bitbucket, through the shared chain-detect fence."""

    def setUp(self):
        super().setUp()
        (self.tmp / "world").mkdir()
        self.w = ConsumerWorld(self.tmp / "world")
        shutil.copy(self.bin / "bkt", self.w.bin / "bkt")

    def detect(self, child, fixture):
        env = {"REPO_ROOT": str(self.w.work), "FLOWCTL": str(self.w.bin / "flowctl"), "SPEC_ID": child, "BASE_REF": "",
               "DRY_RUN": "0", "AUTONOMOUS": "0", "FORGE": "bitbucket", "PR_READ": str(HELPER), "PR_HEAD_REFS": "",
               "STUB_CALLS": str(self.calls), "ORIGIN_PROJECT": PROJECT, "BKT_ANSWERS": answers(fixture)}
        script = "export STUB_CALLS ORIGIN_PROJECT BKT_ANSWERS\n" + fence(MAKE_PR / "workflow.md", "chain-detect")
        return self.w.run_rc(script, env, DETECT_OUT, cwd=self.w.work)

    def chain(self, parent_branch):
        a_tip = self.w.branch(parent_branch, "main", [("a.txt", "a\n")])
        self.w.branch("B", parent_branch, [("b.txt", "b\n")])
        parent = self.w.spec("parent", parent_branch)
        return parent, self.w.spec("child", "B", deps=[parent]), a_tip

    def test_open_parent_pull_request_targets_the_parent_branch(self):
        parent, child, a_tip = self.chain("fx-reused")
        rc, got = self.detect(child, recorded("pr-branch-reused"))
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["CHAIN_PARENT"], got["CHAIN_BOUNDARY"], got["PARENT_PR"], got["PARENT_PR_STATE"]),
                         ("origin/fx-reused", parent, a_tip, "4", "OPEN"))

    def test_merged_parent_targets_the_default_branch(self):
        parent, child, a_tip = self.chain("fx-merged")
        self.w.squash_merge("fx-merged")
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.detect(child, recorded("pr-branch-merged"))
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["CHAIN_BOUNDARY"], got["CHAIN_REWRITE"], got["PARENT_PR"], got["PARENT_PR_STATE"]),
                         ("origin/main", a_tip, "1", "5", "MERGED"))

    def test_unreadable_parent_pull_request_stops_needs_human(self):
        parent, child, _ = self.chain("fx-reused")
        for name, fixture in (("bkt fails", self.derived("pr-branch-missing-repo", argv=branch_argv("fx-reused"))),
                              ("empty output", self.derived("pr-branch-reused", stdout=""))):
            with self.subTest(name):
                rc, got = self.detect(child, fixture)
                self.assertEqual(rc, 2, got["_stderr"])
                self.assertIn(f"NEEDS_HUMAN: cannot read the PR state of parent {parent} (fx-reused)", got["_stderr"])


class ExistingPullRequestTests(BitbucketShellCase):
    """The existing-PR check on Bitbucket, run from §0.5 to the end so a wrong "no PR" would close the spec."""

    TAIL = "set -e\n# --- §0.5:" + PREFLIGHT.read_text(encoding="utf-8").split("# --- §0.5:", 1)[1]
    FLOWCTL = '''#!/usr/bin/env bash
printf 'flowctl %s\\n' "$*" >> "$STUB_CALLS"
[[ "$1" == show ]] && printf '{"id":"fn-1","status":"%s","tasks":[{"id":"fn-1.1","status":"done"}]}\\n' "$SPEC_STATUS"
'''

    def tail(self, fixture, *, update="0", status="open"):
        self.stub("flowctl", self.FLOWCTL)
        repo = self.repo_on("fx-reused")
        return self.run_sh(["bash", "-c", self.TAIL + '\nprintf "UPDATE=%s" "$UPDATE_PR_NUMBER"'], cwd=repo,
                           REPO_ROOT=str(repo), FLOWCTL=str(self.bin / "flowctl"), SPEC_ID="fn-1", SPEC_STATUS=status,
                           DRY_RUN="0", UPDATE_MODE=update, AUTONOMOUS="0", HEAD_SHA="x", COMMITS_AHEAD="1",
                           PR_READ=str(HELPER), BKT_ANSWERS=answers(fixture))

    def test_open_pull_request_without_update_stops_as_on_github(self):
        result = self.tail(recorded("pr-branch-reused"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f"branch already has an OPEN PR: {PR_URL}4", result.stderr)
        updated = self.tail(recorded("pr-branch-reused"), update="1", status="done")
        self.assertEqual((updated.returncode, updated.stdout), (0, "UPDATE=4"), updated.stderr)

    def test_failed_or_malformed_read_stops_before_close(self):
        for name, fixture in (("bkt fails", self.derived("pr-branch-missing-repo", argv=branch_argv("fx-reused"))),
                              ("malformed", self.derived("pr-branch-reused", lambda page: [r.pop("destination") for r in page["values"]] and None)),
                              ("empty output", self.derived("pr-branch-reused", stdout=""))):
            with self.subTest(name):
                self.calls.write_text("", encoding="utf-8")
                result = self.tail(fixture)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("NEEDS_HUMAN: cannot read the merge requests of this branch", result.stderr)
                self.assertEqual(self.calls_of("flowctl"), ["flowctl show fn-1 --json"])


class NoSpecTests(BitbucketShellCase):
    def test_no_spec_exit_prints_the_forge_values_the_no_spec_path_needs(self):
        self.stub("flowctl", '#!/usr/bin/env bash\nprintf \'{"success":true,"spec_ids":[]}\\n\'\n')
        (self.bin / "make-pr-bitbucket.sh").symlink_to(HELPER)
        repo = self.repo_on("main", ORIGIN)
        result = self.run_sh(["bash", "-c", 'source "$SCRIPT"'], cwd=repo, SCRIPT=str(PREFLIGHT), REPO_ROOT=str(repo),
                             DRY_RUN="0", FLOWCTL=str(self.bin / "flowctl"), SPEC_ID="", BASE_REF="", UPDATE_MODE="0",
                             AUTONOMOUS="1", ORIGIN_PROJECT="", BKT_ANSWERS=answers(recorded("repo-read")))
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0],
                         f"FORGE=bitbucket PR_READ={self.bin / 'make-pr-bitbucket.sh'} GITLAB_HOST='' ORIGIN_PROJECT={PROJECT}")
        self.assertEqual(result.stdout.splitlines()[-1], "NO_SPEC")


class HelperWriteTests(BitbucketShellCase):
    """`pr create` and `pr edit`: the request body bkt sends, and the URL printed."""

    def test_create_sends_the_body_and_prints_the_url(self):
        body = self.body_file()
        for draft, name, branch, number in ((True, "pr-create-draft", "fx-draft", 2), (False, "pr-create-ready", "fx-open", 1)):
            with self.subTest(name):
                result = self.run_sh([str(HELPER), "pr", "create", "--title", "t", "--body-file", str(body),
                                      *(["--draft"] if draft else []), "--base", "main", "--head", branch],
                                     BKT_ANSWERS=answers(recorded(name)))
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

    def test_refused_create_prints_bitbuckets_answer(self):
        result = self.run_sh([str(HELPER), "pr", "create", "--title", "t", "--body-file", str(self.body_file()),
                              "--base", "main", "--head", "fx-not-pushed"], BKT_ANSWERS=answers(recorded("pr-create-no-branch")))
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertIn("source: branch not found: fx-not-pushed", result.stderr)


class CreateScriptTests(BitbucketShellCase):
    """make-pr-create.sh on Bitbucket: push, then create or update through the helper, never gh."""

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
  "sync active") printf '{"active": false}\\n' ;;
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

    def create(self, fixtures, branch="fx-open", **env):
        base = {"BRANCH": branch, "FLOWCTL": str(self.bin / "flowctl"), "PR_READ": str(HELPER), "FORGE": "bitbucket",
                "OPEN_ITEMS_COUNT": "0", "DRAFT_FORCE": "auto", "UPDATE_MODE": "0", "BODY_FILE": str(self.body_file()),
                "BASE_REF": "origin/main", "PR_TITLE": "fixture title", "REPO_ROOT": str(self.tmp),
                "PHASE0_CONTEXT": "{}", "SPEC_ID": "fn-1", "SCRIPT": str(CREATE), "BKT_ANSWERS": answers(*fixtures)}
        return self.run_sh(["bash", "-c", 'set -e; source "$SCRIPT"; printf "RESULT=%s" "$PR_URL"'], **{**base, **env})

    def test_create_pushes_then_opens_the_pull_request(self):
        for name, open_items, number, branch in (("draft", "1", 2, "fx-draft"), ("ready", "0", 1, "fx-open")):
            with self.subTest(name):
                self.calls.write_text("", encoding="utf-8")
                result = self.create([recorded(f"pr-create-{name}")], branch=branch, OPEN_ITEMS_COUNT=open_items)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"RESULT={PR_URL}{number}")
                self.assertEqual(self.bodies()[-1].get("draft"), True if name == "draft" else None)
                calls = [c for c in self.calls.read_text(encoding="utf-8").splitlines() if not c.startswith("bkt context")]
                self.assertEqual([c.split()[0] for c in calls], ["git", "bkt"])   # push first; no gh
                self.assertIn("-X POST", calls[1])

    def test_create_retries_only_bitbuckets_missing_branch_answer(self):
        retried = self.create([recorded("pr-create-no-branch"), recorded("pr-create-ready")], branch="fx-not-pushed")
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(retried.stdout, f"RESULT={PR_URL}1")
        self.assertEqual(len(self.calls_of("bkt --context flownextnew api /repositories/flownextnew/flownext/pullrequests -X POST")), 2)
        self.calls.write_text("", encoding="utf-8")
        other = self.derived("pr-create-no-branch", stderr="Error: 400 Bad Request: destination: branch not found: main\n")
        stopped = self.create([other, recorded("pr-create-ready")], branch="fx-not-pushed")
        self.assertEqual(stopped.returncode, 1)
        self.assertIn("Error: PR create failed", stopped.stderr)
        self.assertEqual(len(self.calls_of("bkt --context flownextnew api /repositories/flownextnew/flownext/pullrequests -X POST")), 1)

    def test_update_replaces_the_description_and_ready_marks_the_draft_ready(self):
        for force, written in (("auto", {"description": BODY}), ("ready", {"description": BODY, "draft": False})):
            with self.subTest(force):
                self.calls.write_text("", encoding="utf-8")
                Path(f"{self.calls}.used").unlink(missing_ok=True)
                answer = recorded("pr-edit-ready" if force == "ready" else "pr-edit-description")
                result = self.create([recorded("pr-branch-edit"), answer], branch="fx-edit", UPDATE_MODE="1", DRAFT_FORCE=force)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"RESULT={PR_URL}6")
                self.assertIn("Updated PR #6 description", result.stderr)
                self.assertEqual(self.bodies()[-1], written)
                self.assertEqual(self.calls_of("gh"), [])
                self.assertEqual([c for c in self.calls_of("bkt") if "-X POST" in c], [])

    def test_update_read_failure_is_never_no_open_pull_request(self):
        result = self.create([self.derived("pr-branch-edit", stdout="")], branch="fx-edit", UPDATE_MODE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read the open merge request", result.stderr)
        self.assertNotIn("no open PR", result.stderr)


if __name__ == "__main__":
    unittest.main()
